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

#################################################################################################################

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

# # filter to relative humidity at the 400 level only
# rhum400 = rhum.sel(level=400)

# # roll up to monthly means
# rhum400_monthly = rhum400.resample(time="MS").mean()

# # add CRS and spatial dims
# rhum400_monthly = rhum400_monthly.rio.write_crs("EPSG:4326")
# rhum400_monthly = rhum400_monthly.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# # filter to N Atlantic basin
# region = basins[basins["basin name"] == "N Atlantic"]

# # filter to hurricane season
# rhum400_full = (
#     rhum400_monthly
#     .where(rhum400_monthly.time.dt.month.isin([6, 7, 8, 9, 10]), drop=True)
#     .rio.clip(region.geometry, region.crs, drop=True)
# )

# save monthly RH means to dataset (NOT ANOM)
#rhum400_full.to_netcdf("datasets/RHUM/post-processing/RHUM400_mon_mean_1979-2025.nc")

# ######################################################################################

# # calculate moving window anomaly
# # for moving mean, remove last 10 years (2015-2024) of data since we don't have enough future data to cover the long term mean calc
# start = str(int(rhum400_full.time.dt.year.min()) + 10)
# end   = str(int(rhum400_full.time.dt.year.max()) - 10)

# #rhum400_filt = rhum400_full.sel(time=slice(start, end)).load()
# rhum400_filt = rhum400_full.load()

# # anomaly calc: use moving mean for year n (year-10, year+10)
# rolling_clim = rhum400_filt.groupby("time.month").map(
#     lambda x: x.rolling(time=21, center=True).mean()
# )
# rhum400_anom = rhum400_filt - rolling_clim

#rhum400_anom = rhum400_anom.dropna(dim="time")

#######################################################################################

# # save filtered datasets
# rhum400_anom.to_netcdf("datasets/RHUM/post-processing/RHUM400_anom_moving_window_1989-2015.nc")

#######################################################################################

# # check plots
# annual_mean = (
#     rhum400_anom
#     .mean(dim=("lat", "lon"))
#     .groupby("time.year")
#     .mean()
# )

# plt.figure(figsize=(10, 4))

# annual_mean.plot(marker="o")

# plt.axhline(0, color="k", ls="--")
# plt.ylabel("RH Anomaly (percentage points)")
# plt.xlabel("Year")
# plt.title("Global Mean 400 hPa Relative Humidity Anomaly - North Atlantic")
# plt.savefig("images/data_viz/RHUM400/rhum400_anom_moving_window_annual_mean.png")
# plt.show()

#print(ds.rhum.attrs)

#######################################################################################

# # plot anomaly with sub basin overlay

# # read in MSLP anom dataset
# ds = xr.open_dataset(r"datasets/RHUM/post-processing/RHUM400_mon_mean_1979-2025.nc")

# var = ds['rhum']

# # collapse over time dimension
# # rhum400_anom = ds["rhum"].mean(dim="time")
# rh = var.mean(dim="time")

# # plot MSLP for hurricane season
# fig = plt.figure(figsize=(8,6))
# ax = plt.axes(projection=ccrs.PlateCarree()) 

# # Plot sub-basins first
# sub_basins.plot(
#      ax=ax,
#      facecolor='none',
#      edgecolor='black',
#      path_effects=[pe.withStroke(linewidth=3, foreground='white')],
#      linewidth=1,
#      transform=ccrs.PlateCarree(),
#      zorder=4
# )

# # plot rh
# #v = np.nanmax(np.abs(rh))

# rh.plot(
#     ax=ax,
#     transform=ccrs.PlateCarree(),
#     cmap="YlGnBu",
#     vmin=0,
#     vmax=75,
#     cbar_kwargs={
#         "label": "RH (%)",
#         "pad": 0.08
#     }
# )

# # add coastline outlines
# ax.coastlines()

# # set extent
# lon_min = -108
# lon_max = 23
# lat_min = -3
# lat_max = 93
# ax.set_extent([lon_min, lon_max, lat_min, lat_max],crs=ccrs.PlateCarree())

# # add axis labels
# ax.set_xlabel("Longitude", labelpad=15)
# ax.set_ylabel("Latitude", labelpad=15)

# # Add gridlines with labels
# gl = ax.gridlines(
#     draw_labels=True,
#     linewidth=0.1,
#     color='gray',
#     linestyle='--'
# )

# gl.xlocator = plt.MultipleLocator(10)  # longitude every 10°
# gl.ylocator = plt.MultipleLocator(10)  # latitude every 10°
# gl.xlabel_style = {'size': 10, 'color': 'black'}
# gl.ylabel_style = {'size': 10, 'color': 'black'}

# # set title
# ax.set_title("Mean 400hPa Relative Humidity (Jun-Oct, 1979-2025)")

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

# plt.savefig("images/data_viz/RHUM400/rhum400_mon_mean_NAtl.png")
# plt.show()

#######################################################################################

# timeseries of RH anom per sub basin

# read in MSLP anom dataset
ds = xr.open_dataset(r"datasets/RHUM/post-processing/RHUM400_mon_mean_1979-2025.nc")

rh = ds['rhum']

# convert to dataframe
df = rh.to_dataframe().reset_index()

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
df_points = gpd.GeoDataFrame(
    df, 
    geometry = gpd.points_from_xy(df.lon, df.lat),
    crs = "EPSG:4326"
)

# convert lon to -180-180 from 0-360
df_points['lon'] = ((df_points['lon'] + 180) % 360) - 180

# filter points to North Atlantic
df_filtered = gpd.sjoin(
    df_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# add Year column so we can create a timeseries
df_filtered['year'] = df_filtered['time'].dt.year

# join sub basin name for starting and ending points
df_gdf = gpd.GeoDataFrame(
    df_filtered,
    geometry=gpd.points_from_xy(
        df_filtered.lon,
        df_filtered.lat
    ),
    crs=sub_basins.crs
)

# drop index_right column before joining again
df_gdf = df_gdf.drop(columns="index_right", errors="ignore")

df_join = gpd.sjoin(
    df_gdf,
    sub_basins[['sub_basin_name', 'geometry']],
    how='left',
    predicate='within'
)

#print(df_join)

# calc annual mean of rh anomaly per sub basin
yearly_rh = (
    df_join
    .dropna(subset=["sub_basin_name"])
    .pivot_table(
        index="year",
        columns="sub_basin_name",
        values="rhum",
        aggfunc="mean"
    )
)

#print(yearly_rh)

# scatter plot per sub basin
# filter to sub basin
sb = 'Arctic'

plt.figure(figsize=(10, 5))

x = yearly_rh.index
y = yearly_rh[sb]

plt.plot(
    x,
    y,
    marker="o",      
    linestyle="-",   
    color="blue"
)

# plt.axhline(
#     y=0,
#     color="gray",
#     linestyle="--",
#     linewidth=1
# )

plt.title(f'Mean Relative Humidity in North Atlantic - {sb}')
plt.xlabel('Year')
plt.ylabel('RH (%)')

plt.savefig(f'images/data_viz/RHUM400/rhum400_mon_mean_timeseries_{sb}.png')
plt.show()