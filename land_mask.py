import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature
import matplotlib.patheffects as pe
import textwrap
import matplotlib.colors as colors
import seaborn as sns
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
import numpy as np
import math
import xarray as xr

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

# load variable dataset
ds = xr.open_mfdataset(
    "datasets/RHUM/*.nc",
    combine = "by_coords",
    preprocess=lambda ds: ds.drop_vars("time_bnds", errors="ignore"),
)

# load land mask
land_ds = xr.open_dataset(
    "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis2/surface/land.nc"
)

# get the land variable from the dataset
land_mask = land_ds["land"].isel(time=0)

# make sure coordinates match the variable dataset ds
land_mask = land_mask.assign_coords(
    lat=ds.lat,
    lon=ds.lon
)

# make variables into True/False
land_mask = land_mask > 0.5

# get ocean mask (opposite of land mask)
ocean_mask = ~land_mask

# create a 2D map of lat/lon points from variable dataset ds
lon2d, lat2d = np.meshgrid(
    ds.lon.values,
    ds.lat.values
)

# convert longitude
lon2d_geo = (lon2d + 180) % 360 - 180

# convert grid to points
points = [
    Point(lon, lat)
    for lon, lat in zip(
        lon2d_geo.ravel(),
        lat2d.ravel()
    )
]

# convert points to a geo data frame
grid_points = gpd.GeoDataFrame(
    geometry=points,
    crs="EPSG:4326"
)

# assign each point to a sub basin
grid_points = gpd.sjoin(
    grid_points,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="within"
)

# convert landmask to True/False
subbasin_mask = grid_points["sub_basin_name"].notna().values

# put back into a grid
subbasin_mask = subbasin_mask.reshape(
    len(ds.lat),
    len(ds.lon)
)

# convert to an xarray
subbasin_mask = xr.DataArray(
    subbasin_mask,
    coords={
        "lat": ds.lat,
        "lon": ds.lon
    },
    dims=["lat", "lon"],
    name="subbasin_mask"
)






# check plot
fig, ax = plt.subplots(figsize=(12, 8))

# Plot your original sub-basin polygons
sub_basins.plot(
    ax=ax,
    facecolor="none",
    edgecolor="red",
    linewidth=1.5
)

# Plot grid points that are inside the sub-basins
inside = grid_points[grid_points["sub_basin_name"].notna()]

inside.plot(
    ax=ax,
    color="blue",
    markersize=10
)

ax.set_xlim(-100, 20)
ax.set_ylim(0, 70)

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("Sub-basin polygons and selected NCEP grid points")

plt.show()
