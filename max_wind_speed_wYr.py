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
from matplotlib.ticker import MaxNLocator

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# TC Nodes:
df = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
#df = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# filter to columns we need
df = df[['TID', 'LON', 'LAT', 'ISOTIME', 'WS', 'MSLP']]

# convert longitude to 180 scale
df['LON_180'] = ((df['LON'] + 180) % 360) - 180

#######################################################################################################

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
basins["geometry"] = basins["geometry"].apply(shift_lon)

#######################################################################################################

# calculate max wind shear per grid cell (4deg)

# filter points
points = gpd.GeoDataFrame(
    df, 
    geometry = gpd.points_from_xy(df.LON_180, df.LAT),
    crs = "EPSG:4326"
)

filtered = gpd.sjoin(
    points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# set axis bounds for the region (match same dimensions as reg gen plots)
lon_min = filtered['LON_180'].min()
lon_max = filtered['LON_180'].max()
lat_min = filtered['LAT'].min()
lat_max = filtered['LAT'].max()

# set up 4x4 degree spacing
lon_edges = np.arange(lon_min, lon_max + 4, 4)
lat_edges = np.arange(lat_min, lat_max + 4, 4)

filtered["lon_bin"] = np.floor(filtered["LON_180"] / 4) * 4
filtered["lat_bin"] = np.floor(filtered["LAT"] / 4) * 4

# join sub basin name for each point
filtered_gdf = gpd.GeoDataFrame(
    filtered,
    geometry=gpd.points_from_xy(
        filtered.LON_180,
        filtered.LAT
    ),
    crs=sub_basins.crs
)

filtered_gdf = filtered_gdf.drop(columns="index_right", errors="ignore")

filtered_join = gpd.sjoin(
    filtered_gdf,
    sub_basins[['sub_basin_name', 'geometry']],
    how='left',
    predicate='within'
)

# trim columns
ws = filtered_join[['lon_bin', 'lat_bin', 'sub_basin_name', 'ISOTIME', 'WS', 'MSLP']]

# add year column
ws['YEAR'] = ws['ISOTIME'].dt.year

#print(ws.head())

# pivot by year to get time series of mean WS (or MSLP)
ws_yr = ws.pivot_table(
    index="YEAR",
    columns="sub_basin_name",
    values="MSLP",
    aggfunc="mean"
)

#print(ws_yr.head())

#######################################################################################################

# # plot mean WS as a time series per sub basin

# # select sub basin
# sb = 'Northeastern Seaboard'

# # scatter plot
# ax = ws_yr[sb].plot(
#    kind='line',
#    marker='o',
#    figsize=(10, 6)
# )

# ax.set_xlabel("Year")
# ax.set_ylabel("MSLP (Pa)")
# ax.set_title(f"Mean Sea Level Pressure for TC/TDs in North Atlantic ({sb})")
# ax.yaxis.set_major_locator(MaxNLocator(integer=True))

# plt.savefig(f"images/data_viz/MSLP/timeseries/tc_mslp_timeseries_{sb}_v2.png")
# plt.show()

#######################################################################################################

# pivot to get correlation between WS and MSLP

# pivot to year means
yearly = (
    ws
    .groupby(["YEAR", "sub_basin_name"], as_index=False)
    .agg(
        mean_WS=("WS", "mean"),
        mean_MSLP=("MSLP", "mean")
    )
)

print(yearly.head())

# save to csv
yearly.to_csv("datasets/SyCLoPS/WS_MSLP_bySubbasin_TC+TD_table.csv")

# compute correl between WS and MSLP
corrs = (
    yearly
    .groupby("sub_basin_name")
    .apply(lambda x: x["mean_WS"].corr(x["mean_MSLP"]))
    .rename("correlation")
    .reset_index()
)

#print(corrs)

# save to csv
corrs.to_csv("datasets/SyCLoPS/WS_MSLP_correl_TC+TD.csv")

#######################################################################################################

# # plot

# # set up map projection
# fig, ax = plt.subplots(figsize = (10,6), subplot_kw = {"projection": ccrs.PlateCarree()})

# #add coastlines & set axis bounds
# ax.coastlines()

# # custom colormap so 0 displays as white on the map
# base_cmap = plt.cm.plasma_r
# cmap_colors = base_cmap(np.linspace(0, 1, 256))
# cmap_colors[0] = [1.0, 1.0, 1.0, 1.0]  # white (RGBA)
# plasma_r_zero_white = colors.ListedColormap(cmap_colors)

# # Plot sub-basins first
# sub_basins.plot(
#     ax=ax,
#     facecolor='none',
#     edgecolor='red',
#     path_effects=[pe.withStroke(linewidth=3, foreground='white')],
#     linewidth=1,
#     transform=ccrs.PlateCarree(),
#     zorder=4
# )

# # plot
# grid = grid_mean_ws.pivot(
#     index="lat_bin",
#     columns="lon_bin",
#     values="mean_WS"
# )

# lon = grid.columns.values
# lat = grid.index.values
# Lon, Lat = np.meshgrid(lon, lat)

# pcm = ax.pcolormesh(
#     Lon,
#     Lat,
#     grid.values,
#     cmap=plasma_r_zero_white,
#     shading="auto",
#     transform=ccrs.PlateCarree()
# )

# plt.colorbar(pcm, ax=ax, label="Mean Wind Speed (m/s)")

# # # Set labels and title
# ax.set_ylabel('Latitude')
# ax.set_xlabel('Longitude')
# ax.set_title('Max Wind Speed (10m) of TC/TDs in the North Atlantic (1940-2024)')

# # round to nearest 10deg
# lon_min_10 = np.floor(lon_min / 10) * 10 
# lon_max_10 = np.ceil(lon_max / 10) * 10   
# lat_min_10 = np.floor(lat_min / 10) * 10
# lat_max_10 = np.ceil(lat_max / 10) * 10

# # add sub-basin labels
# for idx, row in sub_basins.iterrows():
#     point = row.geometry.centroid
#     name = row["sub_basin_name"]

#     # wrap text (adjust width as needed)
#     name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
    
#     # move Arctic label downward
#     if name == "Arctic":
#         point = Point(point.x, point.y - 15)
#         #continue

#     # Northern Europe label down a bit
#     elif name == "Northern Europe":
#         point = Point(point.x, point.y - 5)
#         #continue

#     txt = ax.text(
#         point.x,
#         point.y,
#         name_wrapped,
#         transform=ccrs.PlateCarree(),
#         fontsize=7,
#         weight='bold',
#         ha='center',
#         va='center',
#         color='black',
#         zorder=10
#     )

#     txt.set_path_effects([
#         pe.withStroke(linewidth=3, foreground="white")
#     ])

# # Set tick marks every 10 degrees
# ax.set_extent([lon_min_10, lon_max_10, lat_min_10, lat_max_10],crs=ccrs.PlateCarree())
# ax.set_xticks(np.arange(lon_min_10, lon_max_10, 10), crs=ccrs.PlateCarree())
# ax.set_yticks(np.arange(lat_min_10, lat_max_10, 10), crs=ccrs.PlateCarree())

#plt.savefig(r"images/data_viz/WS/max_wind_speed_syclops_TC+TD_coarse.png")
#plt.show()