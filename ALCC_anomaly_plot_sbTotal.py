import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import xarray as xr
import numpy as np
import tarfile
import matplotlib.colors as colors
import seaborn as sns
import cartopy.mpl.ticker as cticker
import matplotlib.patheffects as pe

# TC version
TC = 'TC.2'

# load dataset
df = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{TC}_all_counts_origins_avg_table.csv")

# filter only oo mode
df_oo = df[df['mode'] == 'oo'].copy()

# sum all 5deg bins within each sub-basin for each year
annual_subbasin = (
    df_oo
    .groupby(['year', 'sub_basin_start'])['mean_count']
    .sum()
    .reset_index(name='annual_TCs')
)

# average the annual sub-basin totals across all years
density = (
    annual_subbasin
    .groupby('sub_basin_start')['annual_TCs']
    .mean()
    .reset_index(name='TCs_per_year')
)

print(df_oo.head())

################################################################################
# set up sub basins
# read in NAtl subbasin polygons
sub_polygons_dict = {}

with open("tc_subbasins_NAtl_v5_abbreviated.dat", "r") as f:
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

# create sub basin map to match anomalies
sub_basin_map = {
    "Deep Tropics": "DT",
    "Caribbean": "CR",
    "Eastern Tropics": "ET",
    "Western Africa": "WA",
    "Gulf (B)": "GB",
    "Gulf (A)": "GA",
    "Southeastern Seaboard": "SESB",
    "Central Atlantic": "CA",
    "Subtropical Atlantic": "SA",
    "Mid-latitudinal US/CA": "MLUC",
    "Northeastern Seaboard": "NESB",
    "Mid-latitudinal Atlantic": "MLA",
    "Mediterranean Sea": "MS",
    "Arctic": "AC",
    "Northern Europe": "NE"
}

# convert from full name to abbreviations
df['sub_basin_start'] = df['sub_basin_start'].map(sub_basin_map)

###############################################################################

# calc density for the other 8 modes
modes = df['mode'].unique()

# number of years
n_years = df['year'].nunique()

def calculate_density(data):

    # sum all 5deg bins within each sub-basin for each year
    annual_subbasin = (
        data
        .groupby(['year', 'sub_basin_start'])['mean_count']
        .sum()
        .reset_index(name='annual_TCs')
    )

    # average the annual sub-basin totals across all years
    density = (
        annual_subbasin
        .groupby('sub_basin_start')['annual_TCs']
        .mean()
        .rename('TCs_per_year')
    )

    return density

# calculate all mode density maps
density_maps = {}

for mode in modes:
    df_mode = df[df['mode'] == mode]
    density_maps[mode] = calculate_density(df_mode)

# reference oo density
oo_density = density_maps['oo']

# print(oo_density)

# calc anomalies relative to oo
anomaly_maps = {}
for mode in modes:
    if mode != 'oo':
        mode_density = density_maps[mode].reindex(oo_density.index).fillna(0)
        anomaly_maps[mode] = mode_density - oo_density

# plot anomalies
density_cmap = plt.cm.plasma_r.copy()
density_cmap.set_under('lightgray')
anom_cmap = plt.cm.RdBu

# make symmetric anomaly scale
max_anom = max(
    abs(np.nanmin([
        x.values.min() for x in anomaly_maps.values()
    ])),
    abs(np.nanmax([
        x.values.max() for x in anomaly_maps.values()
    ]))
)

anom_norm = colors.TwoSlopeNorm(
    vmin=-max_anom,
    vcenter=0,
    vmax=max_anom
)

# density normalization
density_norm = colors.Normalize(
    vmin=1e-10,
    vmax=oo_density.max()
)

# plot grid
fig, axes = plt.subplots(
    3, 3,
    figsize=(14, 8),
    subplot_kw={"projection": ccrs.PlateCarree()}
)

axes = axes.flatten()

plot_order = [
    'np', 'op', 'pp',
    'no', 'oo', 'po',
    'nn', 'on', 'pn'
]

density_mesh = None
anom_mesh = None

for i, (ax, mode) in enumerate(zip(axes, plot_order)):
    # map extent / coastlines
    ax.set_extent(
        [-100, 15, 0, 70],
        crs=ccrs.PlateCarree()
    )

    ax.coastlines(linewidth=0.8)

    # axis labels
    if i % 3 == 0:
        ax.set_yticks(
            [0, 15, 40, 60],
            crs=ccrs.PlateCarree()
        )

        ax.yaxis.set_major_formatter(
            cticker.LatitudeFormatter()
        )
    else:
        ax.set_yticks([])

    if i >= 6:
        ax.set_xticks(
            [-100, -80, -60, -40, -20, 0, 15],
            crs=ccrs.PlateCarree()
        )

        ax.xaxis.set_major_formatter(
            cticker.LongitudeFormatter()
        )
    else:
        ax.set_xticks([])

    # get values for each sub-basin
    if mode == 'oo':
        values = oo_density

        cmap = density_cmap
        norm = density_norm

        ax.set_title(
            "oo",
            fontweight='bold'
        )

    else:
        values = anomaly_maps[mode]

        cmap = anom_cmap
        norm = anom_norm

        ax.set_title(
            f"{mode}",
            fontweight='bold'
        )

    # plot each sub-basin polygon    
    for idx, row in sub_basins.iterrows():

        basin_name = row["sub_basin_name"]

        # get density/anomaly for this basin
        value = values.get(basin_name, np.nan)

        # skip if no value
        if pd.isna(value) or value == 0:
            facecolor = "lightgray"
        else:
            facecolor = cmap(norm(value))

        # fill polygon
        ax.add_geometries(
            [row.geometry],
            crs=ccrs.PlateCarree(),
            facecolor=facecolor,
            edgecolor='black',
            linewidth=1.2,
            zorder=2
        )

        # label sub-basin
        point = row.geometry.centroid

        label_x = point.x
        label_y = point.y

        # move Arctic label downward
        if basin_name == "AC":
            label_y -= 5

        ax.text(
            label_x,
            label_y,
            basin_name,
            transform=ccrs.PlateCarree(),
            fontsize=6,
            weight='bold',
            ha='center',
            va='center',
            color='black',
            zorder=6,
            path_effects=[
                pe.withStroke(
                    linewidth=2.5,
                    foreground='white'
                )
            ]
        )

    # create dummy mappable for colorbars
    if mode == 'oo':
        density_mesh = plt.cm.ScalarMappable(
            norm=density_norm,
            cmap=density_cmap
        )

    else:
        anom_mesh = plt.cm.ScalarMappable(
            norm=anom_norm,
            cmap=anom_cmap
        )

# oo density colorbar
cax1 = fig.add_axes([0.15, 0.08, 0.3, 0.025])

cb1 = fig.colorbar(
    density_mesh,
    cax=cax1,
    orientation='horizontal'
)
cb1.set_label("TC Origin Locations (origin nodes per year)")

# anomaly colorbar
cax2 = fig.add_axes([0.55, 0.08, 0.3, 0.025])

cb2 = fig.colorbar(
    anom_mesh,
    cax=cax2,
    orientation='horizontal'
)
cb2.set_label("Origin node anomaly (reference mode oo)")

fig.subplots_adjust(
    left=0.05,
    right=0.95,
    bottom=0.15, 
    top=0.90,
    wspace=0.08,
    hspace=0.12
)

fig.suptitle(
    f"TC Origin Node Anomalies ({TC})",
    fontsize=16,
    y=0.98
)

# plt.tight_layout()
plt.savefig(f"images/data_viz/alcc/{TC}/runs_averaged/{TC}_origin_anomaly_sbTotal_grid.png")
plt.show()


# for col in ['count_1', 'count_2', 'mean_count']:
#     annual = (
#         df[df['mode'] == 'oo']
#         .groupby('year')[col]
#         .sum()
#     )

#     print(f"\n{col}")
#     print("mean annual:", annual.mean())
#     print("total:", annual.sum())