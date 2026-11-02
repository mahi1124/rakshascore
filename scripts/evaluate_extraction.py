"""Measure extraction accuracy and consistency (the 'Output Analysis' slide).

Add cases to tests/test_cases.json (aim for 20-30). Usage:
    python scripts/evaluate_extraction.py [--llm] [--repeat 3]

The expected value "POOR" means "any poor-sounding label", so it works across datasets.
"""
import argparse
import json

import _bootstrap  # noqa: F401  (makes `rakshascore` importable)

from rakshascore import paths, pipeline as P

POOR = {"poor", "weak", "low", "no", "none", "never"}


def evaluate(cases, use_llm, repeat):
    correct = total = stable = 0
    for case in cases:
        runs = [P.extract_factors(case["text"], use_llm)[0] for _ in range(repeat)]
        got = runs[0]
        stable += all(r == runs[0] for r in runs)
        for field, want in case["expected"].items():
            total += 1
            have = got.get(field)
            ok = (str(have).lower() in POOR) if want == "POOR" and have else (
                have == want or (isinstance(want, (int, float)) and have is not None and abs(float(have) - want) < 0.5))
            correct += ok
            print(f"{'OK ' if ok else 'MISS'} {field:26} expected={want!s:10} got={have}")

    print(f"\nField-level extraction accuracy: {correct}/{total} = {100 * correct / total:.1f}%")
    print(f"Consistency over {repeat} runs: {stable}/{len(cases)} cases identical")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Evaluate attribute extraction against labelled cases.")
    ap.add_argument("--llm", action="store_true", help="use the configured LLM instead of the offline rules")
    ap.add_argument("--repeat", type=int, default=1, help="runs per case, for consistency measurement")
    ap.add_argument("--cases", default=str(paths.DEFAULT_TEST_CASES), help="JSON file with test cases")
    args = ap.parse_args()
    evaluate(json.loads(open(args.cases, encoding="utf-8").read()), args.llm, args.repeat)
