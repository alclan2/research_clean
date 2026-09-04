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
from shapely.geometry import box

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
basins["geometry"] = basins["geometry"].apply(shift_lon)

#######################################################################################

# combine u-wind files (from NOAA https://downloads.psl.noaa.gov/Datasets/ncep.reanalysis2/Dailies/pressure/)

# remove time bounds variable since we don't need it/mismatched data types across raw files
def clean(ds):
    if "time_bnds" in ds:
        ds = ds.drop_vars("time_bnds")
    
    return ds

ds = xr.open_mfdataset(
    "datasets/u-wind/*.nc",
    combine="by_coords",
    preprocess=clean,
    chunks={"time": 365}
)

# select the 850hPa pressure level
uwnd = ds["uwnd"].sel(level=850)

# convert lon to -180-180
uwnd = uwnd.assign_coords(
    lon=(((uwnd.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
uwnd = uwnd.rio.write_crs("EPSG:4326")
uwnd = uwnd.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atl
region = basins[basins["basin name"] == "N Atlantic"]
uwnd = uwnd.rio.clip(region.geometry, region.crs, drop=True)

# filter to hurricane season
uwnd = (
    uwnd
    .where(uwnd.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
)

# print(uwnd)

# # convert to data frame
df = uwnd.to_dataframe(name="uwnd").reset_index()

# version for absolute value (magnitude)
# df = np.abs(uwnd).to_dataframe(name="uwnd").reset_index()

# create points
df_pts = gpd.GeoDataFrame(
    df,
    geometry=gpd.points_from_xy(
        df['lon'],
        df['lat']
    ),
    crs="EPSG:4326"
)

# join sub basins
df_sb = gpd.sjoin(
    df_pts,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="covered_by"
)

# create 5deg bins
df_sb["lat_bin"] = np.floor(df_sb["lat"] / 5) * 5
df_sb["lon_bin"] = np.floor(df_sb["lon"] / 5) * 5

# trim columns
# df_sb = df_sb[['time', 'lat', 'lon', 'uwnd', 'sub_basin_name', 'lat_bin', 'lon_bin']]

# calc mean u wind per 5deg bin
df_means = (
    df_sb
    .groupby(["lat_bin", "lon_bin"], observed=True)["uwnd"]
    .mean()
    .reset_index()
)

#################################################################################################

# # spatial map of means
# fig = plt.figure(figsize=(10, 6))
# ax = plt.axes(projection=ccrs.PlateCarree())

# # plot sub-basins first
# sub_basins.plot(
#     ax=ax,
#     facecolor='none',
#     edgecolor='black',
#     path_effects=[pe.withStroke(linewidth=3, foreground='white')],
#     linewidth=1.5,
#     transform=ccrs.PlateCarree(),
#     zorder=4
# )

# # set axis bounds
# lon_min = -110
# lon_max = 20
# lat_min = 0
# lat_max = 50

# # add sub-basin labels
# for idx, row in sub_basins.iterrows():
#     point = row.geometry.centroid
#     name = row["sub_basin_name"]

#     # wrap text (adjust width as needed)
#     name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
    
#     if (lon_min <= point.x <= lon_max) and (lat_min <= point.y <= lat_max):
#         txt = ax.text(
#             point.x, point.y,
#             name_wrapped,
#             transform=ccrs.PlateCarree(),
#             fontsize=7,
#             weight='bold',
#             ha='center',
#             va='center',
#             color='black',
#             zorder=4
#         )
        
#         txt.set_path_effects([
#             pe.withStroke(linewidth=3, foreground="white")
#         ])

# # convert 5-degree bins back into a gridded xarray DataArray
# wind_grid_df = df_means.pivot(
#     index="lat_bin",
#     columns="lon_bin",
#     values="uwnd"
# )

# wind_grid = xr.DataArray(
#     wind_grid_df.to_numpy(),
#     coords={
#         "lat": wind_grid_df.index.to_numpy() + 2.5,
#         "lon": wind_grid_df.columns.to_numpy() + 2.5
#     },
#     dims=["lat", "lon"],
#     name="uwnd"
# )

# wind_grid.plot(
#     ax=ax,
#     transform=ccrs.PlateCarree(),
#     cmap="plasma_r",
#     cbar_kwargs={"label": "Mean Zonal Wind (m/s)"}
# )

# # coastlines
# ax.coastlines(resolution="10m", linewidth=0.8)

# # North Atlantic extent
# ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

# # Set tick marks every 10 degrees
# ax.set_xticks(np.arange(lon_min, lon_max, 10), crs=ccrs.PlateCarree())
# ax.set_yticks(np.arange(lat_min, lat_max, 10), crs=ccrs.PlateCarree())

# # add labels
# ax.set_xlabel("Longitude")
# ax.set_ylabel("Latitude")

# ax.set_title("Mean 850-hPa Zonal Wind (Jun-Oct, 1979-2025)")

# plt.savefig("images/data_viz/zonal_wind/mean_uwnd_spatial_map_absValue.png")
# plt.show()

#################################################################################################

# add year columns for timeseries
df_sb['year'] = df_sb['time'].dt.year

# calc mean u wind per 5deg bin per year and keep sub basin name
df_means = (
    df_sb
    .groupby(["year", "sub_basin_name"], observed=True)["uwnd"]
    .mean()
    .reset_index()
)

# print(df_means)

print(df_means["uwnd"].agg(["min", "max", "mean", "std"]))

# save 
df_means.to_csv("datasets/u-wind/post_processing/uwnd_mean_rawValues_perYr_perSb.csv")
