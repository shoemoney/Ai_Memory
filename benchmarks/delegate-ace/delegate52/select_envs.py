"""Fix the DELEGATE-52 sample before any score is seen.

Rule: environments whose seed document is at most 3600 tokens (cl100k_base, all seed files
of the start state), one environment per domain chosen with a fixed seed, then 40 domains
chosen with the same seed. Output: selected.json (environment ids and sizes only).
"""
import json, random, sys, collections
import tiktoken

SEED = 20261122
N_ENVS = 40
MAX_SEED_TOKENS = 3600

def main(dataset_path, out_path):
    enc = tiktoken.get_encoding("cl100k_base")
    by_domain = collections.defaultdict(list)
    with open(dataset_path) as f:
        for line in f:
            r = json.loads(line)
            start = r["metadata"]["start_state"]
            st = next(s for s in r["states"] if s["state_id"] == start)
            tokens = sum(len(enc.encode(v)) for k, v in r["files"].items()
                         if k.startswith(st["solution_folder"]) and not v.startswith("base64:"))
            if tokens <= MAX_SEED_TOKENS:
                by_domain[r["sample_type"]].append((r["sample_id"], tokens))
    rng = random.Random(SEED)
    domains = sorted(by_domain)
    picked = {d: rng.choice(sorted(by_domain[d])) for d in domains}
    chosen = sorted(rng.sample(domains, N_ENVS))
    out = [{"sample_id": picked[d][0], "domain": d, "seed_tokens": picked[d][1]} for d in chosen]
    json.dump({"seed": SEED, "max_seed_tokens": MAX_SEED_TOKENS, "eligible_domains": len(domains),
               "environments": out}, open(out_path, "w"), indent=1)
    print(len(out), "environments from", len(domains), "eligible domains")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
