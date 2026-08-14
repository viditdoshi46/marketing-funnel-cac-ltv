"""
Generate a realistic growth dataset: the acquisition funnel and unit economics
across marketing channels. The numbers are tuned so the channels have a genuine
spread — some channels are efficient (Referral, Email, Organic) and some are not
(Display), which is exactly what makes the CAC:LTV analysis actionable.

For each channel we simulate the funnel:
    impressions -> clicks -> signups -> activations -> paying customers
plus spend, and the per-customer economics that drive LTV:
    monthly ARPU, gross margin, and monthly retention (=> expected lifetime).

Deterministic (seeded). Writes small aggregates the app reads directly:
  data/channel_summary.csv   (one row per channel, all unit economics)
  data/funnel.csv            (long form: channel, stage, count)

Usage:  python src/make_data.py
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path(__file__).resolve().parents[1] / "data"
DATA.mkdir(parents=True, exist_ok=True)
RNG = np.random.default_rng(21)
GROSS_MARGIN = 0.75

# channel: impressions, ctr, signup_rate (click->signup), activation_rate,
#          paid_rate (signup->paying), cost model, ARPU (monthly), retention
CH = {
    "Paid Search": dict(impr=4_000_000, ctr=0.038, signup=0.11, activ=0.72,
                        paid=0.075, cpc=1.60, reward=0, arpu=44, ret=0.90),
    "Paid Social": dict(impr=9_000_000, ctr=0.014, signup=0.06, activ=0.62,
                        paid=0.045, cpc=0.75, reward=0, arpu=32, ret=0.86),
    "Display":     dict(impr=22_000_000, ctr=0.0045, signup=0.035, activ=0.52,
                        paid=0.025, cpc=0.45, reward=0, arpu=26, ret=0.80),
    "Email":       dict(impr=1_500_000, ctr=0.11, signup=0.14, activ=0.76,
                        paid=0.11, cpc=0.015, reward=0, arpu=40, ret=0.92),
    "Referral":    dict(impr=350_000, ctr=0.22, signup=0.28, activ=0.82,
                        paid=0.16, cpc=0, reward=25, arpu=50, ret=0.93),
    "Organic":     dict(impr=3_000_000, ctr=0.065, signup=0.12, activ=0.74,
                        paid=0.085, cpc=0, reward=0, arpu=42, ret=0.91),
}
FIXED_COST = {"Organic": 60_000, "Referral": 8_000,     # content/program overhead
              "Email": 28_000}                           # ESP + content + ops


def _noise(x, sd=0.03):
    return int(round(x * (1 + RNG.normal(0, sd))))


def main():
    rows, funnel = [], []
    for ch, p in CH.items():
        impr = p["impr"]
        clicks = _noise(impr * p["ctr"])
        signups = _noise(clicks * p["signup"])
        activations = _noise(signups * p["activ"])
        paying = _noise(signups * p["paid"])

        spend = clicks * p["cpc"] + paying * p["reward"] + FIXED_COST.get(ch, 0)
        cac = spend / paying if paying else 0.0

        arpu = p["arpu"]
        lifetime_months = 1 / (1 - p["ret"])            # expected tenure
        ltv = arpu * GROSS_MARGIN * lifetime_months     # gross-margin LTV
        ltv_cac = ltv / cac if cac else float("inf")
        payback = cac / (arpu * GROSS_MARGIN) if arpu else 0.0   # months to recoup CAC

        rows.append({
            "channel": ch, "impressions": impr, "clicks": clicks,
            "signups": signups, "activations": activations, "paying_customers": paying,
            "spend": round(spend, 0),
            "ctr": round(clicks / impr, 4),
            "signup_rate": round(signups / clicks, 4),
            "paid_rate": round(paying / signups, 4),
            "cac": round(cac, 2), "arpu_monthly": arpu,
            "gross_margin": GROSS_MARGIN,
            "avg_lifetime_months": round(lifetime_months, 1),
            "ltv": round(ltv, 2),
            "ltv_cac_ratio": round(ltv_cac, 2) if np.isfinite(ltv_cac) else 99.0,
            "payback_months": round(payback, 1),
        })
        for stage, n in [("Impressions", impr), ("Clicks", clicks),
                         ("Signups", signups), ("Activations", activations),
                         ("Paying", paying)]:
            funnel.append({"channel": ch, "stage": stage, "count": n})

    pd.DataFrame(rows).to_csv(DATA / "channel_summary.csv", index=False)
    pd.DataFrame(funnel).to_csv(DATA / "funnel.csv", index=False)

    s = pd.DataFrame(rows)
    print(s[["channel", "spend", "paying_customers", "cac", "ltv",
             "ltv_cac_ratio", "payback_months"]].to_string(index=False))
    print(f"\nTotal spend ${s.spend.sum():,.0f} | paying customers "
          f"{s.paying_customers.sum():,} | blended CAC "
          f"${s.spend.sum()/s.paying_customers.sum():,.0f}")


if __name__ == "__main__":
    main()
