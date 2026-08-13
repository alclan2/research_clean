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
df = pd.read_csv(f"datasets/ALCC/post_python_processing/{TC}/{TC}_all_counts_density_avg_table.csv")

print(df)

# # filter only oo mode
# df_oo = df[df['mode'] == 'oo'].copy()

# print(df_oo)

# # aggregate density per 5-degree bin
# density = (
#     df_oo.groupby(['lat_bin', 'lon_bin'])['mean_count']
#     .sum()
#     .div(df['year'].nunique())   # average per year
#     .reset_index(name='TCs_per_year')
# )

# # print(density)

# # pivot for heatmap format
# heatmap_data = density.pivot(
#     index='lat_bin',
#     columns='lon_bin',
#     values='TCs_per_year'
# )

# ################################################################################
# # set up sub basins
# # read in NAtl subbasin polygons
# sub_polygons_dict = {}

# with open("tc_subbasins_NAtl_v5_abbreviated.dat", "r") as f:
#     for line in f:
#         line = line.strip()
#         if not line or line.startswith("#"):
#             continue

#         parts = line.split(",")
#         sub_basin_name = parts[0].replace('"', '')
#         n_vertices = int(parts[1])

#         lon_vals = list(map(float, parts[2:2+n_vertices]))
#         lon_vals = [(lon + 180) % 360 - 180 for lon in lon_vals]
#         lat_vals = list(map(float, parts[2+n_vertices:2+2*n_vertices]))

#         coords = list(zip(lon_vals, lat_vals))
#         poly = Polygon(coords)

#         if sub_basin_name not in sub_polygons_dict:
#             sub_polygons_dict[sub_basin_name] = []
#         sub_polygons_dict[sub_basin_name].append(poly)

# # Convert to GeoDataFrame
# sub_basin_records = []

# for name, poly_list in sub_polygons_dict.items():
#     if len(poly_list) == 1:
#         geom = poly_list[0]
#     else:
#         geom = MultiPolygon(poly_list)

#     sub_basin_records.append({
#         "sub_basin_name": name,
#         "geometry": geom
#     })

# sub_basins = gpd.GeoDataFrame(sub_basin_records, crs="EPSG:4326",geometry="geometry")

# # fix invalid polygons
# sub_basins["geometry"] = sub_basins["geometry"].buffer(0)

# # remove empty geometries
# sub_basins = sub_basins[~sub_basins.geometry.is_empty]

# # longitude conversion
# import shapely.ops
# def shift_lon(geom):
#     return shapely.ops.transform(
#         lambda x, y: (((x + 180) % 360) - 180, y),
#         geom
#     )

# # shift lon
# sub_basins["geometry"] = sub_basins["geometry"].apply(shift_lon)

# ###############################################################################

# # calc density for the other 8 modes
# modes = df['mode'].unique()

# # number of years
# n_years = df['year'].nunique()

# def calculate_density(data):
#     density = (
#         data.groupby(['lat_bin', 'lon_bin'])['mean_count']
#         .sum()
#         .div(n_years)
#         .reset_index(name='TCs_per_year')
#     )

#     return density.pivot(
#         index='lat_bin',
#         columns='lon_bin',
#         values='TCs_per_year'
#     ).fillna(0)

# # calculate all mode density maps
# density_maps = {}

# for mode in modes:
#     df_mode = df[df['mode'] == mode]
#     density_maps[mode] = calculate_density(df_mode)


# # reference oo density
# oo_density = density_maps['oo']

# # calc anomalies relative to oo
# anomaly_maps = {}
# for mode in modes:
#     if mode != 'oo':
        
#         # force same lat/lon grid as oo
#         mode_density = density_maps[mode].reindex_like(oo_density).fillna(0)

#         anomaly_maps[mode] = mode_density - oo_density

# # plot anomalies
# density_cmap = plt.cm.plasma_r

# anom_cmap = plt.cm.RdBu

# # make symmetric anomaly scale
# max_anom = max(
#     abs(np.nanmin([x.values.min() for x in anomaly_maps.values()])),
#     abs(np.nanmax([x.values.max() for x in anomaly_maps.values()]))
# )

# anom_norm = colors.TwoSlopeNorm(
#     vmin=-max_anom,
#     vcenter=0,
#     vmax=max_anom
# )

# # for mode, data in anomaly_maps.items():
# #     print(mode, data.shape, np.nanmin(data.values), np.nanmax(data.values))

# # plot grid
# fig, axes = plt.subplots(
#     3, 3,
#     figsize=(14, 8),
#     subplot_kw={"projection": ccrs.PlateCarree()}
# )

# axes = axes.flatten()

# plot_order = [
#     'np', 'op', 'pp',
#     'no', 'oo', 'po',
#     'nn', 'on', 'pn'
# ]

# density_mesh = None
# anom_mesh = None

# for i, (ax, mode) in enumerate(zip(axes, plot_order)):

#     # map extent and coastlines

#     ax.set_extent([-100, 15, 0, 70], crs=ccrs.PlateCarree())
#     ax.coastlines(linewidth=0.8)

#     # axis labels

#     if i % 3 == 0:
#         ax.set_yticks(
#             [0, 15, 40, 60],
#             crs=ccrs.PlateCarree()
#         )
#         ax.yaxis.set_major_formatter(
#             cticker.LatitudeFormatter()
#         )
#     else:
#         ax.set_yticks([])

#     if i >= 6:
#         ax.set_xticks(
#             [-100, -80, -60, -40, -20, 0, 15],
#             crs=ccrs.PlateCarree()
#         )
#         ax.xaxis.set_major_formatter(
#             cticker.LongitudeFormatter()
#         )
#     else:
#         ax.set_xticks([])

#     # plot density and anomaly

#     if mode == 'oo':

#         data = oo_density

#         density_mesh = ax.pcolormesh(
#             data.columns,
#             data.index,
#             data.values,
#             cmap=density_cmap,
#             shading='auto',
#             transform=ccrs.PlateCarree(),
#             zorder=1
#         )

#         ax.set_title("oo", fontweight = 'bold')

#     else:

#         data = anomaly_maps[mode]

#         anom_mesh = ax.pcolormesh(
#             data.columns,
#             data.index,
#             data.values,
#             cmap=anom_cmap,
#             norm=anom_norm,
#             shading='auto',
#             transform=ccrs.PlateCarree(),
#             zorder=1
#         )

#         ax.set_title(f"{mode}", fontweight = 'bold')

#     # sub basin overlay

#     for geom in sub_basins.geometry:
#         ax.add_geometries(
#             [geom],
#             crs=ccrs.PlateCarree(),
#             facecolor='none',
#             edgecolor='black',
#             linewidth=1.2,
#             zorder=4
#         )

#         for idx, row in sub_basins.iterrows():
        
#             point = row.geometry.centroid
        
#             label_x = point.x
#             label_y = point.y

#             # Move Arctic label downward
#             if row["sub_basin_name"] == "AC":
#                 label_y -= 5

#             ax.text(
#                 label_x,
#                 label_y,
#                 row["sub_basin_name"],
#                 transform=ccrs.PlateCarree(),
#                 fontsize=6,
#                 weight='bold',
#                 ha='center',
#                 va='center',
#                 color='black',
#                 zorder=6,
#                 path_effects=[
#                     pe.withStroke(
#                         linewidth=2.5,
#                         foreground='white'
#                     )
#                 ]
#             )



# # oo density colorbar
# cax1 = fig.add_axes([0.15, 0.08, 0.3, 0.025])

# cb1 = fig.colorbar(
#     density_mesh,
#     cax=cax1,
#     orientation='horizontal'
# )

# cb1.set_label("TC Density")


# # anomaly colorbar
# cax2 = fig.add_axes([0.55, 0.08, 0.3, 0.025])

# cb2 = fig.colorbar(
#     anom_mesh,
#     cax=cax2,
#     orientation='horizontal'
# )

# cb2.set_label("Density anomaly (reference mode oo)")


# fig.subplots_adjust(
#     left=0.05,
#     right=0.95,
#     bottom=0.15,   # reserve space for colorbars
#     top=0.90,
#     wspace=0.08,
#     hspace=0.12
# )

# fig.suptitle(
#     f"TC Density Anomalies ({TC})",
#     fontsize=16,
#     y=0.98
# )

# # plt.tight_layout()
# plt.savefig(f"images/data_viz/alcc/{TC}/runs_averaged/{TC}_density_anomaly_grid.png")
# plt.show()

# ##############################################################################################

# # # coordinates
# # lons = heatmap_data.columns.values
# # lats = heatmap_data.index.values
# # values = heatmap_data.values

# # # custom colormap
# # base_cmap = plt.cm.plasma_r
# # cmap_colors = base_cmap(np.linspace(0, 1, 256))
# # cmap_colors[0] = [1, 1, 1, 1]  # zero = white
# # custom_cmap = colors.ListedColormap(cmap_colors)

# # # map plot
# # fig, ax = plt.subplots(
# #     figsize=(10, 6),
# #     subplot_kw={"projection": ccrs.PlateCarree()}
# # )

# # # North Atlantic bounds
# # ax.set_extent([-100, 20, 0, 70], crs=ccrs.PlateCarree())

# # ax.coastlines()

# # mesh = ax.pcolormesh(
# #     lons,
# #     lats,
# #     values,
# #     cmap=custom_cmap,
# #     shading='auto',
# #     transform=ccrs.PlateCarree()
# # )

# # cbar = plt.colorbar(mesh, ax=ax, orientation='vertical')
# # cbar.set_label('oo-mode TCs per year')

# # # ax.set_xlabel('Longitude')
# # # ax.set_ylabel('Latitude')

# # plt.show()