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
import xarray as xr

# read in tc_basins file so we can filter to a specific ocean basin
polygons_dict = {}

with open("tc_basins_NAtl.dat", "r") as f:
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

#################################################################################################################################

## read in and filter our syclops data
# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024_v7.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# TC Nodes: filter to TCs only, tropical flag = 1 so we are only counting before they become extratropical
# tc = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
tc = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# sort by TID and ISOTIME
tc = tc.sort_values(['ISOTIME'])

# convert lon to -180-180 from 0-360
tc['LON'] = ((tc['LON'] + 180) % 360) - 180

# Northern Hemisphere only
tc = tc[tc["LAT"] >= 0].copy()

# hurricane season only
tc["month"] = tc["ISOTIME"].dt.month
tc = tc[tc["month"].between(6, 10)].copy()

# create 5deg lat/lon bins for TC data
tc["LON_bin"] = np.floor(tc["LON"] / 5) * 5
tc["LAT_bin"] = np.floor(tc["LAT"] / 5) * 5

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
tc_points = gpd.GeoDataFrame(
    tc, 
    geometry = gpd.points_from_xy(tc.LON, tc.LAT),
    crs = "EPSG:4326"
)

# filter points to North Atlantic
tc_filtered = gpd.sjoin(
    tc_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# filter to columns we need
tc_filtered = tc_filtered[['TID', 'LON', 'LAT', 'ISOTIME','LON_bin', 'LAT_bin']]

# print(tc_filtered)

################################################################################################################

# load variable dataset
ds = xr.open_dataset("datasets/COBE2 SST/post-processing/SST_daily_mean_1940-2024_clim_jun_oct.nc")

# select variable
var = ds["sst"]

# define the same 5deg bins used for TC data
lat_edges = np.arange(0, 95, 5)
lon_edges = np.arange(-110, 25, 5)

# bin variable into 5deg cells
var_binned = var.groupby_bins(
    "lat",
    lat_edges,
    labels=lat_edges[:-1]
).mean()

var_binned = var_binned.groupby_bins(
    "lon",
    lon_edges,
    labels=lon_edges[:-1]
).mean()

# rename to match TC dataframe
var_binned = var_binned.rename({
    "lat_bins": "LAT_bin",
    "lon_bins": "LON_bin"
})

# convert variable dataset to a DataFrame
var_df = (
    var_binned
    .to_dataframe(name="sst")
    .reset_index()
)

# make sure date formats match between TC and var data
tc_filtered["date"] = pd.to_datetime(tc_filtered["ISOTIME"]).dt.normalize()
var_df["date"] = pd.to_datetime(var_df["time"]).dt.normalize()

# print(tc_filtered.head())
# print(var_df.head())

# merge tables
merged = tc_filtered.merge(
    var_df[["date", "LAT_bin", "LON_bin", "sst"]],
    on=["date", "LAT_bin", "LON_bin"],
    how="left"
)

# print(merged.head())

################################################################################################################

# histogram
# keep June-October and observations with valid SST
merged_valid = merged[
    merged["sst"].notna()
].copy()

plt.figure(figsize=(8, 5))

plt.hist(
    merged_valid["sst"],
    bins=20,
    edgecolor="black"
)

# 26.5°C threshold
plt.axvline(
    26.5,
    color="red",
    linestyle="--",
    linewidth=2,
    label="26.5°C"
)

plt.xlabel("SST (°C)")
plt.ylabel("Number of TC observations")
plt.title("SST Distribution Per Tropical Cyclone (1940-2025)")

plt.tight_layout()
plt.savefig("images/data_viz/thresholds/tc_sstTH_histogram_syclops_noaa_match.png")
plt.show()