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

# combine mslp files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/surface/)
ds = xr.open_mfdataset(
    "datasets/MSLP/1979-2024/*.nc",
    combine = "by_coords"
)

# select the MSLP variable
mslp = ds["mslp"]

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
mslp_full = (
    mslp
    .where(mslp.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
    .rio.clip(region.geometry, region.crs, drop=True)
)

# aggregate daily means to monthly means
mslp_monthly = mslp_full.resample(time="MS").mean("time")

# # calculate moving window anomaly
# # for moving mean, remove last 10 years (2015-2024) of data since we don't have enough future data to cover the long term mean calc
# start = str(int(mslp_monthly.time.dt.year.min()) + 10)
# end   = str(int(mslp_monthly.time.dt.year.max()) - 10)
# mslp_filt = mslp_monthly.sel(time=slice(start, end))
# mslp_filt = mslp_filt.load()

mslp_monthly = mslp_monthly.load()

# anomaly calc: use moving mean for year n (year-10, year+10)
rolling_clim = mslp_monthly.groupby("time.month").map(
    lambda x: x.rolling(time=21, center=True).mean()
)
mslp_anom = mslp_monthly - rolling_clim

mslp_anom = mslp_anom.sel(time=slice("1989-01-01", "2014-12-31"))

#print(mslp_anom)

#######################################################################################

# save filtered datasets
mslp_anom.to_netcdf("datasets/MSLP/post-processing/MSLP_anom_moving_window_1979-2024_v2_rolledUpMonthly.nc")

#print(mslp_anom)

########################################################################################

# join sub basins
# convert DataArray to a DataFrame
df = mslp_anom.to_dataframe(name="mslp_anom").reset_index()

#print(df)

# Create point geometries
points = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(df.lon, df.lat),
    crs="EPSG:4326"
)

# spatial join
points = gpd.sjoin(
    points,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="within"
)

# add year column
points["year"] = points["time"].dt.year

# calculate yearly mean anomaly per sub-basin
mslp_anom_yearly = (
    points
    .groupby(["year", "sub_basin_name"])["mslp_anom"]
    .mean()
    .reset_index()
)

#print(mslp_anom_yearly)

########################################################################################

# plot mean WS as a time series per sub basin

# select sub basin
sb = 'Mediterranean Sea'

df_plot = mslp_anom_yearly[mslp_anom_yearly["sub_basin_name"] == sb]

plt.figure(figsize=(10, 5))
plt.plot(df_plot["year"], df_plot["mslp_anom"], marker="o", color = "green")

plt.axhline(0, color="black", linewidth=1)
plt.title(f"Mean Sea Level Pressure Anomaly in North Atlantic - {sb}")
plt.xlabel("Year")
plt.ylabel("MSLP Anomaly (Pa)")

plt.tight_layout()
plt.savefig(f"images/data_viz/MSLP/NOAA/MSLP_moving_window_anom_timeseries_{sb}.png")
plt.show()