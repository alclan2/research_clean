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

# read in basin definition file
polygons_dict = {}

# read in basin definition file
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

# convert basins' lon to -180-180
basins["geometry"] = basins["geometry"].apply(
    lambda geom: transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )
)

# read in NAtl subbasin polygons
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

###################################################################################################################

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_v4/SyCLoPS_classified_v4.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

# filter to TCs
# tc = df[(df.Tropical_Flag==1) & ((df.Short_Label=='TC') | (df.Short_Label=='TD')) & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]
tc = df[(df.Tropical_Flag==1) & (df.Short_Label=='TC') & ~(df['Track_Info'].str.contains('QS', case=False, na=False))]

# filter columns to what we need
tc = tc[['LAT', 'LON', 'ISOTIME', 'IKE']]

# convert lon to 180 scale
tc['LON_180'] = ((tc['LON'] + 180) % 360) - 180

# convert points
tc = gpd.GeoDataFrame(
    tc,
    geometry=gpd.points_from_xy(tc['LON_180'], tc['LAT']),
    crs="EPSG:4326"
)

# filter to North Atlantic
region = basins[basins["basin name"] == "N Atlantic"]
tc_filt = gpd.sjoin(
    tc,
    region[['geometry']],
    predicate="within"
)

# create 5deg lat/lon bins
tc_filt["lat_bin"] = np.floor(tc_filt["LAT"] / 5) * 5
tc_filt["lon_bin"] = np.floor(tc_filt["LON_180"] / 5) * 5

# sum IKE across bins
ike_grid = (
    tc_filt
    .groupby(["lat_bin", "lon_bin"])["IKE"]
    .mean()
    .reset_index()
)

# print(type(ike_grid))
# print(ike_grid.head())
# print(ike_grid.columns)

#######################################################################################

# # spatial plot

# # set up figure
# fig = plt.figure(figsize=(10, 6))
# ax = plt.axes(projection=ccrs.PlateCarree())

# # plot sub-basins first
# sub_basins.plot(
#     ax=ax,
#     facecolor='none',
#     edgecolor='black',
#     path_effects=[pe.withStroke(linewidth=3, foreground='white')],
#     linewidth=1.5,
#     transform=ccrs.PlateCarree(),
#     zorder=4
# )

# # set axis bounds
# lon_min = -110
# lon_max = 20
# lat_min = 0
# lat_max = 50

# # add sub-basin labels
# for idx, row in sub_basins.iterrows():
#     point = row.geometry.centroid
#     name = row["sub_basin_name"]

#     # wrap text (adjust width as needed)
#     name_wrapped = "\n".join(textwrap.wrap(name, width=10, break_long_words=False, break_on_hyphens=False))
    
#     if (lon_min <= point.x <= lon_max) and (lat_min <= point.y <= lat_max):
#         txt = ax.text(
#             point.x, point.y,
#             name_wrapped,
#             transform=ccrs.PlateCarree(),
#             fontsize=7,
#             weight='bold',
#             ha='center',
#             va='center',
#             color='black',
#             zorder=4
#         )
        
#         txt.set_path_effects([
#             pe.withStroke(linewidth=3, foreground="white")
#         ])

# # total IKE summed across all years
# # convert dataframe into 2D grid
# ike_plot = ike_grid.pivot(
#     index="lat_bin",
#     columns="lon_bin",
#     values="IKE"
# )

# # define lat/lon edges to make sure the grid aligns
# lat_edges = np.arange(
#     ike_grid["lat_bin"].min(),
#     ike_grid["lat_bin"].max() + 5,
#     5
# )
# lon_edges = np.arange(
#     ike_grid["lon_bin"].min(),
#     ike_grid["lon_bin"].max() + 5,
#     5
# )

# # plot
# mesh = ax.pcolormesh(
#     lon_edges,
#     lat_edges,
#     ike_plot.values,
#     transform=ccrs.PlateCarree(),
#     cmap="viridis_r",
#     shading="auto"
# )

# # color bar
# cbar = plt.colorbar(mesh, ax=ax, pad=0.12, orientation = 'horizontal', shrink = 0.6)
# cbar.set_label("Mean IKE (TJ)")

# # coastlines
# ax.coastlines(resolution="10m", linewidth=0.8)

# # North Atlantic extent
# ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

# # set tick marks every 10 degrees
# ax.set_xticks(np.arange(lon_min, lon_max, 10), crs=ccrs.PlateCarree())
# ax.set_yticks(np.arange(lat_min, lat_max, 10), crs=ccrs.PlateCarree())

# # add labels
# ax.set_xlabel("Longitude")
# ax.set_ylabel("Latitude")

# ax.set_title(f"TC Average Integrated Kinetic Energy in North Atlantic (1979-2022)")

# plt.savefig("images/data_viz/IKE/IKE_mean_spatial.png")
# plt.show()

#######################################################################################

# timeseries

# add year column
tc_filt['year'] = tc_filt['ISOTIME'].dt.year

# print(tc_filt.head())

# trim columns to what we actually need
tc_filt = tc_filt[['year', 'LAT', 'LON_180', 'IKE', 'geometry', 'lat_bin', 'lon_bin']]

# join sub basins
tc_sb = gpd.sjoin(
    tc_filt,
    sub_basins[["sub_basin_name", "geometry"]],
    how="inner",
    predicate="within", 
)

# print(tc_sb)

# sum IKE across years and sub basins
ike_piv = (
    tc_sb
    .groupby(["sub_basin_name", "year"])["IKE"]
    .sum()
    .reset_index()
)

print(ike_piv)

# # save timeseries to csv
# ike_piv.to_csv("datasets/IKE/IKE_mean_timeseries.png")

# plot timeseries of IKE per sub basin
# exclude sub basins with little data
exclude = [
    "Arctic",
    "Mid-latitudinal Atlantic",
    "Mid-latitudinal US/CA"
]

ike_plot = ike_piv[
    ~ike_piv["sub_basin_name"].isin(exclude)
].copy()


# Fill in missing years with zero IKE
years = np.arange(
    ike_plot["year"].min(),
    ike_plot["year"].max() + 1
)

ike_complete = (
    ike_plot
    .set_index(["sub_basin_name", "year"])
    .reindex(
        pd.MultiIndex.from_product(
            [
                ike_plot["sub_basin_name"].unique(),
                years
            ],
            names=["sub_basin_name", "year"]
        )
    )
    .reset_index()
)

ike_complete["IKE"] = ike_complete["IKE"].fillna(0)

# Plot
# get sub basin names
subbasins = ike_complete["sub_basin_name"].unique()

# Choose grid dimensions
ncols = 3
nrows = int(np.ceil(len(subbasins) / ncols))

fig, axes = plt.subplots(
    nrows=nrows,
    ncols=ncols,
    figsize=(14, 3 * nrows),
    sharex=True,
    sharey=True
)

# Make axes easy to iterate over
axes = axes.flatten()

for ax, basin in zip(axes, subbasins):

    # Select this basin
    data = ike_complete[
        ike_complete["sub_basin_name"] == basin
    ].sort_values("year")

    # Plot
    ax.plot(
        data["year"],
        data["IKE"],
        color="purple",
        linewidth=1.5
    )

    ax.set_title(basin)
    ax.grid(alpha=0.3)

    ax.tick_params(
    axis="both",
    which="both",
    labelbottom=True,
    labelleft=True
)

# Remove unused panels
for ax in axes[len(subbasins):]:
    ax.remove()

# Common labels
fig.supxlabel("Year")
fig.supylabel("Accumulated annual IKE (TJ)")

fig.suptitle(
    "Accumulated Annual Integrated Kinetic Energy by Sub-Basin",
    fontsize=16,
    y=0.98
)

plt.tight_layout()
# plt.savefig("images/data_viz/IKE/IKE_accum_timeseries_perSubbasin.png")
plt.show()