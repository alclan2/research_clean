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

# read in post python processing ALCC files and average across runs 001 and 002 per mode
ds_nn_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_nn")
ds_no_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_no")
ds_np_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_np")
ds_on_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_on")
ds_oo_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_oo")
ds_op_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_op")
ds_pn_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_pn")
ds_po_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_po")
ds_pp_1 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run1}/ALCC_{TC}_{run1}_output_origins_perYr_wSubbasin_pp")

ds_nn_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_nn")
ds_no_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_no")
ds_np_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_np")
ds_on_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_on")
ds_oo_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_oo")
ds_op_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_op")
ds_pn_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_pn")
ds_po_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_po")
ds_pp_2 = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{run2}/ALCC_{TC}_{run2}_output_origins_perYr_wSubbasin_pp")

# create 5deg lat/lon bins
def bin_counts(df):
    df = df.copy()

    df["lat_bin"] = np.floor(df["lat"] / 5) * 5
    df["lon_bin"] = np.floor(df["lon_180"] / 5) * 5

    return (
        df.groupby(
            ["sub_basin_start", "year", "lat_bin", "lon_bin"]
        )
        .size()
        .reset_index(name="count")
    )

# create new datasets for counts
counts1_nn = bin_counts(ds_nn_1)
counts2_nn = bin_counts(ds_nn_2)
counts1_no = bin_counts(ds_no_1)
counts2_no = bin_counts(ds_no_2)
counts1_np = bin_counts(ds_np_1)
counts2_np = bin_counts(ds_np_2)
counts1_on = bin_counts(ds_on_1)
counts2_on = bin_counts(ds_on_2)
counts1_oo = bin_counts(ds_oo_1)
counts2_oo = bin_counts(ds_oo_2)
counts1_op = bin_counts(ds_op_1)
counts2_op = bin_counts(ds_op_2)
counts1_pn = bin_counts(ds_pn_1)
counts2_pn = bin_counts(ds_pn_2)
counts1_po = bin_counts(ds_po_1)
counts2_po = bin_counts(ds_po_2)
counts1_pp = bin_counts(ds_pp_1)
counts2_pp = bin_counts(ds_pp_2)

# nn
counts_nn = (
    counts1_nn.merge(
        counts2_nn,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_nn["mean_count"] = (counts_nn["count_1"] + counts_nn["count_2"]) / 2

# no
counts_no = (
    counts1_no.merge(
        counts2_no,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_no["mean_count"] = (counts_no["count_1"] + counts_no["count_2"]) / 2

# np
counts_np = (
    counts1_np.merge(
        counts2_np,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_np["mean_count"] = (counts_np["count_1"] + counts_np["count_2"]) / 2

# on
counts_on = (
    counts1_on.merge(
        counts2_on,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_on["mean_count"] = (counts_on["count_1"] + counts_on["count_2"]) / 2

# oo
counts_oo = (
    counts1_oo.merge(
        counts2_oo,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_oo["mean_count"] = (counts_oo["count_1"] + counts_oo["count_2"]) / 2

# op
counts_op = (
    counts1_op.merge(
        counts2_op,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_op["mean_count"] = (counts_op["count_1"] + counts_op["count_2"]) / 2

# pn
counts_pn = (
    counts1_pn.merge(
        counts2_pn,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_pn["mean_count"] = (counts_pn["count_1"] + counts_pn["count_2"]) / 2

# po
counts_po = (
    counts1_po.merge(
        counts2_po,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_po["mean_count"] = (counts_po["count_1"] + counts_po["count_2"]) / 2

# pp
counts_pp = (
    counts1_pp.merge(
        counts2_pp,
        on=["sub_basin_start", "year", "lat_bin", "lon_bin"],
        how="outer",
        suffixes=("_1", "_2")
    )
    .fillna(0)
)
counts_pp["mean_count"] = (counts_pp["count_1"] + counts_pp["count_2"]) / 2

# add mode column
counts_nn['mode'] = 'nn'
counts_no['mode'] = 'no'
counts_np['mode'] = 'np'
counts_on['mode'] = 'on'
counts_oo['mode'] = 'oo'
counts_op['mode'] = 'op'
counts_pn['mode'] = 'pn'
counts_po['mode'] = 'po'
counts_pp['mode'] = 'pp'

# concat into one table
all_counts = pd.concat([
    counts_nn,
    counts_no,
    counts_np,
    counts_on,
    counts_oo,
    counts_op,
    counts_pn,
    counts_po,
    counts_pp,
], ignore_index=True)

################################################################################################

# groupby subbasin and sum all counts across lat/lon bins
sb = "Northeastern Seaboard"

annual = (
    all_counts.loc[all_counts["sub_basin_start"] == sb]
    .groupby(["mode", "year"], as_index=False)["mean_count"]
    .sum()
)

# now plot grid of time series per mode
modes = ["np", "op", "pp",
         "no", "oo", "po",
         "nn", "on", "pn"]

# calculate axis limits
year_min = annual["year"].min()
year_max = annual["year"].max()
y_max = annual["mean_count"].max()

fig, axes = plt.subplots(
    3, 3,
    figsize=(14, 7),
    sharex=True,
    sharey=True
)

for ax, mode in zip(axes.flat, modes):
    df = annual[annual["mode"] == mode]

    ax.plot(df["year"], df["mean_count"], color="g", lw=1.8)
    ax.set_title(mode, fontweight = 'bold')

    # force the same axis limits
    ax.set_xlim(year_min - 1, year_max + 1)
    ax.set_ylim(0, y_max * 1.05)

    # show tick labels on every subplot
    ax.tick_params(axis="x", labelbottom=True)
    ax.tick_params(axis="y", labelleft=True)

fig.suptitle(f"TC Origin Locations - {sb}", fontsize=16)
fig.supxlabel("Year")
fig.supylabel("Count of TC Origin Nodes")

plt.tight_layout()
plt.savefig(f"images/data_viz/alcc/{TC}/runs_averaged/{TC}_runs_origin_nodes_grid_{sb}.png")
plt.show()