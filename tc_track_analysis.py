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
ds = pd.read_csv(r"datasets/SyCLoPS/tc_track_subbasin_coarse_table.csv")
#print(ds.head())

# find fraction of TCs that originate or dissipate per subbasin
sb_start = ds.groupby('sub_basin_start').size()
sb_end = ds.groupby('sub_basin_end').size()

sb_start_frac = sb_start / sb_start.sum()
sb_end_frac = sb_end / sb_end.sum()

# plot fractions
tc_origin = (
    ds['sub_basin_start']
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
)

tc_dissipate = (
    ds['sub_basin_end']
    .value_counts(normalize=True)
    .mul(100)
    .sort_values()
)

#print(tc_origin)
#print(tc_dissipate)

# combine origin and dissipate
orig_to_diss = pd.concat(
    [tc_origin, tc_dissipate],
    axis=1
)

orig_to_diss.columns = ['Origin', 'Dissipation']
orig_to_diss = orig_to_diss.fillna(0)

orig_to_diss = orig_to_diss.sort_values('Origin', ascending=False)

#print(orig_to_diss)
#print(orig_to_diss['Origin'].sum())
#print(orig_to_diss['Dissipation'].sum())

## plot
#ax = orig_to_diss.plot(
#    kind='bar',
#    figsize=(10, 6),
#    width=0.8,
#    color = ['skyblue', 'darkred']
#)

## add axis labels
#ax.set_xlabel('Sub-Basin Name')
#ax.set_ylabel('Share of TCs (%)')
#plt.xticks(rotation=45, ha='right')

## Title
#ax.set_title('Share of TC Origin/Dissipation per Sub-Basin (North Atlantic)')

## Force percent scale
#ax.set_ylim(0, 60)

## Legend
#ax.legend(title='TC Stage')

#plt.tight_layout()
#plt.savefig("images/data_viz/tc_track_sb_coarse_fraction.png")
#plt.show()

#################################################################################

# now find fraction of sub basin end per sub basin start
pivot = pd.pivot_table(
   ds,
    values="TID",
    index="sub_basin_start",
    columns="sub_basin_end",
    aggfunc="count",
    fill_value=0
)
tracks = pivot.div(pivot.sum(axis=1), axis=0).mul(100).round(0)

#print(pivot)

# remove land regions
tracks = tracks.drop(['Mid-latitudinal US/CA', 'Western Africa'])

# add line breaks for plotting ease
tracks_wrapped = pivot.copy()
tracks_wrapped.columns = tracks_wrapped.columns.str.replace(" ", "\n")

## plot as heatmap
#plt.figure(figsize=(14, 8))

#sns.heatmap(
#    tracks_wrapped,
#    cmap="Blues",
#    annot=True,  
#    fmt='d', 
#    linewidths=0.3
#)

#plt.xlabel("Dissipation Sub-Basin", labelpad=10)
#plt.ylabel("Origin Sub-Basin", labelpad=10)
#plt.xticks(rotation=45)
#plt.title("TC Dissipation Sub-Basin by Origin Location (Count of TCs)", pad=20)

#plt.tight_layout()
#plt.savefig("images/data_viz/tc_track_heatmap_coarse_counts.png")
#plt.show()

##################################################################################

# stacked bar chart
cmap = plt.cm.tab20
colors = cmap(np.linspace(0.4, 0.9, tracks.shape[1]))

#colors = sns.color_palette("Set2", n_colors=tracks.shape[1])

ax = tracks.plot(
    kind="bar",
    stacked=True,
    figsize=(12, 6),
    color=colors
)

ax.set_ylabel("%")
ax.set_xlabel("Origin Sub-Basin")
ax.set_title("TC Dissipation Sub-Basin by Origin Location")

plt.legend(title="Dissipation Sub-Basin", bbox_to_anchor=(1.05, 1))
plt.xticks(rotation=45)
plt.tight_layout()
#plt.savefig("images/data_viz/tc_track_sb_coarse_fraction_stacked.png")
plt.show()


#print(tracks.head())

