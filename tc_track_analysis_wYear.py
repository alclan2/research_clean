import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
from matplotlib.ticker import MaxNLocator
import xarray as xr
import regionmask
import numpy as np

## read in subbasin table with starting and ending nodes
#ds = pd.read_csv(r"datasets/SyCLoPS/tc&td_track_subbasin_table_withYear.csv")
#print(ds.head())

## pivot to sub basin by year for TC count
#tc = ds.groupby(['YEAR_end', 'sub_basin_end']).size().unstack(fill_value=0)

## create a total column
#tc['Total'] = tc.sum(axis=1)

#print(tc.columns)

## select sub basin
#sb = 'Total'

## scatter plot
#ax = tc[sb].plot(
#    kind='line',
#    marker='o',
#    figsize=(10, 6)
#)

#ax.set_xlabel("Year")
#ax.set_ylabel("Count of TC/TD Dissipation Nodes")
#ax.set_title(f"Number of TC/TD Dissipation Nodes per Year in North Atlantic ({sb})")
#ax.yaxis.set_major_locator(MaxNLocator(integer=True))

#plt.savefig(f"images/data_viz/TC+TD_track_dissPerYr_{sb}.png")
#plt.show()

####################################################################################

## density plot

## select sub basin to plot
#sb = 'Total'

## set up 4x4 degree spacing
#lon_min, lon_max = -110, 20
#lat_min, lat_max = 0, 90
#lon_edges = np.arange(lon_min, lon_max + 4, 4)
#lat_edges = np.arange(lat_min, lat_max + 4, 4)

## set up map projection
#fig, ax = plt.subplots(figsize = (10,6), subplot_kw = {"projection": ccrs.PlateCarree()})

##add coastlines & set axis bounds
#ax.coastlines()

## custom colormap so 0 displays as white on the map
#base_cmap = plt.cm.plasma_r
#cmap_colors = base_cmap(np.linspace(0, 1, 256))
#cmap_colors[0] = [1.0, 1.0, 1.0, 1.0]  # white (RGBA)
#plasma_r_zero_white = colors.ListedColormap(cmap_colors)

## define our x and y axes for longitude and latitude
#x = filtered["LON_180"]
#y = filtered["LAT"]

## make the TC density plot
#plt.hist2d(x, y, bins = [lon_edges, lat_edges], range = [[lon_min, lon_max], [lat_min, lat_max]], cmap = plasma_r_zero_white, transform = ccrs.PlateCarree())

#ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs = ccrs.PlateCarree())


############################################################################################

# SST overlay



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




# load COBE data set
ds = xr.open_dataset("datasets/COBE2 SST/post-processing/SST_annual_mean_notAnomaly_jun_oct.nc")

#print(ds)

# build sub basin mask
sb = regionmask.Regions(
    outlines=sub_basins.geometry,
    names=sub_basins["sub_basin_name"]
)

# create mask
mask = sb.mask(ds.sst)

# calc sub basin means
#sst_year = (
#    ds.sst
#    .where(ds.time.dt.month.isin([6,7,8,9,10]), drop=True)
#    .groupby("time.year")
#    .mean("time")
#)

# use this line if using the annual mean dataset (not anomaly datasets)
sst_year = ds.sst

sb_mean = (
    sst_year
    .groupby(mask)
    .mean()
    .rename({"mask": "basin"})
    .assign_coords(basin=("basin", sb.names))
)

# plot
sb = "Northeastern Seaboard"
subset = sb_mean.sel(basin=sb)
plt.figure(figsize=(10,4))
plt.plot(subset.year, subset, marker="o", color="green")

#plt.axhline(0, color="black", linewidth=1)
plt.title(f"Average SST (Jun–Oct, 1860-2025) — {sb}")
plt.xlabel("Year")
plt.ylabel("SST (°C)")
plt.savefig(f"images/data_viz/SST_avg_notAnom_subbasin_{sb}.png")
plt.show()
