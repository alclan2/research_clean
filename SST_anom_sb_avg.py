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

# read in anom net cdf
ds = xr.open_dataset("datasets/COBE2 SST/post-processing/SST_mon_mean_anom_full_dataset_clim_jun_oct_wSubbasin.nc")

print(ds)

# convert to a dataframe
df = ds['sst'].to_dataframe(name = 'mean_anom').reset_index()

#print(df)

# save to csv
#df.to_csv("datasets/COBE2 SST/post-processing/sst_anom_fullDataset_bySubbasin_table.csv")

#######################################################################################################

# # plot mean SST anom as a time series per sub basin

# # select sub basin
# sb = 'Deep Tropics'

# # pivot to have sub basins be column heads
# sst_piv = df.pivot_table(
#     index="year",
#     columns="basin",
#     values="mean_anom",
#     aggfunc="mean"
# )

# #print(sst_piv.head())

# # scatter plot
# ax = sst_piv[sb].plot(
#    kind='line',
#    marker='o',
#    figsize=(10, 6)
# )

# ax.set_xlabel("Year")
# ax.set_ylabel("SST Anomaly (°C)")
# ax.set_title(f"Mean Sea Surface Temperature Anomaly in North Atlantic ({sb})")
# #ax.yaxis.set_major_locator(MaxNLocator(integer=True))

# #plt.savefig(f"images/data_viz/MSLP/timeseries/tc_mslp_timeseries_{sb}_v2.png")
# plt.show()
