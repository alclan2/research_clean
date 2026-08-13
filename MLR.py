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
import math

# load all datasets
# load origin node file
ds = pd.read_csv("datasets/data_viz/TC+TD_origin_node_count_perSubbasin_SyCLoPS.csv")

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

# load GPI EN data
gpi = pd.read_csv("datasets/GPI/GPI_EN_calc/GPI_annual_mean_perSubbasin.csv")

# load IKE mean data
ike_mean = pd.read_csv("datasets/IKE/IKE_TC+TD_mean_timeseries.png")

# load IKE accumulated data
ike_sum = pd.read_csv("datasets/IKE/IKE_TC+TD_accum_timeseries.png")

# print(gpi)

# reformat origins, rh, and IKE tables
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

ike_mean = ike_mean[['year', 'sub_basin_name', 'IKE']]
ike_sum = ike_sum[['year', 'sub_basin_name', 'IKE']]

# drop unamed columns
ls = ls.loc[:, ~ls.columns.str.contains("^Unnamed")]
sst_anom = sst_anom.loc[:, ~sst_anom.columns.str.contains("^Unnamed")]
vm = vm.loc[:, ~vm.columns.str.contains("^Unnamed")]
shear = shear.loc[:, ~shear.columns.str.contains("^Unnamed")]
mslp_anom = mslp_anom.loc[:, ~mslp_anom.columns.str.contains("^Unnamed")]
sst_mean = sst_mean.loc[:, ~sst_mean.columns.str.contains("^Unnamed")]
mslp_mean = mslp_mean.loc[:, ~mslp_mean.columns.str.contains("^Unnamed")]
ike_mean = ike_mean.loc[:, ~ike_mean.columns.str.contains("^Unnamed")]
ike_sum = ike_sum.loc[:, ~ike_sum.columns.str.contains("^Unnamed")]

# make sure column names match across datasets
origins = origins.rename(columns={"sub_basin": "sub_basin_name"})
ls = ls.rename(columns={"sub_basin_origin": "sub_basin_name"})
rh = rh.rename(columns={"sub_basin": "sub_basin_name"})
vm = vm[["year", "sub_basin_name", "vm"]]
sst_anom = sst_anom.rename(columns={"mean_anom": "sst_anom"})
sst_mean = sst_mean.rename(columns={"mean": "sst_mean"})
ike_mean = ike_mean.rename(columns={"IKE": "ike_mean"})
ike_sum = ike_sum.rename(columns={"IKE": "ike_sum"})

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
    .merge(
        gpi,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        ike_mean,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        ike_sum,
        on=["year", "sub_basin_name"],
        how="outer"
    )
)

# filter to time period where data exists across all variables
merged = merged[(merged["year"] >= 1940) & (merged["year"] <= 2025)]

# print(merged)

########################################################################################################################

# standardize variables for MLR
predictors = ['ike_mean', 'sst_mean', 'gpi']

# save MLR results
results = {}

# save actual vs. predicted
predictions = {}

for basin, group in merged.groupby("sub_basin_name"):

    # remove rows with missing values
    group = group.dropna(
        subset=["origin_node_count"] + predictors
    )

    # skip if too few observations or no variation in response
    if len(group) < 10:
        continue

    if group["origin_node_count"].nunique() < 2:
        continue

    # standardize predictors
    group = group.copy()

    scaler = StandardScaler()
    group[predictors] = scaler.fit_transform(group[predictors])

    model = smf.ols(
        "origin_node_count ~ ike_mean + sst_mean + gpi",
        data=group
    ).fit()

    results[basin] = model

    predictions[basin] = pd.DataFrame({
        "Actual": group["origin_node_count"],
        "Predicted": model.fittedvalues
})  

    # print(basin)
    # print(results[basin].summary())
    # print(f"{basin}: condition number = {model.condition_number:.1f}")

# combine results into one table per subbasin
coef_results = []

for basin, model in results.items():

    row = {
        "sub_basin": basin,
        "R2": model.rsquared,
        "adj_R2": model.rsquared_adj,
        "n": int(model.nobs)
    }

    # add coefficients
    for predictor, coef in model.params.items():
        row[f"{predictor}_coef"] = coef

    # add p-values
    for predictor, pval in model.pvalues.items():
        row[f"{predictor}_pval"] = pval

    coef_results.append(row)

coef_df = pd.DataFrame(coef_results)

print(coef_df)

# save coef table as csv
# coef_df.to_csv("datasets/data_viz/MLR/TC+TD/single_var_coef_tables/MLR_origin_nodes_vs_ike_mean_coef_table.csv")

######################################################################################################

# # # actual v predicted for TWO variables
# choose sub-basin
sb = "Northeastern Seaboard"

model = results[sb]

# get data for this basin
group = merged[merged["sub_basin_name"] == sb].dropna(
    subset=["origin_node_count"] + predictors
).copy()

# standardize predictors exactly as during model fitting
scaler = StandardScaler()
group[predictors] = scaler.fit_transform(group[predictors])

# predict origin node counts using BOTH predictors
group["Predicted"] = model.predict(group)

# put back in chronological order
group = group.sort_values("year")

# plot
fig, ax = plt.subplots(figsize=(14,6))

# observed counts
ax.plot(
    group["year"],
    group["origin_node_count"],
    color="black",
    linewidth=2,
    marker="o",
    label="Observed TC+TD Origin Nodes"
)

# predicted counts
ax.plot(
    group["year"],
    group["Predicted"],
    color="tab:blue",
    linewidth=2,
    linestyle="--",
    marker="s",
    label="Predicted TC+TD Origin Nodes"
)

ax.set_xlabel("Year")
ax.set_ylabel("TC+TD Origin Nodes")

ax.set_title(
    f"{sb}\nObserved vs. Predicted TC+TD Origin Nodes\n"
    f"Multiple Linear Regression ($R^2$ = {model.rsquared:.2f})"
)

ax.legend()

plt.tight_layout()
plt.savefig(f"images/data_viz/MLR/TC+TD/gpi+sst_mean+ike_mean/actual_v_predicted_origins_gpi+sstMean+ikeMean_{sb}.png")
plt.show()

######################################################################################################

# # # actual v predicted for ONE variable
# # choose sub-basin
# basin = "Southeastern Seaboard"

# model = results[basin]

# # get data for this basin
# group = merged[merged["sub_basin_name"] == basin].dropna(
#     subset=["origin_node_count"] + predictors
# ).copy()

# # save original shear for plotting
# var_original = group["ike_sum"].copy()

# # standardize predictors for model prediction
# scaler = StandardScaler()
# group[predictors] = scaler.fit_transform(group[predictors])

# # predictions
# group["Predicted"] = model.predict(group)

# # put back in time order
# group["ike_sum_original"] = var_original
# group = group.sort_values("year")

# # create figure
# fig, ax1 = plt.subplots(figsize=(14, 6))

# # actual and predicted TC counts
# ax1.plot(
#     group["year"],
#     group["origin_node_count"],
#     color="black",
#     linewidth = 2,
#     label="TC+TD Origin Nodes (count)",
#     zorder = 3
# )

# ax1.plot(
#     group["year"],
#     group["Predicted"],
#     color="tab:blue",
#     linestyle="--",
#     linewidth = 2,
#     label="TC+TD Origin Nodes (count)",
#     zorder = 3
# )

# ax1.set_xlabel("Year")
# ax1.set_ylabel("TC+TD Origin Nodes", color="black")


# # secondary axis for shear
# ax2 = ax1.twinx()

# ax2.plot(
#     group["year"],
#     group["ike_sum_original"],
#     color="red",
#     linewidth=1,
#     alpha=0.5,
#     zorder=1,
#     label = "Accumulated IKE (TJ)"
# )

# ax2.set_ylabel("Accumulated IKE (TJ)")


# # title with R2
# ax1.set_title(
#     f"{basin}\nActual vs. Predicted TC+TD Origin Locations and Accumulated IKE\n$R^2$ = {model.rsquared:.2f}",
#     fontsize=12
# )

# # combine legends
# lines1, labels1 = ax1.get_legend_handles_labels()
# lines2, labels2 = ax2.get_legend_handles_labels()

# ax1.legend(
#     lines1 + lines2,
#     labels1 + labels2,
#     loc="center left",
#     bbox_to_anchor=(1.08, 0.5)
# )

# plt.tight_layout()
# # plt.savefig(f"images/data_viz/MLR/TC+TD/ike/actual_vs_predicted_origin_nodes_ikeAccum_{basin}.png")
# plt.show()

# # save to csv
# coef_df.to_csv("datasets/data_viz/MLR_origin_nodes_standardized_results_shear_mslpMean_sstAnom_rh600.csv")

########################################################################################################################

# # check VIF
# from statsmodels.stats.outliers_influence import variance_inflation_factor
# import statsmodels.api as sm

# vif_tables = []

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
#         "VIF": [
#             variance_inflation_factor(X.values, i)
#             for i in range(X.shape[1])
#         ]
#     })


#     # Add basin name
#     vif["Basin"] = basin

#     vif_tables.append(vif)

# # Combine into one DataFrame
# vif_summary = pd.concat(vif_tables, ignore_index=True)

# # Optional: reorder columns
# vif_summary = vif_summary[["Basin", "Variable", "VIF"]]

# print(vif_summary)

# # # save to csv
# # # vif_summary.to_csv("datasets/data_viz/MLR/VIF_shear_mslpAnom_sstMean_rh600.csv")

########################################################################################################################

# # LASSO to find best predictor variables
# from sklearn.pipeline import Pipeline
# from sklearn.preprocessing import StandardScaler
# from sklearn.linear_model import LassoCV
# from sklearn.impute import SimpleImputer
# from sklearn.metrics import r2_score, mean_squared_error

# # predictors
# vars = [
#     "shear",
#     "vm",
#     "sst_anom",
#     "rh600",
#     "mslp_anom",
#     "sst_mean",
#     "mslp_mean"
# ]

# # lasso function
# def run_lasso(df, target, predictors):

#     # Keep only needed columns
#     data = df[[target] + predictors].copy()

#     # Remove rows where dependent variable is missing
#     data = data.dropna(subset=[target])

#     X = data[predictors]
#     y = data[target]

#     # LASSO pipeline
#     model = Pipeline([
#         ("imputer", SimpleImputer(strategy="median")),
#         ("scaler", StandardScaler()),
#         ("lasso", LassoCV(
#             cv=5,
#             random_state=42,
#             max_iter=10000
#         ))
#     ])

#     # Fit
#     model.fit(X, y)

#     # Predictions
#     y_pred = model.predict(X)

#     # Extract coefficients
#     coef = pd.Series(
#         model.named_steps["lasso"].coef_,
#         index=predictors
#     )

#     # Sort by importance
#     coef = coef.sort_values(
#         key=abs,
#         ascending=False
#     )

#     print("\nTarget:", target)
#     print("-------------------------")
#     print("Best alpha:", model.named_steps["lasso"].alpha_)
#     print("\nSelected variables:")
#     print(coef[coef != 0])

#     print("\nPerformance:")
#     print("R²:", r2_score(y, y_pred))
#     print(
#         "RMSE:",
#         np.sqrt(mean_squared_error(y, y_pred))
#     )

#     return model, coef

# # run lasso
# origin_model, origin_coef = run_lasso(
#     merged,
#     target="origin_node_count",
#     predictors=vars
# )

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

