import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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
import rioxarray

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_input_ERA5_4024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

#print(df.columns)

# filter columns
dpshear = df[['TID', 'LON', 'LAT', 'ISOTIME', 'DEEPSHEAR']]

# recast ISOTIME
#dpshear['time'] = pd.to_datetime(dpshear['ISOTIME'])

# filter to hurricane szn
dpshear = dpshear[dpshear['ISOTIME'].dt.month.isin([6, 7, 8, 9, 10])]

# convert on to -180-180
dpshear['LON'] = ((dpshear['LON'] + 180) % 360) - 180

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

# filter to N Atlantic basin
region = basins[basins["basin name"] == "N Atlantic"]

points = gpd.GeoDataFrame(
    dpshear, 
    geometry = gpd.points_from_xy(dpshear.LON, dpshear.LAT),
    crs = "EPSG:4326"
)
basin_geom = region.geometry.iloc[0]
dpshear_filt = points[points.within(basin_geom)]

# anomaly calc
#dpshear_mean = dpshear_filt['DEEPSHEAR'].mean()
#dpshear_filt['DEEPSHEAR_anom'] = dpshear_filt['DEEPSHEAR'] - dpshear_mean

# create 4deg grid
lat_bins = np.arange(-90, 94, 4)  
lon_bins = np.arange(-180, 184, 4)

# assign each point to a 4deg grid cell
dpshear_copy = dpshear_filt.copy()

dpshear_copy["lat_bin"] = pd.cut(dpshear_copy["LAT"], bins=lat_bins, labels=lat_bins[:-1])
dpshear_copy["lon_bin"] = pd.cut(dpshear_copy["LON"], bins=lon_bins, labels=lon_bins[:-1])

# calc the mean DEEPSHEAR within each grid cell
dpshear_grid_means = (
    dpshear_copy.groupby(["lat_bin", "lon_bin"])["DEEPSHEAR"]
    .mean()
    .reset_index()
)

# convert bins to 2D grid
dpshear_grid_means["lat"] = dpshear_grid_means["lat_bin"].astype(float)
dpshear_grid_means["lon"] = dpshear_grid_means["lon_bin"].astype(float)

pivot = dpshear_grid_means.pivot(index="lat", columns="lon", values="DEEPSHEAR")

# read in tc_subbasins_NAtl file for overlay
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

# plot
fig = plt.figure(figsize=(10,6))
ax = plt.axes(projection=ccrs.PlateCarree())

# Plot sub-basins first
sub_basins.plot(
    ax=ax,
    facecolor='none',
    edgecolor='black',
    path_effects=[pe.withStroke(linewidth=3, foreground='white')],
    linewidth=1,
    transform=ccrs.PlateCarree(),
    zorder=4
)

# find lon/lat min/max for axis bounds
lon_min = dpshear_grid_means['lon'].min()
lon_max = dpshear_grid_means['lon'].max()
lat_min = dpshear_grid_means['lat'].min()
lat_max = dpshear_grid_means['lat'].max()

# round to nearest 10deg
lon_min_10 = np.floor(lon_min / 10) * 10 
lon_max_10 = np.ceil(lon_max / 10) * 10   
lat_min_10 = np.floor(lat_min / 10) * 10
lat_max_10 = np.ceil(lat_max / 10) * 10

# add coastlines
ax.coastlines()
#ax.set_extent([-100, 0, 0, 50])

# add color bar
mesh = ax.pcolormesh(
    pivot.columns,
    pivot.index,
    pivot.values,
    cmap="coolwarm",
    shading="auto",
    transform=ccrs.PlateCarree()
)

# add sub-basin labels
for idx, row in sub_basins.iterrows():
    point = row.geometry.representative_point()
    name = row["sub_basin_name"]

    # wrap text (adjust width as needed)
    name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
    
    if (lon_min_10 <= point.x <= lon_max_10) and (lat_min_10 <= point.y <= lat_max_10):
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

plt.colorbar(mesh, ax=ax, label="Wind Shear")

# Set tick marks every 10 degrees
ax.set_xticks(np.arange(lon_min_10, lon_max_10, 10), crs=ccrs.PlateCarree())
ax.set_yticks(np.arange(lat_min_10, lat_max_10, 10), crs=ccrs.PlateCarree())

ax.set_extent([-113.5, 19.5, 0.5, 59.5],crs=ccrs.PlateCarree())

# add title
plt.title("Wind Shear Between 200-850hPa (1940-2024)")

# save plot
plt.savefig(r"images/TC_density/TC_DEEPSHEAR_NAtl_w_subbasin_overlay.png")
plt.show()