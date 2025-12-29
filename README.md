# Restaurant Staffing Optimization Simulation

**IEOR 174 Project - Comal Restaurant Analysis**

A comprehensive discrete-event simulation framework for optimizing restaurant staffing configurations to maximize Net Revenue per Available Seat Hour (Net RevPASH).

## 🎯 Project Overview

This project implements a full-service restaurant simulation model specifically configured for **Comal Restaurant** in Berkeley, CA. The simulation models the complete customer journey from arrival to departure, including:

- Non-homogeneous Poisson arrival process (dinner rush pattern)
- Component-based cooking operations (5 specialized kitchen stations)
- Multi-zone server allocation
- Dual queue task management system
- Comprehensive performance metrics

**Primary Goal**: Optimize staffing levels (servers, cooks, hosts, food runners, bussers) to maximize Net RevPASH while maintaining service quality.

## 📊 Key Results

### Optimal Configuration
- **5 Servers, 9 Cooks, 1 Host, 1 Food Runner, 0 Bussers**
- **Net RevPASH**: $3.81/seat-hour (95% CI: [$3.64, $3.99])
- **Statistical Validation**: Achieved 5% relative error with 21-87 replications per configuration

### Top 5 Configurations
1. S5_C9_H1_R1_B0: $3.814
2. S5_C9_H1_R2_B0: $3.455
3. S5_C10_H1_R1_B0: $3.419
4. S6_C9_H1_R1_B0: $3.330
5. S5_C10_H1_R2_B0: $3.296

## 🏗️ Project Structure

```
.
├── experiments/              # Core simulation code
│   ├── simulation.py        # Main simulation engine (1408 lines)
│   ├── models.py            # Data models (Party, Dish, Task, etc.)
│   ├── parameters.py        # Configuration parameters
│   ├── results.py           # Metrics calculation
│   ├── statistical_testing.ipynb  # Statistical analysis framework
│   ├── comal_recipes.json   # Restaurant menu & recipes
│   └── ...
├── gui/                     # Streamlit visualization dashboard
├── discussions/             # Class discussion notebooks
├── PROJECT_ANALYSIS_DOCUMENTATION.md  # Comprehensive project documentation
├── PROJECT_STATUS_REPORT.md # Development status
└── requirements.txt         # Python dependencies
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- pip

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd "IEOR 174 proj"
   ```

2. **Create virtual environment**
   ```bash
   python -m venv restaurant_sim_env
   source restaurant_sim_env/bin/activate  # On Windows: restaurant_sim_env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure OpenAI API key (for RAG chatbot)**
   
   Create a `.env` file in the project root:
   ```bash
   # .env
   OPENAI_API_KEY=your_openai_api_key_here
   ```
   
   Get your API key from: https://platform.openai.com/api-keys
   
   > **Note**: The RAG chatbot requires an OpenAI API key. If you don't have one, the rest of the simulation will still work.

5. **Run a simulation**
   ```python
   from experiments.runner import run_single_dish_sim
   from experiments.dish_loading import load_recipes_from_json
   
   params = load_recipes_from_json('experiments/comal_recipes.json')
   results = run_single_dish_sim(params, verbose=True)
   ```

## 📈 Statistical Testing Workflow

The `statistical_testing.ipynb` notebook provides a complete framework for:

1. **Pilot Study**: Estimate variance with n=30 replications
2. **Sample Size Estimation**: Calculate required n for 5% relative error
3. **Configuration Screening**: Test all configs with n=10
4. **Subset Selection**: Bonferroni-corrected screening to identify promising configs
5. **Precision Study**: Iteratively refine promising configs to target precision
6. **Pairwise Comparison**: Welch's t-test for statistical significance

### Example Usage

```python
from experiments.statistical_testing import *
from experiments.dish_loading import load_recipes_from_json

# Load base parameters
base_params = load_recipes_from_json('experiments/comal_recipes.json')

# Generate configuration grid
configs = generate_configuration_grid(
    base_params=base_params,
    server_range=[5, 6, 7],
    cook_range=[8, 9, 10],
    host_range=[1],
    food_runner_range=[1, 2],
    busser_range=[0, 1]
)

# Run screening
screening_results = run_screening_parallel(configs, n_per_config=10)

# Apply subset selection
selection = subset_selection(screening_results)

# Run precision study on promising configs
final_results = {}
for idx in selection['may_be_best']:
    result = run_to_target_precision(
        params=screening_results[idx]['config'],
        pilot_samples=screening_results[idx]['samples'],
        target_relative_error=0.05
    )
    final_results[idx] = result
```

## 🔬 Key Features

### Simulation Engine
- **Discrete-event simulation** using SimPy
- **10-stage customer journey**: Arrival → Seating → Ordering → Cooking → Expo → Delivery → Dining → Checkout → Cleanup → Departure
- **Component-based cooking**: Dishes require parallel processing across multiple stations
- **Dual queue system**: Tasks can be handled by specialists or servers (redundancy)
- **Zone-based organization**: Tables and servers organized into zones

### Statistical Framework
- **Two-stage pilot methodology**: Efficient sample size determination
- **Bonferroni correction**: Controls family-wise error rate in multiple comparisons
- **Welch's t-test**: Robust pairwise comparisons (unequal variances)
- **Iterative precision**: Adapts sample size based on observed variance
- **Comprehensive visualization**: Heatmaps, convergence plots, pairwise comparisons

### Restaurant Model
- **35 menu items** from Comal Restaurant
- **5 kitchen stations**: Wood grill, salad, sauté, tortilla, guac
- **Realistic pricing**: $5-$78 per dish
- **NHPP arrivals**: Gaussian peak distribution (dinner rush)
- **Lognormal service times**: Right-skewed distributions

## 📚 Documentation

- **`PROJECT_ANALYSIS_DOCUMENTATION.md`**: Comprehensive analysis covering:
  - Statistical methods and assumptions
  - Project development history
  - Design decisions and trade-offs
  - Challenges and solutions
  - Results interpretation
  - IEOR field context

- **`PROJECT_STATUS_REPORT.md`**: Current development status and future work

- **`QUICK_REFERENCE_GUIDE.md`**: Quick reference for key metrics and results

## 🧪 Testing

Run the main simulation:
```bash
cd experiments
python -c "from runner import run_single_dish_sim; from dish_loading import load_recipes_from_json; params = load_recipes_from_json('comal_recipes.json'); run_single_dish_sim(params, verbose=True)"
```

## 📊 Key Metrics

### Financial
- **Net RevPASH**: (Revenue - Labor Cost) / (Seats × Hours) - Primary KPI
- **Gross RevPASH**: Revenue / (Seats × Hours)
- **Labor Cost %**: Labor / Revenue × 100%

### Operational
- **Service Rate**: Parties served / Parties arrived
- **Table Turnover**: Parties served / (Tables × Hours)
- **Utilization**: Server, cook, station utilization rates
- **Wait Times**: Table wait, kitchen time, total time

## 🛠️ Technology Stack

- **SimPy 4.1+**: Discrete-event simulation engine
- **NumPy 2.0+**: Numerical computations
- **Pandas 2.0+**: Data analysis
- **SciPy 1.10+**: Statistical functions
- **Matplotlib 3.10+**: Visualization
- **Seaborn**: Statistical visualization
- **Streamlit**: Interactive dashboard (GUI)

## 📝 Key Learnings

1. **Kitchen capacity is the primary bottleneck** - Cook count more critical than server count
2. **Diminishing returns appear quickly** - Optimal at 9 cooks, 10th cook adds cost without proportional benefit
3. **Specialist roles have low ROI** - Food runners and bussers show minimal impact
4. **Two-stage pilot essential** - Variance estimates guide efficient sample size allocation
5. **Screening dramatically reduces cost** - 69% reduction in total simulation runs

## 🔮 Future Work

- Sensitivity analysis on arrival rates and service times
- Scenario analysis (weekend vs weekday, special events)
- Model validation with real restaurant data
- Extended replications for final configurations
- Customer abandonment modeling
- Variable staffing by hour

## 👥 Authors

IEOR 174 Project - Restaurant Simulation Team

## 📄 License

This project is for academic purposes as part of IEOR 174 coursework.

## 🙏 Acknowledgments

- Comal Restaurant (Berkeley, CA) for menu data
- IEOR 174 course instructors
- SimPy development team

---

**For detailed analysis and methodology, see `PROJECT_ANALYSIS_DOCUMENTATION.md`**

