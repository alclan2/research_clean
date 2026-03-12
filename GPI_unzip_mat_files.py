import tarfile
import os
from scipy.io import loadmat
import numpy as np
import xarray as xr
import glob
import re

# unzip the files
#tar_path = r"datasets\GPI\GPI_ERA5_1950_2025.tar.gz"
#extract_path = r"datasets\GPI\GPI_ERA_1950_2025_unzipped"

#with tarfile.open(tar_path, "r:gz") as tar:
#    tar.extractall(path=extract_path, filter="data")

#print("Extraction complete")

# check what was extracted
#for root, dirs, files in os.walk("datasets/GPI/GPI_ERA_1950_2025_unzipped"):
#    for f in files:
#        print(f)

# load first file in
#mat = loadmat(r"datasets\GPI\GPI_ERA_1950_2025_unzipped\GPI_ERA5_1950.mat")

#Ig = mat["Ig"]
#lat = mat["lat"].flatten()
#lon = mat["lon"].flatten()

#print(Ig.shape)

# convert to xarray dataset
#ds = xr.Dataset(
#    {
#        "Ig": (["lat", "lon", "month"], Ig)
#    },
#    coords={
#        "lat": lat,
#        "lon": lon,
#        "month": np.arange(1, 13)
#    }
#)

#print(ds)

# now import all .mat files
files = sorted(glob.glob(r"datasets\GPI\GPI_ERA_1950_2025_unzipped\*.mat"))

datasets = []

for f in files:
    
    mat = loadmat(f)
    
    Ig = mat["Ig"]
    lat = mat["lat"].flatten()
    lon = mat["lon"].flatten()
    
    ds = xr.Dataset(
        {"Ig": (["lat","lon","month"], Ig)},
        coords={
            "lat": lat,
            "lon": lon,
            "month": np.arange(1,13)
        }
    )
    
    datasets.append(ds)

GPI_ds = xr.concat(datasets, dim="year")

# add year coord
years = [int(re.search(r"\d{4}", os.path.basename(f)).group()) for f in files]

print(years[:10])
print(years[-10:])

GPI_ds = GPI_ds.assign_coords(year=("year", years))

print(len(GPI_ds.year))
print(GPI_ds.year.values[:5])
print(GPI_ds.year.values[-5:])

# save combined to one file
GPI_ds.to_netcdf(r"datasets\GPI\GPI_ERA5_1950_2025_combined.nc")

#print(files[:10])