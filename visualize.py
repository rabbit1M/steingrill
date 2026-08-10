"""Visualisierung des Grillplans: Vorderansicht und Draufsicht."""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from steingrill import BRICK_H, HALF_BRICK_L, BRICK_L, WALL

GRATE_TH = 8
BRICK_LW = 1.5
GRATE_LW = 2.0
# Schematische Rostlage in der Vorderansicht (Anteil der Wandhöhe),
# da die Montagehöhe über Schienen später festgelegt wird.
GRATE_POS_FRACTION = 0.4

BRICK_FACE = "#c96a4a"
BRICK_EDGE = "#5a2d1a"
GRATE_COLOR = "#333333"


def stones_along(a: int, b: int, joint: float, start: float = 0.0, course_b: bool = False):
    if course_b:
        lens = [HALF_BRICK_L] + [BRICK_L] * a + ([HALF_BRICK_L] if b == 2 else [])
    else:
        lens = [BRICK_L] * a + ([HALF_BRICK_L] if b else [])
    pos = start
    for length in lens:
        yield pos, length
        pos += length + joint


def draw_front(ax, plan) -> None:
    j = plan.joint
    ax.set_aspect("equal")
    ax.set_xlim(0, plan.outer_width)
    ax.set_ylim(-20, plan.height + 20)

    for r in range(plan.rows):
        z0 = r * (BRICK_H + j)
        course_b = r % 2 == 1
        a, b = (plan.back_a_b, plan.back_b_b) if course_b else (plan.back_a, plan.back_b)
        for x0, length in stones_along(a, b, j, course_b=course_b):
            ax.add_patch(Rectangle(
                (x0, z0), length, BRICK_H,
                facecolor=BRICK_FACE, edgecolor=BRICK_EDGE, lw=BRICK_LW))
        for x0 in (0.0, plan.outer_width - WALL):
            ax.add_patch(Rectangle(
                (x0, z0), WALL, BRICK_H,
                facecolor=BRICK_FACE, edgecolor=BRICK_EDGE, lw=BRICK_LW))

    grate_z = GRATE_POS_FRACTION * plan.height - GRATE_TH
    ax.add_patch(Rectangle(
        (WALL, grate_z), plan.inner_width, GRATE_TH,
        facecolor=GRATE_COLOR, edgecolor="black", hatch="//", lw=GRATE_LW))
    ax.set_xlabel("Breite [mm]")
    ax.set_ylabel("Höhe [mm]")
    ax.set_title("Vorderansicht")


def draw_top(ax, plan) -> None:
    j = plan.joint
    ax.set_aspect("equal")
    ax.set_xlim(-20, plan.outer_width + 20)
    ax.set_ylim(-20, plan.outer_depth + 20)

    for x0, length in stones_along(plan.back_a, plan.back_b, j):
        ax.add_patch(Rectangle(
            (x0, plan.inner_depth), length, WALL,
            facecolor=BRICK_FACE, edgecolor=BRICK_EDGE, lw=BRICK_LW))
    for y0, length in stones_along(plan.side_a, plan.side_b, j):
        for x0 in (0.0, plan.outer_width - WALL):
            ax.add_patch(Rectangle(
                (x0, y0), WALL, length,
                facecolor=BRICK_FACE, edgecolor=BRICK_EDGE, lw=BRICK_LW))

    ax.add_patch(Rectangle(
        (WALL + plan.clear, plan.clear),
        plan.grate_width, plan.grate_depth,
        facecolor=GRATE_COLOR, edgecolor="black", hatch="//", lw=GRATE_LW))
    ax.set_xlabel("Breite [mm]")
    ax.set_ylabel("Tiefe [mm]")
    ax.set_title("Draufsicht (oberste Schicht)")


def show_plan(plan, save_path: str | None = None) -> None:
    fig, (ax_front, ax_top) = plt.subplots(1, 2, figsize=(13, 6))
    draw_front(ax_front, plan)
    draw_top(ax_top, plan)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path)
    plt.show()
