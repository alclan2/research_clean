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

# # combine files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/surface/)
# ds = xr.open_mfdataset(
#     "datasets/RHUM/*.nc",
#     combine = "by_coords",
#     preprocess=lambda ds: ds.drop_vars("time_bnds", errors="ignore"),
# )

# # select the variable
# ds2 = ds["rhum"]

# # convert lon to -180-180
# ds2 = ds2.assign_coords(
#     lon=(((ds2.lon + 180) % 360) - 180)
# ).sortby("lon")

# # add CRS and spatial dims
# ds2 = ds2.rio.write_crs("EPSG:4326")
# ds2 = ds2.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# # filter to N Atlantic basin
# region = basins[basins["basin name"] == "N Atlantic"]

# # filter to hurricane season
# ds2_filt = ds2.where(
#     ds2.time.dt.month.isin([6, 7, 8, 9, 10]),
#     drop=True
# )

# # print("AFTER MONTH FILTER")
# # print(ds2_filt.time.dt.month.values[:30])
# # print(ds2_filt.time.size)

# # filter basin
# ds2_filt = ds2_filt.rio.clip(
#     region.geometry,
#     region.crs,
#     drop=True
# )

# # clip time period
# ds2_filt = ds2_filt.sel(time=slice("1979-06-01", "2025-10-01"))

# # aggregate daily means to monthly means
# ds2_monthly = ds2_filt.resample(time="MS").mean("time")

# ds2_monthly = (
#     ds2_filt
#     .resample(time="MS")
#     .mean("time")
#     .where(
#         lambda x: x.time.dt.month.isin([6,7,8,9,10]),
#         drop=True
#     )
# )

# # rename level to p
# ds2_monthly = ds2_monthly.rename({"level": "p"})

# # # convert from kelvin to C
# # ds2_monthly = ds2_monthly - 273.15

# print(ds2_monthly.time.dt.month.values[:20])
# print(ds2_monthly.sizes)

# # save filtered datasets
# ds2_monthly.to_netcdf("datasets/potential_intensity/input/rhum_mean_1979-2025.nc")

#######################################################################################

# now calc specific humidity

# load air temp dataset
air = xr.open_mfdataset("datasets/potential_intensity/input/air_temp_mean_1979-2025.nc")

# load rhum dataset
rhum = xr.open_dataset("datasets/potential_intensity/input/rhum_mean_1979-2025.nc")

# temperature in Celsius
T = air["air"]

# relative humidity as fraction (0-1)
RH = rhum["rhum"] / 100

# saturation vapor pressure (hPa)
es = 6.112 * np.exp(
    (17.67 * T) / (T + 243.5)
)

# actual vapor pressure (hPa)
e = RH * es

# pressure coordinate (hPa)
p = air.p

# mixing ratio (kg/kg)
r = 0.622 * e / (p - e)

# convert to g/kg for tcpyPI
R = r * 1000

# save to dataset
R.to_netcdf("datasets/potential_intensity/input/mixing_ration_mean_1979-2025.nc")

print(R.min().values)
print(R.max().values)