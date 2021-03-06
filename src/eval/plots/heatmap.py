import json
import numpy as np
import matplotlib
import matplotlib.pyplot as plt

def heatmap(data, row_labels, col_labels, ax=None,
            cbar_kw={}, cbarlabel="", **kwargs):
    """
    Create a heatmap from a numpy array and two lists of labels.

    Parameters
    ----------
    data
        A 2D numpy array of shape (N, M).
    row_labels
        A list or array of length N with the labels for the rows.
    col_labels
        A list or array of length M with the labels for the columns.
    ax
        A `matplotlib.axes.Axes` instance to which the heatmap is plotted.  If
        not provided, use current axes or create a new one.  Optional.
    cbar_kw
        A dictionary with arguments to `matplotlib.Figure.colorbar`.  Optional.
    cbarlabel
        The label for the colorbar.  Optional.
    **kwargs
        All other arguments are forwarded to `imshow`.
    """

    if not ax:
        ax = plt.gca()

    # Plot the heatmap
    im = ax.imshow(data, **kwargs)

    # Create colorbar
    cbar = ax.figure.colorbar(im, ax=ax, **cbar_kw)
    cbar.ax.set_ylabel(cbarlabel, rotation=-90, va="bottom")

    # We want to show all ticks...
    ax.set_xticks(np.arange(data.shape[1]))
    ax.set_yticks(np.arange(data.shape[0]))
    # ... and label them with the respective list entries.
    ax.set_xticklabels(col_labels)
    ax.set_yticklabels(row_labels)

    # Let the horizontal axes labeling appear on top.
    ax.tick_params(top=False, bottom=True,
                   labeltop=False, labelbottom=True)

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=40, ha="right",
             rotation_mode="anchor")

    for tick in ax.get_xticklabels():
        tick.set_fontname("DejaVu Sans")
        tick.set_fontsize(6)
    for tick in ax.get_yticklabels():
        tick.set_fontname("DejaVu Sans")
        tick.set_fontsize(7)

    # Turn spines off and create white grid.
    for edge, spine in ax.spines.items():
        spine.set_visible(False)

    ax.set_xticks(np.arange(data.shape[1]+1)-.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0]+1)-.5, minor=True)
    #ax.grid(which="minor", color="w", linestyle='-', linewidth=3)
    ax.tick_params(which="minor", bottom=False, left=False)

    return im, cbar


def annotate_heatmap(im, data=None, valfmt="{x:.2f}",
                     textcolors=["black", "white"],
                     threshold=None, **textkw):
    """
    A function to annotate a heatmap.

    Parameters
    ----------
    im
        The AxesImage to be labeled.
    data
        Data used to annotate.  If None, the image's data is used.  Optional.
    valfmt
        The format of the annotations inside the heatmap.  This should either
        use the string format method, e.g. "$ {x:.2f}", or be a
        `matplotlib.ticker.Formatter`.  Optional.
    textcolors
        A list or array of two color specifications.  The first is used for
        values below a threshold, the second for those above.  Optional.
    threshold
        Value in data units according to which the colors from textcolors are
        applied.  If None (the default) uses the middle of the colormap as
        separation.  Optional.
    **kwargs
        All other arguments are forwarded to each call to `text` used to create
        the text labels.
    """

    if not isinstance(data, (list, np.ndarray)):
        data = im.get_array()

    # Normalize the threshold to the images color range.
    if threshold is not None:
        threshold = im.norm(threshold)
    else:
        threshold = im.norm(data.max())/2.

    # Set default alignment to center, but allow it to be
    # overwritten by textkw.
    kw = dict(horizontalalignment="center",
              verticalalignment="center")
    kw.update(textkw)

    # Get the formatter in case a string is supplied
    if isinstance(valfmt, str):
        valfmt = matplotlib.ticker.StrMethodFormatter(valfmt)

    # Loop over the data and create a `Text` for each "pixel".
    # Change the text's color depending on the data.
    texts = []
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            kw.update(color=textcolors[int(im.norm(data[i, j]) > threshold)])
            text = im.axes.text(j, i, valfmt(data[i, j], None), **kw)
            texts.append(text)

    return texts

feature_names = None
features_path = './grouped_feature_usages.json'
with open(features_path, 'r') as f:
    data = json.load(f)
    feature_names = sorted([x.strip() for x in data])
    site_names = sorted([x.strip() for x in list(list(data.values())[0].keys())])
    code_coverage = list()
    for feature in feature_names:
        cov_tmp = []
        for site in site_names:
            cov_tmp.append(round(data[feature][site], 2))
        code_coverage.append(cov_tmp)

"""
feature_names = ["Accelerometer", "Execute Command", "Full Screen API",
                 "Gyroscope", "MediaRecorder", "Orientation Sensor",
                 "PDF", "Payment Request", "Selection", 
                 "Synchronous Clipboard", "Video Element",
                 "Web Audio", "Web Authentication", "Web Cryptography",
                 "Web Workers", "WebRTC", "TP_abseil-cpp",
                 "UserMedia/Stream", "TP_libaddressinput", "TP_libphonenumber",
                 "TP_libsrtp", "TP_libvpx", "TP_libyuv", 
                 "TP_lzma_sdk", "TP_opus", "TP_pffft",
                 "TP_usrsctp", "TP_webrtc_overrides", "TP_zlib"]
"""

code_coverage = np.array(code_coverage)
#site_names = [x.encode('ascii').split('.')[0].capitalize() for x in site_names]
site_names = ['Airline', 'Email',  'Financial',  'News', 'Remote_Working',
        'Shopping',  'Social_Media',  'Sports',  'Travel', "Video", "all"]
#feature_names = [x[:10] for x in feature_names]
fig = plt.figure()
ax = fig.gca()
fig.autofmt_xdate(rotation=20)

im, cbar = heatmap(code_coverage, feature_names, site_names, ax=ax,
                   cmap="YlGn", cbarlabel="Code Coverage Rate")

#texts = annotate_heatmap(im, valfmt="{x:.1f} t")

#fig.tight_layout()
#plt.show()
plt.savefig("code-cov-heatmap.pdf")
