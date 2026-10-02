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
import xarray as xr

# read in tc_basins file so we can filter to a specific ocean basin
polygons_dict = {}

with open("tc_basins_NAtl.dat", "r") as f:
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

#################################################################################################################################

# ## read in and filter our syclops data
# # path to the classified dataset
# ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024_v7.parquet"

# # open the parquet format file (PyArrow package required)
# df = pd.read_parquet(ClassifiedData)

# # TC Nodes: filter to TCs only, tropical flag = 1 so we are only counting before they become extratropical
# # tc = df[(df.Tropical_Flag==1) & ((df.Adjusted_Label=='TC') | (df.Adjusted_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
# tc = df[(df.Tropical_Flag==1) & (df.Adjusted_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# # sort by TID and ISOTIME
# tc = tc.sort_values(['ISOTIME'])

# # convert lon to -180-180 from 0-360
# tc['LON'] = ((tc['LON'] + 180) % 360) - 180

# # Northern Hemisphere only
# tc = tc[tc["LAT"] >= 0].copy()

# # hurricane season only
# tc["month"] = tc["ISOTIME"].dt.month
# tc = tc[tc["month"].between(6, 10)].copy()

# # create 5deg lat/lon bins for TC data
# tc["LON_bin"] = np.floor(tc["LON"] / 5) * 5
# tc["LAT_bin"] = np.floor(tc["LAT"] / 5) * 5

# # convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
# tc_points = gpd.GeoDataFrame(
#     tc, 
#     geometry = gpd.points_from_xy(tc.LON, tc.LAT),
#     crs = "EPSG:4326"
# )

# # filter points to North Atlantic
# tc_filtered = gpd.sjoin(
#     tc_points,
#     basins[basins["basin name"] == "N Atlantic"],
#     how = "inner",
#     predicate = "within"
# )

# # filter to columns we need
# tc_filtered = tc_filtered[['TID', 'LON', 'LAT', 'ISOTIME','LON_bin', 'LAT_bin']]

# # create day column to match on day instead of hour since variable data is daily only
# tc_filtered["date"] = pd.to_datetime(tc_filtered["ISOTIME"]).dt.floor("D")

# # print(tc_filtered)

################################################################################################################

# # load variable dataset
# ds1 = xr.open_mfdataset(
#     "datasets/COBE2 SST/daily/*.nc",
#     combine="by_coords",
#     chunks={"time": 30}
# )
# ds2 = xr.open_dataset("datasets/RHUM/post-processing/post_landmask/rhum_600_daily_landmasked.nc")
# ds3 = xr.open_dataset("datasets/u-wind/post_processing/post_landmask/shear_850_200_daily_v2_landmasked.nc")

# # select variable
# sst = ds1["sst"]
# rhum = ds2["rhum"]
# shear = ds3["__xarray_dataarray_variable__"]

# # define the same 5deg bins used for TC data
# lat_edges = np.arange(0, 95, 5)
# lon_edges = np.arange(-110, 25, 5)

# # Convert SST longitude from 0-360 to -180-180
# sst = sst.assign_coords(
#     lon=((sst.lon + 180) % 360) - 180
# )

# # Sort coordinates
# sst = sst.sortby("lat")
# sst = sst.sortby("lon")

# # Restrict SST to the TC study region
# sst = sst.sel(
#     lat=slice(0, 90),
#     lon=slice(-110, 25)
# )

# # Load the smaller SST dataset into memory
# print("Loading SST...")
# sst = sst.load()
# print("SST loaded.")


# # # check
# # test = sst.sel(
# #     time=slice("1981-06-14", "1981-06-15"),
# #     lat=slice(35, 40),
# #     lon=slice(-70, -65)
# # )
# # print(test)
# # print("Valid SST values:", test.notnull().sum().item())




# # Bin SST into 5-degree cells
# sst_binned = sst.groupby_bins(
#     "lat",
#     lat_edges,
#     labels=lat_edges[:-1]
# ).mean()

# sst_binned = sst_binned.groupby_bins(
#     "lon",
#     lon_edges,
#     labels=lon_edges[:-1]
# ).mean()

# # rhum
# rhum_binned = rhum.groupby_bins(
#     "lat",
#     lat_edges,
#     labels=lat_edges[:-1]
# ).mean()
# rhum_binned = rhum_binned.groupby_bins(
#     "lon",
#     lon_edges,
#     labels=lon_edges[:-1]
# ).mean()

# # shear
# shear_binned = shear.groupby_bins(
#     "lat",
#     lat_edges,
#     labels=lat_edges[:-1]
# ).mean()
# shear_binned = shear_binned.groupby_bins(
#     "lon",
#     lon_edges,
#     labels=lon_edges[:-1]
# ).mean()

# # rename to match TC dataframe
# sst_binned = sst_binned.rename({
#     "lat_bins": "LAT_bin",
#     "lon_bins": "LON_bin"
# })
# rhum_binned = rhum_binned.rename({
#     "lat_bins": "LAT_bin",
#     "lon_bins": "LON_bin"
# })
# shear_binned = shear_binned.rename({
#     "lat_bins": "LAT_bin",
#     "lon_bins": "LON_bin"
# })

# # convert variable dataset to a DataFrame
# sst_df = (
#     sst_binned
#     .to_dataframe(name="sst")
#     .reset_index()
# )
# rhum_df = (
#     rhum_binned
#     .to_dataframe(name="rhum")
#     .reset_index()
# )
# shear_df = (
#     shear_binned
#     .to_dataframe(name="shear")
#     .reset_index()
# )

# # make sure variables have day columns
# sst_df["date"] = pd.to_datetime(sst_df["time"]).dt.floor("D")
# rhum_df["date"] = pd.to_datetime(rhum_df["time"]).dt.floor("D")
# shear_df["date"] = pd.to_datetime(shear_df["time"]).dt.floor("D")

# tc_filtered["date"] = pd.to_datetime(
#     tc_filtered["ISOTIME"]
# ).dt.floor("D")

# # merge sst, rhum, and shear onto TC table
# merged = tc_filtered.merge(
#     sst_df[["date", "LAT_bin", "LON_bin", "sst"]],
#     on=["date", "LAT_bin", "LON_bin"],
#     how="left"
# )
# merged = merged.merge(
#     rhum_df[["date", "LAT_bin", "LON_bin", "rhum"]],
#     on=["date", "LAT_bin", "LON_bin"],
#     how="left"
# )
# merged = merged.merge(
#     shear_df[["date", "LAT_bin", "LON_bin", "shear"]],
#     on=["date", "LAT_bin", "LON_bin"],
#     how="left"
# )

# # filter date if syclops and ds don't match
# merged = merged[merged["date"] >= "1981-09-01"]

# # print(merged.head())

# # save merged table to csv
# merged.to_csv("datasets/SyCLoPS/tc_sst+rhum600+shear_merged_table_1981-2025.csv")

###############################################################################################################

# # histogram
# # keep June-October and observations with valid var
# merged_valid = merged[
#     merged["shear"].notna()
# ].copy()

# plt.figure(figsize=(8, 5))

# plt.hist(
#     merged_valid["shear"],
#     bins=20,
#     edgecolor="black",
#     color="orange"
# )

# # TC threshold
# plt.axvline(
#     10,
#     color="gray",
#     linestyle="--",
#     linewidth=2,
#     label="10"
# )

# plt.xlabel("Shear (m/s)")
# plt.ylabel("Number of TC observations")
# plt.title("Shear Distribution Per Tropical Cyclone (1981-2025)")

# plt.tight_layout()
# plt.savefig("images/data_viz/thresholds/tc_shearTH_histogram_syclops_noaa_match.png")
# plt.show()

#################################################################################################################################

# load merged table
ds = pd.read_csv("datasets/SyCLoPS/tc_sst+rhum600+shear_merged_table_1981-2025.csv")

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
points = gpd.GeoDataFrame(
    ds, 
    geometry = gpd.points_from_xy(ds.LON, ds.LAT),
    crs = "EPSG:4326"
)

# print(points)

# filter points to North Atlantic
filtered = gpd.sjoin(
    points,
    basins[basins["basin name"] == "N Atlantic"],
    how = "inner",
    predicate = "within"
)

# drop columns we dont need
filtered = filtered[['TID', 'LON', 'LAT', 'ISOTIME', 'sst', 'rhum', 'shear', 'geometry']]

# join sub basins
sb = gpd.sjoin(
    filtered,
    sub_basins[['sub_basin_name', 'geometry']],
    how='left',
    predicate='intersects'
)

# print(sb)

# # plot histogram per sub basin
# filter out sub basins with low TCs
keep_subbasins = [
    "Caribbean",
    "Central Atlantic",
    "Eastern Tropics",
    "Gulf (A)",
    "Gulf (B)",
    "Northeastern Seaboard",
    "Southeastern Seaboard",
    "Subtropical Atlantic"
]

sb_filtered = sb[
    sb["sub_basin_name"].isin(keep_subbasins)
]

# Get the unique sub-basins
subbasins = sorted(sb_filtered["sub_basin_name"].dropna().unique())

# Create a grid of subplots
n = len(subbasins)
ncols = 3
nrows = int(np.ceil(n / ncols))

fig, axes = plt.subplots(
    nrows=nrows,
    ncols=ncols,
    figsize=(15, 2.5 * nrows),
    sharex=True,
    sharey=True
)

# Make axes easy to loop over
axes = np.atleast_1d(axes).flatten()

# Make one histogram per sub-basin
for ax, subbasin in zip(axes, subbasins):

    data = sb_filtered.loc[
        sb_filtered["sub_basin_name"] == subbasin,
        "shear"
    ].dropna()

    ax.hist(
        data,
        bins=20,
        edgecolor="black",
        color="orange",
        alpha=0.8
    )

    ax.axvline(
        10,
        color="gray",
        linestyle="--",
        linewidth=2,
        label="10 m/s"
    )

    ax.set_title(subbasin)
    ax.set_xlabel("Shear (m/s)")
    ax.set_ylabel("TC Observations")
    ax.grid(alpha=0.2)

# Hide unused subplot(s)
for ax in axes[len(subbasins):]:
    ax.set_visible(False)

plt.suptitle("Shear Distribution Per Tropical Cyclone (1981-2025)")
plt.tight_layout()
plt.savefig("images/data_viz/thresholds/tc_shearTH_histogram_syclops_noaa_match_perSb.png")
plt.show()
