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
import matplotlib.pyplot as plt

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

#print(df['Adjusted_Label'].unique())

# TC Nodes:
#dftc_node=df[(df.Track_Info.str.contains('TC')) & (df.Short_Label=='TC')]
#dftc_node=df[df.Track_Info=='Track_TC']
#dftc_node = df[((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD') | (df.Adjusted_Label=='SS(STLC)')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

dftc_node = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
#dftc_node = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

#print(dftc_node['Adjusted_Label'].unique())

# first node: where the TC originates
tc_origin = (
    dftc_node
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .head(1)
)

#print(tc_origin.shape)

# last node: where the TC dissipates
TC_TIDs = tc_origin['TID']
tc_dissipate = (
    dftc_node[(dftc_node['TID'].isin(TC_TIDs)) & (dftc_node['Tropical_Flag'] == 1)]
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .tail(1)
)

#print(tc_dissipate.shape)

# make a new column with YEAR only from ISOTIME
#dfc_sub["YEAR"] = pd.to_datetime(dfc_sub["ISOTIME"]).dt.year

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

# convert lon to -180-180 from 0-360
tc_origin_filtered['LON'] = ((tc_origin_filtered['LON'] + 180) % 360) - 180
tc_dissipate_filtered['LON'] = ((tc_dissipate_filtered['LON'] + 180) % 360) - 180

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
tc_track = tc_track[['TID', 'LON_start', 'LAT_start', 'LON_end', 'LAT_end', 'YEAR_start', 'YEAR_end']]

#print(tc_track.columns)
#print(tc_track.head())

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

print(tc_track.head())
#print(tc_track.shape)

# save table
tc_track.to_csv("datasets/SyCLoPS/tc&td_track_subbasin_table_withYear.csv", index = False)