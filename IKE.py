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

# path to the classified dataset
ClassifiedData = r"datasets/SyCLoPS/SyCLoPS_classified_ERA5_1940_2024.parquet"

# open the parquet format file (PyArrow package required)
df = pd.read_parquet(ClassifiedData)

print(df.head())