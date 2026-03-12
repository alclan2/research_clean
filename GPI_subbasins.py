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

# open GPI dataset
gpi = xr.open_dataset(r"datasets\GPI\GPI_ERA5_1950_2025_combined.nc", chunks={"year":1})

# convert lon to -180-180
gpi = gpi.assign_coords(
    lon=(((gpi.lon + 180) % 360) - 180)
).sortby("lon")

# stack year and month
gpi = gpi.stack(time=("year","month"))

# build datetime index
time_index = pd.to_datetime(
    [f"{y}-{m:02d}-01" for y, m in gpi.indexes["time"]]
)
gpi = gpi.drop_vars(["year","month"])

# assign new time coordinate
gpi = gpi.assign_coords(time=time_index)

# reorder to (time, lat, lon)
gpi = gpi.transpose("time", "lat", "lon")

# add CRS and spatial dims
gpi = gpi.rio.write_crs("EPSG:4326")
gpi = gpi.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atlantic basin
region = basins[basins["basin name"] == "N Atlantic"]

# filter out Arctic and continental US sub-basins
region_subbasins = sub_basins[
    sub_basins["sub_basin_name"].isin([
        "Gulf","Caribbean","Northeastern Seaboard",
        "Tropical Atlantic","Subtropical Atlantic",
        "Mid-latitudinal Atlantic","Southeastern Seaboard"
    ])
]

# keep full dataset for anom calc
gpi_full = (
    gpi
    .rio.clip(region.geometry, region.crs, drop=True)
    .rio.clip(region_subbasins.geometry, region_subbasins.crs, drop=True)
)

# change to 1deg grid spacing
gpi_coarse = gpi_full.coarsen(lat=4, lon=4, boundary="trim").mean()

# remove edges for rolling climatology
start = str(int(gpi_coarse.time.dt.year.min()) + 10)
end   = str(int(gpi_coarse.time.dt.year.max()) - 10)

gpi_filt = gpi_coarse.sel(time=slice(start, end))

# anomaly calc: use moving mean for year n (year-10, year+10)
rolling_clim = gpi_coarse.groupby("time.month").map(
    lambda x: x.rolling(time=21, center=True).mean()
)

gpi_anom = gpi_filt - rolling_clim.sel(time=gpi_filt.time)

# save filtered datasets
gpi_anom.to_netcdf("GPI_mon_mean_anom_moving_window_1deg.nc")

########################################################################################
# now region mask for subbasin categorization for region generation

# --- Load dataset ---
gpi_ds = xr.open_dataset("GPI_mon_mean_anom_moving_window_1deg.nc", decode_times=True,
    chunks={"time": 12})
gpi_var = "Ig"

# --- Create sub-basin mask (lat, lon) ---
regions = regionmask.from_geopandas(sub_basins, names="sub_basin_name")
mask = regions.mask(gpi_ds)  # lat, lon with basin IDs and NaN outside

# --- Fill NaNs if needed ---
mask_filled = mask.fillna(-1)

# --- Add mask to dataset ---
gpi_ds["sub_basin_id"] = mask_filled
gpi_ds["sub_basin_id"].attrs["sub_basin_names"] = list(sub_basins["sub_basin_name"])

# Stack spatial dims
gpi_stack = gpi_ds[gpi_var].stack(stacked_lat_lon=("lat", "lon"))
mask_stack = gpi_ds["sub_basin_id"].stack(stacked_lat_lon=("lat", "lon"))

# Compute mean per sub-basin (excluding -1)
gpi_basin_mean = gpi_stack.where(mask_stack != -1).groupby(mask_stack).mean(dim="stacked_lat_lon", skipna=True)

# Broadcast back to grid
gpi_basin_grid_stack = gpi_stack.copy()
for basin_id in np.unique(mask_stack.values[~np.isnan(mask_stack.values)]):
    locs = mask_stack == basin_id
    gpi_basin_grid_stack.loc[dict(stacked_lat_lon=locs)] = gpi_basin_mean.sel(sub_basin_id=basin_id)

# Unstack to original lat/lon
gpi_basin_grid = gpi_basin_grid_stack.unstack("stacked_lat_lon")

# Mask out points outside sub-basins
gpi_basin_grid = gpi_basin_grid.where(gpi_ds["sub_basin_id"] != -1)

# Prevent all-NaN slices for clustering
gpi_basin_grid = gpi_basin_grid.fillna(-1e20)

gpi_basin_grid = gpi_basin_grid.to_dataset(name=gpi_var)

# save to netcdf
gpi_basin_grid.to_netcdf("gpi_mon_mean_moving_anom_subbasin.nc")