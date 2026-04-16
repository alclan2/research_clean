import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature
import textwrap
import matplotlib.patheffects as pe

# plot tc_basins over world map
polygons_dict = {}

with open("tc_basins.dat", "r") as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split(",")
        basin_name = parts[0].replace('"', '')
        n_vertices = int(parts[1])

        lon_vals = list(map(float, parts[2:2+n_vertices]))
        lon_vals = [(lon + 180) % 360 - 180 for lon in lon_vals]
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

# convert lon to -180-180
#import shapely.ops
#def shift_lon(geom):
#    return shapely.ops.transform(
#        lambda x, y: (((x + 180) % 360) - 180, y),
#        geom
#    )
#basins["geometry"] = basins["geometry"].apply(shift_lon)

# filter to NE Atlantic basin only
basin_name = "N Atlantic"
basins_NAtl = basins[basins["basin name"] == basin_name]

# read in NAtl subbasin polygons
sub_polygons_dict = {}

with open("tc_subbasins_NAtl_v2.dat", "r") as f:
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

# shift lon
#sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)


# choose projection
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

# add coastlines
ax.add_feature(cfeature.COASTLINE, linewidth=1)

# plot only selected basin
basins_NAtl.plot(ax=ax, edgecolor="black", facecolor="lightblue", alpha=0.5, transform=ccrs.PlateCarree())

# overlay subbasins
sub_basins.plot(ax=ax, edgecolor="darkblue", facecolor="none", linewidth=1.5, transform=ccrs.PlateCarree())

# Zoom to basin
minx, miny, maxx, maxy = basins_NAtl.total_bounds
pad = 2
ax.set_extent([minx-pad, maxx+pad, miny-pad, maxy+pad], crs=ccrs.PlateCarree())

# Add gridlines with labels
gl = ax.gridlines(
    draw_labels=True,
    linewidth=0.1,
    color='gray',
    linestyle='--'
)

# add basin labels
for idx, row in sub_basins.iterrows():
    geom = row.geometry
    name = row["sub_basin_name"]
    
    # wrap text (adjust width as needed)
    name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False))
    
    centroid = geom.centroid
    ax.text(
    centroid.x,
    centroid.y,
    name_wrapped,
    fontsize=8,
    color="darkblue",
    ha="center",
    va="center",
    transform=ccrs.PlateCarree(),
    path_effects=[
        pe.withStroke(linewidth=2, foreground="white")
    ]
)


gl.xlocator = plt.MultipleLocator(10)  # longitude every 10°
gl.ylocator = plt.MultipleLocator(10)  # latitude every 10°
gl.xlabel_style = {'size': 10, 'color': 'black'}
gl.ylabel_style = {'size': 10, 'color': 'black'}

plt.title(f"TC Sub-Basins: {basin_name}")
#plt.savefig("images/sub_basins/NAtlantic_sub_basinsv3_proposed_changes_v2.png")
plt.show()