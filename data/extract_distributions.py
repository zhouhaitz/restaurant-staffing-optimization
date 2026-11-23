"""Extract the small set of aggregate distributions used by generate_synthetic_orders.py.

This script is documentation of provenance. It needs the private POS export
(Toast "OrderDetails" CSV), which is NOT included in this repository, so you
cannot re-run it without that file. Its output, data/distributions.json, is
committed and contains only coarse aggregates: no individual orders, amounts,
tips, table numbers, or employee information.

Usage:  python data/extract_distributions.py /path/to/OrderDetails.csv
"""
import json
import sys
from pathlib import Path

import pandas as pd

START_HOUR = 17          # dinner service starts at 5 PM
MAX_PARTY = 10           # party sizes above this are pooled into the top bin


def main(csv_path: str) -> None:
    df = pd.read_csv(csv_path)
    df["Opened"] = pd.to_datetime(df["Opened"], errors="coerce")
    df = df[df["Dining Options"] == "Dine In"].dropna(subset=["Opened"]).copy()
    df["dow"] = df["Opened"].dt.day_name()
    df["hour_offset"] = df["Opened"].dt.hour - START_HOUR
    df = df[(df["hour_offset"] >= 0) & (df["hour_offset"] <= 5)]

    sizes = df["# of Guests"].clip(lower=1, upper=MAX_PARTY).value_counts(normalize=True).sort_index()

    out = {"party_size_pmf": {int(k): round(float(v), 4) for k, v in sizes.items()},
           "weekday": {}}
    for dow, g in df.groupby("dow"):
        n_days = g["Opened"].dt.date.nunique()
        hourly = g.groupby("hour_offset").size().reindex(range(6), fill_value=0)
        out["weekday"][dow] = {
            "mean_parties_per_day": round(float(len(g) / n_days), 1),
            "hourly_share": [round(float(x), 3) for x in hourly / hourly.sum()],
        }
    path = Path(__file__).with_name("distributions.json")
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"wrote {path}")


if __name__ == "__main__":
    main(sys.argv[1])
