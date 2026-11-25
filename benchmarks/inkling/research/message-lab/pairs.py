"""Deterministic paired agent-memory tasks, aligned under the actual chat tokenizer."""
import argparse
import hashlib
import json
import random
from pathlib import Path

TEMPLATES = (
    ('Session 1\nUser: My archive avatar is {person}. The avatar uses locker {bridge}.\n'
     'Assistant: Saved.\nSession 2\nUser: Locker {left} stores {a}; locker {right} stores {b}.\n'
     'Assistant: Saved.\nSession 3\nUser: My spare locker is {spare}.\nAssistant: Saved.\n'
     'User: Which item is in my archive avatar\'s locker?'),
    ('Session 1\nUser: For project {person}, my courier is {bridge}.\nAssistant: Noted.\n'
     'Session 2\nUser: Courier {left} delivers {a}; courier {right} delivers {b}.\nAssistant: Noted.\n'
     'Session 3\nUser: The spare courier is {spare}.\nAssistant: Noted.\n'
     'User: Which item will my project courier deliver?'),
    ('Session 1\nUser: My game avatar {person} follows guide {bridge}.\nAssistant: Recorded.\n'
     'Session 2\nUser: Guide {left} recommends {a}; guide {right} recommends {b}.\nAssistant: Recorded.\n'
     'Session 3\nUser: The spare guide is {spare}.\nAssistant: Recorded.\n'
     'User: Which item does my avatar\'s guide recommend?'),
)
# All entities are invented identifiers; answer objects are ordinary objects.
ITEMS = ('amber', 'paper', 'silver', 'copper', 'velvet', 'marble', 'cotton', 'ribbon', 'pearl', 'glass')
SUFFIX = '\nAnswer with exactly one item from the log and no explanation.\nAnswer:'


def encode(tok, text):
    return list(tok.encode(text, add_special_tokens=False))


def render(tok, prompt):
    rendered = tok.apply_chat_template([{'role': 'user', 'content': prompt}], tokenize=False,
                                       add_generation_prompt=True, reasoning_effort='none')
    # The checkpoint template ignores add_generation_prompt: force a text-answer channel.
    if not rendered.endswith('<|message_model|><|content_text|>'):
        rendered += '<|message_model|><|content_text|>'
    return rendered


def token_span(tok, text, start, end):
    """Tokens touching a character span, including tokenizer boundary merges.

    Uses prefix/suffix agreement with the full encoding, requiring no fast tokenizer.
    """
    full = encode(tok, text)
    prefix, suffix = encode(tok, text[:start]), encode(tok, text[end:])
    left = 0
    while left < min(len(full), len(prefix)) and full[left] == prefix[left]:
        left += 1
    right = 0
    while right < min(len(full) - left, len(suffix)) and full[-1-right] == suffix[-1-right]:
        right += 1
    return list(range(left, len(full) - right))


def align(tok, prompts, spans, irrelevant_spans):
    texts = [render(tok, p) for p in prompts]
    ids = [encode(tok, t) for t in texts]
    positions, irrelevant = [], []
    for p, t, span, irr in zip(prompts, texts, spans, irrelevant_spans):
        offset = t.index(p)
        positions.append(token_span(tok, t, offset + span[0], offset + span[1]))
        irrelevant.append(token_span(tok, t, offset + irr[0], offset + irr[1]))
    if len(ids[0]) != len(ids[1]) or positions[0] != positions[1] or len(positions[0]) < 2:
        return None
    bridge = set(positions[0])
    differences = {i for i, (a, b) in enumerate(zip(*ids)) if a != b}
    if not differences or not differences <= bridge:
        return None
    # Equal-size contiguous negative-control window in the spare-identifier span.
    width = len(bridge)
    if irrelevant[0] != irrelevant[1] or len(irrelevant[0]) < width:
        return None
    irr = irrelevant[0][:width]
    if set(irr) & bridge or any(ids[0][i] != ids[1][i] for i in irr):
        return None
    return dict(tokens=ids, bridge_positions=positions[0], irrelevant_positions=irr)


def build(tok, n=300, seed=16, max_attempts=100000):
    if n < 3 or n % 3:
        raise ValueError('n must be a positive multiple of three')
    rng = random.Random(seed)
    rows = []
    attempts = 0
    while len(rows) < n and attempts < max_attempts:
        attempts += 1
        template = len(rows) % 3
        # Random synthetic identifiers; rejection sampling only on token alignment.
        names = [''.join(rng.choice('bdfklmnprstvwz') + rng.choice('aeiou') for _ in range(3)).capitalize()
                 for _ in range(4)]
        if len(set(names)) != 4:
            continue
        person, left, right, spare = names
        a, b = rng.sample(ITEMS, 2)
        prompts, spans, irrelevant = [], [], []
        for bridge in (left, right):
            fields = dict(person=person, left=left, right=right, spare=spare, a=a, b=b, bridge='BRIDGE_SLOT')
            raw = TEMPLATES[template].format(**fields)
            start = raw.index('BRIDGE_SLOT')
            prompt = raw.replace('BRIDGE_SLOT', bridge) + SUFFIX
            prompts.append(prompt)
            spans.append((start, start + len(bridge)))
            s = prompt.index(spare)
            irrelevant.append((s, s + len(spare)))
        aligned = align(tok, prompts, spans, irrelevant)
        if aligned is None:
            continue
        # Answers must be distinguishable single tokens in this scoring context.
        answer_tokens = []
        valid = True
        for p, answer in zip(prompts, (a, b)):
            prefix = render(tok, p)
            base = encode(tok, prefix)
            extended = encode(tok, prefix + answer)
            if extended[:-1] != base or len(extended) != len(base) + 1:
                valid = False
                break
            answer_tokens.append(extended[-1])
        if not valid or answer_tokens[0] == answer_tokens[1]:
            continue
        # Single-hop control preserves the paired log, asks about one fixed locker/courier/guide.
        noun = ('locker', 'courier', 'guide')[template]
        control_question = f'Which item is associated with {noun} {left}?'
        controls = [p[:p.rfind('User:')] + 'User: ' + control_question + SUFFIX for p in prompts]
        control_aligned = align(tok, controls, spans, irrelevant)
        if control_aligned is None:
            continue
        rows.append(dict(id=f'pair-{len(rows):03d}', template=template,
            split='heldout' if template == 2 else 'discovery', task='two_hop',
            prompts=prompts, answers=[a, b], answer_tokens=answer_tokens,
            bridge_character_spans=spans, irrelevant_character_spans=irrelevant,
            controls=[dict(prompt=p, answer=a, foil=b) for p in controls],
            control_tokens=control_aligned['tokens'],
            control_bridge_positions=control_aligned['bridge_positions'], **aligned))
    if len(rows) != n:
        raise RuntimeError(f'Only {len(rows)}/{n} aligned pairs after {attempts} attempts; inspect tokenizer')
    return dict(schema=1, seed=seed, n=n, heldout_template=2, attempts=attempts, pairs=rows)


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--mlx-lm', type=Path)
    ap.add_argument('--n', type=int, default=300)
    ap.add_argument('--seed', type=int, default=16)
    args = ap.parse_args()
    if args.mlx_lm:
        import sys
        sys.path.insert(0, str(args.mlx_lm))
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    data = build(tok, args.n, args.seed)
    data['tokenizer'] = str(args.model)
    data['fingerprint'] = fingerprint(data)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, indent=2) + '\n')


if __name__ == '__main__':
    main()
