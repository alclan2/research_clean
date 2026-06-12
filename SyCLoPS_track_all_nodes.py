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

# read in tc_basins file so we can filter to a specific ocean basin
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






## read in and filter our syclops data
# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# TC Nodes: filter to TCs only, tropical flag = 1 so we are only counting before they become extratropical
#dftc_node = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
dftc = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# sort by TID and ISOTIME
dftc = dftc.sort_values(['TID', 'ISOTIME'])

# convert lon to -180-180 from 0-360
dftc['LON'] = ((dftc['LON'] + 180) % 360) - 180

# find origin nodes
dftc_origin = dftc.groupby('TID', as_index=False).first()

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
tc_origin_pts = gpd.GeoDataFrame(
    dftc_origin,
    geometry=gpd.points_from_xy(dftc_origin.LON, dftc_origin.LAT),
    crs="EPSG:4326"
)

# filter points to specific subbasin origin
tc_origin_sb = gpd.sjoin(
    tc_origin_pts,
    sub_basins[sub_basins["sub_basin_name"] == "Mid-latitudinal US/CA"],
    how = "inner",
    predicate = "within"
)

# get TIDs
track_TIDs = tc_origin_sb["TID"].unique()

# filter on TIDs that have origin nodes in that specific subbasin
dftc_track = dftc[dftc['TID'].isin(track_TIDs)]

# create a figure with a geographic projection
fig = plt.figure(figsize=(8,6))
ax = plt.axes(projection=ccrs.PlateCarree()) 

# plot sub-basins first
sub_basins.plot(
    ax=ax,
    facecolor='none',
    edgecolor='darkblue',
    path_effects=[pe.withStroke(linewidth=3, foreground='white')],
    linewidth=1.5,
    transform=ccrs.PlateCarree(),
    zorder=4
)

# plot the TC tracks
for id_, group in dftc_track.groupby('TID'):
    ax.plot(
        group['LON'],
        group['LAT'],
        linewidth=0.8,
        label=str(id_)
    )

# Add coastlines
ax.coastlines(resolution='50m', color='black', linewidth=1)

# Set labels and title
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Track of TCs with Mid-latitudinal US/CA Origin (North Atlantic, 1940-2024)')

# set axis bounds
lon_min = -110
lon_max = 20
lat_min = 0
lat_max = 60

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

ax.set_extent([lon_min, lon_max, lat_min, lat_max],crs=ccrs.PlateCarree())

plt.savefig(r"images/data_viz/TC_track_MidLatUS.png")
plt.show()


