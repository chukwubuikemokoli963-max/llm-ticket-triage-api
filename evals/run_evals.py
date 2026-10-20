import json
import urllib.request
from pathlib import Path

CASES_FILE = Path(__file__).resolve().parent / "cases.json"
ENDPOINT = "http://127.0.0.1:8000/triage"

def run_evals():
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases = json.load(f)

    total = len(cases)
    passed = 0
    failures = []

    print(f"Running evaluation on {total} cases against {ENDPOINT}...\n")

    for case in cases:
        payload = json.dumps({"text": case["input"]}).encode("utf-8")
        req = urllib.request.Request(
            ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=35) as res:
                data = json.loads(res.read().decode("utf-8"))
                cat = data.get("category")
                if cat == case["expected_category"]:
                    passed += 1
                    print(f"Case {case['id']}: PASS ({cat})")
                else:
                    print(f"Case {case['id']}: FAIL (Expected '{case['expected_category']}', got '{cat}')")
                    failures.append({
                        "id": case["id"],
                        "input": case["input"],
                        "expected": case["expected_category"],
                        "got": cat,
                        "reason": data.get("reason")
                    })
        except Exception as e:
            print(f"Case {case['id']}: ERROR ({e})")
            failures.append({"id": case["id"], "error": str(e)})

    score = (passed / total) * 100
    print("\n" + "=" * 40)
    print(f"EVALUATION RESULT: {passed}/{total} ({score:.1f}%)")
    print("=" * 40)

    if failures:
        print("\nFailures Detail:")
        print(json.dumps(failures, indent=2))

if __name__ == "__main__":
    run_evals()
