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
# ds1 = ds1[ds1["year"] >= 1940]
shear = shear[shear["year"] <= 2024]

# index by year
origins = ds1.set_index("year")
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
ds3 = pd.read_csv("datasets/data_viz/max_wind_speed_annual_mean_allTimeSteps_PW.csv")

# pivot max wind to match origins file format
vm = (
    ds3
    .pivot(index="year", columns="sub_basin_name", values="vm")
    .reset_index()
)

# print(vm)

# index by year
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

# trim columns
sst = sst[["year", "sub_basin_name", "mean_anom"]]

# load RH 600hPa 
rh = pd.read_csv("datasets/data_viz/RH_600hPa_yearly_mean_perSubbasin.csv")

# load lifespan annual mean file
ls = pd.read_csv("datasets/data_viz/lifespan_annual_mean_per_origin_subbasin.csv")

# trim ls columns
ls = ls[['year', 'sub_basin_origin', 'mean_lifespan_days']]

# rename ls column to match origins
ls = ls.rename(columns={"sub_basin_origin": "sub_basin_name"})

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

rh_long = (
    rh
    .reset_index(drop=True)
    .melt(
        id_vars="year",
        var_name="sub_basin_name",
        value_name="rh600"
    )
)

# merge on year and sub basin
merged = (
    origins_long
    .merge(
        ls,
        on=["year", "sub_basin_name"],
        how="outer"
    )
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
    .merge(
            rh_long,
            on=["year", "sub_basin_name"],
            how="outer"
        )
)

#print(merged)

# drop sub basins with very few/no origin nodes
drop_basins = ["Arctic", "Northern Europe", "Deep Tropics", "Mediterranean Sea", "Mid-latitudinal Atlantic", "Mid-latitudinal US/CA", "Subtropical Atlantic", "Western Africa"]

merged_filt = merged[
    ~merged["sub_basin_name"].isin(drop_basins)
]

# filter to time
merged_filt = merged_filt[(merged_filt["year"] >= 1940) & (merged_filt["year"] <= 2024)]

#print(merged_filt)

# select variables for plot
plot_df = merged_filt.dropna(subset=["mean_lifespan_days", "vm"])

# calc correlation to add to plots
from scipy.stats import pearsonr
def add_corr(data, **kwargs):
    r, p = pearsonr(data["vm"], data["mean_lifespan_days"])
    ax = plt.gca()
    
    ax.text(
        0.05, 0.90,
        f"r = {r:.2f}",
        transform=ax.transAxes,
        fontsize=10,
        bbox=dict(
            boxstyle="round,pad=0.3",
            facecolor="white",
            edgecolor="black",
            alpha=0.8
        )
    )

#print(plot_df)

# plot
col_order = sorted(plot_df["sub_basin_name"].unique())

g = sns.FacetGrid(
    plot_df,
    col="sub_basin_name",
    col_order=col_order,
    col_wrap=4,
    height=3,
    aspect=1.2,
    sharex=True,
    sharey=True
)

g.map_dataframe(
    sns.scatterplot,
    x="vm",
    y="mean_lifespan_days",
    color="green" 
)

g.map_dataframe(add_corr)

g.set_titles("{col_name}")

# Remove all individual axis labels
for ax in g.axes.flat:
    ax.set_xlabel("")
    ax.set_ylabel("")
    
    # Show tick numbers everywhere
    ax.tick_params(axis="x", labelbottom=True)
    ax.tick_params(axis="y", labelleft=True)

# Add one common label for the whole figure
g.figure.supxlabel("Mean Maximum Wind Speed (m/s)", y=0.02)
g.figure.supylabel("Mean Lifespan (days)", x=0.02)

# add title
g.figure.suptitle(
    "TC Lifespan vs. Maximum Wind Speed by Sub-basin",
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

plt.savefig("images/data_viz/origin_vs/TC_mean_lifespan_vs_max_wind_vm_allTimeSteps_perSubbasin_withCorrelation.png")
plt.show()
