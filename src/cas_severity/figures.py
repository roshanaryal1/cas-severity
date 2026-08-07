"""Publication figures.

Rendered at 300 dpi in a greyscale-safe palette so that the figures survive
both the Springer print process and monochrome reproduction.
"""

from __future__ import annotations

import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config

logger = logging.getLogger(__name__)

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.titlesize": 10,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.dpi": 300,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
    }
)

INK = "#1a1a1a"
MID = "#6e6e6e"
LIGHT = "#b8b8b8"


def figure_1_forest() -> None:
    """Crude vs adjusted odds ratios for light and weather."""
    ors = pd.read_csv(config.OUTPUTS / "table_2_odds_ratios.csv")
    crude = pd.read_csv(config.OUTPUTS / "table_1_crude.csv")

    adj = ors[
        (ors.model == "M2 adjusted") & ors.label.str.startswith(("Light", "Weather"))
    ].copy()
    adj["level"] = adj["label"].str.split(": ").str[-1]

    order = [
        ("Light", "Overcast"),
        ("Light", "Twilight"),
        ("Light", "Dark"),
        ("Weather", "Light rain"),
        ("Weather", "Heavy rain"),
        ("Weather", "Mist or fog"),
        ("Weather", "Snow or hail"),
    ]

    fig, ax = plt.subplots(figsize=(5.5, 3.6))
    ypos = np.arange(len(order))[::-1]

    for i, (domain, level) in enumerate(order):
        y = ypos[i]
        row = adj[adj.level == level].iloc[0]
        crude_row = crude[crude.level == level].iloc[0]

        ax.plot(
            [crude_row.crude_lo, crude_row.crude_hi],
            [y + 0.17, y + 0.17],
            color=LIGHT,
            lw=1.4,
            solid_capstyle="butt",
        )
        ax.plot(
            crude_row.crude_or, y + 0.17, "o", ms=4.5, color=LIGHT, mec=MID, mew=0.6
        )
        ax.plot(
            [row.or_lo, row.or_hi], [y - 0.17, y - 0.17], color=INK, lw=1.6,
            solid_capstyle="butt",
        )
        ax.plot(row["or"], y - 0.17, "s", ms=4.5, color=INK)

    ax.axvline(1.0, color=MID, ls=(0, (4, 3)), lw=0.8, zorder=0)
    ax.set_yticks(ypos)
    ax.set_yticklabels([f"{lvl}" for _, lvl in order])
    ax.set_xscale("log")
    ax.set_xticks([0.5, 0.7, 1.0, 1.5])
    ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_xlim(0.45, 1.75)
    ax.set_xlabel("Odds ratio for death or serious injury (log scale)")

    ax.axhline(3.5, color=LIGHT, lw=0.6)
    ax.text(0.46, 6.35, "Light condition\n(ref: bright sun)", fontsize=7.5, color=MID,
            va="center", ha="left")
    ax.text(0.46, 2.4, "Weather\n(ref: fine)", fontsize=7.5, color=MID,
            va="center", ha="left")

    handles = [
        plt.Line2D([], [], color=LIGHT, marker="o", mec=MID, ls="-", ms=4.5,
                   label="Crude"),
        plt.Line2D([], [], color=INK, marker="s", ls="-", ms=4.5, label="Adjusted"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=False)
    fig.savefig(config.OUTPUTS / "fig1_forest.png")
    fig.savefig(config.OUTPUTS / "fig1_forest.pdf")
    plt.close(fig)
    logger.info("wrote fig1_forest")


def figure_2_interaction() -> None:
    """Weather odds ratios stratified by speed environment."""
    data = pd.read_csv(config.OUTPUTS / "table_6_weather_by_speed.csv")
    bands = ["<=50 km/h", "60-80 km/h", ">=90 km/h"]
    band_labels = ["\u226450", "60\u201380", "\u226590"]
    weathers = ["Light rain", "Heavy rain", "Mist or fog"]
    markers = ["o", "s", "^"]
    offsets = [-0.19, 0.0, 0.19]

    fig, ax = plt.subplots(figsize=(5.5, 3.3))
    x = np.arange(len(bands), dtype=float)

    for weather, marker, offset, shade in zip(
        weathers, markers, offsets, [INK, MID, LIGHT]
    ):
        block = data[data.weather == weather].set_index("speed_environment")
        block = block.reindex(bands)
        xs = x + offset
        ax.errorbar(
            xs,
            block["or"],
            yerr=[block["or"] - block["or_lo"], block["or_hi"] - block["or"]],
            fmt=marker,
            ms=5,
            lw=1.3,
            capsize=2.5,
            color=shade,
            mec=INK,
            mew=0.6,
            label=weather,
        )
        ax.plot(xs, block["or"], color=shade, lw=0.9, alpha=0.6, zorder=0)

    ax.axhline(1.0, color=MID, ls=(0, (4, 3)), lw=0.8, zorder=0)
    ax.set_xticks(x)
    ax.set_xticklabels(band_labels)
    ax.set_xlabel("Posted speed environment (km/h)")
    ax.set_ylabel("Odds ratio vs fine weather")
    ax.set_yscale("log")
    ax.set_yticks([0.6, 0.8, 1.0, 1.3])
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
    ax.set_ylim(0.55, 1.5)
    ax.legend(frameon=False, loc="upper right", ncol=3, columnspacing=1.0)
    fig.savefig(config.OUTPUTS / "fig2_weather_by_speed.png")
    fig.savefig(config.OUTPUTS / "fig2_weather_by_speed.pdf")
    plt.close(fig)
    logger.info("wrote fig2_weather_by_speed")


def figure_3_calibration() -> None:
    """Decile calibration for the adjusted model."""
    cal = pd.read_csv(config.OUTPUTS / "table_4_calibration_m2.csv")
    fig, ax = plt.subplots(figsize=(3.5, 3.5))
    lim = [0, max(cal.predicted.max(), cal.observed.max()) * 1.12]
    ax.plot(lim, lim, color=MID, ls=(0, (4, 3)), lw=0.8)
    ax.plot(cal.predicted, cal.observed, "o-", color=INK, ms=4.5, lw=1.0)
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed DSI proportion")
    ax.set_aspect("equal")
    fig.savefig(config.OUTPUTS / "fig3_calibration.png")
    fig.savefig(config.OUTPUTS / "fig3_calibration.pdf")
    plt.close(fig)
    logger.info("wrote fig3_calibration")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)-7s %(message)s"
    )
    config.ensure_dirs()
    figure_1_forest()
    figure_2_interaction()
    figure_3_calibration()
    figure_4_dag()
    print("Figures written to", config.OUTPUTS)



def figure_4_dag() -> None:
    """Causal diagram showing the conditioning point that defines the estimand.

    Deliberately minimal. The boxed node is the selection event: the analysis
    is conditional on it. Because it is a common effect of the environmental
    exposure and of unmeasured severity determinants, conditioning on it opens
    a non-causal association between them (dashed).
    """
    import matplotlib.patches as mpatches

    fig, ax = plt.subplots(figsize=(5.6, 3.1))
    ax.set_xlim(0, 10.6)
    ax.set_ylim(0, 5.6)
    ax.axis("off")

    W = (1.55, 4.05)
    U = (1.55, 1.15)
    C = (5.45, 2.60)
    S = (9.25, 2.60)

    ax.text(*W, "Weather\nand light", ha="center", va="center", fontsize=8.5)
    ax.text(*U, "Unmeasured severity\ndeterminants", ha="center", va="center",
            fontsize=8.5)
    ax.text(*S, "Injury\nseverity", ha="center", va="center", fontsize=8.5)

    ax.add_patch(
        mpatches.FancyBboxPatch(
            (C[0] - 1.32, C[1] - 0.46), 2.64, 0.92,
            boxstyle="square,pad=0.03", linewidth=1.7,
            edgecolor=INK, facecolor="#ededed", zorder=2,
        )
    )
    ax.text(*C, "Crash occurs\nand is reported", ha="center", va="center",
            fontsize=8.5, zorder=3)

    def link(a, b, rad=0.0, sa=34, sb=34, color=INK, ls="-", style="-|>"):
        ax.annotate("", xy=b, xytext=a, zorder=1,
                    arrowprops=dict(arrowstyle=style, color=color, lw=1.15,
                                    linestyle=ls, shrinkA=sa, shrinkB=sb,
                                    connectionstyle=f"arc3,rad={rad}"))

    link(W, C, sb=46)
    link(U, C, sb=46)
    link(C, S, sa=46)
    link(W, S, rad=-0.30, sb=30)
    link(U, S, rad=0.30, sb=30)
    link(W, U, rad=0.0, sa=26, sb=30, color=MID, ls=(0, (3, 2)), style="<->")

    ax.text(0.62, 2.60, "induced by\nconditioning", fontsize=7, color=MID,
            ha="center", va="center", style="italic", rotation=90)
    ax.text(5.45, 5.15, "Estimand is conditional on the boxed node",
            fontsize=7.5, color=MID, ha="center", style="italic")

    fig.savefig(config.OUTPUTS / "fig4_dag.png")
    fig.savefig(config.OUTPUTS / "fig4_dag.pdf")
    plt.close(fig)
    logger.info("wrote fig4_dag")


if __name__ == "__main__":
    main()
