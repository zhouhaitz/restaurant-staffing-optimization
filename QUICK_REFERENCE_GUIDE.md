# Quick Reference Guide - Restaurant Simulation Project

## 🎯 Project Overview

**Objective**: Optimize restaurant staffing to maximize Net RevPASH (Revenue per Available Seat Hour)

**Restaurant**: Comal (Berkeley, CA)
- 35 menu items
- Price range: $5-$78
- Component-based cooking with 5 stations

**Primary KPI**: Net RevPASH = (Revenue - Labor Cost) / (Total Seats × Hours)

---

## 📊 Key Results

### Optimal Configuration
- **4 Servers, 7 Cooks**
- **20 Tables** (60 total seats)
- **Net RevPASH**: $15.71 per seat-hour
- **Gross RevPASH**: $20.88 per seat-hour
- **Server Utilization**: 66.8%
- **Cook Utilization**: 79.9%
- **Table Turnover**: 0.70 parties/table/hour

### Statistical Validation
- **25 configurations tested**: 5 server levels × 5 cook levels
- **Two-stage pilot**: n=10 initial, n=37 final (validated for 5% CI half-width)
- **Pairwise CRN tests**: n=50 per pair
- **Coefficient of Variation**: 8.06% - 15.44%

### Top 5 Configurations (by Net RevPASH)
1. 4 servers, 7 cooks: **$15.71**
2. 5 servers, 7 cooks: **$15.62**
3. 4 servers, 6 cooks: **$15.39**
4. 6 servers, 7 cooks: **$15.29**
5. 5 servers, 6 cooks: **$15.24**

---

## 🔬 Simulation Architecture

### 10-Stage Flow

1. **Guest Arrival** → NHPP (Gaussian peak at 120 min)
2. **Table Matching** → Round-robin zone balancing
3. **Host Seating** → FIFO queue
4. **Ordering** → Server takes order
5. **Kitchen** → Component-based parallel cooking
6. **Expo** → Quality check (capacity: 2)
7. **Delivery** → Food runner OR server
8. **Dining** → Lognormal (scales with party size)
9. **Checkout** → Server processes payment
10. **Cleanup** → Busser OR server

### Kitchen Stations (5 stations)
- **wood_grill**: Capacity 2
- **salad_station**: Capacity 3
- **sautee_station**: Capacity 2
- **tortilla_station**: Capacity 3
- **guac_station**: Capacity 2

### Component-Based Cooking
- Each dish = list of components
- Components cook in parallel across stations
- Dish complete = max(component completion times)
- Example: "Rock Cod Tacos" = [wood_grill, tortilla_station, guac_station]

---

## 📈 Performance Metrics

### Financial
- **Net RevPASH**: Primary KPI
- **Gross RevPASH**: Revenue per seat-hour
- **Total Revenue**: Sum of dish prices
- **Labor Cost**: All staff wages
- **Average Check Size**: Revenue per party

### Operational
- **Parties Served**: Throughput
- **Service Rate**: % of parties served
- **Table Turnover**: Parties/table/hour
- **Wait Times**: Table, ordering, kitchen, total

### Utilization
- **Server Utilization**: 66.8% (optimal)
- **Cook Utilization**: 79.9% (optimal)
- **Station Utilization**: Per-station tracking
- **Host/Food Runner/Busser**: All tracked

---

## 🛠️ Technical Stack

- **SimPy 4.1+**: Discrete-event simulation
- **NumPy 2.0+**: Numerical computations
- **SciPy 1.10+**: Statistical functions
- **Pandas 2.0+**: Data analysis
- **Matplotlib 3.10+**: Visualization

### Key Files
- `simulation.py`: Core engine (845 lines)
- `models.py`: Data models (176 lines)
- `parameters.py`: Configuration (196 lines)
- `results.py`: Metrics (497 lines)
- `statistical_validation.py`: Framework (630 lines)
- `comal_recipes.json`: Restaurant data (113 lines)

---

## 📝 Draft Report Sections

### 1. Problem Description
**What to write**: 
- Restaurant staffing optimization challenge
- Balance between service quality and labor costs
- Comal restaurant specifics (35 dishes, component cooking)
- Net RevPASH as decision metric

**Key points**:
- Labor = 25-35% of revenue
- Wait times impact satisfaction
- Data-driven decisions vs intuition

### 2. Analysis Methods
**What to write**:
- Discrete-event simulation approach
- Statistical validation framework
- Two-stage pilot study
- Common Random Numbers (CRN)
- Sample size estimation

**Key points**:
- DES models complete operations
- Statistical rigor ensures valid comparisons
- CRN reduces variance
- 5% CI half-width target

### 3. Simulation Algorithms
**What to write**:
- 10-stage flow description
- Component-based cooking
- Dual queue system
- NHPP arrival process
- Zone-based allocation

**Key points**:
- Parallel component cooking
- Redundancy (works with zero specialized staff)
- Realistic dinner rush pattern
- Efficient resource utilization

### 4. Primary Results
**What to write**:
- Optimal configuration: 4s/7c
- Net RevPASH: $15.71
- Top 5 comparison
- Statistical significance
- Utilization analysis

**Key points**:
- Marginal returns diminish beyond 7 cooks
- 4-5 servers optimal range
- Cook capacity critical bottleneck
- Statistical validation confirms results

### 5. Further Work
**What to write**:
- Sensitivity analysis (not yet done)
- Scenario analysis (different time periods)
- Model validation (face validity, parameters)
- Additional features (abandonment, variable staffing)
- Extended replications

---

## ⚠️ Critical Missing Pieces

### Documentation Gaps
1. ❌ **Problem statement** - Needs formal write-up
2. ❌ **Methodology section** - Needs detailed explanation
3. ❌ **Results interpretation** - Needs narrative
4. ❌ **Literature review** - Not started
5. ❌ **Limitations discussion** - Needs formal documentation

### Analysis Gaps
1. ❌ **Sensitivity analysis** - Planned but not executed
2. ❌ **Scenario analysis** - Different day parts
3. ❌ **ANOVA analysis** - Across all configurations
4. ❌ **Extended replications** - More n for final configs
5. ❌ **Model validation** - Face validity, parameter checks

---

## 🎯 Quick Stats for Report

### Experimental Results
- **Configurations tested**: 25
- **Total replications**: 25 × 37 = 925 (pilot) + 10 × 50 = 500 (pairwise)
- **Runtime**: ~0.02 seconds per replication
- **Total simulation time**: ~30 seconds

### Optimal Configuration Performance
- **Net RevPASH**: $15.71 ± $1.35
- **Parties Served**: ~57 per 4-hour shift
- **Service Rate**: ~51%
- **Total Revenue**: ~$5,011 per shift
- **Labor Cost**: ~$1,200 per shift

### Key Insight
Cook capacity (7 cooks) is more critical than server count for this restaurant configuration. Marginal improvement from 4 to 5 servers is minimal ($0.09 Net RevPASH difference).

---

## 📚 Key Concepts for Report

### Net RevPASH
Revenue per Available Seat Hour (after labor costs)
- Measures profit efficiency per seat
- Accounts for both revenue and costs
- Primary decision metric

### Component-Based Cooking
Dishes require multiple station visits:
- Components cook in parallel
- Dish complete = max component time
- Realistic kitchen operations

### Dual Queue System
Tasks added to multiple queues:
- Delivery: food_runner_queue + server_zone_queue
- Cleaning: busser_queue + server_zone_queue
- Provides redundancy and flexibility

### NHPP Arrivals
Non-Homogeneous Poisson Process:
- Gaussian peak at 120 minutes
- Models realistic dinner rush
- Time-varying arrival rate

---

## ✅ What's Working Well

1. ✅ Complete simulation implementation
2. ✅ Statistical validation framework
3. ✅ Real restaurant data integration
4. ✅ Comprehensive metrics calculation
5. ✅ Flexible configuration system
6. ✅ Robust dual queue design
7. ✅ Optimal configuration identified

---

## 🚧 Areas Needing Work

### Before Draft Report
1. Write problem statement
2. Document methodology
3. Compile results tables
4. Write results interpretation
5. Create flow diagrams

### Before Final Report
1. Sensitivity analysis
2. Scenario analysis
3. Extended validation
4. Model enhancements
5. Complete documentation

---

## 💡 Report Writing Tips

### Problem Statement
- Start broad (restaurant operations challenge)
- Narrow to specific problem (staffing optimization)
- Introduce Comal restaurant
- Define Net RevPASH as objective

### Methodology
- Explain DES approach
- Describe simulation flow
- Document statistical methods
- Justify experimental design

### Results
- Present optimal configuration
- Show comparison with alternatives
- Discuss statistical significance
- Interpret business implications

### Further Work
- List planned analyses
- Describe model enhancements
- Outline validation needs
- Propose additional experiments

---

## 📊 Ready-to-Use Data

**All data available in**:
- `validation_analysis.ipynb`: Complete experimental results
- `comal_simulation.ipynb`: Working demo with sample output
- `comal_recipes.json`: Full menu configuration
- `results.py`: All metrics definitions

**Visualizations**:
- Heatmaps (Net RevPASH, utilization, wait times)
- Performance trade-off plots
- Uncertainty analysis charts

---

## 🎓 Academic Requirements

### Draft Report Should Include:
- ✅ Problem description
- ✅ Analysis methods explanation
- ✅ Simulation algorithms/structures
- ✅ Primary results
- ✅ Further work outline

**Status**: ~65% ready for draft
**Time Estimate**: 8-12 hours to complete draft

---

## 🔗 Quick Links

- **Main Notebook**: `experiments/comal_simulation.ipynb`
- **Analysis**: `experiments/validation_analysis.ipynb`
- **Status Report**: `PROJECT_STATUS_REPORT.md`
- **Checklist**: `DRAFT_REPORT_CHECKLIST.md`
- **This Guide**: `QUICK_REFERENCE_GUIDE.md`


