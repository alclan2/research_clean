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

# read in tc basins file and filter the N Atlantic points only
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

# filter points
points = gpd.GeoDataFrame(
    dfc_sub, 
    geometry = gpd.points_from_xy(dfc_sub.LON, dfc_sub.LAT),
    crs = "EPSG:4326"
)

filtered = gpd.sjoin(
    points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

#convert LON to 180 coordinates
filtered.loc[:, 'LON_180'] = filtered['LON'].where(
    filtered['LON'] <= 180,
    filtered['LON'] - 360
)

# define our x and y axes for longitude and latitude
x = filtered["LON_180"]
y = filtered["LAT"]

# set axis bounds for the region (match same dimensions as reg gen plots)
lon_min, lon_max = -113.5, 19.5
lat_min, lat_max = 0.5, 59.5

# set up 4x4 degree spacing
lon_edges = np.arange(lon_min, lon_max + 4, 4)
lat_edges = np.arange(lat_min, lat_max + 4, 4)

# set up map projection
fig, ax = plt.subplots(figsize = (10,6), subplot_kw = {"projection": ccrs.PlateCarree()})

#add coastlines & set axis bounds
ax.coastlines()

# custom colormap so 0 displays as white on the map
base_cmap = plt.cm.plasma_r
cmap_colors = base_cmap(np.linspace(0, 1, 256))
cmap_colors[0] = [1.0, 1.0, 1.0, 1.0]  # white (RGBA)
plasma_r_zero_white = colors.ListedColormap(cmap_colors)

# make the TC density plot
plt.hist2d(x, y, bins = [lon_edges, lat_edges], range = [[lon_min, lon_max], [lat_min, lat_max]], cmap = plasma_r_zero_white, transform = ccrs.PlateCarree())

ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs = ccrs.PlateCarree())





# read in NAtl subbasin polygons
sub_polygons_dict = {}

with open("tc_subbasins_NAtl_coarse_v3.dat", "r") as f:
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

# add axis labels
gl = ax.gridlines(
    crs=ccrs.PlateCarree(),
    draw_labels=True,
    linewidth=0.8,
    color='gray',
    alpha=0,
)

# keep labels only on left and bottom
gl.top_labels = False
gl.right_labels = False
gl.xlocator = mticker.MultipleLocator(20)
gl.ylocator = mticker.MultipleLocator(10)

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

# Add basin labels
for idx, row in sub_basins.iterrows():
    geom = row.geometry
    name = row["sub_basin_name"]

    # wrap text (adjust width as needed)
    name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
    
    # For MultiPolygon, use the largest polygon
    if geom.geom_type == "MultiPolygon":
        largest_poly = max(geom.geoms, key=lambda p: p.area)
        centroid = largest_poly.centroid
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda p: p.area)

    pt = geom.centroid

    x = max(min(pt.x, lon_max), lon_min)
    y = max(min(pt.y, lat_max), lat_min)

    # center the Arctic label since it's getting cut off the plot
    if name == "Arctic":
        padding = (lat_max - lat_min) * 0.03
        y = lat_max - padding
        x = (lon_min + lon_max) / 2
    
    ax.text(
        x,
        y,
        name_wrapped,
        horizontalalignment='center',
        fontsize=7,
        fontweight='bold',
        color='black',
        transform=ccrs.PlateCarree(),
        path_effects=[
            pe.withStroke(linewidth=2, foreground="white")
        ]
    )

ax.tick_params(
    bottom=True, top=False,
    left=True, right=False,
    labelsize=10
)

# add legend & title
plt.colorbar(shrink = 0.7, fraction = 0.05, orientation = 'horizontal')
plt.title("TC Density in North Atlantic (1940-2024)")

# save plot
#plt.savefig("images/TC_density/TC_density_NAtl_w_subbasin_overlay.png")

# display the plot
plt.show()