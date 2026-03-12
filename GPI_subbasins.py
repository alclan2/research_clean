import xarray as xr

ds = xr.open_dataset(r"datasets\GPI\GPI_ERA5_1950_2025_combined.nc")

print(ds)

print(ds.lat.min().values, ds.lat.max().values)
print(ds.lon.min().values, ds.lon.max().values)

print(len(ds.year))
print(ds.year.values[:5])
print(ds.year.values[-5:])

print(ds.Ig.dims)