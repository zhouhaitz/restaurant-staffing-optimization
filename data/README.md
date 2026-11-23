# Data

The original study used ~2 months (Oct 1 – Nov 30, 2025) of point-of-sale exports from the restaurant:
order timestamps and party sizes, a product-mix report, and a payroll export for wage averages.
**None of that raw data is in this repository.** It contained order-level revenue and employee payroll
records, so it was removed before publishing.

## What the simulator actually needs
The simulator and the Streamlit app do **not** read any CSV at runtime. They run from:

| Input | Where it lives | How it was derived |
|---|---|---|
| Arrival process (non-homogeneous Poisson: base rate, peak size/time/width) | defaults in `engine/parameters.py` | Gaussian-peak curve fit to average Friday dine-in parties per hour |
| Menu mix, recipes, station times, menu prices | `engine/comal_recipes.json` | product-mix report (aggregated), public menu prices |
| Average hourly wages by role | `engine/parameters.py` | averages from the payroll export |

## Synthetic sample (`sample_orders.csv`)
A synthetic POS-style file with the same columns as the Toast "OrderDetails" export, used to demo the
optional **"Fit from CSV"** arrival-rate fitting in the app (tick "use the bundled synthetic sample").
It contains no real orders: only dine-in rows, location `Sample`, no tips/taxes/table numbers.

How it is generated (`python data/generate_synthetic_orders.py --seed 7`):
1. `distributions.json` holds a handful of coarse aggregates from the real export: the party-size
   distribution, mean parties per day for each weekday, and each weekday's share of parties by
   dinner hour (extracted by `extract_distributions.py`, which needs the private file to re-run).
2. For each date, hourly arrival counts are drawn from a Poisson with that weekday's mean; times within
   the hour are uniform; party size comes from the empirical distribution.
3. Check amounts are the sum of public menu prices for dishes drawn from the menu mix.
4. Dining duration uses a lognormal, the same family the simulator uses.

**Fidelity caveat:** fitting the sample's Fridays gives the same peaked shape (R² ≈ 0.95) but not
identical parameters to the real fit (peak width ≈ 106 vs 93 min; base rate ≈ 0 vs 0.036 parties/min),
because the sample has only 9 Fridays of Poisson noise. The study's headline results use the parameters
in `engine/parameters.py`, not this file.
