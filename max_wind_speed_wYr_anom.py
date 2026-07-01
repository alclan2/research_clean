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
ds = filtered_join[['lon_bin', 'lat_bin', 'sub_basin_name', 'ISOTIME', 'WS', 'MSLP']]

# add year column
ds['YEAR'] = ds['ISOTIME'].dt.year

# calc anomaly (baseline: entire time period)
# overall climatology per sub-basin
clim = ds.groupby("sub_basin_name")[["WS", "MSLP"]].mean().rename(
    columns={"WS": "clim_WS", "MSLP": "clim_MSLP"}
)

# merge climatology back
ds_anom = ds.merge(clim, on="sub_basin_name", how="left")

# compute anomalies
ds_anom["WS_anom"] = ds_anom["WS"] - ds_anom["clim_WS"]
ds_anom["MSLP_anom"] = ds_anom["MSLP"] - ds_anom["clim_MSLP"]

# now aggregate yearly anomalies
yearly_anom = (
    ds_anom
    .groupby(["YEAR", "sub_basin_name"], as_index=False)
    .agg(
        mean_WS_anom=("WS_anom", "mean"),
        mean_MSLP_anom=("MSLP_anom", "mean")
    )
)

#print(yearly_anom)

# save to csv
#yearly_anom.to_csv("datasets/SyCLoPS/WS_MSLP_anom_bySubbasin_TC+TD_table.csv")

#######################################################################################################

# plot mean WS as a time series per sub basin

# # select sub basin
# sb = 'Mid-latitudinal Atlantic'

# df_plot = yearly_anom[yearly_anom["sub_basin_name"] == sb]

# plt.figure(figsize=(10, 5))
# plt.plot(df_plot["YEAR"], df_plot["mean_MSLP_anom"], marker="o", color = "green")

# plt.axhline(0, color="black", linewidth=1)
# plt.title(f"Mean Sea Level Pressure Anomaly for TC/TDs in North Atlantic - {sb}")
# plt.xlabel("Year")
# plt.ylabel("MSLP Anomaly (Pa)")

# plt.tight_layout()
#plt.savefig(f"images/data_viz/MSLP/timeseries/TC+TD_MSLP_anom_timeseries_{sb}.png")
#plt.show()

#######################################################################################################

# compute correl between WS and MSLP
corrs = (
    yearly_anom
    .groupby("sub_basin_name")
    .apply(lambda x: x["mean_WS_anom"].corr(x["mean_MSLP_anom"]))
    .rename("correlation")
    .reset_index()
)

#print(yearly_anom.head())
#print(corrs)

# save to csv
corrs.to_csv("datasets/SyCLoPS/WS_MSLP_anom_correl_TC+TD.csv")