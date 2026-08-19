import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import xarray as xr
import numpy as np
import tarfile

# toggle
TC = 'TC.2'
run1 = '001'
run2 = '002'
subject = 'mslp'

# read in post python processing ALCC files and average across runs 001 and 002 per mode
ds_nn_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_nn")
ds_no_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_no")
ds_np_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_np")
ds_on_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_on")
ds_oo_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_oo")
ds_op_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_op")
ds_pn_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_pn")
ds_po_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_po")
ds_pp_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/{subject}/ALCC_{TC}_{run1}_output_{subject}_perYr_wSubbasin_pp")

ds_nn_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_nn")
ds_no_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_no")
ds_np_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_np")
ds_on_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_on")
ds_oo_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_oo")
ds_op_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_op")
ds_pn_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_pn")
ds_po_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_po")
ds_pp_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/{subject}/ALCC_{TC}_{run2}_output_{subject}_perYr_wSubbasin_pp")

# # COUNT OF TCS; create 5deg lat/lon bins 
# def bin_counts(df):
#     df = df.copy()

#     df["lat_bin"] = np.floor(df["lat"] / 5) * 5
#     df["lon_bin"] = np.floor(df["lon_180"] / 5) * 5

#     return (
#         df.groupby(
#             ["sub_basin_name", "year", "lat_bin", "lon_bin"]
#         )
#         .size()
#         .reset_index(name="count")
#     )

# MSLP avg; create 5deg lat/lon bins
def bin_slp(df):
    df = df.copy()

    df["lat_bin"] = np.floor(df["lat"] / 5) * 5
    df["lon_bin"] = np.floor(df["lon_180"] / 5) * 5

    return (
        df.groupby(
            ["sub_basin_name", "year", "lat_bin", "lon_bin"]
        )["slp"]
        .mean()
        .div(100)
        .reset_index(name="mean_slp")
    )

# create new datasets for counts
slp1_nn = bin_slp(ds_nn_1)
slp2_nn = bin_slp(ds_nn_2)
slp1_no = bin_slp(ds_no_1)
slp2_no = bin_slp(ds_no_2)
slp1_np = bin_slp(ds_np_1)
slp2_np = bin_slp(ds_np_2)
slp1_on = bin_slp(ds_on_1)
slp2_on = bin_slp(ds_on_2)
slp1_oo = bin_slp(ds_oo_1)
slp2_oo = bin_slp(ds_oo_2)
slp1_op = bin_slp(ds_op_1)
slp2_op = bin_slp(ds_op_2)
slp1_pn = bin_slp(ds_pn_1)
slp2_pn = bin_slp(ds_pn_2)
slp1_po = bin_slp(ds_po_1)
slp2_po = bin_slp(ds_po_2)
slp1_pp = bin_slp(ds_pp_1)
slp2_pp = bin_slp(ds_pp_2)

# print(slp1_nn)

# nn
slp_nn = (
    slp1_nn.merge(
        slp2_nn,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_nn["mslp"] = slp_nn[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# no
slp_no = (
    slp1_no.merge(
        slp2_no,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_no["mslp"] = slp_no[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# np
slp_np = (
    slp1_np.merge(
        slp2_np,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_np["mslp"] = slp_np[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# oo
slp_oo = (
    slp1_oo.merge(
        slp2_oo,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_oo["mslp"] = slp_oo[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# on
slp_on = (
    slp1_on.merge(
        slp2_on,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_on["mslp"] = slp_on[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# op
slp_op = (
    slp1_op.merge(
        slp2_op,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_op["mslp"] = slp_op[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# pp
slp_pp = (
    slp1_pp.merge(
        slp2_pp,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_pp["mslp"] = slp_pp[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# po
slp_po = (
    slp1_po.merge(
        slp2_po,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_po["mslp"] = slp_po[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# pn
slp_pn = (
    slp1_pn.merge(
        slp2_pn,
        on=["sub_basin_name", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    # .fillna(0)
)
slp_pn["mslp"] = slp_pn[["mean_slp_1", "mean_slp_2"]].mean(axis=1)

# add mode column
slp_nn['mode'] = 'nn'
slp_no['mode'] = 'no'
slp_np['mode'] = 'np'
slp_on['mode'] = 'on'
slp_oo['mode'] = 'oo'
slp_op['mode'] = 'op'
slp_pn['mode'] = 'pn'
slp_po['mode'] = 'po'
slp_pp['mode'] = 'pp'

# concat into one table
all_slp = pd.concat([
    slp_nn,
    slp_no,
    slp_np,
    slp_on,
    slp_oo,
    slp_op,
    slp_pn,
    slp_po,
    slp_pp,
], ignore_index=True)

print(all_slp)

# save to csv
all_slp.to_csv(f"datasets/ALCC/post_python_processing/{TC}/{TC}_all_mslp_{subject}_avg_table.csv")

################################################################################################

# # groupby subbasin and sum all counts across lat/lon bins
# sb = "Northeastern Seaboard"

# annual = (
#     all_counts.loc[all_counts["sub_basin_start"] == sb]
#     .groupby(["mode", "year"], as_index=False)["mean_count"]
#     .sum()
# )

# # now plot grid of time series per mode
# modes = ["np", "op", "pp",
#          "no", "oo", "po",
#          "nn", "on", "pn"]

# # calculate axis limits
# year_min = annual["year"].min()
# year_max = annual["year"].max()
# y_max = annual["mean_count"].max()

# fig, axes = plt.subplots(
#     3, 3,
#     figsize=(14, 7),
#     sharex=True,
#     sharey=True
# )

# for ax, mode in zip(axes.flat, modes):
#     df = annual[annual["mode"] == mode]

#     ax.plot(df["year"], df["mean_count"], color="g", lw=1.8)
#     ax.set_title(mode, fontweight = 'bold')

#     # force the same axis limits
#     ax.set_xlim(year_min - 1, year_max + 1)
#     ax.set_ylim(0, y_max * 1.05)

#     # show tick labels on every subplot
#     ax.tick_params(axis="x", labelbottom=True)
#     ax.tick_params(axis="y", labelleft=True)

# fig.suptitle(f"TC Origin Locations - {sb}", fontsize=16)
# fig.supxlabel("Year")
# fig.supylabel("Count of TC Origin Nodes")

# plt.tight_layout()
# plt.savefig(f"images/data_viz/alcc/{TC}/runs_averaged/{TC}_runs_origin_nodes_grid_{sb}.png")
# plt.show()