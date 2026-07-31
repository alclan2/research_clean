import pandas as pd
from pathlib import Path
import itertools
import statsmodels.api as sm
import statsmodels.formula.api as smf
import numpy as np

# load datasets
folder = Path("datasets/ALCC/post_python_processing")

files = folder.glob("ALCC_tc_output_origins_perYr_wSubbasin_*")

# read all files
dfs = [pd.read_csv(f) for f in files]

# combine into one dataframe
alcc = pd.concat(dfs, ignore_index=True)

# print(alcc.head())

# pivot by origin count per year per subbasin per mode
annual_origins = (
    alcc
    .groupby(["year", "sub_basin_start", "mode"])
    .size()
    .reset_index(name="origin_node_count")
)

# print(annual_origins)

# make sure years with 0 origin nodes are added (need for poisson distribution)
years = annual_origins["year"].unique()
basins = annual_origins["sub_basin_start"].unique()
modes = annual_origins["mode"].unique()

full_index = pd.DataFrame(
    itertools.product(years, basins, modes),
    columns=["year", "sub_basin_start", "mode"]
)

annual_origins = (
    full_index
    .merge(
        annual_origins,
        on=["year", "sub_basin_start", "mode"],
        how="left"
    )
    .fillna({"origin_node_count": 0})
)

annual_origins["origin_node_count"] = annual_origins["origin_node_count"].astype(int)

# get lambda parameter per mode per subbasin
lambda_df = (
    annual_origins
    .groupby(["sub_basin_start", "mode"])
    ["origin_node_count"]
    .mean()
    .reset_index(name="lambda")
)

# format so oo (neutral) is the reference
annual_origins["mode"] = pd.Categorical(
    annual_origins["mode"],
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

for basin in annual_origins.sub_basin_start.unique():

    subset = annual_origins[
        annual_origins.sub_basin_start == basin
    ]

    model = smf.glm(
        formula="origin_node_count ~ C(mode, Treatment(reference='oo'))",
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

# save to csv
# results_df.to_csv("datasets/data_viz/ALCC_poisson_results.csv")

###################################################################################################

# # check for over dispersion
# dispersion = []

# for item in models:
#     model = item["model"]

#     dispersion.append(
#         {
#             "basin": item["basin"],
#             "dispersion": model.pearson_chi2 / model.df_resid
#         }
#     )

# dispersion_df = pd.DataFrame(dispersion)

# # print(dispersion_df)