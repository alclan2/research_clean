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

print(annual)

# # plot 
# variables = ["tc_TH"]

# subbasins = annual["sub_basin_name"].unique()

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

#         sb = annual[
#             annual["sub_basin_name"] == subbasin
#         ]

#         ax.plot(
#             sb["year"],
#             sb[variable],
#             linewidth=2,
#             color = 'purple'
#         )

#         ax.set_title(subbasin)
#         ax.set_ylabel("Days")
#         ax.set_xlim(1982, 2020)


#     # Hide unused subplot(s)
#     for ax in axes[len(subbasins):]:
#         ax.set_visible(False)

#     fig.suptitle(
#         f"Days per Year TC Threshold Was Met (SST, RH, Shear)",
#         fontsize=16
#     )

#     fig.supxlabel("Year")

#     plt.subplots_adjust(hspace=0.6, wspace=0.5)
#     plt.tight_layout(rect=[0, 0, 1, 0.95])

#     plt.savefig("images/data_viz/MLR/thresholds/TC_threshold_days_perSb.png")
#     plt.show()

####################################################################################################################

# load origin node file
ds = pd.read_csv("datasets/data_viz/TC+TD_origin_node_count_perSubbasin_SyCLoPS.csv")

# print(ds.head())

# reformat 
origins = ds.melt(
    id_vars="year",
    value_vars=ds.columns.drop(["year", "Total"]),
    var_name="sub_basin",
    value_name="origin_node_count"
)

# print(origins.head())

# rename 
origins = origins.rename(columns={"sub_basin": "sub_basin_name"})

# merge with variables
table = (
    annual
    .merge(
        origins,
        on=["year", "sub_basin_name"],
        how="outer"
    )
)

# print(table)

subbasin = "Mid-latitudinal Atlantic"
variable = "tc_TH"

sb = table[
    table["sub_basin_name"] == subbasin
].sort_values("year")

plt.figure(figsize=(10, 5))

plt.plot(
    sb["year"],
    sb["origin_node_count"],
    label="Origin node count",
    color="black",
    linewidth=2
)

plt.plot(
    sb["year"],
    sb[variable],
    label="Days with All Thresholds Satisfied",
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

# plt.savefig(f"images/data_viz/MLR/thresholds/origin_nodes_vs_{variable}_threshold_{subbasin}.png")
plt.show()

