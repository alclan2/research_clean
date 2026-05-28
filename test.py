import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images/SST_CtrlAtl_mon_mean_jun.png",
    r"images/SST_CtrlAtl_mon_mean_jul.png",
    r"images/SST_CtrlAtl_mon_mean_aug.png",
    r"images/SST_CtrlAtl_mon_mean_sep.png",
    r"images/SST_CtrlAtl_mon_mean_oct.png"
]

fig, axes = plt.subplots(2, 3, figsize=(12, 6))
axes = axes.flatten()

for ax, file, in zip(axes, files):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")  # hide axes ticks

plt.subplots_adjust(left=0, right=1, top=1, bottom=0, wspace=0, hspace=0)

#plt.tight_layout()
plt.savefig(r"images/SST_CtrlAtl_mon_mean_jun_oct.png")
plt.show()