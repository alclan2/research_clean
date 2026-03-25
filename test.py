import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_3reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_4reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_5reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_6reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_7reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_8reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_9reg.png",
    r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_10reg.png",
]

fig, axes = plt.subplots(2, 4, figsize=(12, 6))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.tight_layout()
plt.savefig(r"images\region_generation\SST\Jun-Oct\Grid\SST_mon_mean_anom_moving_window_1deg_jun_oct_grid.png")
plt.show()