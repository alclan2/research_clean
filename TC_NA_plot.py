import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as colors
import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import textwrap
import matplotlib.patheffects as pe
from shapely.geometry import Polygon, MultiPolygon, Point
import geopandas as gpd

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
dfc = pd.read_parquet(ClassifiedData)

# select TC and TD LPS nodes and filter QS out of Track_Info
dfc_sub = dfc[((dfc.Short_Label=='TC') | (dfc.Short_Label=='TD')) & ~(dfc['Track_Info'].str.contains('QS', case=False, na=False))]

#convert LON to 180 coordinates
dfc_sub.loc[:, 'LON_180'] = dfc_sub['LON'].where(
    dfc_sub['LON'] <= 180,
    dfc_sub['LON'] - 360
)

# define our x and y axes for longitude and latitude
x = dfc_sub["LON_180"]
y = dfc_sub["LAT"]

# set axis bounds for the region
lon_min, lon_max = -180, -30
lat_min, lat_max = 0, 60

# set up 4x4 degree spacing
lon_edges = np.arange(lon_min, lon_max + 4, 4)
lat_edges = np.arange(lat_min, lat_max + 4, 4)

# set up map projection
fig, ax = plt.subplots(figsize = (10,5), subplot_kw = {"projection": ccrs.PlateCarree()})

#add coastlines & set axis bounds
ax.coastlines()
ax.set_extent([-180, -30, 0, 60], crs = ccrs.PlateCarree())

# custom colormap so 0 displays as white on the map
base_cmap = plt.cm.plasma_r
cmap_colors = base_cmap(np.linspace(0, 1, 256))
cmap_colors[0] = [1.0, 1.0, 1.0, 1.0]  # white (RGBA)
plasma_r_zero_white = colors.ListedColormap(cmap_colors)

# make the TC density plot
plt.hist2d(x, y, bins = [lon_edges, lat_edges], range = [[-180, -30], [0, 60]], cmap = plasma_r_zero_white, transform = ccrs.PlateCarree())

# read in NAtl subbasin polygons
sub_polygons_dict = {}

with open("tc_subbasins_NAtl_v3.dat", "r") as f:
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

# add X (longitude) tick marks
ax.set_xticks([-180, -150, -120, -90, -60, -30], crs=ccrs.PlateCarree())
ax.xaxis.set_major_formatter(
    mticker.FuncFormatter(lambda x, _: f"{x:.0f}°")
)

# add Y (latitude) tick marks
ax.set_yticks([0, 15, 30, 45, 60], crs=ccrs.PlateCarree())
ax.yaxis.set_major_formatter(
    mticker.FuncFormatter(lambda y, _: f"{y:.0f}°")
)

# plot sub-basins
sub_basins.plot(ax=ax,
    linewidth=1.5,
    edgecolor="gray",
    facecolor="none",
    path_effects=[
        pe.Stroke(linewidth=3, foreground="white"), 
        pe.Normal()
    ],
    transform=ccrs.PlateCarree(),
    zorder=3
)



ax.tick_params(
    bottom=True, top=False,
    left=True, right=False,
    labelsize=10
)

# add legend
plt.colorbar(shrink = 0.7, fraction = 0.05, orientation = 'horizontal')

# display the plot
plt.show()