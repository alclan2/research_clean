import numpy as np
import pandas as pd
import cartopy.crs as ccrs
import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon, Point
from shapely.ops import transform
import matplotlib.colors as colors
import matplotlib.pyplot as plt
import xarray as xr

# load variable datasets
vort = xr.open_dataset("datasets/GPI/GPI_EN_calc/abs_vort_850_monthly.nc")
vmax = xr.open_dataset("datasets/potential_intensity/pi_output.nc")
rhum = xr.open_dataset("datasets/GPI/GPI_EN_calc/rhum_600_monthly.nc")
shear = xr.open_dataset("datasets/GPI/GPI_EN_calc/shear_850_200_monthly_v2.nc")

vort = vort["__xarray_dataarray_variable__"]
vmax = vmax["vmax"]
rhum = rhum["rhum"]
shear = shear["__xarray_dataarray_variable__"]

# print(vmax.min().values)
# print(vmax.max().values)

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

gpi_clim = gpi.mean("time")

gpi_clim.plot(
    cmap="viridis",
    robust=True,
    figsize=(10,5)
)

plt.show()