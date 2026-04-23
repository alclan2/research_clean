import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images/reg_gen_w_subbasin/detailed subbasins/GPI/GPI_mon_mean_anom_moving_window_1deg_lateszn_10reg_with_subbasins_detailed_v3.png",
    r"images/reg_gen_w_subbasin/detailed subbasins/SST/SST_mon_mean_anom_moving_window_1deg_lateszn_10reg_with_subbasins_detailed_v3.png"
]

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

#plt.tight_layout()
plt.savefig(r"images/reg_gen_w_subbasin/detailed subbasins/SSTvsGPI_mon_mean_anom_moving_window_1deg_lateszn_10reg_subbasins_detailed_grid.png")
plt.show()