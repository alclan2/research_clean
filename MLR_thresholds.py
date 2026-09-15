import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature
import matplotlib.patheffects as pe
import textwrap
import matplotlib.colors as colors
from matplotlib.ticker import MaxNLocator
import xarray as xr
import math

# load sst file
sst = pd.read_csv("datasets/COBE2 SST/post-processing/sst_daily_mean_bySubbasin_table_v2.csv")

# load rh file
rh = pd.read_csv("datasets/RHUM/post-processing/rhum_daily_mean_bySubbasin_table.csv")

# load shear file
shear = pd.read_csv("datasets/u-wind/post_processing/shear_daily_mean_bySubbasin_table.csv")

# drop columns we don't need
sst = sst[['time', 'sub_basin_name', 'mean']]
rh = rh[['time', 'sub_basin_name', 'mean']]
shear = shear[['time', 'sub_basin_name', 'mean']]

# rename columns
sst = sst.rename(columns={"time": "date", "mean": "sst_mean"})
rh = rh.rename(columns={"time": "date", "mean": "rh600"})
shear = shear.rename(columns={"time": "date", "mean": "shear"})

# join tables
merged = (
    sst
    .merge(
        rh,
        on=["date", "sub_basin_name"],
        how="outer"
    )
    .merge(
        shear,
        on=["date", "sub_basin_name"],
        how="outer"
    )
)

# create threshold flag columns
merged["sst_TH"] = (merged["sst_mean"] >= 26.5).astype(int)
merged["rh600_TH"] = (merged["rh600"] >= 70).astype(int)
merged["shear_TH"] = (merged["shear"] < 10).astype(int)
merged["tc_TH"] = ((merged["sst_TH"] == 1) & (merged["rh600_TH"] == 1) & (merged["shear_TH"] == 1)).astype(int)
merged["tc_TH_one"] = ((merged["sst_TH"] == 1) | (merged["rh600_TH"] == 1) | (merged["shear_TH"] == 1)).astype(int)
merged["tc_TH_two"] = (((merged["sst_TH"] == 1) & (merged["rh600_TH"] == 1)) | ((merged["sst_TH"] == 1) & (merged["shear_TH"] == 1) | ((merged["shear_TH"] == 1) & (merged["rh600_TH"] == 1)))).astype(int)

# now pivot to count number of days where the thresholds are met per year
merged["date"] = pd.to_datetime(merged["date"])
merged["year"] = merged["date"].dt.year

# print(merged.head())

annual = (
    merged.groupby(["year", "sub_basin_name"])[
        ["sst_TH", "rh600_TH", "shear_TH", "tc_TH", "tc_TH_one", "tc_TH_two"]
    ]
    .sum()
    .reset_index()
)

# print(annual)

# load MSLP threshold file
mslp = pd.read_csv("datasets/data_viz/MLR/thresholds/mslp_daily_meanPerSB_bySubbasin_table.csv")
mslp = mslp[['year', 'sub_basin_name', 'days_below_threshold']]
mslp = mslp.rename(columns={"days_below_threshold": "mslp_TH"})

# print(mslp)

# # plot 
# variables = ["mslp_TH"]

# subbasins = mslp["sub_basin_name"].unique()

# # Set grid dimensions
# ncols = 4
# nrows = math.ceil(len(subbasins) / ncols)

# for variable in variables:

#     fig, axes = plt.subplots(
#         nrows=nrows,
#         ncols=ncols,
#         figsize=(14, 2 * nrows),
#         sharex=True,
#         sharey = True
#     )

#     # Make axes easy to loop over even if there's only one
#     axes = axes.flatten()

#     for ax, subbasin in zip(axes, subbasins):

#         sb = mslp[
#             mslp["sub_basin_name"] == subbasin
#         ]

#         ax.plot(
#             sb["year"],
#             sb[variable],
#             linewidth=2,
#             color = 'red'
#         )

#         ax.set_title(subbasin)
#         ax.set_ylabel("Days")
#         ax.set_xlim(1982, 2020)


#     # Hide unused subplot(s)
#     for ax in axes[len(subbasins):]:
#         ax.set_visible(False)

#     fig.suptitle(
#         f"Days per Year TC MSLP Threshold Was Met",
#         fontsize=16
#     )

#     fig.supxlabel("Year")

#     plt.subplots_adjust(hspace=0.6, wspace=0.5)
#     plt.tight_layout(rect=[0, 0, 1, 0.95])

#     # plt.savefig("images/data_viz/MLR/thresholds/MSLP_threshold_days_perSb.png")
#     plt.show()

####################################################################################################################

# load origin node file
ds = pd.read_csv("datasets/SyCLoPS/tc_density_allTIDs_perYr_perSb.csv")

# # print(ds.head())

# reformat 
origins = ds.rename(
    columns={
        "YEAR": "year",
        "sub_basin_name": "sub_basin",
        "tc_count": "origin_node_count"
    }
)[["year", "sub_basin", "origin_node_count"]]

# print(origins.head())

# rename 
origins = origins.rename(columns={"sub_basin": "sub_basin_name"})

# # print(origins)
# # print(mslp)

# merge with variables
table = (
    mslp
    .merge(
        origins,
        on=["year", "sub_basin_name"],
        how="outer"
    )
)

# # print(table)

subbasin = "Mid-latitudinal Atlantic"
variable = "mslp_TH"

sb = table[
    table["sub_basin_name"] == subbasin
].sort_values("year")

plt.figure(figsize=(10, 5))

plt.plot(
    sb["year"],
    sb["origin_node_count"],
    label="TC node count",
    color="black",
    linewidth=2
)

plt.plot(
    sb["year"],
    sb[variable],
    label="Days with MSLP Threshold Satisfied",
    color="purple",
    linewidth=2
)

plt.title(subbasin)
plt.xlabel("Year")
plt.ylabel("Count")
plt.xlim(1981, 2025)
plt.legend()
plt.grid(alpha=0.3)

plt.tight_layout()

plt.savefig(f"images/data_viz/MLR/thresholds/TC_allNodes/all_nodes_vs_{variable}_threshold_{subbasin}.png")
plt.show()

####################################################################################################################

# # correlation between threshold variables and dependents

# # load tc node files
# tc_allNodes = pd.read_csv("datasets/SyCLoPS/tc_density_allTIDs_perYr_perSb.csv")
# tctd_allNodes = pd.read_csv("datasets/SyCLoPS/tc+td_density_allTIDs_perYr_perSb.csv")
# tc_ogNodes = pd.read_csv("datasets/SyCLoPS/tc_density_uniqueTIDs_perYr_perSb.csv")
# tctd_ogNodes = pd.read_csv("datasets/SyCLoPS/tc+td_density_uniqueTIDs_perYr_perSb.csv")

# # rename columns
# tc_allNodes = tc_allNodes.rename(columns={"YEAR": "year", "tc_count": "tc_origins"})
# tctd_allNodes = tctd_allNodes.rename(columns={"YEAR": "year", "tc_count": "tc+td_origins"})
# tc_ogNodes = tc_ogNodes.rename(columns={"YEAR": "year", "tc_count": "tc_all_nodes"})
# tctd_ogNodes = tctd_ogNodes.rename(columns={"YEAR": "year", "tc_count": "tc+td_all_nodes"})

# # drop unamed columns
# tc_allNodes = tc_allNodes.loc[:, ~tc_allNodes.columns.str.contains("^Unnamed")]
# tctd_allNodes = tctd_allNodes.loc[:, ~tctd_allNodes.columns.str.contains("^Unnamed")]
# tc_ogNodes = tc_ogNodes.loc[:, ~tc_ogNodes.columns.str.contains("^Unnamed")]
# tctd_ogNodes = tctd_ogNodes.loc[:, ~tctd_ogNodes.columns.str.contains("^Unnamed")]

# # print(tc_allNodes.head())
# # print(tctd_allNodes.head())
# # print(tc_ogNodes.head())
# # print(tctd_ogNodes.head())

# # merge with variables
# tab = (
#     mslp
#     .merge(
#         tc_allNodes,
#         on=["year", "sub_basin_name"],
#         how="outer"
#     )
#     .merge(
#         tctd_allNodes,
#         on=["year", "sub_basin_name"],
#         how="outer"
#     )
#     .merge(
#         tc_ogNodes,
#         on=["year", "sub_basin_name"],
#         how="outer"
#     )
#     .merge(
#         tctd_ogNodes,
#         on=["year", "sub_basin_name"],
#         how="outer"
#     )        
# )

# print(tab)

# # check correlations
# env_vars = [
#     "mslp_TH"
# ]

# tc_vars = [
#     "tc_origins",
#     "tc+td_origins",
#     "tc_all_nodes",
#     "tc+td_all_nodes"
# ]

# corr_results = []

# for sub_basin, group in tab.groupby("sub_basin_name"):

#     for env in env_vars:
#         for tc in tc_vars:

#             corr = group[env].corr(group[tc])

#             corr_results.append({
#                 "sub_basin_name": sub_basin,
#                 "environmental_variable": env,
#                 "tc_variable": tc,
#                 "correlation": corr
#             })

# corr_results = pd.DataFrame(corr_results)

# print(corr_results)

# # save to csv
# corr_results.to_csv("datasets/data_viz/MLR/thresholds/MSLP_threshold_variable_correlations.csv")
