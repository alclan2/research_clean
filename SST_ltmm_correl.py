import xarray as xr
import matplotlib.pyplot as plt
import seaborn as sns
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.ticker as cticker
import matplotlib.ticker as mticker
from region_funcs_SST import generate_regions
import numpy as np

# open the sst dataset with sub-basin mappings
time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)
ds = xr.open_dataset("SST_ltmm_NAtl_subbasins.nc", decode_times=time_coder)
#print(ds)

# stack spatial grid
sst_stack = ds["sst"].stack(grid=("lat","lon"))
basin_stack = ds["sub_basin_id"].stack(grid=("lat","lon"))

# compute mean SST per basin
sst_region = sst_stack.groupby(basin_stack).mean("grid")

# remove NaN basin
sst_region = sst_region.dropna("sub_basin_id")

# convert back into a grid
sst_for_script = sst_region.rename({"sub_basin_id":"lon"})
sst_for_script = sst_for_script.expand_dims(lat=[0])
sst_for_script.name = "sst"
sst_for_script = sst_for_script.to_dataset()

# save as netcdf file to pass into fpaths
sst_for_script.to_netcdf("SST_ltmm_NAtl_subbasins_for_region_generation.nc")

fpaths = [
    "SST_ltmm_NAtl_subbasins_for_region_generation.nc"
]

da_region, reconstructed = generate_regions(fpaths, nRegions = 4, nIter = 10)

# map basin values back to the spatial grid for plotting
cluster_map = xr.full_like(ds["sub_basin_id"], np.nan)

for rid in da_region.lon.values:         # loop over basins
    cluster_val = da_region.sel(lon=rid).item()  # scalar cluster value
    cluster_map = cluster_map.where(ds["sub_basin_id"] != rid, cluster_val)


# create map with projection of continents
fig = plt.figure(figsize=(10, 6))
ax = plt.axes(projection=ccrs.PlateCarree())

#da_region.plot()
cluster_map.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),
    cmap="viridis",
    add_colorbar=True
)

# add axis labels
gl = ax.gridlines(
    crs=ccrs.PlateCarree(),
    draw_labels=True,
    linewidth=0.8,
    color='gray',
    alpha=0,
)

# keep labels only on left and bottom
gl.top_labels = False
gl.right_labels = False
gl.xlocator = mticker.MultipleLocator(20)
gl.ylocator = mticker.MultipleLocator(10)

# add continents and coastlines
ax.coastlines()

# format and save
plt.title("SST Long Term Monthly Mean in North Atlantic (1991-2020) (4 regions, sub-basin)")
plt.savefig("./images/region_generation/SST_ltmm_NAtlantic_4regions_subbasin.png")
plt.show()