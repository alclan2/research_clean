import pandas as pd
from pathlib import Path
import itertools
import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np

# # read in dataset
TC = 'TC.0'
# alcc = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{TC}_all_counts_density_avg_table.csv")

base = Path(f"datasets/ALCC/post_python_processing/{TC}")

runs = ["001", "002"]

dfs = []

for run in runs:
    folder = base / run / "density"

    files = folder.glob(
        f"ALCC_{TC}_{run}_output_density_perYr_wSubbasin_*"
    )

    run_dfs = [pd.read_csv(f) for f in files]

    # combine files within this run
    run_df = pd.concat(run_dfs, ignore_index=True)

    # identify model run
    run_df["run"] = run

    dfs.append(run_df)

# combine both model runs
alcc = pd.concat(dfs, ignore_index=True)

# pivot
annual_counts = (
    alcc
    .groupby(["year", "run", "sub_basin_start", "mode"])
    .size()
    .reset_index(name="count")
)

# print(annual_counts)

# make sure years with 0 origin nodes are added (need for poisson distribution)
years = annual_counts["year"].unique()
runs = annual_counts["run"].unique()
basins = annual_counts["sub_basin_start"].unique()
modes = annual_counts["mode"].unique()

full_index = pd.DataFrame(
    itertools.product(years, runs, basins, modes),
    columns=["year", "run", "sub_basin_start", "mode"]
)

annual_counts = (
    full_index
    .merge(
        annual_counts,
        on=["year", "run", "sub_basin_start", "mode"],
        how="left"
    )
    .fillna({"count": 0})
)

annual_counts["count"] = annual_counts["count"].astype(int)

# get lambda parameter per mode per subbasin
lambda_df = (
    annual_counts
    .groupby(["sub_basin_start", "mode"])
    ["count"]
    .mean()
    .reset_index(name="lambda")
)

# format so oo (neutral) is the reference
annual_counts["mode"] = pd.Categorical(
    annual_counts["mode"],
    categories=[
        "oo",
        "nn",
        "pn",
        "np",
        "pp",
        "no",
        "on",
        "po",
        "op"
    ],
    ordered=False
)

# fit poisson distribution per subbasin
models = []
results = []

for basin in annual_counts.sub_basin_start.unique():

    subset = annual_counts[
        annual_counts.sub_basin_start == basin
    ]

    # Skip basins with no observed counts
    if subset["count"].sum() == 0:
        print(f"Skipping {basin}: all counts are zero.")
        continue

    model = smf.glm(
        formula="count ~ C(mode, Treatment(reference='oo'))",
        data=subset,
        family=sm.families.Poisson()
    ).fit()

    # save model for diagnostics
    models.append(
        {
            "basin": basin,
            "model": model
        }
    )

    # save coefficients
    for term, coef, pval in zip(
        model.params.index,
        model.params.values,
        model.pvalues.values
    ):
        if term == "Intercept":
            continue

        results.append(
            {
                "basin": basin,
                "mode": term.split("T.")[-1].replace("]", ""),
                "coefficient": coef,
                "rate_ratio": np.exp(coef),
                "p_value": pval
            }
        )

# convert results to dataframe
results_df = pd.DataFrame(results)

# sort for easier viewing
results_df = results_df.sort_values(
    ["basin", "p_value"]
)

# round numeric columns
results_df = results_df.round({
    "coefficient": 3,
    "rate_ratio": 2,
    "lower_ci": 2,
    "upper_ci": 2,
    "p_value": 4
})

print(results_df.to_string(index=False))

print(subset["count"].describe())
print((subset["count"] == 0).mean())

# save to csv
# results_df.to_csv(f"datasets/data_viz/ALCC_{TC}_poisson_results.csv")

###################################################################################################

# check for over dispersion
dispersion = []

for item in models:
    model = item["model"]

    dispersion.append(
        {
            "basin": item["basin"],
            "dispersion": model.pearson_chi2 / model.df_resid
        }
    )

dispersion_df = pd.DataFrame(dispersion)

print(dispersion_df)