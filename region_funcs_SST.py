import xarray as xr

time_coder = xr.coders.CFDatetimeCoder(use_cftime=True)

def open_and_normalize_datasets(
        fpaths: list[str], 
        weights: list[float] = None, 
        start_year = None, 
        end_year = None
    ): 
    import xarray as xr

    """ 
    Normalizes and concatonates input datasets
    Works with 12-month climatology datasets (no anomaly needed).
    """

    variable_names = []
    da_arr = []
    da_raw_arr = []
    

    for fpath in fpaths: 
        ds = xr.open_dataset(fpath, decode_times=time_coder)
        latname = [coord for coord in ds.coords if "lat" in coord or "latitude" in coord]
        lonname = [coord for coord in ds.coords if "lon" in coord or "longitude" in coord]

        try: 
            latname = latname[0]
        except Exception as e: 
            print("Latitude coordinate not found in dataset")
            break

        try: 
            lonname = lonname[0]
        except Exception as e: 
            print("Latitude coordinate not found in dataset")
            break

        ds = ds.transpose("time", latname , lonname, ...)
        #ds = ds.isel(time = ds.time.dt.year.isin(range(start_year, end_year + 1)))
        varname = list(ds.data_vars)[0]
        variable_names.append(varname)
        da = ds['sst']
        da_raw_arr.append(da)

        # Assign month numbers 1-12 (since dataset is monthly mean climatology)
        da = da.assign_coords(month=("time", range(1, da.sizes['time'] + 1)))

        # Skip anomaly computation (mean over months would be zero)
        da_anom = da  # keep raw values for clustering

        # Flatten the DataArray for clustering: (time, lat*lon)
        #da_arr_flat = da_anom.values.reshape(da.sizes['time'], -1)

        # Convert back to DataArray for xr.concat
        #da_arr_da = xr.DataArray(
        #    da_arr_flat,
        #    dims=("time", "space"),
        #    coords={"time": da.month}
        #)

        da_arr.append(da_anom)

        #da_anom = da.groupby("time.month") - da.groupby("time.month").mean()
        #da_anom_std = (da_anom - da_anom.mean(dim = "time"))/(da_anom.std(dim = "time"))
        #da_arr.append(da_anom_std)

    if weights: 
        if len(weights) != len(da_arr): 
            raise ValueError("Must provide same number of weights as datasets")
        da_arr = [da*w for da, w in zip(da_arr, weights)]
    
    # concat along time
    da_std = xr.concat(da_arr, dim = "time")
    da_raw = xr.concat(da_raw_arr, dim = "time")
    
    print(f"Concatenated {len(da_arr)} datasets, {variable_names}")
    return da_raw, da_std

def slope_intercept(y, x, dim = "time"): 
    import xarray as xr

    y, x = xr.align(y, x, join = "inner")

    x_mean = x.mean(dim)
    y_mean = y.mean(dim)

    x_anom = x - x_mean
    y_anom = y - y_mean

    var_x  = (x_anom**2).mean(dim)
    cov_xy = (x_anom * y_anom).mean(dim)
    slope = cov_xy / var_x
    intercept = y_mean - slope*x_mean

    return slope, intercept

def get_corr_from_given_points(da_anom, points): 
    import xarray as xr

    da_anom = da_anom.transpose("time", "lat", "lon")

    time_mean = da_anom.mean(dim = "time")
    time_std = da_anom.std(dim = "time")
    da_std = (da_anom - time_mean)/time_std
    corr_arr = []
    out_points = []

    for point in points: 
        rlat, rlon = point
        ref_ts = da_std.sel(lat = rlat, lon = rlon, method = "nearest")
        corr = (da_std * ref_ts).mean(dim = "time")
        corr_arr.append(corr)
        lat_nearest = float(ref_ts["lat"].values)
        lon_nearest = float(ref_ts["lon"].values)
        out_points.append((lat_nearest, lon_nearest))

    return out_points, xr.concat(corr_arr, dim = "point")


def get_starting_points(da_anom, numRegions, init_point = None): 
    import random 
    import numpy as np
    import xarray as xr

    da_anom = da_anom.transpose("time", "lat", "lon")

    # da_anom = da.groupby("time.month") - da.groupby("time.month").mean()
    
    feature_points = []
    corr_arr = []

    mask = np.isfinite(da_anom).all(axis = 0)

    iy, ix = np.where(mask.values)
    k = np.random.randint(0, iy.size)
    lat_idx = iy[k]
    lon_idx = ix[k]

    time_mean = da_anom.mean(dim = "time")
    time_std = da_anom.std(dim = "time")

    da_std = (da_anom - time_mean)/time_std

    if init_point is None: 
        lat0 = da_anom["lat"].values[lat_idx]
        lon0 = da_anom["lon"].values[lon_idx]
    
    else:
        lat0_init, lon0_init = init_point
        lat0 = da_anom.sel(lat = lat0_init, lon = lon0_init, method = "nearest")["lat"].values
        lon0 = da_anom.sel(lat = lat0_init, lon = lon0_init, method = "nearest")["lon"].values

        print(lat0)
        print(lon0)
        
    feature_points.append((lat0, lon0))
    ref_ts = da_std.sel(lat=lat0, lon=lon0)
    corr = (da_std * ref_ts).mean(dim="time")
    # return corr
    
    corr_arr.append(corr)
    da_corr_max = corr.copy()  # running max over "point"

    for region in range(1, numRegions): 
        min_index = da_corr_max.argmin()
        
        i_lat = min_index // corr.sizes["lon"]
        i_lon = min_index % corr.sizes["lon"]

        next_lat = float(da_anom.isel(lat = i_lat, lon = i_lon).lat.values)
        next_lon = float(da_anom.isel(lat = i_lat, lon = i_lon).lon.values)

        feature_points.append((next_lat, next_lon))

        ref_ts = da_std.sel(lat = next_lat, lon = next_lon)
        corr = (da_std * ref_ts).mean(dim = "time")
        # corr = xr.corr(da_anom, da_anom.sel(lat = region_lat, lon = region_lon), dim = "time")
        corr_arr.append(corr)
        # da_corr_max = xr.concat(corr_arr, dim="point").max("point")
        da_corr_max = xr.ufuncs.maximum(da_corr_max, corr)

    #last_lat, last_lon = feature_points[-1]
    #corr = xr.corr(da_anom, da_anom.sel(lat = last_lat, lon = last_lon), dim = "time")

    #corr_arr.append(corr)

    da_corr = xr.concat(corr_arr, dim = "point")
    print('points created')

    return feature_points, da_corr
    
def get_regions_from_points(da_corr): 
    import numpy as np
    da_corr = da_corr.assign_coords(point=np.arange(da_corr.sizes["point"]))
    return da_corr.idxmax(dim="point")

def get_mean_point(da_region, da_anom, numRegions): 

    closest_points = []
    time_mean = da_anom.mean(dim = "time")
    time_std = da_anom.std(dim = "time")

    da_std = (da_anom - time_mean)/time_std

    for region in range(numRegions): 
        mask = da_region == region

        da_anom_region = da_anom.where(mask)
        mean_timeseries = da_anom_region.mean(dim = ["lat", "lon"], skipna = True)
        mean_ts_std = (mean_timeseries - mean_timeseries.mean("time")) / mean_timeseries.std("time")
        opt_func = (da_std * mean_ts_std).mean(dim = "time")

        min_idx = opt_func.argmax(dim = ("lat", "lon"))
        closest_lat = opt_func["lat"].values[min_idx["lat"]]
        closest_lon = opt_func["lon"].values[min_idx["lon"]]

        closest_points.append((closest_lat, closest_lon))

    return closest_points

def add_points(da_anom, nPoints, feature_points, da_corr): 
    import random 
    import numpy as np
    import xarray as xr

    feature_points = []

    # mask = np.isfinite(da_anom).all(axis = 0)

    for n in range(0, nPoints): 
        da_corr_max = da_corr.max("point")
        min_index = da_corr_max.argmin()
        i_lat = min_index // da_corr.sizes["lon"]
        i_lon = min_index % da_corr.sizes["lon"]

        next_lat = float(da_anom.isel(lat = i_lat, lon = i_lon).lat.values)
        next_lon = float(da_anom.isel(lat = i_lat, lon = i_lon).lon.values)

        corr_point = xr.corr(da_anom, da_anom.sel(lat = next_lat, lon = next_lon), dim = "time")
        da_corr = xr.concat([da_corr, corr_point], dim = "point")
        feature_points.append((next_lat, next_lon))


    return feature_points, da_corr

def get_corr2(da_anom, points):
    import numpy as np
    import xarray as xr

    da_anom = da_anom.transpose("time", "lat", "lon")

    # standardize
    time_mean = da_anom.mean(dim="time")
    time_std = da_anom.std(dim="time")
    time_std = time_std.where(time_std != 0)  # avoid divide by zero
    da_std = (da_anom - time_mean) / time_std

    lats = np.array([p[0] for p in points])
    lons = np.array([p[1] for p in points])
    n_points = len(points)

    lat_indexer = xr.DataArray(lats, dims="point", coords={"point": np.arange(n_points)})
    lon_indexer = xr.DataArray(lons, dims="point", coords={"point": np.arange(n_points)})

    ref_ts = da_std.sel(lat=lat_indexer, lon=lon_indexer, method="nearest")

    prod = da_std.expand_dims(point=ref_ts.sizes["point"]) * ref_ts # (time, lat, lon, point)

    da_corr = prod.mean(dim="time")

    da_corr = da_corr.transpose("point", "lat", "lon")

    return da_corr

def reconstruct_da(da, region_da, points, numRegions):
    import xarray as xr
    import numpy as np

    ds_out = xr.Dataset(coords = {"lat": da.lat, 
                            "lon": da.lon, 
                            "time": da.time, 
                            "pf": range(numRegions)})

    ds_out["PF"] = xr.DataArray(
        data = np.zeros((numRegions, len(da.time))),
        dims = ["pf", "time"]
    )

    slope_arr = []
    int_arr = []
    clats, clons = zip(*points)
    
    for i, (lat, lon) in enumerate(zip(clats, clons)): 
        region_mask = region_da == i

        da_anom_region = da.where(region_mask)
        t1 = da.sel(lat = lat, lon = lon)
        b,a = slope_intercept(da_anom_region, t1)

        slope_arr.append(b)
        int_arr.append(a)

        ds_out["PF"].loc[dict(pf=i)] = t1

    da_slope = xr.concat(slope_arr, dim = "pf")
    da_intercept = xr.concat(int_arr, dim = "pf")

    ds_out["slope"] = da_slope
    ds_out["intercept"] = da_intercept
    #reconstructed = (ds_out["intercept"] + ds_out["slope"]*ds_out["PF"]).mean(dim = "pf")

    return ds_out

def reconstruct_da_fast(da, region_da, points, numRegions, dim="time"):
    """
    Returns full reconstructed DataArray with same dims/coords as da.
    """
    import numpy as np
    import xarray as xr

    da_llt = da.transpose("lat", "lon", dim)
    reg_ll = region_da.transpose("lat", "lon")

    nlat = da_llt.sizes["lat"]
    nlon = da_llt.sizes["lon"]
    ntime = da_llt.sizes[dim]
    npoint = nlat * nlon

    y = da_llt.data.reshape(npoint, ntime)          # (point, time)
    r = reg_ll.data.reshape(npoint)                 # (point,)
    pts = np.asarray(points, dtype=float)[:numRegions]  # (pf,2)
    PF = da.sel(
        lat=xr.DataArray(pts[:, 0], dims="pf"),
        lon=xr.DataArray(pts[:, 1], dims="pf"),
        method="nearest",
    )
    if PF.dims[0] == dim:
        PF = PF.transpose("pf", dim)
    PFv = PF.data                                   # (pf, time)

    valid = np.isfinite(r) & (r >= 0) & (r < numRegions)
    r_safe = np.where(valid, r, 0).astype(np.int64)       # (point,)
    x = PFv[r_safe, :]                                     # (point, time)
    y = np.where(valid[:, None], y, np.nan)
    x = np.where(valid[:, None], x, np.nan)

    # Regression per point
    x_mean = np.nanmean(x, axis=1, keepdims=True)
    y_mean = np.nanmean(y, axis=1, keepdims=True)

    x_anom = x - x_mean
    y_anom = y - y_mean

    var_x  = np.nanmean(x_anom**2, axis=1)                 # (point,)
    cov_xy = np.nanmean(x_anom * y_anom, axis=1)           # (point,)

    slope = cov_xy / var_x                                  # (point,)
    intercept = (y_mean[:, 0] - slope * x_mean[:, 0])       # (point,)

    recon = intercept[:, None] + slope[:, None] * x         # (point, time)

    recon = np.where(valid[:, None], recon, np.nan)
    recon_llt = recon.reshape(nlat, nlon, ntime)
    slope_llt = slope.reshape(nlat, nlon)
    intercept_llt = intercept.reshape(nlat, nlon)

    recon_ds = xr.Dataset(
        data_vars={
            "reconstructed": xr.DataArray(
                recon_llt,
                dims=("lat", "lon", dim),
                coords={"lat": da_llt["lat"], "lon": da_llt["lon"], dim: da_llt[dim]},
            ),
            "slope": xr.DataArray(
                slope_llt,
                dims=("lat", "lon"),
                coords={"lat": da_llt["lat"], "lon": da_llt["lon"]},
            ),
            "intercept": xr.DataArray(
                intercept_llt,
                dims=("lat", "lon"),
                coords={"lat": da_llt["lat"], "lon": da_llt["lon"]},
            ),
        },
        attrs={"description": "reconstruction and regression parameters"},
    )

    # Return in original da dim order
    return recon_ds.transpose(*da.dims)

def iterateN(da, da_region, da_corr, n):
    # number of current regions
    numRegions = len(da_corr.point)

    for k in range(n): 
        print(f"Iteration: {k}")
        points = get_mean_point(da_region, da, numRegions) # slow 3
        da_corr = get_corr2(da, points) # slow    
        da_region = get_regions_from_points(da_corr) # fast 
    return points, da_region, da_corr


def generate_regions(
        fpaths: list[str],
        nRegions: int, 
        nIter : int, 
        weights: list[float] = None,
        init_point: tuple = None, 
        starting_points: list[tuple] = None, 
        # explicitly set starting points
):      
    import numpy as np 
    import xarray as xr

    """
    Inputs
    - fpaths: list of paths to the input datasets. Paths should point to NetCDF files each containing one variable (time, lat, lon)
    - nRegions: Integer number of regions to group the input data into
    - nInter: Integer number of iterations to run. 
    - weights: List of floats  -> Must be the same length as fpaths. Multiplies respective standardized anomaly datasets by the given weights
    - init_point: tuple (latitude, longitude) Choose a starting point for the iteration rather than choosing a random point
    - starting_points [(latitude, longitude), ...] - List of starting latitude/longitude points. Supercedes starting point creation using minimum correlation method

    Output: 
    - da_region: xr.DataArray (latitude, longitude) -> Original spatial grid, with integer values representing which region that grid point belongs to
    - ds_out: xr.Dataset (point, latitude, longitude, time)
        xr.DataArray -> slope (point, latitude, longitude): LOBF slope between grid point and the the principal feature point within the corresponding region
        xr.DataArray -> intercept (point, latitude, longitude): LOBF intercept between grid point and the the principal feature point within the corresponding region
        xr.DataArray -> PF (point, time): Time series within the original dataset for each principal point within the grouped regions.

    Note: To reconstruct the original dataset using the output, 
        reconstruct_param = (reconstruct_param["intercept"] + reconstruct_param["slope"]*reconstruct_param["PF"]).mean(dim = "pf")
    """

    da_raw, da = open_and_normalize_datasets(fpaths, weights = weights, start_year=1980, end_year = 2014)

    if starting_points is None:
        points, da_corr = get_starting_points(da, nRegions, init_point=init_point)
    else:
        points, da_corr = get_corr_from_given_points(da, starting_points)

    da_region = get_regions_from_points(da_corr)
    points, da_region, da_corr = iterateN(da, da_region, da_corr, nIter)
    reconstruct_param = reconstruct_da(da_raw, da_region, points, nRegions)
    
    return da_region, reconstruct_param


