"""Generate a synthetic POS "OrderDetails"-style CSV for demos and tests.

Nothing here is copied from real orders. The generator draws:
  * arrival counts per hour   ~ Poisson(mean_parties_per_day * hourly_share)   (per weekday)
  * arrival time within hour  ~ Uniform
  * party size                ~ empirical party-size distribution
  * dishes per party          ~ party_size * U(1.0, 1.5), each dish drawn from the menu mix
  * check amount              = sum of public menu prices for those dishes
  * dining duration           ~ Lognormal (same family the simulator uses)
The aggregate inputs live in distributions.json (see extract_distributions.py).

Usage:  python data/generate_synthetic_orders.py [--seed 7] [--out data/sample_orders.csv]
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
START_HOUR = 17
DAYS = pd.date_range("2025-10-01", "2025-11-30")   # same span as the original study window


def generate(seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dist = json.loads((HERE / "distributions.json").read_text())
    recipes = json.loads((HERE.parent / "engine" / "comal_recipes.json").read_text())

    sizes = np.array(sorted(int(k) for k in dist["party_size_pmf"]))
    size_p = np.array([dist["party_size_pmf"][str(s)] for s in sizes])
    size_p = size_p / size_p.sum()

    dishes = list(recipes["menu_distribution"])
    dish_p = np.array([recipes["menu_distribution"][d] for d in dishes], dtype=float)
    dish_p /= dish_p.sum()
    price = np.array([recipes["menu_catalog"][d]["price"] for d in dishes], dtype=float)

    rows = []
    for day in DAYS:
        wd = dist["weekday"].get(day.day_name())
        if wd is None:
            continue
        for h, share in enumerate(wd["hourly_share"]):
            n = rng.poisson(wd["mean_parties_per_day"] * share)
            for _ in range(n):
                opened = day + pd.Timedelta(hours=START_HOUR + h, minutes=float(rng.uniform(0, 60)))
                size = int(rng.choice(sizes, p=size_p))
                n_dishes = max(1, int(round(size * rng.uniform(1.0, 1.5))))
                amount = float(price[rng.choice(len(dishes), size=n_dishes, p=dish_p)].sum())
                minutes = float(rng.lognormal(2.8 + 0.1 * size, 0.35)) + 15
                rows.append({
                    "Location": "Sample", "Order #": None, "Opened": opened,
                    "# of Guests": size, "Table": "", "Dining Options": "Dine In",
                    "Discount Amount": 0, "Amount": round(amount, 2), "Tax": 0, "Tip": 0,
                    "Gratuity": 0, "Closed": opened + pd.Timedelta(minutes=minutes),
                    "Duration (Opened to Paid)": "",
                })
    df = pd.DataFrame(rows).sort_values("Opened").reset_index(drop=True)
    df["Order #"] = np.arange(1, len(df) + 1)
    for col in ("Opened", "Closed"):
        df[col] = df[col].dt.strftime("%m/%d/%y %H:%M")
    return df


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", default=str(HERE / "sample_orders.csv"))
    a = ap.parse_args()
    out = generate(a.seed)
    out.to_csv(a.out, index=False)
    print(f"wrote {len(out)} synthetic orders to {a.out}")
