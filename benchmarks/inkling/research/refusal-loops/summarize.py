"""Print markdown tables for a refusal-loops study directory (aggregates only, no completions)."""
import json
import sys
from pathlib import Path

import numpy as np

CORE = range(6, 18)


def main(study):
    study = Path(study)
    an = json.loads((study / "analysis.json").read_text())
    rf = json.loads((study / "refusal.json").read_text())
    rs = json.loads((study / "rescore.json").read_text())["conditions"] if (study / "rescore.json").exists() else {}
    print("### Unedited refusal (held-out, 12 per class)\n\n| N | harmful refused (regex) | harmful refused (judge) | benign refused (regex) | benign refused (judge) |\n|---|---|---|---|---|")
    for n, v in rf.items():
        def cell(g):
            h = v[g]
            j = rs.get(f"refusal-N{n}-{g}", {}).get("judge")
            return f"{h['refused']}/{h['n']}", (f"{j['refused']}/{j['n']}" if j else "n/a")
        (hr, hj), (br, bj) = cell("harmful"), cell("benign")
        print(f"| {n} | {hr} | {hj} | {br} | {bj} |")
    print("\n### Separation (validation score, mean over core layers 6-17) and best visit\n\n| N | pass | mean val score | best core visit (layer, pass, val, eval) |\n|---|---|---|---|")
    for n, v in an["by_n"].items():
        vis = v["visits"]
        b = v["best_core_visit"]
        for p in range(1, int(n) + 1):
            s = [x["val_score"] for x in vis if x["pass_number"] == p and x["layer"] in CORE]
            print(f"| {n} | {p} | {np.mean(s):.2f} | " + (f"L{b['layer']} p{b['pass_number']} {b['val_score']:.2f} / {b['eval_score']:.2f}" if p == 1 else "") + " |")
    print("\n### Direction cosine between passes, same layer (mean over core layers 6-17)\n")
    for n, v in an["by_n"].items():
        pc = v["pass_cosines"]
        if not pc:
            continue
        m = np.mean([np.array(x["matrix"]) for x in pc.values()], axis=0)
        print(f"N={n}:\n```\n{np.array2string(m, precision=2)}\n```")
    print("\n### Direction cosine across pass counts, same (layer, pass); mean over core layers\n\n| pair | pass 1 | pass 2 | pass 3 |\n|---|---|---|---|")
    for pair, d in an["cross_n_cosines"].items():
        cells = []
        for p in (1, 2, 3):
            vals = [x for k, x in d.items() if int(k.split(":")[0]) in CORE and int(k.split(":")[1]) == p]
            cells.append(f"{np.mean(vals):.2f}" if vals else "-")
        print(f"| {pair} | " + " | ".join(cells) + " |")


if __name__ == "__main__":
    main(sys.argv[1])
