"""v3 evaluation (AMENDMENT-2): arms A, B-native, B-lean, C on in-template and out-of-template tests.

Imports the recipe at the frozen snapshot named in provenance.json (PYTHONPATH). Nothing here edits
the recipe or changes any earlier arm. Predicted commands execute only against the fake reference
tools (`commands.execute`), exactly as in v2.
"""

from __future__ import annotations

import asyncio
import json
import re
import shlex
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from tinker_cookbook import renderers
from tinker_cookbook.recipes.trained_tools.commands import TOOLS, command_parts, execute
from tinker_cookbook.recipes.trained_tools.data import SYSTEM, load_samples, make_renderer
from tinker_cookbook.recipes.trained_tools.prompts import (
    CHEAT_SHEET,
    FIXTURE_INSTRUCTION,
    SCHEMAS,
    TRANSPORT,
)

MAX_TURNS = 4
MAX_PROMPT = 4096
MODEL_NAME = "thinkingmachines/Inkling-2-Mini"
ARMS_IN = ("A", "B-native", "B-lean", "C")
ARMS_OOD = ("A", "B-native", "C")
# Follow-up run (AMENDMENT-2 addendum): B-native plus one sentence asking for a single call per turn.
ARMS_FOLLOWUP = ("B-native-1call",)
ONE_CALL = "Call one command per turn."
NAME_RE = re.compile(r"\b(" + "|".join(TOOLS) + r")\b")
PARAM_NOTE = "The one text argument, passed unchanged; -h shows usage instead."


@dataclass
class Item:
    id: str
    skill: str
    request: str
    expected: list[str]  # command names in order, [] when no tool is needed
    split: str  # "in" or "ood"


def items_in_template(path: Path) -> list[Item]:
    return [
        Item(
            s.id,
            s.skill,
            s.messages[1].content,
            [command_parts(c)[0] for c in s.commands],
            "in",
        )
        for s in load_samples(path)
    ]


def items_ood(path: Path) -> list[Item]:
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    return [Item(r["id"], r["skill"], r["request"], r["expected"], "ood") for r in rows]


# ---------------------------------------------------------------- prompts


def lean_schemas() -> list[dict[str, Any]]:
    """The v2 B schemas with only the repeated ~90-word description paragraph removed."""
    lean = json.loads(json.dumps(SCHEMAS))
    for schema in lean:
        fn = schema["function"]
        fn["description"] = TOOLS[fn["name"]]
    return lean


def native_specs() -> list[renderers.ToolSpec]:
    """Eight one-argument tools for `create_conversation_prefix_with_tools`; no boilerplate."""
    return [
        renderers.ToolSpec(
            name=name,
            description=description,
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string", "description": PARAM_NOTE}},
                "required": ["text"],
            },
        )
        for name, description in TOOLS.items()
    ]


def arm_messages(request: str, arm: str, renderer: Any) -> list[renderers.Message]:
    system = SYSTEM + " " + FIXTURE_INSTRUCTION
    user = renderers.Message(role="user", content=request)
    if arm in ("B-native", "B-native-1call"):
        if arm == "B-native-1call":
            system += " " + ONE_CALL
        return [*renderer.create_conversation_prefix_with_tools(native_specs(), system), user]
    if arm == "B-lean":
        system += "\nAvailable tool transport and command schemas:\n" + json.dumps(
            [TRANSPORT, *lean_schemas()], indent=2
        )
    elif arm == "C":
        system += "\nAvailable tool transport:\n" + json.dumps([TRANSPORT], indent=2)
        system += "\n" + CHEAT_SHEET
    elif arm != "A":
        raise ValueError(f"Unknown arm {arm}")
    return [renderers.Message(role="system", content=system), user]


# ---------------------------------------------------------------- parsing


def extract_command(message: renderers.Message) -> str | None:
    """bash transport or a native call to one of the eight commands; anything else raises."""
    if message.get("unparsed_tool_calls"):
        raise ValueError("unparsed call")
    calls = message.get("tool_calls", [])
    if not calls:
        return None
    if len(calls) != 1:
        raise ValueError("expected exactly one call")
    name = calls[0].function.name
    args = json.loads(calls[0].function.arguments)
    if not isinstance(args, dict):
        raise ValueError("arguments are not an object")
    native = name.removeprefix("functions.")
    if native in TOOLS:
        if len(args) != 1 or not isinstance(next(iter(args.values())), str):
            raise ValueError("expected one text argument")
        argument = next(iter(args.values()))
        if not argument:
            raise ValueError("empty argument")
        return shlex.join([native, argument])
    if name != "bash" or set(args) != {"command"} or not isinstance(args["command"], str):
        raise ValueError("expected bash command string or a known command")
    return args["command"]


def command_name(command: str) -> str:
    try:
        parts = shlex.split(command)
    except ValueError:
        return "INVALID"
    return parts[0] if parts else "INVALID"


def raw_text(message: renderers.Message) -> str:
    content = message["content"]
    return content if isinstance(content, str) else json.dumps(message, default=str)


def has_call_marker(message: renderers.Message) -> bool:
    return bool(message.get("tool_calls") or message.get("unparsed_tool_calls")) or (
        "content_invoke_tool" in raw_text(message)
    )


def intended_name(message: renderers.Message) -> str | None:
    """Best-effort command a malformed first turn was reaching for (heuristic, see RESULTS)."""
    raw = raw_text(message)
    marker = raw.find("content_invoke_tool")
    if marker < 0:
        return None
    start = max(0, raw.rfind("<|message_model|>", 0, marker))
    found = NAME_RE.search(raw[start : marker + 400])
    return found.group(1) if found else None


def classify(message: renderers.Message, clean: bool, truncated: bool) -> dict[str, Any]:
    """kind: call | final | malformed | truncated | invalid."""
    if truncated:
        return {"kind": "truncated", "command": None}
    if not clean or message.get("unparsed_tool_calls"):
        return {"kind": "malformed", "command": None}
    try:
        command = extract_command(message)
    except (ValueError, TypeError, json.JSONDecodeError):
        return {"kind": "invalid", "command": None}
    if command is None:
        return {"kind": "final", "command": None}
    return {"kind": "call", "command": command}


# ---------------------------------------------------------------- episode


async def run_episode(
    item: Item,
    arm: str,
    client: Any,
    renderer: Any,
    tinker_mod: Any,
    sem: asyncio.Semaphore,
    max_tokens: int = 512,
) -> dict[str, Any]:
    messages = arm_messages(item.request, arm, renderer)
    commands: list[str] = []
    valid: list[bool] = []
    turns: list[dict[str, Any]] = []
    end, clean_final = "turns_exhausted", False
    with TemporaryDirectory(prefix="tools-v3-") as tmp:
        for _ in range(MAX_TURNS):
            prompt = renderer.build_generation_prompt(messages, effort=0.0)
            if prompt.length > MAX_PROMPT:
                end = "prompt_over_limit"
                break
            async with sem:
                response = await client.sample_async(
                    prompt=prompt,
                    num_samples=1,
                    sampling_params=tinker_mod.SamplingParams(
                        max_tokens=max_tokens,
                        temperature=1.0,
                        stop=renderer.get_stop_sequences(),
                    ),
                )
            seq = response.sequences[0]
            actual, termination = renderer.parse_response(seq.tokens)
            truncated = not termination.is_clean and len(seq.tokens) >= max_tokens
            verdict = classify(actual, termination.is_clean, truncated)
            turn = {
                "prompt_tokens": prompt.length,
                "completion_tokens": len(seq.tokens),
                "response": actual,
                "termination": termination.value,
                "kind": verdict["kind"],
                "attempt": verdict["kind"] in ("call", "invalid")
                or (verdict["kind"] in ("malformed", "truncated") and has_call_marker(actual)),
                "native": False,
                "intended": intended_name(actual) if verdict["kind"] == "malformed" else None,
            }
            turns.append(turn)
            messages.append(actual)
            if verdict["kind"] in ("malformed", "truncated", "invalid"):
                end = verdict["kind"]
                break
            if verdict["kind"] == "final":
                end, clean_final = "answered", True
                break
            command = verdict["command"]
            turn["native"] = actual["tool_calls"][0].function.name != "bash"
            commands.append(command)
            try:
                result = await asyncio.to_thread(execute, command, Path(tmp) / "memory")
                valid.append(True)
            except (ValueError, OSError, subprocess.SubprocessError):
                result = "ERROR: invalid command or argument"
                valid.append(False)
            call = actual["tool_calls"][0]
            call_id = call.id or f"call_{len(commands)}"
            actual["tool_calls"] = [call.model_copy(update={"id": call_id})]
            messages.append(
                renderers.Message(
                    role="tool", name=call.function.name, tool_call_id=call_id, content=result
                )
            )
    return {
        "id": item.id,
        "split": item.split,
        "skill": item.skill,
        "arm": arm,
        "request": item.request,
        "expected": item.expected,
        "commands": commands,
        "valid": valid,
        "end": end,
        "clean_final": clean_final,
        "turns": turns,
        "messages": messages,
    }


def greedy_match(observed: list[str], expected: list[str]) -> int:
    matched = 0
    for name in observed:
        if matched < len(expected) and name == expected[matched]:
            matched += 1
    return matched


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    expected = record["expected"]
    observed = [command_name(c) for c in record["commands"]]
    needed = bool(expected)
    first = record["turns"][0] if record["turns"] else None
    first_malformed = bool(first and first["kind"] == "malformed")
    attempts = sum(1 for t in record["turns"] if t["attempt"])
    ok_calls = sum(1 for t in record["turns"] if t["kind"] == "call")
    return {
        "needed": needed,
        "first_command_right": needed and bool(observed) and observed[0] == expected[0],
        "first_turn_malformed": needed and first_malformed,
        "first_malformed_intended_right": needed
        and first_malformed
        and first is not None
        and first["intended"] == expected[0],
        "first_turn_other_failure": needed
        and bool(first)
        and first["kind"] in ("invalid", "truncated"),
        "exact_sequence": needed and record["clean_final"] and observed == expected,
        "extra_calls": len(observed) - greedy_match(observed, expected),
        "no_tool_ok": (not needed) and record["clean_final"] and not observed,
        "call_attempts": attempts,
        "call_ok": ok_calls,
        "malformed_turns": sum(1 for t in record["turns"] if t["kind"] == "malformed"),
        "prompt_tokens": sum(t["prompt_tokens"] for t in record["turns"]),
        "completion_tokens": sum(t["completion_tokens"] for t in record["turns"]),
        "turns": len(record["turns"]),
    }


def provenance_item(item: Item) -> dict[str, Any]:
    return asdict(item)
