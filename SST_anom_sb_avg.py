import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
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
from matplotlib.ticker import MaxNLocator
import xarray as xr

# read in anom net cdf
ds = xr.open_dataset("datasets/COBE2 SST/post-processing/SST_mon_mean_anom_moving_window_jun_oct.nc")

print(ds.head())