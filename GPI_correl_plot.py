import xarray as xr
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

# open GPI dataset
ds = xr.open_dataset(r"datasets\GPI\post-processing\GPI_mon_mean_with_year_dim.nc")

gpi = ds["GPI"]

# reorder dimensions
gpi = ds["GPI"].transpose("year", "month", "lat", "lon")

# reduce spatial dimensions
gpi_ts = gpi.mean(dim=["lat", "lon"])

# basin mean time series for one month
#gpi_ts.sel(month=8).plot(marker="o")
#plt.title("August GPI (1950–2025)")
#plt.grid()
#plt.show()

# correlation between months
#data = gpi_ts.values
#corr = np.corrcoef(data.T)
#plt.figure(figsize=(8,6))
#sns.heatmap(corr, annot=True, cmap="coolwarm")
#plt.title("Correlation Between Months (GPI)")
#plt.xlabel("Month")
#plt.ylabel("Month")
#plt.show()

# lag correlation
#june = gpi_ts.sel(month=6)
#aug = gpi_ts.sel(month=8)
#corr = xr.corr(june, aug, dim="year")
#print(corr.values)

# spatial correlation map
## variability in the basin mean
## Red: When basin GPI is high, this location is also high
## Blue: When basin GPI is high, this location is low
## White: Local variability is independent of basin mean
#aug_ts = gpi_ts.sel(month=8)
#aug_map = gpi.sel(month=8)
#corr_map = xr.corr(aug_map, aug_ts, dim="year")
#corr_map.plot(cmap="coolwarm", vmin=-1, vmax=1)
#plt.title("Correlation with Basin-Mean August GPI")
#plt.show()

# year to year variability
## How basin-mean GPI varies across months (seasonality) and across years (interannual variability).
#plt.figure(figsize=(10,6))
#ax = sns.heatmap(gpi_ts, cmap="viridis")
#years = gpi_ts['year'].values
# Set ticks at every year (so grid stays aligned)
#ax.set_yticks(np.arange(len(years)) + 0.5)
# Label only every 10th year
#labels = [str(y) if i % 10 == 0 else "" for i, y in enumerate(years)]
#ax.set_yticklabels(labels)
#plt.title("GPI (Year vs Month)")
#plt.xlabel("Month")
#plt.ylabel("Year")
#plt.savefig("./images/GPI/GPI_mon_mean_timeseries_GPI_vs_month_seasonality.png")
#plt.show()

# strong vs weak years
## active vs. inactive years
## Red (positive values): Higher GPI in strong years; These regions are enhanced during active years
## Blue (negative values): Lower GPI in strong years (or higher in weak years); These regions are suppressed during active years
## Near zero: Little difference between strong and weak years
aug_ts = gpi_ts.sel(month=8)

strong_years = aug_ts.where(aug_ts > aug_ts.mean(), drop=True).year
weak_years = aug_ts.where(aug_ts < aug_ts.mean(), drop=True).year

strong_comp = gpi.sel(year=strong_years, month=8).mean(dim="year")
weak_comp = gpi.sel(year=weak_years, month=8).mean(dim="year")

(strong_comp - weak_comp).plot(cmap="coolwarm")
plt.title("Strong - Weak August GPI")
#plt.savefig("./images/GPI/GPI_mon_mean_timeseries_active_years.png")
plt.show()