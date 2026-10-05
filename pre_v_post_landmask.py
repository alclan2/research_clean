import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.patheffects as pe
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

# load pre landmask data
ds = pd.read_csv("datasets/data_viz/RH_600hPa_yearly_mean_perSubbasin.csv", index_col=0)

# load post landmasked data
lm = pd.read_csv("datasets/RHUM/post-processing/post_landmask/RHUM600_annual_mean_bySubbasin_table_postLandmask.csv", index_col=0)

# print(ds)
# print(lm)

ds = ds.reset_index()

# match formatting
no_lm = ds.melt(
    id_vars="year",
    var_name="sub_basin_name",
    value_name="mean"
)

# no_lm = ds
no_lm = no_lm.rename(columns={"rh600": "mean"})

# get sub-basins that occur in both datasets
subbasins = no_lm["sub_basin_name"].unique()

# set up subplot grid
ncols = 3
nrows = int(np.ceil(len(subbasins) / ncols))

fig, axes = plt.subplots(
    nrows,
    ncols,
    figsize=(14, 2 * nrows),
    sharex=True,
    sharey=True
)

# flatten axes so we can loop through them
axes = np.array(axes).flatten()

for ax, subbasin in zip(axes, subbasins):

    # Select this sub-basin
    no_lm_sub = no_lm[
        no_lm["sub_basin_name"] == subbasin
    ]

    lm_sub = lm[
        lm["sub_basin_name"] == subbasin
    ]

    # Plot no landmask
    ax.plot(
        no_lm_sub["year"],
        no_lm_sub["mean"],
        label="No landmask",
        color="steelblue",
        linewidth=2
    )

    # Plot landmask
    ax.plot(
        lm_sub["year"],
        lm_sub["mean"],
        label="Landmask",
        color="orange",
        linewidth=2
    )

    ax.set_title(subbasin)
    ax.set_xlabel("Year")
    ax.set_ylabel("RH (%)")
    ax.grid(alpha=0.3)

# Remove unused subplot(s)
for ax in axes[len(subbasins):]:
    ax.remove()

# One legend for the whole figure
handles, labels = axes[0].get_legend_handles_labels()

fig.legend(
    handles,
    labels,
    loc="upper center",
    ncol=2,
    bbox_to_anchor=(0.5, 0.98)
)

fig.suptitle(
    "Annual Mean Relative Humidity (600hPa) by Sub-basin",
    fontsize=16,
    y=1.02
)

plt.tight_layout()
plt.savefig("images/data_viz/thresholds/RH_preVsPost_landmask_perSb.png")
plt.show()

########################################################################################################

# # check

# ds = xr.open_dataset("datasets/RHUM/post-processing/RHUM600_daily_mean_1979-2025.nc")

# ds2 = xr.open_dataset("datasets/RHUM/post-processing/post_landmask/rhum_600_daily_landmasked.nc")

# # Pick a date
# date = "1981-06-01"

# fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# # Before landmask
# ds["rhum"].sel(time=date).plot(
#     ax=axes[0],
#     cmap="viridis"
# )
# axes[0].set_title("RHUM 600 hPa — Before Landmask")

# # After landmask
# ds2["rhum"].sel(time=date).plot(
#     ax=axes[1],
#     cmap="viridis"
# )
# axes[1].set_title("RHUM 600 hPa — After Landmask")

# plt.tight_layout()
# plt.show()