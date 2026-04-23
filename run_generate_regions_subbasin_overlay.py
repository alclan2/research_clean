import sys 
sys.path.insert(0, "./")
import matplotlib.pyplot as plt
from region_funcs import generate_regions
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.ticker as cticker
import matplotlib.ticker as mticker
import xarray as xr
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
import textwrap
import matplotlib.patheffects as pe

# select dataset for clustering
fpaths = [
    r"datasets/GPI/post-processing/GPI_mon_mean_anom_moving_window_1deg_sep_oct_lateszn.nc"
]

# call clustering function
da_region, reconstructed = generate_regions(fpaths, nRegions = 10, nIter = 5)

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

# create map with projection of continents
fig = plt.figure(figsize=(10, 8))
ax = plt.axes(projection=ccrs.PlateCarree())

#da_region.plot()
da_region.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),   # tells cartopy data are lat/lon
    cmap="viridis",
    add_colorbar=True
)

# set axis bounds
minx = float(da_region.lon.min())
maxx = float(da_region.lon.max())
miny = float(da_region.lat.min())
maxy = float(da_region.lat.max())

#print(minx, maxx, miny, maxy)

ax.set_extent([-113.5, 19.5, 0.5, 59.5], crs=ccrs.PlateCarree())

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

# add continents and coastlines
ax.add_feature(cfeature.COASTLINE, linewidth=1, zorder=1)

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
    name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False))
    
    # For MultiPolygon, use the largest polygon
    if geom.geom_type == "MultiPolygon":
        largest_poly = max(geom.geoms, key=lambda p: p.area)
        centroid = largest_poly.centroid
    if geom.geom_type == "MultiPolygon":
        geom = max(geom.geoms, key=lambda p: p.area)

    pt = geom.representative_point()

    x = max(min(pt.x, maxx), minx)
    y = max(min(pt.y, maxy), miny)

    # center the Arctic label since it's getting cut off the plot
    if name == "Arctic":
        padding = (maxy - miny) * 0.03
        y = maxy - padding
        x = (minx + maxx) / 2
    
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

# format and save
plt.title("GPI Monthly Mean Anomaly in North Atlantic Late Season (Sep-Oct, 1960-2015) (10 regions, 1deg)")
plt.tight_layout()
plt.savefig("images/region_generation/GPI_mon_mean_anom_moving_window_1deg_lateszn_10reg_with_subbasins_v3.png")
plt.show()