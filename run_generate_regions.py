import sys 
sys.path.insert(0, "./")
import matplotlib.pyplot as plt
from region_funcs import generate_regions
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.ticker as cticker
import matplotlib.ticker as mticker
import xarray as xr
import numpy as np


# for subbasin clustering only: clean dataset (i.e. remove sub-basin = -1 first, which are points falling outside subbasin polygons)
#sst_var = "sst"
#sst_ds = xr.open_dataset(r"datasets\COBE2 SST\post-processing\SST_mon_mean_anom_moving_window_subbasin_v2_jun_oct.nc")
#da = sst_ds[sst_var]
# remove points outside subbasins
#da = da.where(sst_ds["sub_basin_id"] != -1)
# Boolean mask for timesteps with at least one valid point
#valid_time_mask = ~da.isnull().all(dim=("lat", "lon"))
# Keep only valid timesteps
#da = da.sel(time=valid_time_mask)
#valid_grid_mask = ~da.isnull().all(dim="time")
#da = da.where(valid_grid_mask)
# save clean version for region generation
#da.to_netcdf(r"datasets\COBE2 SST\post-processing\SST_mon_mean_anom_moving_window_subbasin_v2_jun_oct_cleanForRegGen.nc")

fpaths = [
    "datasets/GPI/post-processing/GPI_mon_mean_anom_moving_window_1deg_aug.nc"
]

da_region, reconstructed = generate_regions(fpaths, nRegions = 6, nIter = 5)

# create map with projection of continents
fig = plt.figure(figsize=(10, 6))
ax = plt.axes(projection=ccrs.PlateCarree())

#da_region.plot()
da_region.plot(
    ax=ax,
    transform=ccrs.PlateCarree(),   # tells cartopy data are lat/lon
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
plt.title("GPI Monthly Mean Anomaly in North Atlantic (August, 1960-2015) (6 regions, 1deg)")
plt.tight_layout()
plt.savefig("images/region_generation/GPI_mon_mean_anom_moving_window_1deg_aug_6reg.png")
plt.show()