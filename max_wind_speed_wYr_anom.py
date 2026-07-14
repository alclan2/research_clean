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

# first node: where the TC originates
tc_origin = (
    df
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .head(1)
)

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
    tc_origin, 
    geometry = gpd.points_from_xy(tc_origin.LON_180, tc_origin.LAT),
    crs = "EPSG:4326"
)

filtered = gpd.sjoin(
    points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# # set axis bounds for the region (match same dimensions as reg gen plots)
# lon_min = filtered['LON_180'].min()
# lon_max = filtered['LON_180'].max()
# lat_min = filtered['LAT'].min()
# lat_max = filtered['LAT'].max()

# # set up 4x4 degree spacing
# lon_edges = np.arange(lon_min, lon_max + 4, 4)
# lat_edges = np.arange(lat_min, lat_max + 4, 4)

# filtered["lon_bin"] = np.floor(filtered["LON_180"] / 4) * 4
# filtered["lat_bin"] = np.floor(filtered["LAT"] / 4) * 4

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
ds = filtered_join[['LON_180', 'LAT', 'sub_basin_name', 'ISOTIME', 'WS']]

# add year column
ds['YEAR'] = ds['ISOTIME'].dt.year

# filter to hurricane season
ds_full = ds.loc[
    ds["ISOTIME"].dt.month.isin([6, 7, 8, 9, 10])
]

# aggregate daily means to monthly means
ds_monthly = (
    ds_full
    .groupby([
        "sub_basin_name",
        ds_full["ISOTIME"].dt.to_period("M")
    ])["WS"]
    .mean()
    .reset_index()
)

# convert month back to datetime
ds_monthly["ISOTIME"] = ds_monthly["ISOTIME"].dt.to_timestamp()

# calculate 21-year moving window (year-10 to year+10) by calendar month
ds_monthly["MONTH"] = ds_monthly["ISOTIME"].dt.month

ds_monthly["rolling_clim"] = (
    ds_monthly
    .groupby(["sub_basin_name", "MONTH"])["WS"]
    .transform(
        lambda x: x.rolling(
            21,
            center=True,
            min_periods=11
        ).mean()
    )
)

# calculate anomaly
ds_monthly["WS_anom"] = (
    ds_monthly["WS"] -
    ds_monthly["rolling_clim"]
)

# average by year and sub basin
annual_anom = (
    ds_monthly
    .groupby([
        "sub_basin_name",
        ds_monthly["ISOTIME"].dt.year.rename("YEAR")
    ])["WS_anom"]
    .mean()
    .reset_index()
)

# reorder columns
annual_anom = annual_anom[
    ["YEAR", "sub_basin_name", "WS_anom"]
]

print(annual_anom)

annual_anom = annual_anom.loc[
    (annual_anom["YEAR"] >= 1950) &
    (annual_anom["YEAR"] <= 2014)
]

# save to csv
annual_anom.to_csv("datasets/SyCLoPS/WS_anom_moving_window_bySubbasin_TC+TD_table.csv")

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

# # compute correl between WS and MSLP
# corrs = (
#     yearly_anom
#     .groupby("sub_basin_name")
#     .apply(lambda x: x["mean_WS_anom"].corr(x["mean_MSLP_anom"]))
#     .rename("correlation")
#     .reset_index()
# )

# #print(yearly_anom.head())
# #print(corrs)

# # save to csv
# corrs.to_csv("datasets/SyCLoPS/WS_MSLP_anom_correl_TC+TD.csv")

#######################################################################################################

# calc WS moving window anom at origin node

# # first node: where the TC originates
# tc_origin = (
#     df
#     .sort_values(by='ISOTIME')
#     .groupby('TID', as_index=False)
#     .head(1)
# )

# # create origin/dissipation points
# tc_origin_points = gpd.GeoDataFrame(
#     tc_origin, 
#     geometry = gpd.points_from_xy(tc_origin['LON_180'], tc_origin['LAT']),
#     crs = "EPSG:4326"
# )

# # filter points to North Atlantic
# tc_origin_NAtl = gpd.sjoin(
#     tc_origin_points,
#     sub_basins[['sub_basin_name', 'geometry']],
#     how='left',
#     predicate='within'
# )

# # rename and trim columns
# tc_origin_NAtl = (tc_origin_NAtl[["TID", "ISOTIME", "LON", "LAT", "MSLP", "WS", "sub_basin_name"]]
#              .rename(columns={
#                  "ISOTIME": "origin_time",
#                  "MSLP": "MSLP_origin",
#                  "WS": "WS_origin",
#                  "LON": "LON_origin",
#                  "LAT": "LAT_origin",
#                  "sub_basin_name": "origin_sub_basin"
#                  }))

# # add year column
# tc_origin_NAtl['year'] = tc_origin_NAtl['origin_time'].dt.year

# print(tc_origin_NAtl)

# # # calc anomaly (baseline: entire time period)
# # # overall climatology per sub-basin
# # clim = tc_origin_NAtl.groupby("origin_sub_basin")["WS_origin"].mean().rename(
# #     columns={"WS": "clim_WS", "MSLP": "clim_MSLP"}
# # )

# # # merge climatology back
# # ds_anom = tc_origin_NAtl.merge(clim, on="sub_basin_name", how="left")

# # # compute anomalies
# # ds_anom["WS_anom"] = ds_anom["WS"] - ds_anom["clim_WS"]
# # ds_anom["MSLP_anom"] = ds_anom["MSLP"] - ds_anom["clim_MSLP"]

# # # now aggregate yearly anomalies
# # yearly_anom = (
# #     ds_anom
# #     .groupby(["YEAR", "sub_basin_name"], as_index=False)
# #     .agg(
# #         mean_WS_anom=("WS_anom", "mean"),
# #         mean_MSLP_anom=("MSLP_anom", "mean")
# #     )
# # )