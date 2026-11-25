"""Cut the train and validation files to the first N rows (fixed rule, no sampling) and point
sample_config.json at them. The 200-row formula test file is used whole."""
import json, sys, os
d, n_train, n_val = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
def cut(src, dst, n):
    rows = open(os.path.join(d, src)).read().splitlines()[:n]
    open(os.path.join(d, dst), "w").write("\n".join(rows) + "\n")
cut("formula_train_subset_500.jsonl", "formula_train_cut.jsonl", n_train)
cut("formula_val_subset_300.jsonl", "formula_val_cut.jsonl", n_val)
cfg = json.load(open(os.path.join(d, "sample_config.json")))
cfg["formula"]["train_data"] = "./eval/finance/data/formula_train_cut.jsonl"
cfg["formula"]["val_data"] = "./eval/finance/data/formula_val_cut.jsonl"
json.dump(cfg, open(os.path.join(d, "sample_config.json"), "w"), indent=2)
