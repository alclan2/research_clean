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

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

#print(df['Adjusted_Label'].unique())

# TC Nodes:
#dftc_node=df[(df.Track_Info.str.contains('TC')) & (df.Short_Label=='TC')]
#dftc_node=df[df.Track_Info=='Track_TC']
dftc_node = df[((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD') | (df.Adjusted_Label=='SS(STLC)')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
#dftc_node = df[((df.Adjusted_Label=='TC')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

#print(dftc_node['Adjusted_Label'].unique())

# first node: where the TC originates
tc_origin = (
    dftc_node
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .head(1)
)

#print(tc_origin.shape)

# last node: where the TC dissipates
TC_TIDs = tc_origin['TID']
tc_dissipate = (
    dftc_node[dftc_node['TID'].isin(TC_TIDs)]
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .tail(1)
)

#print(tc_dissipate.shape)

# make a new column with YEAR only from ISOTIME
#dfc_sub["YEAR"] = pd.to_datetime(dfc_sub["ISOTIME"]).dt.year

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

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
tc_origin_points = gpd.GeoDataFrame(
    tc_origin, 
    geometry = gpd.points_from_xy(tc_origin.LON, tc_origin.LAT),
    crs = "EPSG:4326"
)

# filter points to North Atlantic
tc_origin_filtered = gpd.sjoin(
    tc_origin_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

#print(tc_origin_filtered['Adjusted_Label'].unique())

# convert lon to -180-180 from 0-360
tc_origin_filtered['LON'] = ((tc_origin_filtered['LON'] + 180) % 360) - 180

# plot tc dissipate points for North Atlantic
# Create a figure with a geographic projection
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

# Scatter the points
ax.scatter(
    tc_origin_filtered['LON'],
    tc_origin_filtered['LAT'],
    c='blue',
    alpha=0.6,
    transform=ccrs.PlateCarree()
)

# custom colormap so 0 displays as white on the map
base_cmap = plt.cm.plasma_r
cmap_colors = base_cmap(np.linspace(0, 1, 256))
cmap_colors[0] = [1.0, 1.0, 1.0, 1.0]  # white (RGBA)
plasma_r_zero_white = colors.ListedColormap(cmap_colors)

# set axis bounds for the region (match same dimensions as reg gen plots)
lon_min, lon_max = -113.5, 19.5
lat_min, lat_max = 0.5, 59.5

# set up 4x4 degree spacing
lon_edges = np.arange(lon_min, lon_max + 4, 4)
lat_edges = np.arange(lat_min, lat_max + 4, 4)

# make the TC density plot
#plt.hist2d(tc_origin_filtered['LON'], tc_origin_filtered['LAT'], bins = [lon_edges, lat_edges], range = [[lon_min, lon_max], [lat_min, lat_max]], cmap = plasma_r_zero_white, transform = ccrs.PlateCarree())

# Add coastlines
ax.coastlines(resolution='50m', color='black', linewidth=1)

# Set labels and title
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Origin (First Node) of TCs + TDs + SS(STLC) in the North Atlantic (1940-2024)')

# add legend
#plt.colorbar(shrink = 0.7, fraction = 0.05, orientation = 'horizontal')

# find lon/lat min/max for axis bounds
#lon_min = tc_origin_filtered['LON'].min()
#lon_max = tc_origin_filtered['LON'].max()
#lat_min = tc_origin_filtered['LAT'].min()
#lat_max = tc_origin_filtered['LAT'].max()

# round to nearest 10deg
lon_min_10 = np.floor(lon_min / 10) * 10 
lon_max_10 = np.ceil(lon_max / 10) * 10   
lat_min_10 = np.floor(lat_min / 10) * 10
lat_max_10 = np.ceil(lat_max / 10) * 10

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

# Set tick marks every 10 degrees
ax.set_xticks(np.arange(lon_min_10, lon_max_10, 10), crs=ccrs.PlateCarree())
ax.set_yticks(np.arange(lat_min_10, lat_max_10, 10), crs=ccrs.PlateCarree())

ax.set_extent([lon_min_10, lon_max_10, lat_min_10, lat_max_10],crs=ccrs.PlateCarree())

plt.savefig(r"images/TC_density/TC_origin_NAtl_w_subbasin_overlay_TC+TD+SS_v2.png")
plt.show()