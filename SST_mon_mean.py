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
ds = xr.open_dataset(r"datasets\sst.mon.mean.nc", decode_times=time_coder)

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
region_subbasins = sub_basins[sub_basins["sub_basin_name"].isin(["Gulf", "Caribbean", "Northeastern Seaboard", "Tropical Atlantic", "Subtropical Atlantic", "Mid-latitudinal Atlantic", "Southeastern Seaboard", "Arctic", "Mid-latitudinal US/CA"])]

sst_filt = (
    sst
    .rio.clip(region.geometry, region.crs, drop=True)
    .rio.clip(region_subbasins.geometry, region_subbasins.crs, drop=True)
    .sel(time=slice(None, "2025-12-31"))
)

# calculate the climatological mean
monthly_clim = sst_filt.groupby("time.month").mean("time")

# calculate the sst anomaly
sst_anom = sst_filt.groupby("time.month") - monthly_clim

# save filtered datasets
sst_anom.to_netcdf("SST_mon_mean_anom_withArcticAndCONUS.nc")


#check
#print(sst_anom.dims)
#print(len(sst_anom.time))

#print(sst_anom.groupby("time.month").mean("time"))

#print(sst_anom.groupby("time.month").mean("time"))
#print(sst_anom.min().values, sst_anom.max().values)
#sst_anom.isel(time=0).plot()
#plt.show()

#print(sst_anom.groupby("time.month").mean("time"))
#print(sst_anom.time.min().values)
#print(sst_anom.time.max().values)
#print(sst_anom.dims)

#print(sst_filt.min().values)
#print(sst_filt.max().values)
#print(sst_filt.count())

#print(sst.rio.crs)
#print(region.crs)
#print(region_subbasins.crs)

#sst_filt.isel(time=0).plot()
#plt.show()


# save filtered datasets
#sst_filt_final.to_netcdf("SST_mon_mean_1deg.nc")

# add sub basin region mask
#sst_subbasin = xr.open_dataset("SST_ltmm_NAtl_1deg.nc", decode_times=time_coder)

# read in tc_subbasins_NAtl file
#sub_polygons_dict = {}

#with open("tc_subbasins_NAtl.dat", "r") as f:
#    for line in f:
#        line = line.strip()
#        if not line or line.startswith("#"):
#            continue

#        parts = line.split(",")
#        sub_basin_name = parts[0].replace('"', '')
#        n_vertices = int(parts[1])

#        lon_vals = list(map(float, parts[2:2+n_vertices]))
#        lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

#        coords = list(zip(lon_vals, lat_vals))
#        poly = Polygon(coords)

#        if sub_basin_name not in sub_polygons_dict:
#            sub_polygons_dict[sub_basin_name] = []
#        sub_polygons_dict[sub_basin_name].append(poly)

# Convert to GeoDataFrame
#sub_basin_records = []

#for name, poly_list in sub_polygons_dict.items():
#    if len(poly_list) == 1:
#        geom = poly_list[0]
#    else:
#        geom = MultiPolygon(poly_list)

#    sub_basin_records.append({
#        "sub_basin_name": name,
#        "geometry": geom
#    })

#sub_basins = gpd.GeoDataFrame(sub_basin_records, crs="EPSG:4326",geometry="geometry")

# fix invalid polygons
#sub_basins["geometry"] = sub_basins["geometry"].buffer(0)

# remove empty geometries
#sub_basins = sub_basins[~sub_basins.geometry.is_empty]

# longitude conversion
#import shapely.ops
#def shift_lon(geom):
#    return shapely.ops.transform(
#        lambda x, y: (((x + 180) % 360) - 180, y),
#        geom
#    )

# shift lon
#sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)

# create a region mask
#regions = regionmask.from_geopandas(
#    sub_basins,
#    names="sub_basin_name"
#)

# create the polygon mask
#mask = regions.mask(sst_subbasin)

# add mask to dataset
#sst_subbasin["sub_basin_id"] = mask

# save sub basin names
#sst_subbasin["sub_basin_id"].attrs["sub_basin_names"] = list(sub_basins["sub_basin_name"])

# remove problematic metadata
#var = sst_subbasin["sst"]
#var.attrs.pop("missing_value", None)
#var.attrs.pop("_FillValue", None)

# clear encoding that may still contain missing_value
#var.encoding = {}

# save sst dataset with sub basin ids
#sst_subbasin.to_netcdf("SST_ltmm_NAtl_subbasins.nc")

#print(sst_filt.coords)

#ds = xr.open_dataset("SST_ltmm_NAtl_1deg.nc", decode_times=time_coder)
#da = ds['sst']
#print(ds)