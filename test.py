import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images\region_generation\GPI_mon_mean_anom_moving_window_1deg_iter1.png",
    r"images\region_generation\GPI_mon_mean_anom_moving_window_1deg_iter2.png",
    r"images\region_generation\GPI_mon_mean_anom_moving_window_1deg_iter3.png",
    r"images\region_generation\GPI_mon_mean_anom_moving_window_1deg_iter4.png"
]

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.tight_layout()
plt.savefig("./images/GPI/GPI_mon_mean_anom_moving_window_1deg_iter_grid.png")
plt.show()