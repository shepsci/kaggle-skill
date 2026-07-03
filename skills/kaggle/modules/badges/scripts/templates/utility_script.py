"""Badge Collector — Utility Script.

A simple utility script (not a notebook) for Kaggle badge collection.
Utility scripts run as .py files on Kaggle Kernel Backend.
"""

import json
import sys


def generate_report(n: int = 10) -> dict:
    """Generate a sample report."""
    report = {
        "title": "Badge Collector Utility Report",
        "rows": n,
        "data": [{"id": i, "value": i * i, "even": i % 2 == 0} for i in range(1, n + 1)],
    }
    return report


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    report = generate_report(n)
    print(json.dumps(report, indent=2))

    # Save output
    with open("report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to report.json ({len(report['data'])} rows)")
