import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# File paths
files = [
    r"images/data_viz/alcc/tc_origin_nodes_np_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_op_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_pp_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_no_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_oo_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_po_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_nn_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_on_Western Africa_v2.png",
    r"images/data_viz/alcc/tc_origin_nodes_pn_Western Africa_v2.png",
]

fig, axes = plt.subplots(3, 3, figsize=(10, 6))
axes = axes.flatten()

labels = ['np', 'op', 'pp', 'no', 'oo', 'po', 'nn', 'on', 'pn']

for label, (ax, file) in zip(labels, zip(axes, files)):
    img = mpimg.imread(file)
    ax.imshow(img)
    ax.axis("off")

    # add label box (bottom-left)
    ax.text(
        0.14, 0.148, label,
        transform=ax.transAxes,
        fontsize=8,
        color="black",
        bbox=dict(
            boxstyle="square,pad=0.2",
            facecolor="white",
            alpha=0.7,
            edgecolor="black",
            linewidth=0.5
        )
    )

# add row and column labels
row_labels = ["EOF2 Positive", "EOF2 Neutral", "EOF2 Negative"]
col_labels = ["EOF1 Negative", "EOF1 Neutral", "EOF1 Positive"]

for i, col in enumerate(col_labels):
    fig.text(
        0.2 + i * 0.32,   # x position (adjust if needed)
        0.90,             # y position (top)
        col,
        ha="center",
        va="center",
        fontsize=10
    )

for i, row in enumerate(row_labels):
    fig.text(
        0.05,             # x position (left margin)
        0.75 - i * 0.30,  # y position (adjust spacing)
        row,
        ha="center",
        va="center",
        rotation=90,
        fontsize=10
    )

plt.subplots_adjust(left=0.03, right=1, top=0.90, bottom=0, wspace=0, hspace=0)
fig.suptitle("TC Origin Nodes in North Atlantic (Western Africa)", fontsize=14)

#plt.tight_layout()
#plt.savefig(r"images/data_viz/alcc/tc_origin_nodes_grid_Western Africa.png")
plt.show()