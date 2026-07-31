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
import xarray as xr
import glob
from tcpyPI import pi

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

#######################################################################################

# load input variables
sst_ds = xr.open_dataset("datasets/potential_intensity/input/sst_mean_1979-2025.nc")
msl_ds = xr.open_dataset("datasets/potential_intensity/input/mslp_mean_1979-2025.nc")
t_ds = xr.open_dataset("datasets/potential_intensity/input/air_temp_mean_1979-2025.nc")
r_ds = xr.open_dataset("datasets/potential_intensity/input/mixing_ratio_mean_1979-2025.nc")

# DataArrays
sst = sst_ds["sst"]
msl = msl_ds["mslp"]
t   = t_ds["air"]
r   = r_ds["__xarray_dataarray_variable__"]

# pressure coordinate
p = t["p"]

# update units
t.attrs["units"] = "degC"

# convert mslp from Pa to hPa
msl = msl / 100
msl.attrs["units"] = "hPa"

# interpolate sst grid to match other variable grids (1deg to 2.5deg)
sst = sst.interp(
    lat=t.lat,
    lon=t.lon,
    method="linear"
)

# align datasets
sst, msl, t, r = xr.align(
    sst,
    msl,
    t,
    r,
    join="inner"
)

# # filter to only points over the ocean
# valid = (
#     (sst > 26) &
#     np.isfinite(sst) &
#     np.isfinite(msl)
# )

# sst = sst.where(valid)
# msl = msl.where(valid)
# t = t.where(valid)
# r = r.where(valid)

# run pi.py
result = xr.apply_ufunc(
    pi,
    sst,
    msl,
    p,
    t,
    r,
    kwargs=dict(
        CKCD=0.9,
        ascent_flag=0,
        diss_flag=1,
        ptop=50,
        miss_handle=1,
    ),
    input_core_dims=[
        [],
        [],
        ["p"],
        ["p"],
        ["p"],
    ],
    output_core_dims=[
        [], [], [], [], []
    ],
    output_dtypes=[
        float, float, int, float, float
    ],
    vectorize=True,
    dask="parallelized",
)

vmax, pmin, ifl, t0, otl = result

pi_ds = xr.Dataset(
    {
        "vmax": vmax,
        "pmin": pmin,
        "ifl": ifl,
        "t0": t0,
        "otl": otl,
    }
)

# print(pi_ds)

# save to csv
pi_ds.to_netcdf("datasets/potential_intensity/pi_output.nc")

#######################################################################################

# # plot

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

# # avg PI across hurricane season across all years
# vmax_mean = pi_ds["vmax"].mean(dim="time", skipna=True)
# vmax_mean.plot(
#     ax=ax,
#     transform=ccrs.PlateCarree(),
#     cmap="plasma_r",
#     cbar_kwargs={"label": "Potential Intensity (m/s)"}
# )

# # coastlines
# ax.coastlines(resolution="10m", linewidth=0.8)

# # North Atlantic extent
# ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=ccrs.PlateCarree())

# # Set tick marks every 10 degrees
# ax.set_xticks(np.arange(lon_min, lon_max, 10), crs=ccrs.PlateCarree())
# ax.set_yticks(np.arange(lat_min, lat_max, 10), crs=ccrs.PlateCarree())

# # add labels
# ax.set_xlabel("Longitude")
# ax.set_ylabel("Latitude")

# ax.set_title(f"TC Mean Potential Intensity in North Atlantic (1979-2025)")

# plt.savefig("images/data_viz/potential_intensity/PI_NAtl.png")
# plt.show()