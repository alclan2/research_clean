import pandas as pd
from pathlib import Path
import itertools
import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# load threshold dataset
ds = pd.read_csv("datasets/data_viz/MLR/thresholds/threshold_days_perYr_table.csv")

# print(ds)

# rename columns for ease
ds = ds.rename(columns={"tc+td_origins": "tc_td_origins"})
ds = ds.rename(columns={"tc+td_all_nodes": "tc_td_all_nodes"})

# select y variable
y = "tc_origins"

# select x variable
x = "tc_TH_one"

# drop NANs
dat = ds.dropna(subset=[y, x]).copy()

# store results per sub basin
results = []

for basin, basin_data in dat.groupby("sub_basin_name"):

    model = smf.glm(
        formula=f"{y} ~ {x}",
        data=basin_data,
        family=sm.families.Poisson()
    ).fit()

    beta = model.params[x]
    se = model.bse[x]
    p = model.pvalues[x]

    ci_low, ci_high = model.conf_int().loc[x]

    dispersion = sum(model.resid_pearson ** 2) / model.df_resid

    results.append({
        "sub_basin": basin,
        "n": len(basin_data),
        "beta": beta,
        "SE": se,
        "p_value": p,
        "CI_low": ci_low,
        "CI_high": ci_high,
        "rate_ratio": np.exp(beta),
        "RR_CI_low": np.exp(ci_low),
        "RR_CI_high": np.exp(ci_high),
        "dispersion": dispersion
    })

results_df = pd.DataFrame(results)

# print(results_df)

# save results to csv
# results_df.to_csv("datasets/data_viz/MLR/thresholds/poisson_threshold_atleastTwoThresholds_vs_tctdOrigins.csv")

# plot x vs y
basins = [
    "Caribbean",
    "Central Atlantic",
    "Deep Tropics",
    "Eastern Tropics",
    "Gulf (A)",
    "Gulf (B)",
    "Northeastern Seaboard",
    "Southeastern Seaboard",
    "Subtropical Atlantic"
]

plot_dat = dat[dat["sub_basin_name"].isin(basins)].copy()

g = sns.lmplot(
    data=plot_dat,
    x=x,
    y=y,
    col="sub_basin_name",
    col_wrap=3,
    height=3,
    aspect=1.2,
    sharex = False,
    sharey = False,
    scatter_kws={
        "s": 40,
        "alpha": 0.7
    },
    line_kws={
        "color": "black",
        "linewidth": 2
    }
)

# Axis titles
g.set_axis_labels(
    "Days per Year One TC Threshold Is Satisfied",
    "TC Origins"
)

# Make subplot titles cleaner
g.set_titles("{col_name}")

# Adjust spacing
g.figure.subplots_adjust(
    top=0.90,
    wspace=0.20,
    hspace=0.30
)

# Overall figure title
g.figure.suptitle(
    "TC Origins vs. TC Threshold Days",
    fontsize=16,
    fontweight="bold"
)

# plt.savefig("images/data_viz/MLR/thresholds/threshold_atleastOneThresholds_vs_tcOrigins_perSb.png")
plt.show()