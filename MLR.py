import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature
import matplotlib.patheffects as pe
import textwrap
import matplotlib.colors as colors
import seaborn as sns
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
import numpy as np

# load all datasets
# load origin node file
ds = pd.read_csv("datasets/data_viz/TC_origin_node_count_perSubbasin_SyCLoPS.csv")

# load lifespan annual mean file
ls = pd.read_csv("datasets/data_viz/lifespan_annual_mean_per_origin_subbasin.csv")

# load wind shear 
shear = pd.read_csv("datasets/u-wind/post_processing/wind_shear_850_200_yearly_by_subbasin.csv")

# load max mean wind speed
vm = pd.read_csv("datasets/data_viz/max_wind_speed_annual_mean_allTimeSteps_PW.csv")

# load sst anom
sst_anom = pd.read_csv("datasets/COBE2 SST/post-processing/sst_anom_moving_window_bySubbasin_table.csv")

# load sst mean
sst_mean = pd.read_csv("datasets/COBE2 SST/post-processing/sst_annual_mean_bySubbasin_table.csv")

# load RH 600hPa 
ds2 = pd.read_csv("datasets/data_viz/RH_600hPa_yearly_mean_perSubbasin.csv")

# load MSLP anom
mslp_anom = pd.read_csv("datasets/MSLP/post-processing/MSLP_anom_moving_window_bySubbasin_table.csv")

# load MSLP mean
mslp_mean = pd.read_csv("datasets/MSLP/post-processing/MSLP_annual_mean_bySubbasin_table.csv")

# print(mslp_mean)

# reformat origins and rh tables
origins = ds.melt(
    id_vars="year",
    value_vars=ds.columns.drop(["year", "Total"]),
    var_name="sub_basin",
    value_name="origin_node_count"
)

rh = ds2.melt(
    id_vars="year",
    var_name="sub_basin",
    value_name="rh600"
)

# drop unamed columns
ls = ls.loc[:, ~ls.columns.str.contains("^Unnamed")]
sst_anom = sst_anom.loc[:, ~sst_anom.columns.str.contains("^Unnamed")]
vm = vm.loc[:, ~vm.columns.str.contains("^Unnamed")]
shear = shear.loc[:, ~shear.columns.str.contains("^Unnamed")]
mslp_anom = mslp_anom.loc[:, ~mslp_anom.columns.str.contains("^Unnamed")]
sst_mean = sst_mean.loc[:, ~sst_mean.columns.str.contains("^Unnamed")]
mslp_mean = mslp_mean.loc[:, ~mslp_mean.columns.str.contains("^Unnamed")]

# make sure column names match across datasets
origins = origins.rename(columns={"sub_basin": "sub_basin_name"})
ls = ls.rename(columns={"sub_basin_origin": "sub_basin_name"})
rh = rh.rename(columns={"sub_basin": "sub_basin_name"})
vm = vm[["year", "sub_basin_name", "vm"]]
sst_anom = sst_anom.rename(columns={"mean_anom": "sst_anom"})
sst_mean = sst_mean.rename(columns={"mean": "sst_mean"})

# merge into one table on year and sub basin
merged = (
    origins
    .merge(
        ls,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        shear,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        vm,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        sst_anom,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        rh,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        mslp_anom,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        sst_mean,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        mslp_mean,
        on=["year", "sub_basin_name"],
        how="outer"
    )
)

# filter to time period where data exists across all variables
merged = merged[(merged["year"] >= 1989) & (merged["year"] <= 2014)]

# print(merged)

########################################################################################################################

# # standardize variables for MLR

predictors = ["shear", "vm", "mslp_mean","mslp_anom", "sst_mean", "sst_anom", "rh600"]

# results = {}

# for basin, group in merged.groupby("sub_basin_name"):

#     # remove rows with missing values
#     group = group.dropna(
#         subset=["origin_node_count"] + predictors
#     )

#     # skip if too few observations or no variation in response
#     if len(group) < 10:
#         continue

#     if group["origin_node_count"].nunique() < 2:
#         continue

#     # standardize predictors
#     scaler = StandardScaler()
#     group[predictors] = scaler.fit_transform(group[predictors])

#     # run standardized MLR
#     model = smf.ols(
#         "origin_node_count ~ shear + mslp_mean + sst_mean + rh600",
#         data=group
#     ).fit()

#     results[basin] = model

#     # print(basin)
#     # print(results[basin].summary())
#     # print(f"{basin}: condition number = {model.condition_number:.1f}")

# # combine results into one table per subbasin
# coef_results = []

# for basin, model in results.items():

#     row = {
#         "sub_basin": basin,
#         "R2": model.rsquared,
#         "adj_R2": model.rsquared_adj,
#         "n": int(model.nobs)
#     }

#     # add coefficients
#     for predictor, coef in model.params.items():
#         row[f"{predictor}_coef"] = coef

#     # add p-values
#     for predictor, pval in model.pvalues.items():
#         row[f"{predictor}_pval"] = pval

#     coef_results.append(row)

# coef_df = pd.DataFrame(coef_results)

# print(coef_df)

# # save to csv
# coef_df.to_csv("datasets/data_viz/MLR_origin_nodes_standardized_results_v4.csv")

########################################################################################################################

# # # check VIF
# from statsmodels.stats.outliers_influence import variance_inflation_factor
# import statsmodels.api as sm

# vif_results = {}

# for basin, group in merged.groupby("sub_basin_name"):

#     group = group.dropna(subset=predictors)

#     if len(group) < 10:
#         continue

#     X = pd.DataFrame(
#         StandardScaler().fit_transform(group[predictors]),
#         columns=predictors
#     )

#     X = sm.add_constant(X)

#     vif = pd.DataFrame({
#         "Variable": X.columns,
#         "VIF": [variance_inflation_factor(X.values, i)
#                 for i in range(X.shape[1])]
#     })

#     vif_results[basin] = vif

# for basin, vif in vif_results.items():
#     print(f"\n{basin}")
#     print(vif)

########################################################################################################################

# LASSO to find best predictor variables
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LassoCV
from sklearn.impute import SimpleImputer
from sklearn.metrics import r2_score, mean_squared_error

# predictors
vars = [
    "shear",
    "vm",
    "sst_anom",
    "rh600",
    "mslp_anom",
    "sst_mean",
    "mslp_mean"
]

# lasso function
def run_lasso(df, target, predictors):

    # Keep only needed columns
    data = df[[target] + predictors].copy()

    # Remove rows where dependent variable is missing
    data = data.dropna(subset=[target])

    X = data[predictors]
    y = data[target]

    # LASSO pipeline
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("lasso", LassoCV(
            cv=5,
            random_state=42,
            max_iter=10000
        ))
    ])

    # Fit
    model.fit(X, y)

    # Predictions
    y_pred = model.predict(X)

    # Extract coefficients
    coef = pd.Series(
        model.named_steps["lasso"].coef_,
        index=predictors
    )

    # Sort by importance
    coef = coef.sort_values(
        key=abs,
        ascending=False
    )

    print("\nTarget:", target)
    print("-------------------------")
    print("Best alpha:", model.named_steps["lasso"].alpha_)
    print("\nSelected variables:")
    print(coef[coef != 0])

    print("\nPerformance:")
    print("R²:", r2_score(y, y_pred))
    print(
        "RMSE:",
        np.sqrt(mean_squared_error(y, y_pred))
    )

    return model, coef

# run lasso
origin_model, origin_coef = run_lasso(
    merged,
    target="origin_node_count",
    predictors=vars
)





########################################################################################################################

# # variable selection for multiple linear regression
# vars = [
#     "origin_node_count",
#     "shear",
#     "vm",
#     "mean_anom",
#     "rh600"
# ]
# reg = merged[vars].dropna()

# # run MLR
# results = {}

# for basin, group in merged.groupby("sub_basin_name"):

#     group = group.dropna(
#         subset=["origin_node_count", "shear", "vm", "mean_anom", "rh600"]
#     )

#     # skip insufficient data or no variation
#     if len(group) < 10:
#         print(f"Skipping {basin}: insufficient data ({len(group)} rows)")
#         continue

#     if group["origin_node_count"].nunique() < 2:
#         print(f"Skipping {basin}: origin_node_count has no variation")
#         continue

#     model = smf.ols(
#         "origin_node_count ~ shear + vm + mean_anom + rh600",
#         data=group
#     ).fit()

#     results[basin] = model
#     print(basin)
#     print(results[basin].summary())

