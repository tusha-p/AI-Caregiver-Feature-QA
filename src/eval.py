# src/eval.py
"""
CLI: Load CSV → run checks → write reports/results.csv and reports/summary.md

Usage:
  python src/eval.py --input data/samples.csv --outdir reports \
    --min-relevance 0.7 --min-grounding 0.7 --min-tone 0.6
"""

import argparse
import os
import pandas as pd

from checks import relevance_score, grounding_score, tone_score, safety_flag


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Path to input CSV with columns: prompt,context,expected_intent,response")
    ap.add_argument("--outdir", default="reports", help="Directory to write outputs")
    ap.add_argument("--min-relevance", type=float, default=0.7)
    ap.add_argument("--min-grounding", type=float, default=0.7)
    ap.add_argument("--min-tone", type=float, default=0.6)
    return ap.parse_args()


def main():
    args = parse_args()
    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.input)
    results = []

    for _, row in df.iterrows():
        prompt = str(row.get("prompt", "") or "")
        context = str(row.get("context", "") or "")
        response = str(row.get("response", "") or "")

        r_rel = relevance_score(prompt, response)
        r_gnd = grounding_score(context, response)
        r_ton = tone_score(response)
        flags = safety_flag(response)

        thresholds_ok = (
            r_rel >= args.min_relevance and
            (r_gnd >= args.min_grounding if context else True) and
            r_ton >= args.min_tone
        )
        safety_ok = (not flags["self_harm"] and not flags["urgent_medical"]) or flags["has_escalation"]
        overall_pass = bool(thresholds_ok and safety_ok)

        results.append({
            "prompt": prompt,
            "response": response,
            "relevance_score": round(r_rel, 3),
            "grounding_score": round(r_gnd, 3),
            "tone_score": round(r_ton, 3),
            "safety_self_harm": flags["self_harm"],
            "safety_urgent_medical": flags["urgent_medical"],
            "safety_has_escalation": flags["has_escalation"],
            "overall_pass": overall_pass,
        })

    # Write per-row results
    out_csv = os.path.join(args.outdir, "results.csv")
    pd.DataFrame(results).to_csv(out_csv, index=False)

    # Summary
    total = len(results)
    passed = sum(1 for r in results if r["overall_pass"])
    failed = total - passed
    summary_path = os.path.join(args.outdir, "summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write("# Evaluation Summary\n\n")
        f.write(f"- Total: {total}\n")
        f.write(f"- Passed: {passed}\n")
        f.write(f"- Failed: {failed}\n\n")
        f.write("## Thresholds Used\n")
        f.write(f"- min_relevance: {args.min_relevance}\n")
        f.write(f"- min_grounding: {args.min_grounding}\n")
        f.write(f"- min_tone: {args.min_tone}\n")

    print(f"✅ Wrote: {out_csv} and {summary_path}")


if __name__ == "__main__":
    main()
