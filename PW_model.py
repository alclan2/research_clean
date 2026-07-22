import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import xarray as xr
import math
from geopy.distance import geodesic
import seaborn as sns

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

#################################################################################################

## read in and filter our syclops data
# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# TC Nodes: filter to TCs only, tropical flag = 1 so we are only counting before they become extratropical
#dftc_node = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
tc = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# sort by TID and ISOTIME
tc = tc.sort_values(['TID', 'ISOTIME'])

# convert lon to -180-180 from 0-360
tc['LON'] = ((tc['LON'] + 180) % 360) - 180

# trim columns
tc = tc[['TID', 'LON', 'LAT', 'ISOTIME', 'MSLP', 'WS']]

# convert MSLP to hPa from Pa
#tc['MSLP'] = tc['MSLP']/100

# calc translation speed since we'll need it later
tc['translation_speed'] = None

# loop through each storm
for tid, group in tc.groupby("TID"):

    idx = group.index

    for i in range(1, len(group)):
        # Previous and current positions
        p1 = (group.iloc[i-1]["LAT"], group.iloc[i-1]["LON"])
        p2 = (group.iloc[i]["LAT"], group.iloc[i]["LON"])

        # Distance (km)
        distance = geodesic(p1, p2).km

        # Time difference (hours)
        dt = (group.iloc[i]["ISOTIME"] - group.iloc[i-1]["ISOTIME"]).total_seconds() / 3600

        # Translation speed (km/h)
        tc.loc[idx[i], "translation_speed"] = distance / dt

# set first time step translation speed to NaN
tc["translation_speed"] = pd.to_numeric(
    tc["translation_speed"], errors="coerce"
)

# add column for average environmental pressure
tc['pn'] = 101500 #Pa

# change in pressure from environment to center
tc['delta_p'] = tc['pn'] - tc['MSLP']

# Pressure deficit in hPa for Holland B equation
tc['delta_p_hPa'] = tc['delta_p'] / 100

# calc pressure using Eq (8)
tc['p_rmw'] = tc['MSLP'] + (tc['delta_p'])/3.7

# add dry gas constant
tc['Rd'] = 287.05   # J kg^-1 K^-1

# # e
# tc['e'] = math.e

# convert LAT to absolute value
tc['LAT_abs'] = tc['LAT'].abs()

# Ts (surface air temperature)
tc['Ts (C)'] = 28 - (3*(tc['LAT'] - 10))/10

# numerator/denominator for qm calc
tc['qm_num'] = 17.67*tc['Ts (C)']
tc['qm_den'] = 243.5 + tc['Ts (C)']

# qm (vapor pressure at an assumed relative humidity of 90%)
tc['qm'] = 0.9*(3.802/tc['p_rmw'])*(np.exp(tc['qm_num']/tc['qm_den']))

# Tvs (virtual temperature at a 10m height in the max wind regime)
tc['Tvs (K)'] = (tc['Ts (C)'] + 273.15)*(1 + 0.81*tc['qm'])

# drop unnecessary columns
tc = tc.drop(["qm_num", "qm_den"], axis=1)

# use the Holland P-W model to derive max wind speed
# # parameter x
tc['x'] = 0.6 * (1 - tc['delta_p_hPa']/215)

# partial of pc wrt time
tc["dt_hours"] = (tc.groupby("TID")["ISOTIME"].diff().dt.total_seconds() / 3600)
tc["dMSLP/dt"] = (tc.groupby("TID")["MSLP"].diff()/tc["dt_hours"]) / 100

# parameter bs
tc["bs"] = (
    (-4.4 * 10**(-5)) * (tc["delta_p_hPa"]**2)
    + 0.01 * tc["delta_p_hPa"]
    + 0.03 * tc["dMSLP/dt"]
    - 0.014 * tc["LAT_abs"]
    + 0.15 * (tc["translation_speed"] ** tc["x"])
    + 1.0
)

# maximum wind
tc['vm'] = ((tc['bs']*tc['p_rmw']*tc['delta_p'])/(tc['Rd']*tc['Tvs (K)']*np.e))**0.5

# print(tc.head(20))

#################################################################################################

# now join sub basins and plot per sub basin

# create points
points = gpd.GeoDataFrame(
    tc,
    geometry=gpd.points_from_xy(
        tc['LON'],
        tc['LAT']
    ),
    crs="EPSG:4326"
)

# spatial join
tc_sb = gpd.sjoin(
    points,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="covered_by"
)

# trim columns
tc_sb = tc_sb[['TID', 'LON', 'LAT', 'ISOTIME', 'MSLP', 'WS', 'vm', 'sub_basin_name']]

# create year column
tc_sb['year'] = tc['ISOTIME'].dt.year

# # filter to specific sub basin
# sb = 'Western Africa'

# tc_sb_filt = tc_sb[tc_sb['sub_basin_name'] == sb]

# find the max vm per TID
tc_max = (
    tc_sb.groupby(["TID", "sub_basin_name", "year"])["vm"]
    .max()
    .reset_index()
)

# average per yr to create time series
annual_max = (
    tc_max
    .groupby(["sub_basin_name", "year"])["vm"]
    .max()
    .reset_index()
)

# # scatter plot
# plt.figure(figsize=(12,6))

# plt.plot(
#     annual_max['year'],
#     annual_max['vm'],
#     marker='o',
#     linewidth=1
# )

# plt.xlabel("Year")
# plt.ylabel("Maximum Wind (m/s)")
# plt.title(f"TC Maximum Wind Speed in North Atlantic - {sb}")

# #plt.savefig(f'images/data_viz/vmax_PW/max_wind_speed_vm_PW_timeseries_{sb}')
# plt.show()

#################################################################################################

# tc_valid = tc_sb.dropna(subset=["vm"])

# plt.figure(figsize=(10,6))

plt.figure(figsize=(10, 6))

order = sorted(tc_max["sub_basin_name"].dropna().unique())

sns.boxplot(
    data=tc_max,
    x="sub_basin_name",
    y="vm",
    order=order
)

plt.xticks(rotation=45, ha="right")
plt.xlabel("Sub-basin")
plt.ylabel("Maximum Wind Speed (m/s)")
plt.title("Distribution of TC Maximum Wind Speed by Sub-basin in North Atlantic")

plt.savefig('images/data_viz/vmax_PW/max_wind_speed_vm_distribution_max_per_TID.png')
plt.tight_layout()
plt.show()

#################################################################################################

# storm_peak = (
#     annual_max.dropna(subset=["vm"])
#     .groupby(["TID", "sub_basin_name"])["vm"]
#     .max()
#     .reset_index()
# )

# plt.figure(figsize=(10,5))

# sns.boxplot(
#     data=storm_peak,
#     x="sub_basin_name",
#     y="vm"
# )

# plt.xticks(rotation=45, ha="right")
# plt.ylabel("Peak Wind Speed (m/s)")
# plt.xlabel("Sub-basin")
# plt.title("Peak TC Intensity by Sub-basin")

# plt.show()