import sys 
sys.path.insert(0, "./")
import matplotlib.pyplot as plt
from region_funcs import generate_regions
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.mpl.ticker as cticker
import matplotlib.ticker as mticker
import xarray as xr

#time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)

#ds = xr.open_dataset("SST_ltmm_NAtl_subbasins.nc", decode_times=time_coder)
#print(ds)

fpaths = [
    "GPI_mon_mean_anom_moving_window_subbasin_v2.nc"
]

da_region, reconstructed = generate_regions(fpaths, nRegions = 10, nIter = 5)

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
plt.title("GPI Monthly Mean Anomaly in North Atlantic (1960-2015) (10 regions, sub-basin)")
#plt.savefig("./images/region_generation/SST_mon_mean_anom_moving_window_subbasin.png")
plt.show()