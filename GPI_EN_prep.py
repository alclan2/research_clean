import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import xarray as xr
from glob import glob
from windspharm.xarray import VectorWind

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

#################################################################################################################

# # load in u and v wind data to calculate 850hPa vorticity
# ds1 = xr.open_mfdataset(
#     "datasets/u-wind/*.nc", 
#     combine = "by_coords", 
#     preprocess=lambda ds: ds.drop_vars("time_bnds", errors="ignore")
# )
# ds2 = xr.open_mfdataset(
#     "datasets/v-wind/*.nc", 
#     combine = "by_coords", 
#     preprocess=lambda ds: ds.drop_vars("time_bnds", errors="ignore")
# )

# # select the variables
# uwnd = ds1["uwnd"]
# vwnd = ds2["vwnd"]

# # convert lon to -180-180
# uwnd = uwnd.assign_coords(
#     lon=(((uwnd.lon + 180) % 360) - 180)
# ).sortby("lon")
# vwnd = vwnd.assign_coords(
#     lon=(((vwnd.lon + 180) % 360) - 180)
# ).sortby("lon")

# # filter to relative humidity to a specific pressure level only
# uwnd850 = uwnd.sel(level=850)
# vwnd850 = vwnd.sel(level=850)

# # filter to hurricane season
# uwnd850_szn = (
#     uwnd850
#     .where(uwnd850.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
# )
# vwnd850_szn = (
#     vwnd850
#     .where(vwnd850.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
# )

# # compute daily relative vorticity
# w = VectorWind(uwnd850_szn, vwnd850_szn)
# vort850 = w.vorticity()

# # compute planetary vorticity and add to relative (to calc absolute vort)
# omega = 7.2921e-5
# f = 2 * omega * np.sin(np.deg2rad(vort850.lat))
# abs_vort = vort850 + f

# # filter to N Atlantic basin
# abs_vort = abs_vort.rio.write_crs("EPSG:4326")
# region = basins[basins["basin name"] == "N Atlantic"]
# abs_vort = abs_vort.rio.clip(region.geometry, region.crs, drop=True)

# # average to monthly
# abs_vort_monthly = abs_vort.resample(time="1MS").mean()

# print(abs_vort_monthly)

# # save dataset
# abs_vort_monthly.to_netcdf("datasets/GPI/GPI_EN_calc/abs_vort_850_monthly.nc")

#################################################################################################################

# # rhum data
# # combine relative humidity files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/pressure/)
# ds = xr.open_mfdataset(
#     "datasets/RHUM/*.nc",
#     combine = "by_coords",
#     preprocess=lambda ds: ds.drop_vars("time_bnds", errors="ignore"),
# )

# # print(ds)

# # select the RHUM variable
# rhum = ds["rhum"]

# # convert lon to -180-180
# rhum = rhum.assign_coords(
#     lon=(((rhum.lon + 180) % 360) - 180)
# ).sortby("lon")

# # filter to relative humidity to a specific pressure level only
# rhum600 = rhum.sel(level=600)

# # roll up to monthly means
# rhum600_monthly = rhum600.resample(time="MS").mean()

# # add CRS and spatial dims
# rhum600_monthly = rhum600_monthly.rio.write_crs("EPSG:4326")
# rhum600_monthly = rhum600_monthly.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# # filter to N Atlantic basin
# region = basins[basins["basin name"] == "N Atlantic"]

# # filter to hurricane season
# rhum600_full = (
#     rhum600_monthly
#     .where(rhum600_monthly.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
#     .rio.clip(region.geometry, region.crs, drop=True)
# )

# print(rhum600_full.head())

# # save dataset
# rhum600_full.to_netcdf("datasets/GPI/GPI_EN_calc/rhum_600_monthly.nc")

#################################################################################################################

# potential intensity data
ds = xr.open_dataset("datasets/potential_intensity/pi_output.nc")

print(ds)

# select variable
vmax = ds['vmax']

print(vmax)

# # save dataset
# vmax.to_netcdf("datasets/GPI/GPI_EN_calc/potential_intensity_monthly.nc")

#################################################################################################################

# # load shear dataset
# # combine u-wind files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/pressure/)

# # remove time bounds variable since we don't need it/mismatched data types across raw files
# def clean(ds):
#     if "time_bnds" in ds:
#         ds = ds.drop_vars("time_bnds")
    
#     return ds

# ds = xr.open_mfdataset(
#     "datasets/u-wind/*.nc",
#     combine="by_coords",
#     preprocess=clean,
#     chunks={"time": 365}
# )
# ds = ds.sel(level=[850, 200])

# # convert lon to -180-180
# ds = ds.assign_coords(
#     lon=(((ds.lon + 180) % 360) - 180)
# ).sortby("lon")

# # add CRS and spatial dims
# ds = ds.rio.write_crs("EPSG:4326")
# ds = ds.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# # filter to N Atlantic basin
# region = basins[basins["basin name"] == "N Atlantic"]

# # filter to hurricane season
# ds_filt = (
#     ds
#     .where(ds.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
#     .rio.clip(region.geometry, region.crs, drop=True)
# )

# # select 250 and 800 hPa
# uwind = ds_filt.uwnd.sel(level=[850, 200])

# # calculate vertical shear
# shear = uwind.sel(level=200) - uwind.sel(level=850)

# # roll up to monthly means
# shear_monthly = shear.resample(time="MS").mean()

# print(shear_monthly)

# # save dataset
# shear_monthly.to_netcdf("datasets/GPI/GPI_EN_calc/shear_850_200_monthly.nc")
