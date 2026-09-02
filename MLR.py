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

# load MSLP anom (from NOAA - independent variable)
mslp_anom = pd.read_csv("datasets/MSLP/post-processing/MSLP_anom_moving_window_bySubbasin_table.csv")

# load MSLP mean (from NOAA - independent variable)
mslp_mean = pd.read_csv("datasets/MSLP/post-processing/MSLP_annual_mean_bySubbasin_table.csv")

# load GPI EN data
gpi = pd.read_csv("datasets/GPI/GPI_EN_calc/GPI_annual_mean_perSubbasin.csv")

# load IKE mean data
ike_mean = pd.read_csv("datasets/IKE/IKE_TC+TD_mean_timeseries.png")

# load IKE accumulated data
ike_sum = pd.read_csv("datasets/IKE/IKE_TC+TD_accum_timeseries.png")

# load MSLP mean (from SYCLOPS - dependent variable)
mslp_mean_y = pd.read_csv("datasets/MSLP/mslp_mean_timeseries_perYr_perSB_SYCLOPS.csv")

# load MSLP sum (from SYCLOPS - dependent variable)
mslp_sum_y = pd.read_csv("datasets/MSLP/mslp_summed_timeseries_perYr_perSB_SYCLOPS.csv")

# load MSLP anom from environmental norm (from SYCLOPS - dependent variable)
mslp_anom_y = pd.read_csv("datasets/MSLP/mslp_anom_timeseries_perYr_perSB_SYCLOPS.csv")

# load MPI (maximum potential intensity) from python package calc
mpi = pd.read_csv("datasets/potential_intensity/vmax_max_perYr_perSb.csv")

# load PI (potential intensity) from python package calc
pi = pd.read_csv("datasets/potential_intensity/vmax_mean_perYr_perSb.csv")

# print(mslp_sum_y)
# print(mslp_anom_y)

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
mslp_mean_y = mslp_mean_y.loc[:, ~mslp_mean_y.columns.str.contains("^Unnamed")]
mslp_sum_y = mslp_sum_y.loc[:, ~mslp_sum_y.columns.str.contains("^Unnamed")]
mslp_anom_y = mslp_anom_y.loc[:, ~mslp_anom_y.columns.str.contains("^Unnamed")]
gpi = gpi.loc[:, ~gpi.columns.str.contains("^Unnamed")]
rh = rh.loc[:, ~rh.columns.str.contains("^Unnamed")]
mpi = mpi.loc[:, ~mpi.columns.str.contains("^Unnamed")]
pi = pi.loc[:, ~pi.columns.str.contains("^Unnamed")]

# make sure column names match across datasets
origins = origins.rename(columns={"sub_basin": "sub_basin_name"})
ls = ls.rename(columns={"sub_basin_origin": "sub_basin_name"})
rh = rh.rename(columns={"sub_basin": "sub_basin_name"})
vm = vm[["year", "sub_basin_name", "vm"]]
sst_anom = sst_anom.rename(columns={"mean_anom": "sst_anom"})
sst_mean = sst_mean.rename(columns={"mean": "sst_mean"})
ike_mean = ike_mean.rename(columns={"IKE": "ike_mean"})
ike_sum = ike_sum.rename(columns={"IKE": "ike_sum"})
mslp_mean_y = mslp_mean_y.rename(columns={"MSLP": "mslp_mean_y"})
mslp_sum_y = mslp_sum_y.rename(columns={"MSLP": "mslp_sum_y"})
mslp_anom_y = mslp_anom_y.rename(columns={"MSLP_anom": "mslp_anom_y"})
mpi = mpi.rename(columns={"vmax": "mpi"})
pi = pi.rename(columns={"vmax": "pi"})

# print(pi.head())

# merge into one table on year and sub basin
merged = (
    origins
    .merge(
        ls,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        mslp_mean_y,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        mslp_sum_y,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        mslp_anom_y,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        mpi,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        pi,
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
predictors = ['rh600']

# save MLR results
results = {}

# save actual vs. predicted
predictions = {}

for basin, group in merged.groupby("sub_basin_name"):

    # remove rows with missing values
    group = group.dropna(
        subset=["mpi"] + predictors
    )

    # skip if too few observations or no variation in response
    if len(group) < 10:
        continue

    if group["mpi"].nunique() < 2:
        continue

    # standardize predictors
    group = group.copy()

    scaler = StandardScaler()
    group[predictors] = scaler.fit_transform(group[predictors])

    model = smf.ols(
        "mpi ~ rh600",
        data=group
    ).fit()

    results[basin] = model

    predictions[basin] = pd.DataFrame({
        "Actual": group["mpi"],
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
coef_df.to_csv(f"datasets/data_viz/MLR/intensity/v3_runs/MLR_mpi_vs_rh600_coef_table.csv")

######################################################################################################

# # # actual v predicted for TWO variables
# choose sub-basin
sb = "Subtropical Atlantic"

# print(coef_df[coef_df['sub_basin']==sb])

model = results[sb]

# get data for this basin
group = merged[merged["sub_basin_name"] == sb].dropna(
    subset=["mpi"] + predictors
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
    group["mpi"],
    color="black",
    linewidth=2,
    marker="o",
    label="Observed MPI"
)

# predicted counts
ax.plot(
    group["year"],
    group["Predicted"],
    color="tab:blue",
    linewidth=2,
    linestyle="--",
    marker="s",
    label="Predicted MPI"
)

ax.set_xlabel("Year")
ax.set_ylabel("MPI (m/s)")

ax.set_title(
    f"{sb}\nObserved vs. Predicted Maximum Potential Intensity\n"
    f"Multiple Linear Regression ($R^2$ = {model.rsquared:.2f})"
)

ax.legend()

plt.tight_layout()
plt.savefig(f"images/data_viz/MLR/intensity/v3_runs/actual_v_predicted_mpi_rh600_{sb}.png")
plt.show()

######################################################################################################

# # # actual v predicted for ONE variable
# # choose sub-basin
# basin = "Subtropical Atlantic"

# model = results[basin]

# # get data for this basin
# group = merged[merged["sub_basin_name"] == basin].dropna(
#     subset=["ike_mean"] + predictors
# ).copy()

# # save original shear for plotting
# var_original = group["sst_mean"].copy()

# # standardize predictors for model prediction
# scaler = StandardScaler()
# group[predictors] = scaler.fit_transform(group[predictors])

# # predictions
# group["Predicted"] = model.predict(group)

# # put back in time order
# group["sst_mean_original"] = var_original
# group = group.sort_values("year")

# # create figure
# fig, ax1 = plt.subplots(figsize=(14, 6))

# # actual and predicted TC counts
# ax1.plot(
#     group["year"],
#     group["ike_mean"],
#     color="black",
#     linewidth = 2,
#     label="Actual IKE (TJ)",
#     zorder = 3
# )

# ax1.plot(
#     group["year"],
#     group["Predicted"],
#     color="tab:blue",
#     linestyle="--",
#     linewidth = 2,
#     label="Predicted IKE (TJ)",
#     zorder = 3
# )

# ax1.set_xlabel("Year")
# ax1.set_ylabel("IKE", color="black")


# # secondary axis for shear
# ax2 = ax1.twinx()

# ax2.plot(
#     group["year"],
#     group["sst_mean_original"],
#     color="red",
#     linewidth=1,
#     alpha=0.5,
#     zorder=1,
#     label = "Mean SST (°C)"
# )

# ax2.set_ylabel("Mean SST (°C)")


# # title with R2
# ax1.set_title(
#     f"{basin}\nActual vs. Predicted Integrated Kinetic Energy and Sea Surface Temperature\n$R^2$ = {model.rsquared:.2f}",
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
# plt.savefig(f"images/data_viz/MLR/IKE/sst/actual_vs_predicted_ikeMean_sstMean_{basin}.png")
# plt.show()

# save to csv
# coef_df.to_csv("datasets/data_viz/MLR_origin_nodes_standardized_results_shear_mslpMean_sstAnom_rh600.csv")

########################################################################################################################

# check VIF
from statsmodels.stats.outliers_influence import variance_inflation_factor
import statsmodels.api as sm

vif_tables = []

for basin, group in merged.groupby("sub_basin_name"):

    group = group.dropna(subset=predictors)

    if len(group) < 10:
        continue

    X = pd.DataFrame(
        StandardScaler().fit_transform(group[predictors]),
        columns=predictors
    )

    X = sm.add_constant(X)

    vif = pd.DataFrame({
        "Variable": X.columns,
        "VIF": [
            variance_inflation_factor(X.values, i)
            for i in range(X.shape[1])
        ]
    })


    # Add basin name
    vif["Basin"] = basin

    vif_tables.append(vif)

# Combine into one DataFrame
vif_summary = pd.concat(vif_tables, ignore_index=True)

# Optional: reorder columns
vif_summary = vif_summary[["Basin", "Variable", "VIF"]]

# print(vif_summary[vif_summary['Basin']==sb])

# save to csv
# vif_summary.to_csv(f"datasets/data_viz/MLR/intensity/v3_runs/VIF_mpi_vs_sstMean.csv")

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
