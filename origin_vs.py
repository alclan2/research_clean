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
import seaborn as sns

# origin node count vs. 850-200hPa wind shear correlation
# load origin node file
ds1 = pd.read_csv("datasets/data_viz/TC_origin_node_count_perSubbasin_SyCLoPS.csv")

# load wind shear 
ds2 = pd.read_csv("datasets/u-wind/post_processing/wind_shear_850_200_yearly_by_subbasin.csv")

# pivot shear to match origins file format
shear = (
    ds2
    .pivot(index="year", columns="sub_basin_name", values="shear")
    .reset_index()
)

#print(shear)

# filter origins and shear to the same time period
origins = ds1[ds1["year"] >= 1979]
shear = shear[shear["year"] <= 2024]

# index by year
origins = origins.set_index("year")
shear = shear.set_index("year")

# # match on sub basins
# common_basins = origins.columns.intersection(shear.columns)

# origins_filt = origins[common_basins]
# shear_filt = shear[common_basins]

# # print(origins_filt.head())
# # print(shear_filt.head())

# # correlations per sub basin
# correlations = pd.Series({
#     basin: origins_filt[basin].corr(shear_filt[basin])
#     for basin in common_basins
# })

# print(correlations)

##################################################################################################################

# origin node count vs. max mean wind speed correlation
# load max mean wind speed
ds3 = pd.read_csv("datasets/data_viz/max_wind_speed_annual_mean_maximum_PW.csv")

# print(ds1.head())
# print(ds2.head())

# pivot max wind to match origins file format
vm = (
    ds3
    .pivot(index="year", columns="sub_basin_name", values="vm")
    .reset_index()
)

# print(vm)

# index by year
origins = ds1.set_index("year")
vm = vm.set_index("year")

# # match on sub basins
# common_basins = origins.columns.intersection(vm.columns)

# origins_filt = origins[common_basins]
# vm_filt = vm[common_basins]

# print(origins_filt.head())
# print(vm_filt.head())

# # correlations per sub basin
# correlations = pd.Series({
#     basin: origins_filt[basin].corr(vm_filt[basin])
#     for basin in common_basins
# })

# print(correlations)

##################################################################################################################

# load sst anomaly
sst = pd.read_csv("datasets/COBE2 SST/post-processing/sst_anom_moving_window_bySubbasin_table.csv")

# filter to 1979-2024 since that is when we have wind shear & origin data
sst = sst[sst["year"] >= 1940]

sst = sst[["year", "sub_basin_name", "mean_anom"]]

#print(sst)

# drop total column from origins
origins = origins.drop(columns=["Total"])

# convert tables so sub basin is not a column
origins_long = (
    origins
    .reset_index()
    .melt(
        id_vars="year",
        var_name="sub_basin_name",
        value_name="origins"
    )
)

shear_long = (
    shear
    .reset_index()
    .melt(
        id_vars="year",
        var_name="sub_basin_name",
        value_name="shear"
    )
)

vm_long = (
    vm
    .reset_index()
    .melt(
        id_vars="year",
        var_name="sub_basin_name",
        value_name="vm"
    )
)

# merge on year and sub basin
merged = (
    origins_long
    .merge(
        shear_long,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        vm_long,
        on=["year", "sub_basin_name"],
        how="outer"
    )
    .merge(
        sst,
        on=["year", "sub_basin_name"],
        how="outer"
    )
)

# drop sub basins with very few/no origin nodes
drop_basins = ["Arctic", "Northern Europe", "Deep Tropics", "Mediterranean Sea", "Mid-latitudinal Atlantic", "Mid-latitudinal US/CA", "Subtropical Atlantic", "Western Africa"]

merged_filt = merged[
    ~merged["sub_basin_name"].isin(drop_basins)
]

#print(merged_filt)

# filter to time
merged_filt = merged_filt[(merged_filt["year"] >= 1940) & (merged_filt["year"] <= 2014)]

plot_df = merged_filt.dropna(subset=["origins", "mean_anom"])

g = sns.FacetGrid(
    plot_df,
    col="sub_basin_name",
    col_wrap=4,
    height=3,
    aspect=1.2,
    sharex=True,
    sharey=True
)

g.map_dataframe(
    sns.scatterplot,
    x="mean_anom",
    y="origins"
)

g.set_titles("{col_name}")

# Remove all individual axis labels
for ax in g.axes.flat:
    ax.set_xlabel("")
    ax.set_ylabel("")
    
    # Show tick numbers everywhere
    ax.tick_params(axis="x", labelbottom=True)
    ax.tick_params(axis="y", labelleft=True)

# Add one common label for the whole figure
g.figure.supxlabel("SST Anom (°C)", y=0.02)
g.figure.supylabel("Number of Origin Locations", x=0.02)

# add title
g.figure.suptitle(
    "TC Origin Locations vs. SST Anomaly by Sub-basin",
    fontsize=16,
    y=0.98
)

# adjust spacing
g.figure.subplots_adjust(
    hspace=0.5,
    wspace=0.25,
    bottom=0.12,
    left=0.08,
    top=0.85
)

plt.savefig("images/data_viz/TC_origin_nodes_vs_sst_moving_window_anom_perSubbasin.png")
plt.show()