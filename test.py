import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images/data_viz/TC+TD_track_originPerYr_SubTrop.png",
    r"images/data_viz/SST_avg_notAnom_subbasin_Subtropical Atlantic.png"
]

fig, axes = plt.subplots(1, 2, figsize=(12, 6))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

#plt.tight_layout()
plt.savefig(r"images/data_viz/TC+TD_track_originPerYr_SubTrop_wSSTAvg.png")
plt.show()