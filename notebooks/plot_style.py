"""Reelvana matplotlib theme.

Mirrors the dashboard's Plotly styling so notebook figures look like the same
visual family. Designed for inclusion in the written report (PDF, vector) and
PPT slides (PNG, 300dpi).
"""
import os

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

# ─── Brand colors ──────────────────────────────────────────────────────────
BG_PRIMARY   = "#0A0E1A"
BG_PANEL     = "#111827"
TEXT_PRIMARY = "#F5F7FA"
TEXT_SEC     = "#8B949E"
TEXT_MUTED   = "#4B5563"
GRID         = "#2A2F3E"
SPINE        = "#3A3F4E"

# ─── Palettes ──────────────────────────────────────────────────────────────
# Categorical: 8 high-contrast colors (mirrors dashboard PALETTE)
REELVANA_PALETTE = [
    "#00D4AA",  # teal      (primary / Trends accent)
    "#FF8B00",  # orange    (Financials accent)
    "#6554C0",  # purple    (Audience accent)
    "#00B8D9",  # cyan
    "#FF5630",  # red
    "#36B37E",  # green
    "#FFC400",  # yellow
    "#DE350B",  # crimson
]

# Sequential: dark-to-teal (heatmap with capped scale)
REELVANA_SEQUENTIAL = LinearSegmentedColormap.from_list(
    "reelvana_seq",
    [(0.0, BG_PRIMARY), (0.5, "#1A6960"), (1.0, "#00D4AA")],
)

# Diverging: red ↔ dark ↔ teal (correlation matrix, [-1, 1])
REELVANA_DIVERGING = LinearSegmentedColormap.from_list(
    "reelvana_div",
    [(0.0, "#FF5630"), (0.5, BG_PRIMARY), (1.0, "#00D4AA")],
)


def apply_reelvana_style():
    """Set global matplotlib rcParams for the Reelvana dark theme."""
    mpl.rcParams.update({
        # Figure backgrounds
        "figure.facecolor": BG_PRIMARY,
        "axes.facecolor": BG_PRIMARY,
        "savefig.facecolor": BG_PRIMARY,
        "savefig.edgecolor": BG_PRIMARY,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",

        # Text colors
        "text.color": TEXT_PRIMARY,
        "axes.labelcolor": TEXT_SEC,
        "xtick.color": TEXT_MUTED,
        "ytick.color": TEXT_MUTED,
        "axes.titlecolor": TEXT_PRIMARY,

        # Title / labels
        "axes.titleweight": "bold",
        "axes.titlesize": 15,
        "axes.titlepad": 14,
        "axes.labelsize": 11,
        "axes.labelweight": "normal",

        # Spines: hide top/right, dim left/bottom
        "axes.edgecolor": SPINE,
        "axes.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": True,
        "axes.spines.bottom": True,

        # Grid
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": GRID,
        "grid.linewidth": 0.6,
        "grid.alpha": 0.5,

        # Ticks
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "xtick.minor.size": 2,
        "ytick.minor.size": 2,
        "xtick.major.width": 0.6,
        "ytick.major.width": 0.6,

        # Legend
        "legend.fontsize": 10,
        "legend.frameon": False,
        "legend.labelcolor": TEXT_SEC,

        # Lines
        "lines.linewidth": 2.2,
        "lines.markersize": 7,

        # Font: Inter preferred, fall back to Windows/Linux defaults
        "font.family": ["Inter", "Segoe UI", "DejaVu Sans", "sans-serif"],
        "font.size": 11,

        # Color cycle
        "axes.prop_cycle": mpl.cycler(color=REELVANA_PALETTE),
    })


def save_figure(fig, name, figures_dir="figures"):
    """Save a figure as both 300dpi PNG (for PPT) and PDF (vector for report)."""
    os.makedirs(figures_dir, exist_ok=True)
    fig.savefig(os.path.join(figures_dir, f"{name}.png"), dpi=300, bbox_inches="tight",
                facecolor=BG_PRIMARY)
    fig.savefig(os.path.join(figures_dir, f"{name}.pdf"), bbox_inches="tight",
                facecolor=BG_PRIMARY)


def add_titles(fig, title, subtitle=None):
    """Render figure-level title + subtitle at the top, left-aligned.

    Use this in place of `ax.set_title()` — it places title and subtitle
    cleanly above the axes without colliding with chart annotations.
    """
    fig.suptitle(title, x=0.015, y=0.985, ha="left", fontsize=15,
                 fontweight="bold", color=TEXT_PRIMARY)
    if subtitle:
        fig.text(0.015, 0.94, subtitle, fontsize=10,
                 color=TEXT_MUTED, ha="left", va="top")


def add_source(fig, source="Source: TMDB + MovieLens · films released ≤ July 2017"):
    """Add a tiny gray source attribution at the bottom-right of the figure."""
    fig.text(0.99, 0.01, source, fontsize=8, color=TEXT_MUTED,
             ha="right", va="bottom", style="italic")
