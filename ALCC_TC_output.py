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
with tarfile.open("datasets/ALCC/ALCC_TC_output.tar", "r") as tar:
    print(tar.getnames())