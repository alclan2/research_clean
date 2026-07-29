import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import xarray as xr
import math
from geopy.distance import geodesic
import seaborn as sns
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import matplotlib.patheffects as pe
import textwrap

# read in tc_subbasins_NAtl file
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

#################################################################################################

# load in origin node dataset
origins = pd.read_csv("datasets/SyCLoPS/tc_track_subbasin_table.csv")

# create 5deg grid cell centers based on origin node
origins["lon_bin"] = 5 * np.round(origins["LON_start"] / 5)
origins["lat_bin"] = 5 * np.round(origins["LAT_start"] / 5)

# get origin grid cells from the track dataset
origin_cells = (
    origins[["lon_bin", "lat_bin", "sub_basin_start"]]
    .drop_duplicates()
    .rename(columns={"sub_basin_start": "sub_basin_name"})
)

# load in variable dataset
ds = pd.read_csv("datasets/data_viz/spatial_map/sst_mean_spatial_map.csv")

# drop NaNs
ds = ds.dropna(subset=['mean'])

# create 5deg lat x lon bins
ds["lon_bin"] = 5 * np.round(ds["lon"] / 5)
ds["lat_bin"] = 5 * np.round(ds["lat"] / 5)

# calc mean vm per bin
mean_sst = (
    ds.groupby(['sub_basin_name', 'lon_bin', 'lat_bin'])['mean']
    .mean()
    .reset_index(name='mean_sst')
)

#calc sub-basin wide mean
sub_basin_mean_sst = (
    ds.groupby('sub_basin_name')['mean']
    .mean()
    .reset_index(name='sub_basin_mean_sst')
)

# merge
mean_sst = mean_sst.merge(
    sub_basin_mean_sst,
    on='sub_basin_name'
)

# calc anomaly between grid cell means and basin mean
mean_sst['sst_difference'] = (
    mean_sst['mean_sst'] - mean_sst['sub_basin_mean_sst']
)

# match variable to origin grid cells bins
# Keep only cells with an origin node
sst_origin = mean_sst.merge(
    origin_cells,
    on=["lon_bin", "lat_bin", "sub_basin_name"],
    how="inner"
)

# print(sst_origin)

#################################################################################################

# plot difference

# for grid cells that overlap a subbasin, value is averaged across different versions that exist within two subbasins
# edge cases might be weird
pivot = sst_origin.pivot_table(
    index='lat_bin',
    columns='lon_bin',
    values='sst_difference',
    aggfunc='mean'
)

lons = pivot.columns.values
lats = pivot.index.values
values = pivot.values
lon_edges = np.append(lons, lons[-1] + 5)
lat_edges = np.append(lats, lats[-1] + 5)

# set up figure
fig, ax = plt.subplots(
    figsize=(10,6),
    subplot_kw={'projection': ccrs.PlateCarree()}
)

# add coastlines
ax.coastlines(resolution='50m', linewidth=1)

# plot sub-basins first
sub_basins.plot(
    ax=ax,
    facecolor='none',
    edgecolor='black',
    path_effects=[pe.withStroke(linewidth=3, foreground='white')],
    linewidth=1.5,
    transform=ccrs.PlateCarree(),
    zorder=4
)

# automatically determine color limits
abs_max = np.nanmax(np.abs(values))
vmin = -abs_max
vmax = abs_max

# plot anomaly per bin
mesh = ax.pcolormesh(
    lon_edges,
    lat_edges,
    values,
    cmap='RdBu_r',
    shading='flat',
    transform=ccrs.PlateCarree(),
    vmin=-abs_max,
    vmax=abs_max,
    edgecolors='face',
    linewidth=0
)

# set axis bounds
lon_min = -110
lon_max = 20
lat_min = 0
lat_max = 52

# add sub-basin labels
for idx, row in sub_basins.iterrows():
    point = row.geometry.centroid
    name = row["sub_basin_name"]

    # wrap text (adjust width as needed)
    name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
    
    if (lon_min <= point.x <= lon_max) and (lat_min <= point.y <= lat_max):
        txt = ax.text(
            point.x, point.y,
            name_wrapped,
            transform=ccrs.PlateCarree(),
            fontsize=7,
            weight='bold',
            ha='center',
            va='center',
            color='black',
            zorder=4
        )
        
        txt.set_path_effects([
            pe.withStroke(linewidth=3, foreground="white")
        ])

# Set tick marks every 10 degrees
ax.set_xticks(np.arange(lon_min, lon_max, 10), crs=ccrs.PlateCarree())
ax.set_yticks(np.arange(lat_min, lat_max, 10), crs=ccrs.PlateCarree())

# add labels
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")

ax.set_extent([lon_min, lon_max, lat_min, lat_max],crs=ccrs.PlateCarree())

# colorbar
cbar = plt.colorbar(mesh, ax=ax, label='Mean SST Anom (°C)')
cbar.set_label('Mean SST Anom (°C)')

plt.title('TC Origin SST Anomaly Relative to Sub-Basin Mean')

# plt.savefig("images/data_viz/spatial_anom/sst_mean_vs_subbasin_mean_at_origin.png")
plt.show()