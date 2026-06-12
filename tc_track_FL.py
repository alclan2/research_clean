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

# read in subbasin table with starting and ending nodes
ds = pd.read_csv(r"datasets/SyCLoPS/tc_track_subbasin_table.csv")

# add flag for TCs that dissipate east or west of Florida (using -82W as axis (edge of Gulf A subbasin))
ds['FL_diss'] = np.where(ds['LON_end'] > -82, "East of FL", "West of FL")

print(ds.head())

# pivot
piv = ds.pivot_table(
    index='sub_basin_start',      
    columns='FL_diss',
    aggfunc='size',
    fill_value=0    
)

#print(piv.head())
#piv = piv.sort_values('East of FL', ascending=False)
#print(piv.head())

# calc share of east v west FL diss
#piv['% East FL'] = piv['East of FL'] / (piv['East of FL'] + piv['West of FL'])
#piv['% West FL'] = piv['West of FL'] / (piv['East of FL'] + piv['West of FL'])
#print(piv.head())

piv = piv.sort_values('East of FL', ascending=False)

# plot
ax = piv[['East of FL', 'West of FL']].plot(
    kind='bar',
    figsize=(12, 8),
    width=0.8,
    color = ['blue', 'orange']
)

plt.title("Dissipation Location East vs. West of Florida by Origin Sub-Basin")
plt.xlabel("Origin Sub-Basin")
plt.ylabel("Count of TCs")
plt.xticks(rotation=45, ha='right')
plt.subplots_adjust(bottom=0.3, right=0.8)
plt.legend(title="FL Dissipation Location", bbox_to_anchor=(1.05, 1))

#plt.savefig("images/data_viz/FL_dissipation_count.png")
#plt.show()