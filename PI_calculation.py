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
sst_ds = xr.open_dataset("datasets/potential_intensity/input/sst_mean_1979-2025_daily.nc")
msl_ds = xr.open_dataset("datasets/potential_intensity/input/mslp_mean_1979-2025_daily.nc")
t_ds = xr.open_dataset("datasets/potential_intensity/input/air_temp_mean_1979-2025_daily.nc")
r_ds = xr.open_dataset("datasets/potential_intensity/input/mixing_ration_mean_1979-2025_daily.nc")

# DataArrays
sst = sst_ds["sst"]
msl = msl_ds["mslp"]
t   = t_ds["air"]
r   = r_ds["__xarray_dataarray_variable__"]

# pressure coordinate
p = t["p"]

# convert temperature from Kelvin to Celsius
t = t - 273.15
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

# filter to only points over the ocean
# valid = (
#     (sst > 26) &
#     np.isfinite(sst) &
#     np.isfinite(msl)
# )
valid = (
    np.isfinite(sst) &
    np.isfinite(msl)
)

sst = sst.where(valid)
msl = msl.where(valid)
t = t.where(valid)
r = r.where(valid)

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

# # check
# # Find valid SST points in the tropical Northern Hemisphere
# tropical_valid = (
#     np.isfinite(sst.values) &
#     (sst.lat.values[np.newaxis, :, np.newaxis] >= 5) &
#     (sst.lat.values[np.newaxis, :, np.newaxis] <= 25)
# )

# indices = np.argwhere(tropical_valid)
# ti, yi, xi = indices[0]
# sst_test = sst.isel(time=ti, lat=yi, lon=xi).item()
# msl_test = msl.isel(time=ti, lat=yi, lon=xi).item()
# t_test = t.isel(time=ti, lat=yi, lon=xi).values
# r_test = r.isel(time=ti, lat=yi, lon=xi).values

# print("SST:", sst_test)
# print("MSL:", msl_test)
# print("T:", t_test)
# print("R:", r_test)
# test_result = pi(
#     sst_test,
#     msl_test,
#     p.values,
#     t_test,
#     r_test,
#     CKCD=0.9,
#     ascent_flag=0,
#     diss_flag=1,
#     ptop=50,
#     miss_handle=1,
# )
# print("PI RESULT:", test_result)

print("===== VMAX =====")
print("NaNs:", vmax.isnull().sum().item(), "/", vmax.size)
print("Min:", vmax.min(skipna=True).item())
print("Max:", vmax.max(skipna=True).item())
print("Mean:", vmax.mean(skipna=True).item())


# print(pi_ds)

# # save to csv
# pi_ds.to_netcdf("datasets/potential_intensity/pi_output_daily.nc")

# check plot
vmax_mean = vmax.mean(dim="time", skipna=True)
vmax_mean.plot(
    figsize=(12, 5),
    cmap="viridis",
    vmin=0,
    vmax=80
)


plt.title("Maximum Potential Intensity — 1981-09-01")
plt.show()

#######################################################################################

# # load PI dataset
# ds = xr.open_dataset("datasets/potential_intensity/pi_output.nc")

# # print(ds)

# # convert to data frame
# df = ds["vmax"].to_dataframe(name="vmax").reset_index()

# # remove missing PI values (over land)
# df = df.dropna(subset=["vmax"])

# # convert grid cells to points
# gdf = gpd.GeoDataFrame(
#     df,
#     geometry=gpd.points_from_xy(df.lon, df.lat),
#     crs="EPSG:4326",
# )

# # join sub basins
# gdf = gpd.sjoin(
#     gdf,
#     sub_basins[["sub_basin_name", "geometry"]],
#     how="inner",
#     predicate="within",   # or "intersects"
# )

# print(gdf)

# # add year column
# gdf['year'] = gdf['time'].dt.year

# # pivot to time series
# ts = (
#     gdf.groupby(["year", "sub_basin_name"])["vmax"]
#        .mean()
#        .reset_index()
# )

# print(ts)

# save to csv
# ts.to_csv("datasets/potential_intensity/vmax_mean_perYr_perSb.csv")

# # Number of sub-basins
# n = len(ts.columns)

# # Choose grid dimensions
# ncols = 4
# nrows = int(np.ceil(n / ncols))

# fig, axes = plt.subplots(
#     nrows=nrows,
#     ncols=ncols,
#     figsize=(5*ncols, 3.5*nrows),
#     sharex=False,
#     sharey=False
# )

# # Flatten axes array for easy iteration
# axes = axes.flatten()

# for ax, sb in zip(axes, ts.columns):
#     ax.plot(
#         ts.index,
#         ts[sb],
#         marker='o',
#         linestyle='-',
#         markersize=4,
#         alpha=0.7
#     )
#     ax.set_title(sb)
#     ax.grid(alpha=0.3)

# # Remove any unused axes
# for ax in axes[len(ts.columns):]:
#     fig.delaxes(ax)

# fig.supxlabel("Year")
# fig.supylabel("Potential Intensity (m/s)")
# fig.suptitle("Average Potential Intensity by Sub-Basin", fontsize=16)

# plt.tight_layout()
# plt.savefig(f"images/data_viz/potential_intensity/PI_timeseries_grid.png")
# plt.show()

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

# # plt.savefig("images/data_viz/potential_intensity/PI_NAtl.png")
# plt.show()