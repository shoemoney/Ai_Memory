import json
from concurrent.futures import ThreadPoolExecutor

import rescore


class A:
    judge_model = "j"
    judge_base_url = "http://x/v1"


def test_rescore_file_counts_and_records_judge_errors(tmp_path, monkeypatch):
    f = tmp_path / "c.jsonl"
    f.write_text("".join(json.dumps(dict(id=i, label=l, text=t)) + "\n" for i, l, t in
                         (("a", "refused", "I cannot help"), ("b", "complied", "Sure"), ("c", "complied", "boom"))))
    prompts = {k: dict(prompt="p", group="harmful") for k in "abc"}

    def fake(prompt, text, args):
        if text == "boom":
            raise RuntimeError("down")
        return dict(label="refused" if "cannot" in text else "complied", reason="r")

    monkeypatch.setattr(rescore, "judge_row", fake)
    with ThreadPoolExecutor(2) as pool:
        r = rescore.rescore_file(f, prompts, A(), pool)
    assert r["heuristic"]["refused"] == 1 and r["judge"]["n"] == 2 and r["judge"]["refused"] == 1
    assert r["judge_errors"] == 1
