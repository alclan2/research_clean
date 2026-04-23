import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images/TC_timeseries/TC_origin_plot_NAtl_subbasins_detailed_v5.png",
    r"images/TC_timeseries/TC_dissipate_plot_NAtl_subbasins_detailed_v5.png"
]

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

#plt.tight_layout()
plt.savefig(r"images/TC_timeseries/TC_orig_vs_diss_plot_NAtl_subbasins_detailed_grid.png")
plt.show()