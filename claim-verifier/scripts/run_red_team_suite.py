#!/usr/bin/env python3
"""
scripts/run_red_team_suite.py
-----------------------------
Run Claim Verifier offline red team regression suite.

Usage:
    python scripts/run_red_team_suite.py
    python scripts/run_red_team_suite.py --json   # machine-readable output

No API keys required — tests guardrails, PII, parser, citation validation only.

Live LLM cases (RT-02, RT-03, RT-05, RT-07, RT-11, RT-12) are listed for manual testing.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.red_team import (
    run_offline_red_team_suite,
    format_finding_report,
    RED_TEAM_CASES,
)


def main():
    parser = argparse.ArgumentParser(description="Claim Verifier red team suite")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    args = parser.parse_args()

    report = run_offline_red_team_suite()

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("=" * 60)
        print("CLAIM VERIFIER — RED TEAM OFFLINE SUITE")
        print("=" * 60)
        print(f"Timestamp: {report['timestamp']}")
        print(f"Pass rate: {report['offline_passed']}/{report['offline_total']} "
              f"({report['offline_pass_rate']}%)")
        print()

        for finding in report["findings"]:
            print(format_finding_report(finding))
            print("-" * 40)

        print("\n📋 LIVE LLM CASES (run manually with streamlit / verify_claim):")
        for case in report["live_llm_cases_pending_manual_run"]:
            print(f"  • {case['case_id']}: {case['attack_type']}")
            print(f"    Payload: {case['payload_preview']}...")

        print("\n📖 Methodology:")
        for step in report["methodology_steps"]:
            print(f"  {step}")

        print(f"\nTotal matrix cases defined: {len(RED_TEAM_CASES)}")

    sys.exit(0 if report["offline_passed"] == report["offline_total"] else 1)


if __name__ == "__main__":
    main()
