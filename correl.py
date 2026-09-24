import pandas as pd
import xarray as xr
import numpy as np

# # load TC origin dataset
# ds = pd.read_csv(r"datasets/SyCLoPS/tc&td_track_subbasin_table_withYear.csv")

# # pivot to sub basin by year for TC count
# tc = ds.groupby(['YEAR_start', 'sub_basin_start']).size().unstack(fill_value=0)

# # load SST yearly average temps dataset
# sst = xr.open_dataset(r"datasets/COBE2 SST/post-processing/SST_mon_mean_anom_full_dataset_clim_jun_oct_wSubbasin.nc")

# print(sstg.head())

# # store correlations for each subbasin in a dictionary
# corrs = {}

#print(tc.columns)

# # run correlation between origin nodes and SST avg for each subbasin
# for sb in tc.columns:
#     tc_sb = tc[sb]

#     sst_sb = (
#         sst['sst']
#     .sel(basin=sb, year=slice(1940,2024))
#     .to_series()
#     )

#     df = pd.concat([tc_sb, sst_sb], axis=1).dropna()
#     corrs[sb] = df.iloc[:, 0].corr(df.iloc[:, 1])

# #print(corrs)

# # convert to a data frame
# corr_df = pd.DataFrame.from_dict(
#     corrs,
#     orient='index',
#     columns=['correlation']
# )

# corr_df.to_csv('datasets/data_viz/sstAnomaly_tcOriginNodes_correl_sb.csv')

# print(corr_df)

####################################################################################################################

# load Gulf SST dataset
sstg = pd.read_csv("datasets/COBE2 SST/post-processing/sst_anom_moving_window_bySubbasin_table.csv")

# print(sstg)

# filter to gulf sub basins
sbs = ["Gulf (A)", "Gulf (B)"]

# filter to sub basins
sstg = sstg[sstg["sub_basin_name"].isin(sbs)]

# drop columns we don't need
sstg = sstg[["year", "mean_anom", "sub_basin_name"]]

# pivot to get sub basins as columns
sstg_wide = sstg.pivot(
    index=["year"], columns="sub_basin_name", values="mean_anom"
).reset_index()

# calculate correlation
correlation_matrix = sstg_wide[["Gulf (A)", "Gulf (B)"]].corr()

# print(correlation_matrix)
