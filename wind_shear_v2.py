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

# CALCULATING SHEAR USING U AND V COMPONENT MAGNITUDE

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

# combine u-wind & v-wind files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/pressure/)

# remove time bounds variable since we don't need it/mismatched data types across raw files
def clean(ds):
    if "time_bnds" in ds:
        ds = ds.drop_vars("time_bnds")
    
    return ds

ds1 = xr.open_mfdataset(
    "datasets/u-wind/*.nc",
    combine="by_coords",
    preprocess=clean,
    chunks={"time": 365}
)

ds2 = xr.open_mfdataset(
    "datasets/v-wind/*.nc",
    combine="by_coords",
    preprocess=clean,
    chunks={"time": 365}
)

uwnd = ds1["uwnd"].sel(level=[850, 200])
vwnd = ds2["vwnd"].sel(level=[850, 200])

# convert lon to -180-180
uwnd = uwnd.assign_coords(
    lon=(((uwnd.lon + 180) % 360) - 180)
).sortby("lon")
vwnd = vwnd.assign_coords(
    lon=(((vwnd.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
uwnd = uwnd.rio.write_crs("EPSG:4326")
uwnd = uwnd.rio.set_spatial_dims(x_dim="lon", y_dim="lat")
vwnd = vwnd.rio.write_crs("EPSG:4326")
vwnd = vwnd.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atl
region = basins[basins["basin name"] == "N Atlantic"]
uwnd = uwnd.rio.clip(region.geometry, region.crs, drop=True)
vwnd = vwnd.rio.clip(region.geometry, region.crs, drop=True)

# filter to hurricane season
uwnd = (
    uwnd
    .where(uwnd.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
    .rio.clip(region.geometry, region.crs, drop=True)
)
vwnd = (
    vwnd
    .where(vwnd.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
    .rio.clip(region.geometry, region.crs, drop=True)
)

# print(uwnd)
# print(vwnd)

# calc shear
u850 = uwnd.sel(level=850)
v850 = vwnd.sel(level=850)

u200 = uwnd.sel(level=200)
v200 = vwnd.sel(level=200)

shear = np.sqrt(
    (u850 - u200)**2 +
    (v850 - v200)**2
)

shear_monthly = shear.resample(time="1MS").mean()

print(shear_monthly)

# save 
shear_monthly.to_netcdf("datasets/GPI/GPI_EN_calc/shear_850_200_monthly_v2.nc")
