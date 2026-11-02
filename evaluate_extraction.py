"""STEP 7 - Measures extraction accuracy + consistency for your 'Output Analysis' slide.
Add more cases to test_cases.json (aim for 20-30).  Run: python evaluate_extraction.py [--llm] [--repeat 3]
Expected value "POOR" means 'any of the poor-sounding labels' - edit to match your dataset's real labels.
"""
import json, sys
import pipeline as P

use_llm = "--llm" in sys.argv
repeat = int(sys.argv[sys.argv.index("--repeat") + 1]) if "--repeat" in sys.argv else 1
cases = json.load(open("test_cases.json"))
POOR = {"poor", "weak", "low", "no", "none", "never"}

correct = total = 0
stable = 0
for case in cases:
    runs = [P.extract_factors(case["text"], use_llm)[0] for _ in range(repeat)]
    got = runs[0]
    stable += all(r == runs[0] for r in runs)
    for field, want in case["expected"].items():
        total += 1
        have = got.get(field)
        ok = (str(have).lower() in POOR) if want == "POOR" and have else (have == want or
             (isinstance(want, (int, float)) and have is not None and abs(float(have) - want) < 0.5))
        correct += ok
        print(f"{'OK ' if ok else 'MISS'} {field:26} expected={want!s:10} got={have}")

print(f"\nField-level extraction accuracy: {correct}/{total} = {100*correct/total:.1f}%")
print(f"Consistency over {repeat} runs: {stable}/{len(cases)} cases identical")
