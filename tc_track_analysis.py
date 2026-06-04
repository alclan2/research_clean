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

# read in subbasin table with starting and ending nodes
ds = pd.read_csv(r"datasets/SyCLoPS/tc_track_subbasin_table.csv")

# find fraction of TCs that originate or dissipate per subbasin
sb_start = ds.groupby('sub_basin_start').size()
sb_end = ds.groupby('sub_basin_end').size()

sb_start_frac = sb_start / sb_start.sum()
sb_end_frac = sb_end / sb_end.sum()

# CHECKS
#print(sb_start, sb_end)
#print(sb_start_frac, sb_end_frac)

#print(sb_start_frac.sum())
#print(sb_end_frac.sum())

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

# combine origin and dissipate
orig_to_diss = pd.concat(
    [tc_origin, tc_dissipate],
    axis=1
)

orig_to_diss.columns = ['Origin', 'Dissipation']
orig_to_diss = orig_to_diss.fillna(0)

orig_to_diss = orig_to_diss.sort_values('Origin', ascending=False)

# plot
ax = orig_to_diss.plot(
    kind='bar',
    figsize=(10, 6),
    width=0.8,
    color = ['skyblue', 'darkred']
)

# add axis labels
ax.set_xlabel('Sub-Basin Name')
ax.set_ylabel('Share of TCs (%)')
plt.xticks(rotation=45, ha='right')

# Title
ax.set_title('Share of TC Origin/Dissipation per Sub-Basin (North Atlantic)')

# Force percent scale
ax.set_ylim(0, 40)

# Legend
ax.legend(title='TC Stage')

plt.tight_layout()
plt.savefig("images/data_viz/tc_track_sb_fraction.png")
plt.show()