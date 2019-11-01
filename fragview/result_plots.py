from os import path
import pandas
import seaborn as sns
import matplotlib
# explicitly set non-interactive backend for plotting
# to avoid potentional problems with default picked
# interactive backends, that may try to create GUI widgets
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa


def _make_isas_plot(rst, unq, png_file):
    plt.figure(figsize=(30, 10), dpi=150)

    ax = sns.lineplot(x="dataset", y="ISa", data=rst, ci="sd", label="ISa", color="#82be00")
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    ax.set_xlabel("Dataset")
    ax.set_ylabel("ISa")
    ax.set_xticklabels(unq)

    plt.savefig(png_file, bbox_inches="tight")


def _make_rfactors_plot(rst, unq, png_file):
    plt.figure(figsize=(30, 10), dpi=150)

    sns.lineplot(x="dataset", y="r_free", data=rst, ci=66,  label="Rfree", color="#82be00")
    ax = sns.lineplot(x="dataset", y="r_work", data=rst, ci=66,  label="Rwork", color="#fea901")
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    ax.set_xlabel("Dataset")
    ax.set_ylabel("Rfactor")
    ax.set_xticklabels(unq)

    plt.savefig(png_file, bbox_inches="tight")


def _make_cellparameters_plot(rst, unq, png_file):
    plt.figure(figsize=(30, 10), dpi=150)

    sns.lineplot(x="dataset", y="a", data=rst, ci="sd", label="a")
    sns.lineplot(x="dataset", y="b", data=rst, ci="sd", label="b")
    sns.lineplot(x="dataset", y="c", data=rst, ci="sd", label="c")
    sns.lineplot(x="dataset", y="alpha", data=rst, ci="sd", label="alpha")
    sns.lineplot(x="dataset", y="beta", data=rst, ci="sd", label="beta")

    ax = sns.lineplot(x="dataset", y="gamma", data=rst, ci="sd", label="gamma")
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)

    ax.set_xlabel("Dataset")
    ax.set_ylabel("Cell Parameter")
    ax.set_xticklabels(unq)

    plt.savefig(png_file, bbox_inches="tight")


def _make_resolutions_plot(rst, unq, png_file):
    plt.figure(figsize=(30, 10), dpi=150)

    ax = sns.lineplot(x="dataset", y="resolution", data=rst, ci="sd", label="Resolution", color="#82be00")
    for tick in ax.get_xticklabels():
        tick.set_rotation(90)
    ax.set_xlabel("Dataset")
    ax.set_ylabel("Resolution")
    ax.set_xticklabels(unq)

    plt.savefig(png_file, bbox_inches="tight")


def generate(results_file, dest_dir):
    rst = pandas.read_csv(results_file)
    unq = []

    [unq.append(x) for x in sorted([x.split("-")[-1] for x in rst["dataset"]]) if x not in unq]

    sns.set(color_codes=True)
    sns.set_style("darkgrid", {"axes.facecolor": ".9"})

    _make_isas_plot(rst, unq, path.join(dest_dir, "ISas.png"))
    _make_rfactors_plot(rst, unq, path.join(dest_dir, "Rfactors.png"))
    _make_cellparameters_plot(rst, unq, path.join(dest_dir, "Cellparameters.png"))
    _make_resolutions_plot(rst, unq, path.join(dest_dir, "Resolutions.png"))
