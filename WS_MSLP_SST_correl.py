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

# load WS and MSLP yearly csv
df1 = pd.read_csv("datasets/SyCLoPS/WS_MSLP_anom_bySubbasin_TC+TD_table.csv")

#load SST anom yearly csv
df2 = pd.read_csv("datasets/COBE2 SST/post-processing/sst_anom_1940-2024_bySubbasin_table.csv")

# trim SST dataframe to match year range for WS and MSLP
df2 = df2[df2['year'].between(1940,2024)]

# trim columns and rename so we can join into one table
df1 = df1[['YEAR', 'sub_basin_name', 'mean_WS_anom', 'mean_MSLP_anom']]
df2 = df2[['year', 'basin', 'mean_anom']]
df2 = df2.rename(columns={
    "year": "YEAR",
    "basin": "sub_basin_name",
    "mean_anom": "mean_SST_anom"
})

# merge on year and subbasin
combined = pd.merge(df1, df2, on=["YEAR", "sub_basin_name"], how="inner")

# compute correlations between WS, MSLP, SST anom
all_corrs = []

for sb, group in combined.groupby("sub_basin_name"):
    corr = group[["mean_WS_anom", "mean_MSLP_anom", "mean_SST_anom"]].corr()
    
    # add a column to identify the basin
    corr["sub_basin_name"] = sb
    
    # move subbasin column to front
    corr = corr.reset_index().rename(columns={"index": "variable"})
    
    all_corrs.append(corr)

corr_table = pd.concat(all_corrs, ignore_index=True)

#print(corr_table)

# save to file
#corr_table.to_csv("datasets/data_viz/SST_WS_MSLP_anom_correl_sb_v2_sst1940-2024.csv")

###########################################################################################################

# now compute correlations with origin nodes

# load origin sb table
df3 = pd.read_csv("datasets/SyCLoPS/tc&td_track_subbasin_table_withYear.csv")

# pivot to get year by sb form
og_count = df3.groupby(['YEAR_start', 'sub_basin_start']).size().reset_index(name='count')

# rename columns for merge
og_count = og_count.rename(columns={
    "YEAR_start": "YEAR",
    "sub_basin_start": "sub_basin_name",
    "count": "tc_origin_nodes"
})

# combine into a mega table with WS, MSLP, SST_anom
combined2 = pd.merge(combined, og_count, on=["YEAR", "sub_basin_name"], how="left")

# compute correlations between origin node count now
corr2 = (
    combined2
    .groupby("sub_basin_name")
    .apply(lambda x: pd.Series({
        "corr_WS": x["tc_origin_nodes"].corr(x["mean_WS_anom"]),
        "corr_MSLP": x["tc_origin_nodes"].corr(x["mean_MSLP_anom"]),
        "corr_SST": x["tc_origin_nodes"].corr(x["mean_SST_anom"]),
        "n": x[["tc_origin_nodes", "mean_WS_anom"]].dropna().shape[0]
    }))
    .reset_index()
)

#print(corr2)

# save to csv
#corr2.to_csv("datasets/data_viz/TC+TDOriginNodes_WSanom+MSLPanom+SSTanom_correl_sb_v2_sst1940-2024.csv")

###########################################################################################################

# plot all three anomalies on one plot per subbasin

# sub basin toggle
sb = 'Mid-latitudinal Atlantic'

df_plot = combined[combined["sub_basin_name"] == sb]

fig, axes = plt.subplots(3, 1, figsize=(10, 8), sharex=True)

# WS
axes[0].plot(
    df_plot["YEAR"],
    df_plot["mean_WS_anom"],
    color="tab:blue",
    marker="o",
    linewidth=2
)
axes[0].axhline(0, color="black", linestyle="--", linewidth=1)
axes[0].set_ylabel("WS Anomaly (m/s)")

# MSLP
axes[1].plot(
    df_plot["YEAR"],
    df_plot["mean_MSLP_anom"],
    color="tab:red",
    marker="s",
    linewidth=2
)
axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
axes[1].set_ylabel("MSLP Anomaly (Pa)")

# Third variable
axes[2].plot(
    df_plot["YEAR"],
    df_plot["mean_SST_anom"],
    color="tab:green",
    marker="^",
    linewidth=2
)
axes[2].axhline(0, color="black", linestyle="--", linewidth=1)
axes[2].set_ylabel("SST Anomaly (°C)")
axes[2].set_xlabel("Year")

plt.suptitle(f"WS, MSLP, SST Anomalies in the North Atlantic - {sb}")
plt.tight_layout()
# plt.savefig(f"images/data_viz/WSvsMSLPvsSST_anom_timeseries_{sb}_v2_sst1940-2024.png")
# plt.show()