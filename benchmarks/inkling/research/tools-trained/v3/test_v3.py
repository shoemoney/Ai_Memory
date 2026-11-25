"""Offline tests for the v3 evaluation. Run with the recipe worktree's python:

    PYTHONPATH=<recipe snapshot>:. .venv/bin/python -m pytest -q v3/test_v3.py
"""

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import ood  # noqa: E402
import tools_v3 as t  # noqa: E402

from tinker_cookbook.recipes.trained_tools import prepare  # noqa: E402
from tinker_cookbook.recipes.trained_tools.commands import TOOLS  # noqa: E402
from tinker_cookbook.recipes.trained_tools.data import make_renderer  # noqa: E402
from tinker_cookbook.recipes.trained_tools.prompts import SCHEMAS  # noqa: E402

# Head verbs and wrapper words the training curriculum uses; none may appear in an OOD request.
TRAIN_WORDS = {
    "find", "look", "locate", "create", "draw", "get", "consult", "read", "fetch", "calculate",
    "calculator", "evaluate", "save", "store", "retrieve", "repeat", "capitalize", "reverse",
    "check", "ask", "please", "could", "task",
}
PLACEHOLDERS = [
    (re.compile(r"cobalt garden \d+"), " ARG "),
    (re.compile(r"fern\d+"), " ARG "),
    (re.compile(r"https://example\.org/archive/\d+"), " ARG "),
    (re.compile(r"\(\d+ \* 7 \+ 23\) / 2"), " ARG "),
    (re.compile(r"\{[a-z]\}"), " ARG "),
]


def words(text: str) -> list[str]:
    for pattern, repl in PLACEHOLDERS:
        text = pattern.sub(repl, text)
    return re.findall(r"[a-z0-9]+", text.lower().replace("'", ""))


def ngrams(tokens: list[str], n: int = 3) -> set[tuple[str, ...]]:
    return {tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)}


@pytest.fixture(scope="module")
def training_requests(tmp_path_factory) -> list[str]:
    out = tmp_path_factory.mktemp("train")
    prepare.build(out, counts=(400, 40, 40))
    rows = [json.loads(line) for line in (out / "train.jsonl").read_text().splitlines()]
    return [r["messages"][1]["content"] for r in rows]


@pytest.fixture(scope="module")
def rows() -> list[dict]:
    return ood.build()


def test_set_shape(rows):
    needed = [r for r in rows if r["expected"]]
    assert len(rows) == 100 and len(needed) == 70 and len(rows) - len(needed) == 30
    assert sum(len(r["expected"]) == 2 for r in rows) >= 15
    assert {n for r in needed for n in r["expected"]} == set(TOOLS)
    assert {n for r in needed if len(r["expected"]) == 1 for n in r["expected"]} == set(TOOLS)
    assert len({r["id"] for r in rows}) == 100 and len({r["family"] for r in rows}) == 100
    assert len({r["request"] for r in rows}) == 100


def test_zero_phrase_family_overlap_with_training(rows, training_requests):
    train_frames = {" ".join(words(r)) for r in training_requests}
    train_grams = set().union(*(ngrams(words(r)) for r in training_requests))
    assert len(train_frames) > 20  # real frames were extracted
    problems = []
    for row in rows:
        frame = words(row["template"])
        if " ".join(frame) in train_frames:
            problems.append((row["id"], "identical frame"))
        if ngrams(frame) & train_grams:
            problems.append((row["id"], sorted(ngrams(frame) & train_grams)))
        if set(frame) & TRAIN_WORDS:
            problems.append((row["id"], sorted(set(frame) & TRAIN_WORDS)))
        if row["request"] in set(training_requests):
            problems.append((row["id"], "identical request"))
    assert not problems, problems


def test_ood_file_matches_generator(rows):
    path = Path(__file__).parent / "data" / "ood.jsonl"
    assert [json.loads(line) for line in path.read_text().splitlines()] == rows


def test_lean_schemas_drop_only_the_paragraph():
    lean = t.lean_schemas()
    assert len(lean) == 8
    for full, short in zip(SCHEMAS, lean, strict=True):
        assert short["function"]["description"] == TOOLS[full["function"]["name"]]
        assert short["function"]["parameters"] == full["function"]["parameters"]
    assert "Takes exactly one positional text argument" not in json.dumps(lean)


def test_arm_prompts():
    renderer = make_renderer(t.MODEL_NAME)
    request = "Open https://example.org/x and tell me what's on it."
    a = t.arm_messages(request, "A", renderer)
    assert all(name not in a[0]["content"] for name in TOOLS)
    native = t.arm_messages(request, "B-native", renderer)
    declare = [m for m in native if m["role"] == "tool_declare"]
    assert len(declare) == 1
    assert {s["function"]["name"] for s in json.loads(declare[0]["content"])} == set(TOOLS)
    lean = t.arm_messages(request, "B-lean", renderer)[0]["content"]
    assert "Takes exactly one positional text argument" not in lean and "web_search" in lean
    sizes = {
        arm: renderer.build_generation_prompt(t.arm_messages(request, arm, renderer), effort=0.0).length
        for arm in ("A", "B-native", "B-lean", "C")
    }
    assert sizes["A"] < sizes["C"] < sizes["B-native"] < sizes["B-lean"]


def test_command_name_and_intended():
    assert t.command_name("web_search 'a b'") == "web_search"
    assert t.command_name("web_search 'unterminated") == "INVALID"
    msg = {
        "role": "assistant",
        "content": "<|message_model|><|content_thinking|>use remember maybe<|end_message|>"
        '<|message_model|>bash<|content_invoke_tool_json|>{"name"""bash","args":{"command":"calc \'1+1\'"}}',
    }
    assert t.intended_name(msg) == "calc"  # thinking text before the call is ignored
    assert t.has_call_marker(msg)
    assert t.intended_name({"role": "assistant", "content": "plain answer"}) is None


def test_classify_and_score():
    assert t.classify({"role": "assistant", "content": "hi"}, True, False)["kind"] == "final"
    assert t.classify({"role": "assistant", "content": "x"}, False, False)["kind"] == "malformed"
    assert t.classify({"role": "assistant", "content": "x"}, False, True)["kind"] == "truncated"
    turn = lambda kind, attempt, intended=None: {  # noqa: E731
        "kind": kind, "attempt": attempt, "intended": intended, "prompt_tokens": 10, "completion_tokens": 5,
    }
    base = {"expected": ["calc"], "commands": [], "clean_final": False}
    bad = t.score_record({**base, "turns": [turn("malformed", True, "calc")]})
    assert bad["first_turn_malformed"] and bad["first_malformed_intended_right"]
    assert not bad["first_command_right"] and bad["call_attempts"] == 1 and bad["call_ok"] == 0
    good = t.score_record(
        {**base, "commands": ["calc '1+1'"], "clean_final": True, "turns": [turn("call", True), turn("final", False)]}
    )
    assert good["first_command_right"] and good["exact_sequence"] and good["extra_calls"] == 0
    extra = t.score_record(
        {**base, "commands": ["calc '1+1'", "calc '2'"], "clean_final": True, "turns": [turn("call", True)] * 2}
    )
    assert extra["extra_calls"] == 1 and not extra["exact_sequence"]
    direct = t.score_record({"expected": [], "commands": [], "clean_final": True, "turns": [turn("final", False)]})
    assert direct["no_tool_ok"]


# ---------------------------------------------------------------- closed loop with a replay client

import asyncio  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import report_v3  # noqa: E402
import tinker  # noqa: E402
from tinker_cookbook import renderers  # noqa: E402
from tinker_cookbook.recipes.trained_tools.commands import execute  # noqa: E402


class Replay:
    """Returns the tokens of pre-rendered assistant turns, after checking the prompt matches."""

    def __init__(self, renderer, conversation, start):
        self.renderer, self.conversation, self.i = renderer, conversation, start

    async def sample_async(self, *, prompt, **kwargs):
        target, _ = self.renderer.build_supervised_example(self.conversation[: self.i + 1], effort=0.0)
        expected = self.renderer.build_generation_prompt(self.conversation[: self.i], effort=0.0)
        assert prompt.to_ints() == expected.to_ints()
        self.i += 2
        return SimpleNamespace(sequences=[SimpleNamespace(tokens=target.to_ints()[prompt.length :])])


def test_native_arm_closed_loop(tmp_path):
    renderer = make_renderer(t.MODEL_NAME)
    item = t.Item("x", "web_search", "Dig up an online source on tides.", ["web_search"], "ood")
    result = execute("web_search tides", tmp_path / "memory")
    conv = t.arm_messages(item.request, "B-native", renderer)
    conv += [
        renderers.Message(
            role="assistant",
            content="",
            tool_calls=[
                renderers.ToolCall(
                    id="c1",
                    function=renderers.ToolCall.FunctionBody(
                        name="web_search", arguments=json.dumps({"text": "tides"})
                    ),
                )
            ],
        ),
        renderers.Message(role="tool", name="web_search", tool_call_id="c1", content=result),
        renderers.Message(role="assistant", content=result),
    ]
    rec = asyncio.run(
        t.run_episode(item, "B-native", Replay(renderer, conv, 3), renderer, tinker, asyncio.Semaphore(2))
    )
    s = t.score_record(rec)
    assert rec["end"] == "answered" and rec["commands"] == ["web_search tides"]
    assert s["first_command_right"] and s["exact_sequence"] and s["call_ok"] == 1 == s["call_attempts"]
    assert rec["turns"][0]["native"] is True


def test_garbled_native_json_is_malformed_with_intended_command():
    renderer = make_renderer(t.MODEL_NAME)
    garbled = (
        "<|message_model|><|content_thinking|>Need remember.<|end_message|>"
        "<|message_model|>bash<|content_invoke_tool_json|>"
        '{"name"""bash","args":{"command":"remember \'x\'"}}<|end_message|><|content_model_end_sampling|>'
    )
    message, termination = renderer.parse_response(renderer.tokenizer.encode(garbled, add_special_tokens=False))
    verdict = t.classify(message, termination.is_clean, False)
    assert verdict["kind"] == "malformed"
    assert t.intended_name(message) == "remember"


def test_paired_bootstrap_is_seeded_and_signed():
    a, b = [True] * 90 + [False] * 10, [True] * 70 + [False] * 30
    first = report_v3.paired_bootstrap(a, b)
    assert first == report_v3.paired_bootstrap(a, b)
    assert first["diff_pp"] == pytest.approx(20.0) and first["lo"] < 20.0 < first["hi"] and first["lo"] > 0


def test_followup_arm_differs_only_by_one_sentence():
    renderer = make_renderer(t.MODEL_NAME)
    base = t.arm_messages("Hello", "B-native", renderer)
    one = t.arm_messages("Hello", "B-native-1call", renderer)
    assert [m for m in base if m["role"] == "tool_declare"] == [m for m in one if m["role"] == "tool_declare"]
    assert one[0]["content"] == base[0]["content"] + " " + t.ONE_CALL
