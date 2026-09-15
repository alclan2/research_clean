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
import xarray as xr
import glob

# read in basin definition file
polygons_dict = {}

# read in basin definition file
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

# convert basins' lon to -180-180
basins["geometry"] = basins["geometry"].apply(
    lambda geom: transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )
)

# read in NAtl subbasin polygons
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

#######################################################################################

# combine mslp files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/surface/)
files = sorted(glob.glob("datasets/MSLP/NOAA/mslp.*.nc"))
mslp_list = [
    xr.open_dataset(f, chunks={"time": 30})["mslp"]
    for f in files
]
mslp = xr.concat(mslp_list, dim="time")

# convert lon to -180-180
mslp = mslp.assign_coords(
    lon=(((mslp.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
mslp = mslp.rio.write_crs("EPSG:4326")
mslp = mslp.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atlantic basin
region = basins[basins["basin name"] == "N Atlantic"]

# filter to hurricane season
mslp_filt = (
    mslp
    .where(mslp.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
    .rio.clip(region.geometry, region.crs, drop=True)
)




# Get the spatial grid from one day
grid = mslp_filt.isel(time=0).to_dataframe(
    name="mslp"
).reset_index()

# Convert grid cells to points
grid_gdf = gpd.GeoDataFrame(
    grid,
    geometry=gpd.points_from_xy(
        grid["lon"],
        grid["lat"]
    ),
    crs="EPSG:4326"
)

# join sub basins
grid_gdf = gpd.sjoin(
    grid_gdf,
    sub_basins[["sub_basin_name", "geometry"]],
    how="inner",
    predicate="within"
)

# lookup table
grid_lookup = grid_gdf[
    ["lat", "lon", "sub_basin_name"]
].copy()

# convert to hPa
mslp_hpa = mslp_filt / 100

# convert to data frame
mslp_df = mslp_hpa.to_dataframe(
    name="mslp"
).reset_index()

# attach sub basins
mslp_df = mslp_df.merge(
    grid_lookup,
    on=["lat", "lon"],
    how="inner"
)

# threshold (lower than the environmental norm)
threshold = 1012

# daily min MSLP per subbasin
daily = (
    mslp_df
    .groupby(["time", "sub_basin_name"])["mslp"]
    .mean()
    .reset_index()
)

daily["below_threshold"] = daily["mslp"] < threshold

daily["year"] = daily["time"].dt.year

# print(daily)

# pivot to an annual count of days per year below the threshold
annual = (
    daily
    .groupby(["year", "sub_basin_name"])["below_threshold"]
    .sum()
    .reset_index(name="days_below_threshold")
)

print(annual)

# save to csv
annual.to_csv("datasets/data_viz/MLR/thresholds/mslp_daily_meanPerSB_bySubbasin_table.csv")