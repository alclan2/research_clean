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

# # read in basin definition file
# polygons_dict = {}

# # read in basin definition file
# with open("tc_basins_NAtl.dat", "r") as f:
#     for line in f:
#         line = line.strip()
#         if not line or line.startswith("#"):
#             continue

#         parts = line.split(",")
#         basin_name = parts[0].replace('"', '')
#         n_vertices = int(parts[1])

#         lon_vals = list(map(float, parts[2:2+n_vertices]))
#         lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

#         coords = list(zip(lon_vals, lat_vals))
#         poly = Polygon(coords)

#         if basin_name not in polygons_dict:
#             polygons_dict[basin_name] = []
#         polygons_dict[basin_name].append(poly)

# # Convert to GeoDataFrame
# basin_records = []

# for name, poly_list in polygons_dict.items():
#     if len(poly_list) == 1:
#         geom = poly_list[0]
#     else:
#         geom = MultiPolygon(poly_list)

#     basin_records.append({
#         "basin name": name,
#         "geometry": geom
#     })

# basins = gpd.GeoDataFrame(basin_records, crs="EPSG:4326")

# # fix invalid polygons
# basins["geometry"] = basins["geometry"].buffer(0)

# # remove empy geometries
# basins = basins[~basins.geometry.is_empty]

# # convert basins' lon to -180-180
# basins["geometry"] = basins["geometry"].apply(
#     lambda geom: transform(
#         lambda x, y: (((x + 180) % 360) - 180, y),
#         geom
#     )
# )

# # read in NAtl subbasin polygons
# sub_polygons_dict = {}

# with open("tc_subbasins_NAtl_v4.dat", "r") as f:
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

# ##########################################################################################################

# # open daily mean files
# ds = xr.open_dataset("datasets/u-wind/post_processing/post_landmask/shear_850_200_daily_v2_landmasked.nc")

# print(ds)

# # filter to variable
# shear = ds["__xarray_dataarray_variable__"]

# # # convert lon to -180-180
# # rhum = rhum.assign_coords(
# #     lon=(((rhum.lon + 180) % 360) - 180)
# # ).sortby("lon")

# # create mask for each sub-basin
# mask = regionmask.Regions(
#     sub_basins.geometry.tolist(),
#     names=sub_basins["sub_basin_name"].tolist()
# )

# results = []

# for i, subbasin in enumerate(sub_basins["sub_basin_name"]):

#     # keep only SST pixels inside this sub-basin
#     sb_shear = shear.where(
#         mask.mask(shear) == i
#     )

#     # calculate daily spatial mean
#     daily_mean = sb_shear.mean(
#         dim=["lat", "lon"],
#         skipna=True
#     )

#     # convert to dataframe
#     temp = daily_mean.to_dataframe(
#         name="mean"
#     ).reset_index()

#     temp["sub_basin_name"] = subbasin

#     results.append(temp)

# daily_table = pd.concat(
#     results,
#     ignore_index=True
# )

# print(daily_table.head())
# print(daily_table.shape)

# # save to csv
# daily_table.to_csv("datasets/u-wind/post_processing/post_landmask/shear_daily_mean_bySubbasin_table.csv", index=False)

###############################################################################################################

# load dataset
sst = pd.read_csv("datasets/COBE2 SST/post-processing/sst_daily_mean_bySubbasin_table_v2.csv")

# filter to Gulf regions
sst = sst[(sst['sub_basin_name']== 'Gulf (A)') | (sst['sub_basin_name']== 'Gulf (B)')]

# make sure time is date time format
sst["time"] = pd.to_datetime(sst["time"])

# convert column formatting
sst_piv = sst.pivot(
    index="time",
    columns="sub_basin_name",
    values="mean"
).reset_index()

# ratio of A to B daily mean
sst_piv['ratio (A2B)'] = sst_piv['Gulf (A)'] / sst_piv['Gulf (B)']

# add year column
sst_piv['year'] = sst_piv['time'].dt.year

# pivot to annual
annual = (
    sst_piv.groupby("year")["ratio (A2B)"]
    .mean()
    .reset_index()
)

# print(annual)

# line plot
annual.plot(
    x="year",
    y='ratio (A2B)',
    figsize=(12, 5)
)

plt.axhline(y=1, color="black", linestyle="--", linewidth=1)

plt.ylabel("Mean")
plt.xlabel("Date")
plt.title("Ratio of SST Annual Mean (Gulf (A) vs. Gulf (B))")

plt.savefig("images/data_viz/SST/avg_notAnom/sst_annual_mean_gulf_ratio.png")
plt.show()
