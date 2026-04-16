import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import xarray as xr
import rioxarray
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature
import numpy as np
import regionmask

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

# read in tc_subbasins_NAtl file
sub_polygons_dict = {}

with open("tc_subbasins_NAtl.dat", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(",")
        sub_basin_name = parts[0].replace('"', '')
        n_vertices = int(parts[1])

        lon_vals = list(map(float, parts[2:2+n_vertices]))
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

# open COBE SST monthly mean file
time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)
ds = xr.open_dataset(r"datasets/COBE2 SST/sst.mon.mean.nc", decode_times=time_coder)

# filter to only SST variable
sst = ds["sst"]

# convert lon to -180-180
sst = sst.assign_coords(
    lon=(((sst.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
sst = sst.rio.write_crs("EPSG:4326")
sst = sst.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atlantic basin
region = basins[basins["basin name"] == "N Atlantic"]

# filter out Arctic and continental US sub-basins
region_subbasins = sub_basins[sub_basins["sub_basin_name"].isin(["Gulf", "Caribbean", "Northeastern Seaboard", "Tropical Atlantic", "Subtropical Atlantic", "Mid-latitudinal Atlantic", "Southeastern Seaboard"])]

# keep full dataset for anom calc
sst_full = (
    sst
    .rio.clip(region.geometry, region.crs, drop=True)
    .rio.clip(region_subbasins.geometry, region_subbasins.crs, drop=True)
    .sel(time=slice(None, "2025-12-31"))
)

# for moving mean, remove last 10 years (2016-2025) of data since we don't have enough future data to cover the long term mean calc
start = str(int(sst_full.time.dt.year.min()) + 10)
end   = str(int(sst_full.time.dt.year.max()) - 10)

sst_filt = sst_full.sel(time=slice(start, end))

# anomaly calc: use moving mean for year n (year-10, year+10)
rolling_clim = sst_full.groupby("time.month").map(
    lambda x: x.rolling(time=21, center=True).mean()
)
sst_anom = sst_filt - rolling_clim.sel(time=sst_filt.time)

# filter to specific months
sst_anom_late_season = sst_anom.sel(time=sst_anom.time.dt.month.isin([9,10]))

# save filtered datasets
sst_anom_late_season.to_netcdf(r"datasets/COBE2 SST/post-processing/SST_mon_mean_anom_moving_window_sep_oct_lateszn.nc")

#print(sst_anom)

########################################################################################
# now region mask for subbasin categorization for region generation

# --- Load dataset ---
#sst_ds = xr.open_dataset(r"datasets\COBE2 SST\post-processing\SST_mon_mean_anom_moving_window_jun_oct.nc", decode_times=True)
#sst_var = "sst"  # variable name

# --- Create sub-basin mask (lat, lon) ---
#regions = regionmask.from_geopandas(region_subbasins, names="sub_basin_name")
#mask = regions.mask(sst_ds)  # lat, lon with basin IDs and NaN outside

# --- Fill NaNs if needed ---
#mask_filled = mask.fillna(-1)

# --- Add mask to dataset ---
#sst_ds["sub_basin_id"] = mask_filled
#sst_ds["sub_basin_id"].attrs["sub_basin_names"] = list(sub_basins["sub_basin_name"])

# Stack spatial dims
#sst_stack = sst_ds[sst_var].stack(stacked_lat_lon=("lat", "lon"))
#mask_stack = sst_ds["sub_basin_id"].stack(stacked_lat_lon=("lat", "lon"))

# Assign coordinate
#sst_stack = sst_stack.assign_coords(sub_basin_id=mask_stack)

# Compute means
#sst_basin_mean = (
#    sst_stack
#    .where(sst_stack.sub_basin_id != -1)
#    .groupby("sub_basin_id")
#    .mean(dim="stacked_lat_lon", skipna=True)
#)

# Broadcast using indexing (THIS is the key line)
#sst_basin_grid_stack = sst_basin_mean.sel(sub_basin_id=sst_stack.sub_basin_id)

# Unstack
#sst_basin_grid = sst_basin_grid_stack.unstack("stacked_lat_lon")

# Mask out invalid regions
#sst_basin_grid = sst_basin_grid.where(sst_ds["sub_basin_id"] != -1)

#print(sst_basin_grid)

# save to netcdf
#sst_basin_grid.to_netcdf(r"datasets\COBE2 SST\post-processing\SST_mon_mean_anom_moving_window_subbasin_v2_jun_oct.nc")

