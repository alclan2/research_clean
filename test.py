import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images/region_generation/GPI_mon_mean_anom_moving_window_1deg_aug_3reg.png",
    r"images/region_generation/GPI_mon_mean_anom_moving_window_1deg_aug_4reg.png",
    r"images/region_generation/GPI_mon_mean_anom_moving_window_1deg_aug_5reg.png",
    r"images/region_generation/GPI_mon_mean_anom_moving_window_1deg_aug_6reg.png",
    r"images/region_generation/SST_mon_mean_anom_moving_window_1deg_aug_3reg.png",
    r"images/region_generation/SST_mon_mean_anom_moving_window_1deg_aug_4reg.png",
    r"images/region_generation/SST_mon_mean_anom_moving_window_1deg_aug_5reg.png",
    r"images/region_generation/SST_mon_mean_anom_moving_window_1deg_aug_6reg.png",
]

fig, axes = plt.subplots(2, 4, figsize=(12, 6))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.tight_layout()
plt.savefig(r"images/region_generation/SSTvsGPI_mon_mean_anom_moving_window_1deg_aug_3_6reg_grid.png")
plt.show()