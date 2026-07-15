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
from matplotlib.ticker import MaxNLocator

# read in tc_basins file so we can filter to a specific ocean basin
polygons_dict = {}

with open("tc_basins.dat", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(",")
        basin_name = parts[0].replace('"', '')
        n_vertices = int(parts[1])

        lon_vals = list(map(float, parts[2:2+n_vertices]))
        lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

        coords = list(zip(lon_vals, lat_vals))
        poly = Polygon(coords)

        if basin_name not in polygons_dict:
            polygons_dict[basin_name] = []
        polygons_dict[basin_name].append(poly)

# Convert to GeoDataFrame
basin_records = []

for name, poly_list in polygons_dict.items():
    if len(poly_list) == 1:
        geom = poly_list[0]
    else:
        geom = MultiPolygon(poly_list)

    basin_records.append({
        "basin name": name,
        "geometry": geom
    })

basins = gpd.GeoDataFrame(basin_records, crs="EPSG:4326")

# fix invalid polygons
basins["geometry"] = basins["geometry"].buffer(0)

# remove empy geometries
basins = basins[~basins.geometry.is_empty]

# read in tc_subbasins_NAtl file
sub_polygons_dict = {}

with open("tc_subbasins_NAtl_v5.dat", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(",")
        sub_basin_name = parts[0].replace('"', '')
        n_vertices = int(parts[1])

        lon_vals = list(map(float, parts[2:2+n_vertices]))
        lon_vals = [(lon + 180) % 360 - 180 for lon in lon_vals]
        lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

        coords = list(zip(lon_vals, lat_vals))
        poly = Polygon(coords)

        if sub_basin_name not in sub_polygons_dict:
            sub_polygons_dict[sub_basin_name] = []
        sub_polygons_dict[sub_basin_name].append(poly)

# Convert to GeoDataFrame
sub_basin_records = []

for name, poly_list in sub_polygons_dict.items():
    if len(poly_list) == 1:
        geom = poly_list[0]
    else:
        geom = MultiPolygon(poly_list)

    sub_basin_records.append({
        "sub_basin_name": name,
        "geometry": geom
    })

sub_basins = gpd.GeoDataFrame(sub_basin_records, crs="EPSG:4326",geometry="geometry")

# fix invalid polygons
sub_basins["geometry"] = sub_basins["geometry"].buffer(0)

# remove empty geometries
sub_basins = sub_basins[~sub_basins.geometry.is_empty]

# longitude conversion
import shapely.ops
def shift_lon(geom):
    return shapely.ops.transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )

# shift lon
sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)
basins["geometry"] = basins["geometry"].apply(shift_lon)

##############################################################################################################

## read in and filter our syclops data
# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# TC Nodes: filter to TCs only, tropical flag = 1 so we are only counting before they become extratropical
#dftc = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
dftc = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# sort by TID and ISOTIME
dftc = dftc.sort_values(['TID', 'ISOTIME'])

# convert lon to -180-180 from 0-360
dftc['LON'] = ((dftc['LON'] + 180) % 360) - 180

# first node: where the TC originates
tc_origin = (
    dftc
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .head(1)
)

# last node: where the TC dissipates
TC_TIDs = tc_origin['TID']
tc_dissipate = (
    dftc[(dftc['TID'].isin(TC_TIDs)) & (dftc['Tropical_Flag'] == 1)]
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .tail(1)
)

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
tc_origin_points = gpd.GeoDataFrame(
    tc_origin, 
    geometry = gpd.points_from_xy(tc_origin.LON, tc_origin.LAT),
    crs = "EPSG:4326"
)

tc_dissipate_points = gpd.GeoDataFrame(
    tc_dissipate, 
    geometry = gpd.points_from_xy(tc_dissipate.LON, tc_dissipate.LAT),
    crs = "EPSG:4326"
)

# filter points to North Atlantic
tc_origin_filtered = gpd.sjoin(
    tc_origin_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

tc_dissipate_filtered = gpd.sjoin(
    tc_dissipate_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# merge start and end nodes on TID
tc_track = (
    tc_origin_filtered
    .merge(
        tc_dissipate_filtered,
        on="TID",
        suffixes=("_start", "_end")
    )
)

#print(tc_track.columns)

# add Year column so we can create a timeseries
tc_track['YEAR_start'] = tc_track['ISOTIME_start'].dt.year
tc_track['YEAR_end'] = tc_track['ISOTIME_end'].dt.year

# filter to only columns we need
tc_track = tc_track[['TID', 'LON_start', 'LAT_start', 'LON_end', 'LAT_end', 'YEAR_start']]

# join sub basin name for starting and ending points
start_gdf = gpd.GeoDataFrame(
    tc_track,
    geometry=gpd.points_from_xy(
        tc_track.LON_start,
        tc_track.LAT_start
    ),
    crs=sub_basins.crs
)

end_gdf = gpd.GeoDataFrame(
    tc_track,
    geometry=gpd.points_from_xy(
        tc_track.LON_end,
        tc_track.LAT_end
    ),
    crs=sub_basins.crs
)

start_join = gpd.sjoin(
    start_gdf,
    sub_basins[['sub_basin_name', 'geometry']],
    how='left',
    predicate='within'
)

end_join = gpd.sjoin(
    end_gdf,
    sub_basins[['sub_basin_name', 'geometry']],
    how='left',
    predicate='within'
)

tc_track['sub_basin_start'] = start_join['sub_basin_name']
tc_track['sub_basin_end'] = end_join['sub_basin_name']

# calc difference in lat/lon
tc_track['LON_diff_abs'] = (tc_track['LON_end'] - tc_track['LON_start']).abs()
tc_track['LAT_diff_abs'] = (tc_track['LAT_end'] - tc_track['LAT_start']).abs()

tc_track['LON_diff'] = tc_track['LON_end'] - tc_track['LON_start']
tc_track['LAT_diff'] = tc_track['LAT_end'] - tc_track['LAT_start']

##############################################################################################################

# # pivot by sub basin for plot
# drop_basins = ['Arctic', 'Mediterranean Sea']

# tc_filtered = tc_track[~tc_track['sub_basin_start'].isin(drop_basins)]

# piv = tc_filtered.pivot_table(
#     index='sub_basin_start',
#     values=['LON_diff', 'LAT_diff'],
#     aggfunc='mean'
# )

# print(piv)

# # plot
# piv.plot(kind='bar', figsize=(10, 6))

# plt.ylabel('Average Absolute Difference (degrees)')
# plt.xlabel('Origin Sub-basin')
# plt.title('Average TC Track Displacement by Origin Sub-basin')
# plt.xticks(rotation=45, ha='right')
# plt.legend(['Longitude Difference', 'Latitude Difference'])
# plt.tight_layout()

# #plt.savefig("images/data_viz/TC_track/track_plots/TC_track_distance_bySubbasin.png")
# plt.show()

##############################################################################################################

# # plot track displacement per sub basin

# # pivot by sub basin for plot
# plt.figure(figsize=(12, 6))

# drop_basins = ['Arctic', 'Mediterranean Sea']
# tc_filtered = tc_track[~tc_track['sub_basin_start'].isin(drop_basins)]

# #print(tc_filtered)

# # alpha order
# order = sorted(tc_filtered['sub_basin_start'].dropna().unique())

# sns.boxplot(
#     data=tc_filtered,
#     x='sub_basin_start',
#     y='LON_diff',
#     color = 'lightblue',
#     linecolor = 'black',
#     order = order
# )

# plt.xticks(rotation=45, ha='right')
# plt.ylabel('Absolute Longitude Displacement (degrees)')
# plt.xlabel('Origin Sub-basin')
# plt.title('TC Track Longitude Displacement Distribution by Origin Sub-basin')

# plt.tight_layout()

# #plt.savefig("images/data_viz/TC_track/track_plots/TC_track_LON_distance_boxplot_bySubbasin.png")
# plt.show()

##############################################################################################################

# # calc east v west and north v south dispacement per sub basin

# filter columns
ds2 = tc_track[['TID', 'sub_basin_start', 'sub_basin_end', 'LON_diff', 'LAT_diff']]

# create columns for east v west and north v south movement
ds2['East/West_displ'] = np.where(
    ds2['LON_diff'] > 0,
    'East',
    np.where(ds2['LON_diff'] < 0, 
    'West', 
    'No displacement')
)

ds2['North/South_displ'] = np.where(
    ds2['LAT_diff'] > 0,
    'North',
    np.where(ds2['LAT_diff'] < 0, 
    'South', 
    'No displacement')
)

# #print(ds2)

# # pivot
# piv_EW = ds2.pivot_table(
#     index='sub_basin_start',
#     columns=['East/West_displ'],
#     values='TID',
#     aggfunc='count',
#     fill_value=0
# )

# piv_NS = ds2.pivot_table(
#     index='sub_basin_start',
#     columns=['North/South_displ'],
#     values='TID',
#     aggfunc='count',
#     fill_value=0
# )

# # print(piv_EW)
# # print(piv_NS)

# # bar plot (all sub basins)
# piv_EW.plot(kind='bar', figsize=(10, 6))

# plt.ylabel('Count of TCs')
# plt.xlabel('Origin Sub-basin')
# plt.title('TC East vs. West Track Displacement From Origin Sub-basin')
# plt.xticks(rotation=45, ha='right')
# plt.legend(['East', 'No Displacement', 'West'])
# plt.tight_layout()

# plt.savefig("images/data_viz/TC_track/track_plots/TC_track_distance_EastvsWest_bySubbasin.png")
# plt.show()

##############################################################################################################

# per sub basin plots 

# sub basin toggle
sb = 'Mid-latitudinal Atlantic'

ds3 = ds2[ds2['sub_basin_start'] == sb]

fig, ax = plt.subplots(figsize=(8,4))

ax.hist(ds3['LON_diff'], bins=20, edgecolor='black', color='lightblue')

ax.axvline(0, color='red', linestyle='--', label='No displacement')

ax = plt.gca()
ax.yaxis.set_major_locator(MaxNLocator(integer=True))

ax.set_xlabel('Longitude displacement (degrees)')
ax.set_ylabel('Number of TCs')
ax.set_title(f'East vs. West Displacement From TCs Originating in {sb}', pad = 30)

ax.text(0.05, 1.05, 'West',
        transform=ax.transAxes,
        ha='left', va='center')

ax.annotate(
    '',
    xy=(0.12, 1.05),      # arrow tip (left)
    xytext=(0.30, 1.05),  # arrow starts (right)
    xycoords='axes fraction',
    textcoords='axes fraction',
    arrowprops=dict(arrowstyle='->', lw=1.5)
)

# North
ax.annotate(
    '',
    xy=(0.88, 1.05),      # arrow tip (right)
    xytext=(0.70, 1.05),  # arrow starts (left)
    xycoords='axes fraction',
    textcoords='axes fraction',
    arrowprops=dict(arrowstyle='->', lw=1.5)
)

ax.text(0.95, 1.05, 'East',
        transform=ax.transAxes,
        ha='right', va='center')

ax.legend()

plt.tight_layout()
plt.savefig(f'images/data_viz/TC_track/track_plots/TC_track_distance_EastvsWest_{sb}.png', dpi=300)
plt.show()