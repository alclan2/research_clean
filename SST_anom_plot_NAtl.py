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





# read in SST anom dataset
ds = xr.open_dataset(r"datasets/COBE2 SST/post-processing/SST_mon_mean_anom_moving_window_jun_oct.nc")

print(ds)

# plot the sst's for hurricane season
fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree()) 

# Plot sub-basins first
sub_basins.plot(
    ax=ax,
    facecolor='none',
    edgecolor='red',
    path_effects=[pe.withStroke(linewidth=3, foreground='white')],
    linewidth=1,
    transform=ccrs.PlateCarree(),
    zorder=4
)

#sst_mean_szn.plot(
#    ax=ax,
#    transform=ccrs.PlateCarree(),
#    cmap="coolwarm",
#    cbar_kwargs={"label": "SST (°C)"}
#)

#ax.coastlines()
#ax.set_extent([-70, -20, 15, 50],crs=ccrs.PlateCarree())

#ax.set_xlabel('Longitude')
#ax.set_ylabel('Latitude')

# Add gridlines with labels
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