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

# # read in NAtl subbasin polygons
# sub_polygons_dict = {}

# with open("tc_subbasins_NAtl_v5.dat", "r") as f:
#     for line in f:
#         line = line.strip()
#         if not line or line.startswith("#"):
#             continue

#         parts = line.split(",")
#         sub_basin_name = parts[0].replace('"', '')
#         n_vertices = int(parts[1])

#         lon_vals = list(map(float, parts[2:2+n_vertices]))
#         lon_vals = [(lon + 180) % 360 - 180 for lon in lon_vals]
#         lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

#         coords = list(zip(lon_vals, lat_vals))
#         poly = Polygon(coords)

#         if sub_basin_name not in sub_polygons_dict:
#             sub_polygons_dict[sub_basin_name] = []
#         sub_polygons_dict[sub_basin_name].append(poly)

# # Convert to GeoDataFrame
# sub_basin_records = []

# for name, poly_list in sub_polygons_dict.items():
#     if len(poly_list) == 1:
#         geom = poly_list[0]
#     else:
#         geom = MultiPolygon(poly_list)

#     sub_basin_records.append({
#         "sub_basin_name": name,
#         "geometry": geom
#     })

# sub_basins = gpd.GeoDataFrame(sub_basin_records, crs="EPSG:4326",geometry="geometry")

# # fix invalid polygons
# sub_basins["geometry"] = sub_basins["geometry"].buffer(0)

# # remove empty geometries
# sub_basins = sub_basins[~sub_basins.geometry.is_empty]

# # longitude conversion
# import shapely.ops
# def shift_lon(geom):
#     return shapely.ops.transform(
#         lambda x, y: (((x + 180) % 360) - 180, y),
#         geom
#     )

# # shift lon
# sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)

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

# check that the grids between landmask and ds match
assert ds.lat.equals(land_ds.lat), "Latitude grids do not match!"
assert ds.lon.equals(land_ds.lon), "Longitude grids do not match!"

# Get the land mask
land_mask = land_ds["land"].isel(time=0) > 0.5

# Convert land mask to ocean mask
ocean_mask = ~land_mask

# Mask RHUM: keep ocean, set land to NaN
ds_ocean = ds["rhum"].where(ocean_mask)

ds_ocean = ds["rhum"].where(ocean_mask)

ds_ocean = ds_ocean.chunk({
    "time": 100,
    "level": 1,
    "lat": 73,
    "lon": 144
})

ds_ocean.to_netcdf(
    "datasets/RHUM/post-processing/post_landmask/RHUM_1979-2025_landmasked.nc"
)

print(ds_ocean)

# save file
ds_ocean.to_netcdf("datasets/RHUM/post-processing/post_landmask/RHUM_1979-2025_landmasked.nc")



# # check plot
# ds_ocean.isel(
#     time=0,
#     level=0
# ).plot(
#     figsize=(12, 6)
# )

# plt.show()

