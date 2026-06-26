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

# read in ALCC TC output tar file
# with tarfile.open("datasets/ALCC/ALCC_TC_output.tar", "r") as tar:
#     tar.extractall(path="datasets/ALCC/post_processing")

## read in csv files which compiles data and takes third entry from each individual DN file
# nn mode (negative ENSO (El Nino), negative North Pacific mode)
ds_nn = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_nn.001/TC.1_nn.001_SN.csv")
ds_nn.columns = ds_nn.columns.str.strip()
ds_nn['mode'] = 'nn'

# no mode (negative ENSO (El Nino), neutral North Pacific mode)
ds_no = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_no.001/TC.1_no.001_SN.csv")
ds_no.columns = ds_no.columns.str.strip()
ds_no['mode'] = 'no'

# np mode (negative ENSO (El Nino), positive North Pacific mode)
ds_np = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_np.001/TC.1_np.001_SN.csv")
ds_np.columns = ds_np.columns.str.strip()
ds_np['mode'] = 'np'

# on mode (neutral ENSO, negative North Pacific mode)
ds_on = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_on.001/TC.1_on.001_SN.csv")
ds_on.columns = ds_on.columns.str.strip()
ds_on['mode'] = 'on'

# oo mode (neutral ENSO, neutral North Pacific mode)
ds_oo = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_oo.001/TC.1_oo.001_SN.csv")
ds_oo.columns = ds_oo.columns.str.strip()
ds_oo['mode'] = 'oo'

# op mode (neutral ENSO, positive North Pacific mode)
ds_op = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_op.001/TC.1_op.001_SN.csv")
ds_op.columns = ds_op.columns.str.strip()
ds_op['mode'] = 'op'

# pn mode (positive ENSO (La Nina), negative North Pacific mode)
ds_pn = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_pn.001/TC.1_pn.001_SN.csv")
ds_pn.columns = ds_pn.columns.str.strip()
ds_pn['mode'] = 'pn'

# po mode (positive ENSO (La Nina), neutral North Pacific mode)
ds_po = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_po.001/TC.1_po.001_SN.csv")
ds_po.columns = ds_po.columns.str.strip()
ds_po['mode'] = 'po'

# pp mode (positive ENSO (La Nina), positive North Pacific mode)
ds_pp = pd.read_csv("datasets/ALCC/post_processing/ALCC_output/TC.1/001/TC.1_pp.001/TC.1_pp.001_SN.csv")
ds_pp.columns = ds_pp.columns.str.strip()
ds_pp['mode'] = 'pp'

# select mode to easily toggle between datasets
mode = 'pp'

# create a dictionary for the mode datasets
ds_dict = {
    'nn' : ds_nn,
    'no' : ds_no,
    'np' : ds_np,
    'on' : ds_on,
    'oo' : ds_oo,
    'op' : ds_op,
    'pn' : ds_pn,
    'po' : ds_po,
    'pp' : ds_pp,
}
ds = ds_dict[mode]

# find origin node
og = (
    ds
    .groupby('track_id', as_index=False)
    .head(1)
)

# convert lon to 180 scale
og['lon_180'] = ((og['lon'] + 180) % 360) - 180

#print(og)

#####################################################################################################################

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

#####################################################################################################################

# convert LAT and LON to a new column Points which contains (lon, lat) and convert to a geo data frame so we can filter using polygons
og_points = gpd.GeoDataFrame(
    og, 
    geometry = gpd.points_from_xy(og.lon_180, og.lat),
    crs = "EPSG:4326"
)

#print(og_points.shape)

# filter points to North Atlantic
og_filt = gpd.sjoin(
     og_points,
     basins[basins["basin name"] == "N Atlantic"],
     how = "inner",
     predicate = "within"
)

#print(og_filt.shape)

# filter to only columns we need
og_filt = og_filt[['track_id', 'year', 'lon_180', 'lat', 'mode', 'geometry', 'slp', 'wind']]

# print(og_filt.columns)
# #print(tc_track.head())

# join sub basin name for starting and ending points
og_gdf = gpd.GeoDataFrame(
     og_filt,
     geometry=gpd.points_from_xy(
         og_filt.lon_180,
         og_filt.lat
     ),
     crs=sub_basins.crs
)

og_join = gpd.sjoin(
     og_gdf,
     sub_basins[['sub_basin_name', 'geometry']],
     how='left',
     predicate='within'
)

og_filt['sub_basin_start'] = og_join['sub_basin_name']

#print(og_filt)

# save table
og_filt.to_csv(f"datasets/ALCC/post_python_processing/ALCC_tc_output_origins_perYr_wSubbasin_{mode}")

#####################################################################################################################

# plot time series

# pivot to sub basin by year for TC count
piv = og_filt.groupby(['year', 'sub_basin_start']).size().unstack(fill_value=0)

# create a total column
piv['Total'] = piv.sum(axis=1)

#print(piv)

# select sub basin
sb = 'Total'

# scatter plot
ax = piv[sb].plot(
     kind='line',
     marker='o',
     figsize=(10, 6)
)

ax.set_xlabel("Year")
ax.set_ylabel("Count of TC Origin Nodes")
ax.set_title(f"Number of TC Origin Nodes (mode {mode}) per Year in North Atlantic ({sb})")
ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

plt.savefig(f"images/data_viz/alcc/tc_origin_nodes_{mode}_{sb}.png")
plt.show()