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
import matplotlib.patheffects as pe
import textwrap

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

with open("tc_subbasins_NAtl_v4.dat", "r") as f:
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

## filter out Arctic and continental US sub-basins
#region_subbasins = sub_basins[sub_basins["sub_basin_name"].isin(["Central Atlantic"])]

# filter to hurricane season
sst_filt = (
    sst
    .where(sst.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
    .rio.clip(region.geometry, region.crs, drop=True)
    .sel(time=slice(None, "2025-12-31"))
)

# calculate the mean SST (not for anomaly calc)
annual_mean = sst_filt.groupby("time.year").mean("time") 

## calculate the climatological mean
#monthly_clim = sst_filt.groupby("time.month").mean("time")

## calculate the sst anomaly
#sst_anom = sst_filt.groupby("time.month") - monthly_clim

print(annual_mean)

# save filtered datasets
annual_mean.to_netcdf("datasets/COBE2 SST/post-processing/SST_annual_mean_notAnomaly_jun_oct.nc")

#print(sst_anom.head())


#####################################################################################

## plot the sst's for hurricane season
#fig = plt.figure(figsize=(8,6))
#ax = plt.axes(projection=ccrs.PlateCarree()) 

## Plot sub-basins first
#sub_basins.plot(
#    ax=ax,
#    facecolor='none',
#    edgecolor='red',
#    path_effects=[pe.withStroke(linewidth=3, foreground='white')],
#    linewidth=1,
#    transform=ccrs.PlateCarree(),
#    zorder=4
#)

#sst_mean_szn.plot(
#    ax=ax,
#    transform=ccrs.PlateCarree(),
#    cmap="coolwarm",
#    cbar_kwargs={"label": "SST (°C)"}
#)

#ax.coastlines()
#ax.set_extent([-70, -20, 15, 50],crs=ccrs.PlateCarree())

# add sub-basin labels
#for idx, row in sub_basins.iterrows():
#    point = row.geometry.representative_point()
#    name = row["sub_basin_name"]
#
#    # wrap text (adjust width as needed)
#    name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
#    
#    if (-120 <= point.x <= 30) and (-5 <= point.y <= 65):
#        txt = ax.text(
#            point.x, point.y,
#            name_wrapped,
#            transform=ccrs.PlateCarree(),
#            fontsize=7,
#            weight='bold',
#            ha='center',
#            va='center',
#            color='black',
#            zorder=4
#        )
#        
#        txt.set_path_effects([
#            pe.withStroke(linewidth=3, foreground="white")
#        ])

#ax.set_xlabel('Longitude')
#ax.set_ylabel('Latitude')

## Add gridlines with labels
#gl = ax.gridlines(
#    draw_labels=True,
#    linewidth=0.1,
#    color='gray',
#    linestyle='--'
#)

#gl.xlocator = plt.MultipleLocator(10)  # longitude every 10°
#gl.ylocator = plt.MultipleLocator(10)  # latitude every 10°
#gl.xlabel_style = {'size': 10, 'color': 'black'}
#gl.ylabel_style = {'size': 10, 'color': 'black'}

#ax.set_title("Mean SST (October, 1850-2025)")

#plt.savefig("images/SST_CtrlAtl_mon_mean_oct.png")
#plt.show()





######################################################################################################

# now calc the anomaly using the long term monthly mean dataset
# open COBE SST long term monthly mean file
#ds_ltmm = xr.open_dataset(r"datasets\sst.mon.ltm.1981-2010.nc", decode_times=time_coder)

#print(ds_ltmm)

# filter to only SST variable
#sst_ltmm = ds_ltmm["sst"]

# convert lon to -180-180
#sst_ltmm = sst_ltmm.assign_coords(
#    lon=(((sst_ltmm.lon + 180) % 360) - 180)
#).sortby("lon")

# add CRS and spatial dims
#sst_ltmm = sst_ltmm.rio.write_crs("EPSG:4326")
#sst_ltmm = sst_ltmm.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# Assign month coordinate and compute 12-month climatology
#sst_ltmm_clim = (
#    sst_ltmm
#    .assign_coords(month=sst_ltmm.time.dt.month)
#    .groupby("month")
#    .mean("time")
#)

# Clip climatology to your basin (after calculating climatology)
#sst_ltmm_clim_filt = (
#    sst_ltmm_clim
#    .rio.clip(region.geometry, region.crs, drop=True)
#    .rio.clip(region_subbasins.geometry, region_subbasins.crs, drop=True)
#)

# sst_filt already clipped and filtered
#sst_filt = sst_filt.copy()

# convert time coordinate to standard datetime index
#sst_filt["time"] = sst_filt.indexes["time"].to_datetimeindex()

# now you can safely groupby months and calculate anomalies
#sst_anom_ltmm = sst_filt.groupby("time.month") - sst_ltmm_clim_filt

# Calculate SST anomaly
#sst_anom_ltmm = sst_filt.groupby("time.month") - sst_ltmm_clim_filt

# save filtered datasets
#sst_anom_ltmm.to_netcdf("SST_mon_mean_anom_ltmm.nc")

#print(sst_anom_ltmm.groupby("time.month").mean(("time","lat","lon")))

########################################################################################
# now region mask for subbasin categorization for region generation

# --- Load dataset ---
#sst_ds = xr.open_dataset("SST_mon_mean_anom.nc", decode_times=True)
#sst_var = "sst"  # variable name

# --- Create sub-basin mask (lat, lon) ---
#regions = regionmask.from_geopandas(sub_basins, names="sub_basin_name")
#mask = regions.mask(sst_ds)  # lat, lon with basin IDs and NaN outside

# --- Fill NaNs if needed ---
#mask_filled = mask.fillna(-1)

# --- Add mask to dataset ---
#sst_ds["sub_basin_id"] = mask_filled
#sst_ds["sub_basin_id"].attrs["sub_basin_names"] = list(sub_basins["sub_basin_name"])

# Stack spatial dims
#sst_stack = sst_ds[sst_var].stack(stacked_lat_lon=("lat", "lon"))
#mask_stack = sst_ds["sub_basin_id"].stack(stacked_lat_lon=("lat", "lon"))

# Compute mean for each sub-basin
# Use groupby to get the mean for each sub-basin (per time)
#sst_basin_mean = sst_stack.groupby(mask_stack).mean(dim="stacked_lat_lon", skipna=True)

# Broadcast the basin mean back to each grid point
# Create a mapping from basin_id -> basin mean
# mask_stack has shape (stacked_lat_lon,)
# We can use xarray's indexing via groupby_bins trick

#sst_basin_grid_stack = sst_stack.copy()  # same shape as stacked
#for basin_id in np.unique(mask_stack.values[~np.isnan(mask_stack.values)]):
#    # select grid points in this basin
#    locs = mask_stack == basin_id
#    # assign the mean to those grid points
#    sst_basin_grid_stack.loc[dict(stacked_lat_lon=locs)] = sst_basin_mean.sel(sub_basin_id=basin_id)

# Unstack to original lat/lon
#sst_basin_grid = sst_basin_grid_stack.unstack("stacked_lat_lon")

# --- Mask out points outside sub-basins (sub_basin_id == -1) ---
#sst_basin_grid = sst_basin_grid.where(sst_ds["sub_basin_id"] != -1)

# save to netcdf
#sst_basin_grid.to_netcdf("SST_mon_mean_anom_subbasin.nc")
