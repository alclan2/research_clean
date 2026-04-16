import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import xarray as xr
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import cartopy.feature as cfeature

# load SST dataset
ds = xr.open_dataset(r"datasets/COBE2 SST/sst.mon.mean.nc")
sst = ds["sst"]

# read in basin definition file to filter to north atlantic only
polygons_dict = {}

# read in basin definition file
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

# convert basins' lon to -180-180
basins["geometry"] = basins["geometry"].apply(
    lambda geom: transform(
        lambda x, y: (((x + 180) % 360) - 180, y),
        geom
    )
)

# convert lon to -180-180
sst = sst.assign_coords(
    lon=(((sst.lon + 180) % 360) - 180)
).sortby("lon")

# add CRS and spatial dims
sst = sst.rio.write_crs("EPSG:4326")
sst = sst.rio.set_spatial_dims(x_dim="lon", y_dim="lat")

# filter to N Atlantic basin
region = basins[basins["basin name"] == "N Atlantic"]
sst_natl = (sst.rio.clip(region.geometry, region.crs, drop=True))

#print(sst_natl)

# calculate GPI monthly mean
sst_monthly_mean = sst_natl.groupby("time.month").mean(dim="time")

# plot means
sst_monthly_mean.plot(
    col="month",
    col_wrap=4,
    cmap="plasma_r",
    vmin=0,
    vmax=30,  # tweak as needed
    figsize=(12, 8),
    cbar_kwargs={"label": "SST"}
)

# Add a main title
plt.suptitle("Monthly Mean SST in North Atlantic", fontsize=16, y=0.95)
plt.subplots_adjust(top=0.85, right=0.80, hspace=0.3, wspace=0.2)
plt.savefig("images/SST_mon_mean.png")
plt.show()


# check
#print(float(sst_monthly_mean.min()))
#print(float(sst_monthly_mean.max()))
