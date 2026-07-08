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
import matplotlib.pyplot as plt

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
basins["geometry"] = basins["geometry"].apply(shift_lon)
sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)

############################################################################################################

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# TC Nodes:
#dftc_node = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
dftc_node = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# convert LON to 180 scale
dftc_node["LON"] = ((dftc_node["LON"] + 180) % 360) - 180

# first node: where the TC originates
tc_origin = (
    dftc_node
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .head(1)
)

# last node: where the TC dissipates
TC_TIDs = tc_origin['TID']
tc_dissipate = (
    dftc_node[(dftc_node['TID'].isin(TC_TIDs)) & (dftc_node['Tropical_Flag'] == 1)]
    .sort_values(by='ISOTIME')
    .groupby('TID', as_index=False)
    .tail(1)
)

# create origin/dissipation points
tc_origin_points = gpd.GeoDataFrame(
    tc_origin, 
    geometry = gpd.points_from_xy(tc_origin['LON'], tc_origin['LAT']),
    crs = "EPSG:4326"
)

tc_diss_points = gpd.GeoDataFrame(
    tc_dissipate, 
    geometry = gpd.points_from_xy(tc_dissipate['LON'], tc_dissipate['LAT']),
    crs = "EPSG:4326"
)

# filter points to North Atlantic
tc_origin_NAtl = gpd.sjoin(
    tc_origin_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

tc_diss_NAtl = gpd.sjoin(
    tc_diss_points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# rename and trim columns
tc_origin_NAtl = (tc_origin_NAtl[["TID", "ISOTIME", "LON", "LAT", "MSLP", "WS"]]
             .rename(columns={
                 "ISOTIME": "origin_time",
                 "MSLP": "MSLP_origin",
                 "WS": "WS_origin",
                 "LON": "LON_origin",
                 "LAT": "LAT_origin"
                 }))
tc_diss_NAtl = (tc_diss_NAtl[["TID", "ISOTIME", "LON", "LAT", "MSLP", "WS"]]
                .rename(columns={
                    "ISOTIME": "diss_time",
                    "MSLP": "MSLP_diss",
                    "WS": "WS_diss",
                    "LON": "LON_diss",
                    "LAT": "LAT_diss"
                    }))

# merge on TID
lifespan = tc_origin_NAtl.merge(tc_diss_NAtl, on="TID", how="inner")

#print(lifespan.head())

# calculate lifespan
lifespan["lifespan"] = lifespan["diss_time"] - lifespan["origin_time"]

# add a lifespan in days column
lifespan["lifespan_days"] = lifespan["lifespan"].dt.total_seconds() / 86400

# print(lifespan.head())

# create origin and dissipation points from lifespan
og_pts = gpd.GeoDataFrame(
    lifespan,
    geometry=gpd.points_from_xy(
        lifespan["LON_origin"],
        lifespan["LAT_origin"]
    ),
    crs="EPSG:4326"
)

diss_pts = gpd.GeoDataFrame(
    lifespan,
    geometry=gpd.points_from_xy(
        lifespan["LON_diss"],
        lifespan["LAT_diss"]
    ),
    crs="EPSG:4326"
)

# join sub basin names
origin_join = gpd.sjoin(
    og_pts,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="within"
)

diss_join = gpd.sjoin(
    diss_pts,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="within"
)

# add origin/dissipation sub basin back to lifespan
lifespan["sub_basin_origin"] = origin_join["sub_basin_name"].values
lifespan["sub_basin_diss"] = diss_join["sub_basin_name"].values

#print(lifespan.columns)

############################################################################################################

# # calc avg life span per sub basin
# avg_lifespan = (
#     lifespan
#     .groupby("sub_basin_origin", as_index=False)["lifespan_days"]
#     .mean()
#     .rename(columns={"lifespan_days": "mean_lifespan_days"})
# )

# # order longest to shortest
# avg_lifespan = avg_lifespan.sort_values(
#     by="mean_lifespan_days",
#     ascending=False
# )

# # plot
# plt.figure(figsize=(10, 5))

# plt.bar(
#     avg_lifespan["sub_basin_origin"],
#     avg_lifespan["mean_lifespan_days"]
# )
# plt.xlabel("Origin Sub-basin")
# plt.ylabel("Average Lifespan (days)")
# plt.title("Average TC Lifespan by Origin Sub-basin")

# plt.xticks(rotation=45, ha="right")
# plt.tight_layout()

# #plt.savefig("images/data_viz/lifespan/tc_lifespan_per_subbasin.png")

# plt.show()

############################################################################################################

# # scatter plot of lifespan vs. WS/MSLP

# # filter to sub basin
# sb = 'Mid-latitudinal Atlantic'

# lifespan_sb = lifespan[lifespan["sub_basin_origin"] == sb]

# #print(lifespan_sb.head())

# plt.figure(figsize=(10, 5))

# plt.scatter(
#     x = lifespan_sb["WS_origin"],
#     y = lifespan_sb["WS_diss"],
#     color = 'purple',
#     s=50
# )

# plt.xlabel("WS at Origin (m/s)")
# plt.ylabel("WS at Dissipation (m/s)")
# plt.title(f"TC Wind Speed at Origin vs. Dissipation - {sb}")

# plt.xticks(rotation=45, ha="right")
# plt.tight_layout()

# plt.savefig(f"images/data_viz/WS/WS_origin_vs_diss_{sb}.png")

# plt.show()

############################################################################################################

# scatter plot with line of best fit
# filter to sub basin
sb = 'Mid-latitudinal Atlantic'

lifespan_sb = lifespan[lifespan["sub_basin_origin"] == sb]

plt.figure(figsize=(10, 5))

x = lifespan_sb["WS_origin"]
y = lifespan_sb["WS_diss"]

plt.scatter(
    x=x,
    y=y,
    color='purple',
    s=50
)

# Line of best fit
m, b = np.polyfit(x, y, 1)
x_fit = np.linspace(x.min(), x.max(), 100)

# add R2
from sklearn.metrics import r2_score
y_pred = m * x + b
r2 = r2_score(y, y_pred)

plt.plot(
    x_fit,
    m * x_fit + b,
    color="black",
    linewidth=2,
    label=f"Best fit: y={m:.2f}x+{b:.2f}, R²={r2:.2f}"
)

plt.xlabel("WS at Origin (m/s)")
plt.ylabel("WS at Dissipation (m/s)")
plt.title(f"TC Wind Speed at Origin vs. Dissipation - {sb}")

plt.legend()

plt.xticks(rotation=45, ha="right")
plt.tight_layout()

plt.savefig(f"images/data_viz/WS/WS_origin_vs_diss_wR2_{sb}.png")

plt.show()