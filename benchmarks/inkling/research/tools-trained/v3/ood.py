"""Out-of-template test set: 100 hand-authored requests (70 need a tool, 30 do not).

Every request comes from its own template. No template reuses a training wrapper, a training
intent phrase or a training head verb (see test_v3.py, which proves it against the generated
training file). Arguments are natural phrases, not the training `cobalt garden N` pattern.
Expected values are the command-name sequences only; arguments are free.
"""

from __future__ import annotations

# (expected command names, template, arguments)
SINGLE = [
    # web_search (7)
    (["web_search"], "What's a good site for learning about {a}? One link is enough.", {"a": "lighthouse keepers in Maine"}),
    (["web_search"], "Dig up an online source on {a}.", {"a": "how sourdough starters work"}),
    (["web_search"], "A friend mentioned {a}; surface a URL that covers it.", {"a": "the Voyager golden record"}),
    (["web_search"], "Hunt down a webpage that explains {a}.", {"a": "tidal power in Scotland"}),
    (["web_search"], "I want a link, any decent one, for {a}.", {"a": "beginner bouldering routes"}),
    (["web_search"], "Go online and pull one article regarding {a}.", {"a": "the history of the metric system"}),
    (["web_search"], "Where on the internet is {a} discussed? Give me the address of one such place.", {"a": "monarch butterfly migration"}),
    # image_search (6)
    (["image_search"], "Show me a snapshot someone already took of {a}.", {"a": "a red fox in snow"}),
    (["image_search"], "I'm after an existing photograph depicting {a}; give me its link.", {"a": "a street market in Marrakech"}),
    (["image_search"], "Pull up a ready-made picture featuring {a}.", {"a": "a vintage typewriter"}),
    (["image_search"], "Which stock image shows {a}? Send me one address.", {"a": "a foggy pine forest"}),
    (["image_search"], "Source a photo, already online, of {a}.", {"a": "a hot air balloon at sunrise"}),
    (["image_search"], "Is there a picture out there of {a}? Link me to it.", {"a": "a snow leopard on a ridge"}),
    # image_gen (7)
    (["image_gen"], "Make me an artwork showing {a}.", {"a": "a robot gardening on the moon"}),
    (["image_gen"], "Produce a fresh illustration: {a}.", {"a": "a fox reading under a lantern"}),
    (["image_gen"], "Render {a} as a brand-new image.", {"a": "a city built inside a giant tree"}),
    (["image_gen"], "I'd like a picture that doesn't exist yet, of {a}.", {"a": "a whale swimming through clouds"}),
    (["image_gen"], "Conjure up a poster-style graphic: {a}.", {"a": "a retro rocket over a desert"}),
    (["image_gen"], "Generate artwork for my album cover: {a}.", {"a": "neon jellyfish in a dark ocean"}),
    (["image_gen"], "Paint, digitally, {a}.", {"a": "a quiet harbor at dusk"}),
    # ask_model (6)
    (["ask_model"], "Run this question past another AI and report back: {a}", {"a": "Is a hot dog a sandwich?"}),
    (["ask_model"], "I want a second pair of eyes from a different model on {a}.", {"a": "whether tabs beat spaces"}),
    (["ask_model"], "Poll another assistant: {a}", {"a": "What's the best way to learn piano as an adult?"}),
    (["ask_model"], "Have a different model weigh in on {a}.", {"a": "choosing between Rust and Go"}),
    (["ask_model"], "Pose this to a different language model and tell me its answer: {a}", {"a": "Why is the sky dark at night?"}),
    (["ask_model"], "Sound out another AI on whether it agrees about {a}.", {"a": "pineapple belonging on pizza"}),
    # read_url (7)
    (["read_url"], "Open {a} and tell me what's on it.", {"a": "https://example.org/notes/42"}),
    (["read_url"], "Pull the text off {a}.", {"a": "https://example.org/blog/spring-update"}),
    (["read_url"], "What does {a} say? Scan it for me.", {"a": "https://example.org/docs/guide"}),
    (["read_url"], "Skim the contents behind {a}.", {"a": "https://example.org/press/release-7"}),
    (["read_url"], "Browse to {a} and give me an excerpt.", {"a": "https://example.org/menu/lunch"}),
    (["read_url"], "Summarize whatever lives at {a}.", {"a": "https://example.org/team/about"}),
    (["read_url"], "Visit {a} and quote its opening lines.", {"a": "https://example.org/essays/first"}),
    # calc (7)
    (["calc"], "What does {a} come out to?", {"a": "(48 + 17) * 3"}),
    (["calc"], "Crunch the numbers on {a}.", {"a": "1250 / 5 - 40"}),
    (["calc"], "Work out {a} exactly.", {"a": "(9 + 11) * (7 - 2)"}),
    (["calc"], "Give me the result of {a}.", {"a": "3 * 3 * 3 + 100 / 4"}),
    (["calc"], "Compute {a} for me, quick.", {"a": "(1000 - 275) / 5"}),
    (["calc"], "How much is {a}? No mental math, run it.", {"a": "88 * 12 + 6"}),
    (["calc"], "Numerically resolve {a}.", {"a": "(15 + 25) / (2 + 6)"}),
    # remember (6)
    (["remember"], "Jot down that {a}.", {"a": "my locker combination hint is blue-three"}),
    (["remember"], "Keep in mind that {a}.", {"a": "the dentist appointment moved to Thursday"}),
    (["remember"], "Make a note: {a}.", {"a": "Priya prefers decaf after noon"}),
    (["remember"], "Hold on to this detail for me: {a}.", {"a": "the spare key lives under the blue pot"}),
    (["remember"], "Log this in your notes: {a}.", {"a": "the wifi password rotates on Mondays"}),
    (["remember"], "Don't forget that {a}.", {"a": "the report is due on the 14th"}),
    # recall (6)
    (["recall"], "What notes did I leave about {a}?", {"a": "Priya"}),
    (["recall"], "Dredge up anything stored that mentions {a}.", {"a": "dentist"}),
    (["recall"], "Did I tell you anything involving {a}?", {"a": "wifi"}),
    (["recall"], "Rummage through your notes for {a}.", {"a": "spare key"}),
    (["recall"], "Anything on file about {a}?", {"a": "report"}),
    (["recall"], "Remind me what I said regarding {a}.", {"a": "locker"}),
]

TWO_STEP = [
    (["web_search", "read_url"], "Unearth a page covering {a}, then skim whatever it says.", {"a": "urban beekeeping"}),
    (["web_search", "read_url"], "Surface a link about {a} and then give me the gist of that link.", {"a": "the Silk Road"}),
    (["web_search", "read_url"], "Hunt up an article on {a}; once you have it, open it and quote a sentence.", {"a": "deep sea vents"}),
    (["web_search", "read_url"], "First a URL on {a}, after that the text found there.", {"a": "medieval castles"}),
    (["image_search", "ask_model"], "Source a photo of {a}, and afterwards have another AI describe how to caption it.", {"a": "a lighthouse in a storm"}),
    (["image_search", "ask_model"], "Pull a ready-made photograph of {a}, and afterwards poll a different assistant on what mood it conveys.", {"a": "an empty train platform"}),
    (["remember", "recall"], "Make a note that {a}, and straight afterwards confirm it by rummaging through your notes for {b}.", {"a": "the picnic is on Saturday", "b": "picnic"}),
    (["remember", "recall"], "Jot down that {a}; next, rummage through your notes for {b}.", {"a": "Marco owes me lunch", "b": "Marco"}),
    (["remember", "recall"], "Keep in mind that {a}, then tell me what you have filed under {b}.", {"a": "the printer is out of toner", "b": "printer"}),
    (["calc", "remember"], "Work out {a} and keep the answer on file.", {"a": "(64 + 36) * 2"}),
    (["calc", "remember"], "Crunch {a}, then make a note of the figure.", {"a": "750 / 25 + 5"}),
    (["calc", "remember"], "Give me {a}, and hold on to the result for later.", {"a": "12 * 12 - 44"}),
    (["web_search", "ask_model"], "Dig up an online source on {a}, then run its main claim past another AI.", {"a": "intermittent fasting"}),
    (["web_search", "ask_model"], "Surface a link regarding {a}; have a second AI judge how trustworthy it seems.", {"a": "cold fusion"}),
    (["read_url", "ask_model"], "Open {a}, then poll another assistant about what it means.", {"a": "https://example.org/policy/terms"}),
    (["read_url", "ask_model"], "Skim {a} and then put a question to a different AI about its tone.", {"a": "https://example.org/letters/open"}),
    (["image_gen", "image_search"], "Paint {a} from scratch, and afterwards source an existing photo that resembles it.", {"a": "a glass bridge over a canyon"}),
    (["image_gen", "image_search"], "Render {a} as new artwork; then pull up a similar picture that's already online.", {"a": "a floating market at night"}),
]

NO_TOOL = [
    "Spell the word 'lantern' backwards.",
    "What's the capital of Portugal?",
    "Write a two-line poem about rain.",
    "Translate 'good morning' into Spanish.",
    "Name a synonym for 'quick'.",
    "Is a tomato technically a fruit or a vegetable?",
    "How many legs does a spider have?",
    "List the three primary colors.",
    "Say hello in French.",
    "Which word rhymes with 'light'?",
    "Turn 'tide pools' into all capitals.",
    "What's the opposite of 'ancient'?",
    "Tell me a short riddle about time.",
    "Who wrote Pride and Prejudice?",
    "How many days are in a leap year?",
    "Describe the color blue to someone who has never seen it, in one sentence.",
    "What does a search engine do, in one sentence?",
    "Explain in plain words what a URL is.",
    "What does the word 'remember' mean?",
    "Why is it hard to hold on to a dream after waking up?",
    "Define the word 'abacus' for a child.",
    "What's the difference between a photo and a painting?",
    "Is it impolite to seek a second opinion from another person?",
    "Give me a friendly sign-off for an email to my coworker.",
    "Which planet is closest to the sun?",
    "Rewrite 'the cat sat' in the past perfect tense.",
    "How do you say 'thank you' in Japanese?",
    "Name two things people keep in a toolbox.",
    "What is the plural of 'mouse'?",
    "Give me a one-word nickname for a very tall person.",
]


def build() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for i, (expected, template, args) in enumerate(SINGLE + TWO_STEP):
        rows.append(
            {
                "id": f"ood-{i:03d}",
                "skill": "+".join(expected),
                "expected": expected,
                "template": template,
                "request": template.format(**args),
                "family": f"ood-t{i:03d}",
            }
        )
    base = len(rows)
    for j, request in enumerate(NO_TOOL):
        rows.append(
            {
                "id": f"ood-{base + j:03d}",
                "skill": "direct",
                "expected": [],
                "template": request,
                "request": request,
                "family": f"ood-t{base + j:03d}",
            }
        )
    return rows


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    out = Path(sys.argv[1] if len(sys.argv) > 1 else "data/ood.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(r) + "\n" for r in build()))
    print(f"wrote {out}")
