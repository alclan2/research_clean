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

# combine u-wind files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/pressure/)

# remove time bounds variable since we don't need it/mismatched data types across raw files
def clean(ds):
    if "time_bnds" in ds:
        ds = ds.drop_vars("time_bnds")
    
    return ds

ds = xr.open_mfdataset(
    "datasets/u-wind/*.nc",
    combine="by_coords",
    preprocess=clean,
    chunks={"time": 365}
)
ds = ds.sel(level=[850, 200])

# convert lon to -180-180
ds = ds.assign_coords(
    lon=(((ds.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
ds = ds.rio.write_crs("EPSG:4326")
ds = ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atlantic basin
region_names = [
    "Deep Tropics",
    "Caribbean",
    "Eastern Tropics",
    "Gulf (A)",
    "Gulf (B)",
    "Southeastern Seaboard",
    "Central Atlantic",
    "Subtropical Atlantic",
    "Northeastern Seaboard",
    "Mid-latitudinal Atlantic",
    "Mid-latitudinal US/CA",
    "Arctic",
    "Northern Europe",
    "Western Africa",
    "Mediterranean Sea"
]
region = sub_basins[sub_basins["sub_basin_name"].isin(region_names)]

# filter to hurricane season
ds_filt = (
    ds
    .where(ds.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
    .rio.clip(region.geometry, region.crs, drop=True)
)

# select 250 and 800 hPa
uwind = ds_filt.uwnd.sel(level=[850, 200])

# calculate vertical shear
shear = uwind.sel(level=200) - uwind.sel(level=850)

# convert to data frame
shear_df = (
    shear
    .rename("shear")
    .to_dataframe()
    .reset_index()
    .dropna(subset=["shear"])
)

# Create point geometries
points = gpd.GeoDataFrame(
    shear_df,
    geometry=gpd.points_from_xy(
        shear_df.lon,
        shear_df.lat
    ),
    crs="EPSG:4326"
)

# spatial join
shear_sb = gpd.sjoin(
    points,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="covered_by"
)

# add year column
shear_sb["year"] = shear_sb["time"].dt.year

# trim columns
shear_sb = shear_sb[['time', 'lat', 'lon', 'shear', 'sub_basin_name', 'year']]

# pivot to yearly values
shear_yr = (
    shear_sb.groupby(["year", "sub_basin_name"], as_index=False)["shear"]
      .mean()
)

#print(shear_yr)

# save to csv
shear_yr.to_csv("datasets/u-wind/post_processing/wind_shear_850_200_yearly_by_subbasin.csv")

########################################################################################

# plot mean WS as a time series per sub basin

# # select sub basin
# sb = 'Caribbean'

# df_plot = shear_yr[shear_yr["sub_basin_name"] == sb]

# #print(df_plot)

# plt.figure(figsize=(10, 5))
# plt.plot(df_plot["year"], df_plot["uwnd"], marker="o", color = "green")

# plt.title(f"Wind Shear in North Atlantic - {sb}")
# plt.xlabel("Year")
# plt.ylabel("Wind Shear (m/s)")

# plt.tight_layout()
# # plt.savefig(f"images/data_viz/MSLP/NOAA/MSLP_moving_window_anom_timeseries_{sb}.png")
# plt.show()