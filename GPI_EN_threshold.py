import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import xarray as xr
import math
import seaborn as sns

# load csv
gpi = pd.read_csv("datasets/GPI/GPI_EN_calc/gpi_monthly_mean_bySubbasin_table.csv")

# trim columns
gpi = gpi[['time','sub_basin_name', 'mean']]

# add year column
gpi['time'] = pd.to_datetime(gpi['time'])
gpi['year'] = gpi['time'].dt.year

# rename columns
gpi = gpi.rename(columns={"mean": "gpi"})

# annual pivot
annual_gpi = (
    gpi.groupby(['year', 'sub_basin_name'])['gpi']
       .mean()
       .reset_index()
)

# print(annual_gpi)

###############################################################################################################

# # plot timeseries of gpi per sub basin
# sub-basins to omit
omit = ["Mid-latitudinal US/CA", "Western Africa", "Mediterranean Sea"]

# filter them out
gpi_plot = annual_gpi[~annual_gpi["sub_basin_name"].isin(omit)]

# # plot of all sub basins
# subbasins = list(gpi_plot["sub_basin_name"].unique())
# n_subbasins = len(subbasins)
# ncols = 3
# nrows = math.ceil(n_subbasins / ncols)

# fig, axes = plt.subplots(
#     nrows=nrows,
#     ncols=ncols,
#     figsize=(13, 2 * nrows),
#     sharex=False
# )

# # make sure axes is always a 1D array
# axes = axes.flatten()

# for ax, (sub_basin, data) in zip(
#     axes,
#     gpi_plot.groupby("sub_basin_name")
# ):
#     ax.plot(data["year"], data["gpi"])
#     ax.set_title(sub_basin)
#     ax.set_ylabel("GPI")

# # hide unused subplots
# for ax in axes[n_subbasins:]:
#     ax.set_visible(False)

# print(gpi_plot)

# plt.tight_layout()
# # plt.savefig("images/data_viz/GPI/GPI_EN/GPI_timeseries_perSb_grid.png")
# plt.show()

###############################################################################################################

# # # box plot per sub basin
# # make figure
# plt.figure(figsize=(14, 8))

# sns.boxplot(
#     data=gpi_plot,
#     y="sub_basin_name",
#     x="gpi",
#     color='skyblue'
# )

# plt.ylabel("Sub-basin")
# plt.xlabel("GPI")
# plt.title("GPI Distribution by Sub-basin")

# plt.tight_layout()
# plt.savefig("images/data_viz/GPI/GPI_EN/GPI_boxplot_perSb.png")
# plt.show()

# convert values from box plot into a table to use as threshold for GPI
threshold_table = (
    gpi_plot
    .groupby("sub_basin_name")["gpi"]
    .agg(
        mean="mean",
        Q3=lambda x: x.quantile(0.75)
    )
    .reset_index()
    .round(3)
)

print(threshold_table)