"""Visualisierung des Grillplans: Vorderansicht (Rueckwand), Seitenansicht
(linke Seitenwand) und Draufsicht (oberste Schicht).

Alle drei Ansichten nutzen die Steinfolge aus `Plan.course_a` / `Plan.course_b`
aus `steingrill.lay_course`, die den U-Lauf als einen durchgehenden Mauerzug im
Laeuferverband auffasst. Eck-Steine (um 90 Grad gedrehte Steine an den Ecken)
werden separat hervorgehoben.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from steingrill import BRICK_H, BRICK_L, BRICK_B, WALL, Plan, Stone

GRATE_TH = 8
BRICK_LW = 1.2
CORNER_LW = 1.8
GRATE_LW = 2.0
GRATE_POS_FRACTION = 0.4

BRICK_FACE = "#c96a4a"
BRICK_EDGE = "#5a2d1a"
CORNER_FACE = "#8c4830"
CORNER_EDGE = "#2a140a"
GRATE_COLOR = "#333333"


def _wall_stones(course, wall: int) -> list[Stone]:
    return [s for s in course if s.wall == wall]


def draw_front(ax, plan: Plan) -> None:
    """Vorderansicht der Rueckwand (Wand 1). x = pos - side_len, so dass die
    Ecke 1 links bei x=0 liegt und Ecke 2 rechts bei x=back_len."""
    j = plan.joint
    ax.set_aspect("equal")
    ax.set_xlim(-20, plan.outer_width + 20)
    ax.set_ylim(-20, plan.height + 20)

    for r in range(plan.rows):
        z0 = r * (BRICK_H + j)
        course = plan.course_b if r % 2 == 1 else plan.course_a
        base = plan.side_len
        for st in _wall_stones(course, wall=1):
            x0 = st.pos - base
            face = CORNER_FACE if st.corner else BRICK_FACE
            edge = CORNER_EDGE if st.corner else BRICK_EDGE
            lw = CORNER_LW if st.corner else BRICK_LW
            ax.add_patch(Rectangle(
                (x0, z0), st.length, BRICK_H,
                facecolor=face, edgecolor=edge, lw=lw))

    grate_z = GRATE_POS_FRACTION * plan.height - GRATE_TH
    ax.add_patch(Rectangle(
        (WALL + plan.clear, grate_z), plan.grate_width, GRATE_TH,
        facecolor=GRATE_COLOR, edgecolor="black", hatch="//", lw=GRATE_LW))
    ax.set_xlabel("Breite [mm]")
    ax.set_ylabel("Hoehe [mm]")
    ax.set_title("Vorderansicht (Rueckwand)")


def draw_side(ax, plan: Plan) -> None:
    """Seitenansicht der linke Seitenwand (Wand 0). x = pos, so dass der
    vordere Anfang links bei x=0 liegt und die Ecke 1 rechts bei x=side_len."""
    j = plan.joint
    ax.set_aspect("equal")
    ax.set_xlim(-20, plan.outer_depth + 20)
    ax.set_ylim(-20, plan.height + 20)

    for r in range(plan.rows):
        z0 = r * (BRICK_H + j)
        course = plan.course_b if r % 2 == 1 else plan.course_a
        for st in _wall_stones(course, wall=0):
            x0 = st.pos
            face = CORNER_FACE if st.corner else BRICK_FACE
            edge = CORNER_EDGE if st.corner else BRICK_EDGE
            lw = CORNER_LW if st.corner else BRICK_LW
            ax.add_patch(Rectangle(
                (x0, z0), st.length, BRICK_H,
                facecolor=face, edgecolor=edge, lw=lw))

    grate_z = GRATE_POS_FRACTION * plan.height - GRATE_TH
    ax.add_patch(Rectangle(
        (plan.clear, grate_z), plan.grate_depth, GRATE_TH,
        facecolor=GRATE_COLOR, edgecolor="black", hatch="//", lw=GRATE_LW))
    ax.set_xlabel("Tiefe [mm]")
    ax.set_ylabel("Hoehe [mm]")
    ax.set_title("Seitenansicht (linke Seitenwand)")


def _wall2rect_top(st: Stone, plan: Plan) -> tuple[float, float, float, float]:
    """Uebersetze einen 1D-Stein des U-Laufs in ein 2D-Rechteck (x, y, w, h)
    der Draufsicht. Ursprung: vorne links; Rueckwand liegt hinten."""
    if st.wall == 0:
        # linke Seitenwand: x = 0..WALL, y = pos..pos+L (vorne->hinten)
        return 0.0, st.pos, float(WALL), st.length
    if st.wall == 1:
        # Rueckwand: y = inner_depth..outer_depth, x = pos-side_len..+L
        x0 = st.pos - plan.side_len
        return x0, plan.inner_depth, st.length, float(WALL)
    if st.wall == 2:
        # rechte Seitenwand: x = outer_width-WALL..outer_width,
        # y = total-end..total-start  (1D-Lauf laeuft von Ecke 2 hinten nach
        # vorne), so dass pos=total-.. ganz vorne liegt
        total = 2 * plan.side_len + plan.back_len
        x0 = plan.outer_width - WALL
        y0 = total - (st.pos + st.length)
        return x0, y0, float(WALL), st.length
    raise ValueError(f"unknown wall {st.wall}")


def draw_top(ax, plan: Plan) -> None:
    ax.set_aspect("equal")
    ax.set_xlim(-20, plan.outer_width + 20)
    ax.set_ylim(-20, plan.outer_depth + 20)

    course = plan.course_a
    for st in course:
        x0, y0, w, h = _wall2rect_top(st, plan)
        face = CORNER_FACE if st.corner else BRICK_FACE
        edge = CORNER_EDGE if st.corner else BRICK_EDGE
        lw = CORNER_LW if st.corner else BRICK_LW
        ax.add_patch(Rectangle(
            (x0, y0), w, h,
            facecolor=face, edgecolor=edge, lw=lw))

    ax.add_patch(Rectangle(
        (WALL + plan.clear, plan.clear),
        plan.grate_width, plan.grate_depth,
        facecolor=GRATE_COLOR, edgecolor="black", hatch="//", lw=GRATE_LW))
    ax.set_xlabel("Breite [mm]")
    ax.set_ylabel("Tiefe [mm]")
    ax.set_title("Draufsicht (Lage A, oberste Schicht)")


def show_plan(plan: Plan, save_path: str | None = None) -> None:
    fig, (ax_front, ax_side, ax_top) = plt.subplots(1, 3, figsize=(18, 6))
    draw_front(ax_front, plan)
    draw_side(ax_side, plan)
    draw_top(ax_top, plan)
    fig.tight_layout()
    if save_path:
        fig.savefig(save_path)
    plt.show()
