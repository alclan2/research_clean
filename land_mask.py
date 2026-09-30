import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
import matplotlib.patheffects as pe
import statsmodels.formula.api as smf
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

# load variable dataset
ds = xr.open_mfdataset(
    "datasets/v-wind/*.nc",
    combine = "by_coords",
    preprocess=lambda ds: ds.drop_vars("time_bnds", errors="ignore"),
)

# load land mask
land_ds = xr.open_dataset(
    "https://psl.noaa.gov/thredds/dodsC/Datasets/ncep.reanalysis2/surface/land.nc"
)

# check that the grids between landmask and ds match
assert ds.lat.equals(land_ds.lat), "Latitude grids do not match!"
assert ds.lon.equals(land_ds.lon), "Longitude grids do not match!"

# Get the land mask
land_mask = land_ds["land"].isel(time=0) > 0.5

# Convert land mask to ocean mask
ocean_mask = ~land_mask

# Mask variable keep ocean, set land to NaN
ds_ocean = ds["vwnd"].where(ocean_mask)

ds_ocean = ds_ocean.chunk({
    "time": 100,
    "level": 1,
    "lat": 73,
    "lon": 144
})

# save file
ds_ocean.to_netcdf("datasets/v-wind/post_processing/vwnd_1979-2025_landmasked.nc")

print(ds_ocean)

# check plot
ds_ocean.isel(
    time=0,
    level=0
).plot(
    figsize=(12, 6)
)

plt.show()
