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
import xarray as xr

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

# read in anom net cdf
ds = xr.open_dataset("datasets/COBE2 SST/post-processing/SST_mon_mean_anom_moving_window_jun_oct.nc")

#print(ds)

# convert to a dataframe
df = ds['sst'].to_dataframe(name = 'mean_anom').reset_index()

#print(df)

# join sub basins
points = gpd.GeoDataFrame(
    df, 
    geometry = gpd.points_from_xy(df.lon, df.lat),
    crs = "EPSG:4326"
)

filtered = gpd.sjoin(
    points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# join sub basin name for each point
filtered_gdf = gpd.GeoDataFrame(
    filtered,
    geometry=gpd.points_from_xy(
        filtered.lon,
        filtered.lat
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

# add year column for group by
filtered_join['year'] = filtered_join['time'].dt.year

# print(filtered_join)

# Calculate annual mean anomaly for each sub-basin
df_clean = filtered_join.dropna(subset=["sub_basin_name"])

annual_table = (
    df_clean.groupby(["year", "sub_basin_name"])["mean_anom"]
            .mean()
            .reset_index()
)

print(annual_table)

# save to csv
annual_table.to_csv("datasets/COBE2 SST/post-processing/sst_anom_moving_window_bySubbasin_table.csv")

#######################################################################################################

# # plot mean SST anom as a time series per sub basin

# # select sub basin
# sb = 'Deep Tropics'

# # pivot to have sub basins be column heads
# sst_piv = df.pivot_table(
#     index="year",
#     columns="basin",
#     values="mean_anom",
#     aggfunc="mean"
# )

# #print(sst_piv.head())

# # scatter plot
# ax = sst_piv[sb].plot(
#    kind='line',
#    marker='o',
#    figsize=(10, 6)
# )

# ax.set_xlabel("Year")
# ax.set_ylabel("SST Anomaly (°C)")
# ax.set_title(f"Mean Sea Surface Temperature Anomaly in North Atlantic ({sb})")
# #ax.yaxis.set_major_locator(MaxNLocator(integer=True))

# #plt.savefig(f"images/data_viz/MSLP/timeseries/tc_mslp_timeseries_{sb}_v2.png")
# plt.show()
