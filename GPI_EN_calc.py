import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import xarray as xr
import matplotlib.ticker as mtick

# load variable datasets
vort = xr.open_dataset("datasets/GPI/GPI_EN_calc/abs_vort_850_monthly.nc")
vmax = xr.open_dataset("datasets/potential_intensity/pi_output.nc")
rhum = xr.open_dataset("datasets/GPI/GPI_EN_calc/rhum_600_monthly.nc")
shear = xr.open_dataset("datasets/GPI/GPI_EN_calc/shear_850_200_monthly_v2.nc")

vort = vort["__xarray_dataarray_variable__"]
vmax = vmax["vmax"]
rhum = rhum["rhum"]
shear = shear["__xarray_dataarray_variable__"]

# print(rhum.min().values)
# print(rhum.max().values)

# filter date ranges so they all match
vort, vmax, rhum, shear = xr.align(
    vort,
    vmax,
    rhum,
    shear,
    join="inner"
)

# calc GPI using Emanual and Nolan model
# first term
a = (np.abs((10**5)*vort)) ** (3/2)

# second term
b = (rhum/50)**3

# third term
c = (vmax/70)**3

# fourth term
d = (1 + (0.1*shear))**(-2)

# calc GPI
gpi = a * b * c * d

# change attributes before saving
gpi.attrs["long_name"] = "Genesis Potential Index"
gpi.attrs["standard_name"] = "genesis_potential_index"
gpi.attrs["units"] = "1"
gpi.attrs["description"] = (
    "Genesis Potential Index from Emanuel and Nolan (2004) model"
)
gpi.attrs["references"] = "Emanuel and Nolan (2004)"
gpi.attrs["cell_methods"] = "time: monthly means"
gpi.name = 'gpi'

# remove inherited attributes that no longer apply
for attr in [
    "GRIB_id",
    "GRIB_name",
    "level_desc",
    "dataset",
    "parent_stat",
    "statistic",
    "actual_range",
    "valid_range",
]:
    gpi.attrs.pop(attr, None)

# # print(gpi)

# # # save to net cdf
# # gpi.to_netcdf("datasets/GPI/GPI_EN_calc/GPI_EN_output.nc")

######################################################################################################

# # plot spatial map
# gpi_clim = gpi.mean("time")

# gpi_clim.plot(
#     cmap="viridis",
#     robust=True,
#     figsize=(10,5)
# )

# plt.show()

######################################################################################################

# plot timeseries of GPI per sub basin
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

# convert to data frame
gpi_df = gpi.to_dataframe().reset_index()

# print(gpi_df)

# add points column to join sub basins
points = gpd.GeoDataFrame(
    gpi_df,
    geometry=gpd.points_from_xy(
        gpi_df.lon,
        gpi_df.lat
    ),
    crs="EPSG:4326"
)

# spatial join
gpi_sb = gpd.sjoin(
    points,
    sub_basins[["sub_basin_name", "geometry"]],
    how="left",
    predicate="covered_by"
)

# add year column
gpi_sb["year"] = gpi_sb["time"].dt.year

# drop NaNs
gpi_sb = gpi_sb.dropna(subset=["sub_basin_name"])

# filter columns
gpi_sb = gpi_sb[['time', 'lat', 'lon', 'gpi', 'sub_basin_name', 'year']]

# find annual average per subbasin
gpi_annual = (
    gpi_sb.groupby(["year", "sub_basin_name"])["gpi"]
      .mean()
      .reset_index()
)

print(gpi_annual)

# # select sub basin
# sb = 'Northern Europe'

# df_plot = gpi_annual[gpi_annual["sub_basin_name"] == sb]

# # print(df_plot)

# plt.figure(figsize=(10, 5))
# plt.plot(df_plot["year"], df_plot["gpi"], marker="o", color = "orange")
# plt.gca().yaxis.set_major_formatter(mtick.FormatStrFormatter('%.2f'))

# plt.title(f"Genesis Potential Index in North Atlantic - {sb}")
# plt.xlabel("Year")
# plt.ylabel("GPI")

# plt.tight_layout()
# # plt.savefig(f"images/data_viz/GPI/GPI_EN_timeseries_{sb}.png")
# # plt.show()

