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

# read in MSLP anom dataset
ds = xr.open_dataset(r"datasets/MSLP/post-processing/MSLP_anom_moving_window_1979-2024.nc")
print(ds["mslp"].attrs)
mslp_anomaly = ds["mslp"].mean(dim="time")

# plot MSLP for hurricane season
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

# plot mslp
v = np.nanmax(np.abs(mslp_anomaly))

mslp_anomaly.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),
    cmap="RdBu_r",
    vmin=-v,
    vmax=v,
    cbar_kwargs={
        "label": "MSLP Anomaly (Pa)",
        "pad": 0.08
    }
)

# add coastline outlines
ax.coastlines()

# set extent
lon_min = -108
lon_max = 23
lat_min = -3
lat_max = 93
ax.set_extent([lon_min, lon_max, lat_min, lat_max],crs=ccrs.PlateCarree())

# add axis labels
ax.set_xlabel("Longitude", labelpad=15)
ax.set_ylabel("Latitude", labelpad=15)

# Add gridlines with labels
gl = ax.gridlines(
    draw_labels=True,
    linewidth=0.1,
    color='gray',
    linestyle='--'
)

gl.xlocator = plt.MultipleLocator(10)  # longitude every 10°
gl.ylocator = plt.MultipleLocator(10)  # latitude every 10°
gl.xlabel_style = {'size': 10, 'color': 'black'}
gl.ylabel_style = {'size': 10, 'color': 'black'}

# set title
ax.set_title("Mean Sea Level Pressure Anomaly (Jun-Oct, 1979-2024)")

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

#plt.savefig("images/data_viz/tc_mslp_anom_moving_window_NAtl.png")
plt.show()