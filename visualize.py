"""Visualisierung des Grillplans als echte 3D-Figur.

Die Platzierung jeder Lage stammt aus `steingrill.lay_course`: Die Steine
liegen als ein durchgehender Laeuferverband im 1D-Lauf der U-Form, der an den
beiden Ecken um 90 Grad umknickt. Jeder Stein wird hier in seine 2D-Grundflaeche
(Draufsicht) uebersetzt und dann als 3D-Box mit Hoehe `BRICK_H` gezeichnet.

Eck-Steine, deren 1D-Lauf eine Ecke kreuzt, werden als gebogener (L-foermiger)
Stein dargestellt, der die Ecke umgreift. Gerade Steine werden an den Ecken so
beschnitten, dass sich nie zwei Steine ueberlappen. Aus den so entstehenden
3D-Boxen werden drei orthografische Ansichten gerendert: von vorne, von der
Seite und von oben.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from steingrill import BRICK_H, BRICK_L, BRICK_B, WALL, Plan, Stone

GRATE_TH = 8
BRICK_FACE = "#c96a4a"
BRICK_EDGE = "#5a2d1a"
GRATE_COLOR = "#333333"

# Ansichten: (Hoehenwinkel, Azimut, Titel)
VIEWS = [
    (8, -90, "Vorderansicht"),
    (8, 0, "Seitenansicht"),
    (90, -90, "Draufsicht"),
]


# ---------------------------------------------------------------------------
# 1D-Lauf -> 2D-Grundflaechen (Draufsicht) einer Lage
# ---------------------------------------------------------------------------
def _course_rects(course: list[Stone], plan: Plan) -> list[tuple[float, float, float, float]]:
    """Grundflaechen-Rechtecke (x, y, w, h) aller Steine einer Lage.

    Ursprung vorne links; die Rueckwand liegt hinten (y = inner_depth..outer_depth).
    Der 1D-Lauf folgt der Aussenseite der U-Form:
      - Wand 0 (links):  x in [0, WALL], y waechst von 0 nach side_len
      - Wand 1 (hinten): y in [inner_depth, outer_depth], x waechst von 0 nach back_len
      - Wand 2 (rechts): x in [outer_width-WALL, outer_width], y faellt nach 0

    Ein Stein, dessen Lauf eine Ecke kreuzt (pos < Ecke, naechstes Zentrum an
    der Ecke), wird als L-foermiger Eck-Stein gezeichnet und besitzt die
    Eckflaeche. Gerade Steine werden an den Ecken so beschnitten, dass sich
    nie zwei Steine ueberlappen.
    """
    e1 = plan.side_len
    e2 = plan.side_len + plan.back_len
    total = 2 * plan.side_len + plan.back_len
    ow = plan.outer_width
    iw = plan.inner_depth
    bl = plan.back_len

    def _wrapper(corner: float) -> Stone | None:
        best: Stone | None = None
        best_gap = float("inf")
        for st in course:
            if st.pos < corner:
                gap = abs(st.pos + st.length / 2 - corner)
                if gap < best_gap:
                    best, best_gap = st, gap
        return best

    wrap_c1 = _wrapper(e1)
    wrap_c2 = _wrapper(e2)

    rects: list[tuple[float, float, float, float]] = []
    for st in course:
        s, e = st.pos, st.pos + st.length
        if st is wrap_c1:
            # Eck-Stein an Ecke 1: laeuft an der linken Wand bis zur Ecke
            # und knickt in die Rueckwand um.
            rects.append((0.0, min(s, iw), float(WALL), e1 - min(s, iw)))
            if e > e1:
                rects.append((0.0, iw, e - e1, float(WALL)))
            continue
        if st is wrap_c2:
            # Eck-Stein an Ecke 2: laeuft an der Rueckwand bis zur Ecke und
            # knickt in die rechte Seitenwand um.
            rects.append((min(s - e1, ow - WALL), iw, bl - min(s - e1, ow - WALL), float(WALL)))
            if e > e2:
                rects.append((ow - WALL, total - e, float(WALL), e - e2))
            continue
        if st.wall == 0:
            y1 = min(e, iw)
            if y1 > s:
                rects.append((0.0, s, float(WALL), y1 - s))
        elif st.wall == 1:
            # Rueckwand: die Eckflaechen (x<WALL und x>ow-WALL) gehoeren den
            # Eck-Steinen, daher an beiden Enden bescheiden.
            x0 = max(s - e1, float(WALL))
            x1 = min(e - e1, ow - WALL)
            if x1 > x0:
                rects.append((x0, iw, x1 - x0, float(WALL)))
        else:
            y0 = total - e
            y1 = min(total - s, iw)
            if y1 > y0:
                rects.append((ow - WALL, y0, float(WALL), y1 - y0))
    return rects


# ---------------------------------------------------------------------------
# 3D-Boxen fuer den gesamten Plan
# ---------------------------------------------------------------------------
def _plan_boxes(plan: Plan) -> list[tuple[float, float, float, float, float, float]]:
    """Alle Steine des Plans als 3D-Boxen (x, y, z, w, h, d)."""
    boxes: list[tuple[float, float, float, float, float, float]] = []
    for r in range(plan.rows):
        course = plan.course_b if r % 2 == 1 else plan.course_a
        z0 = r * (BRICK_H + plan.joint)
        for (x0, y0, w, h) in _course_rects(course, plan):
            boxes.append((x0, y0, z0, w, h, BRICK_H))
    return boxes


# ---------------------------------------------------------------------------
# Rendern einer 3D-Box
# ---------------------------------------------------------------------------
def _box_faces(x: float, y: float, z: float, w: float, h: float, d: float):
    """Liefert die sechs Seitenflaechen einer Box als Listen von Ecken."""
    pts = [
        (x, y, z), (x, y, z + d), (x + w, y, z + d), (x + w, y, z),       # y=y
        (x, y, z), (x, y + h, z), (x + w, y + h, z), (x + w, y, z),       # z=z
    ]
    faces = [
        [pts[0], pts[1], pts[2], pts[3]],  # vorne  (y = y)
        [pts[4], pts[5], pts[6], pts[7]],  # unten  (z = z)
        [(x, y + h, z), (x, y + h, z + d), (x + w, y + h, z + d), (x + w, y + h, z)],  # hinten
        [(x, y, z), (x, y + h, z), (x, y + h, z + d), (x, y, z + d)],     # links
        [(x + w, y, z), (x + w, y + h, z), (x + w, y + h, z + d), (x + w, y, z + d)],  # rechts
        [(x, y, z + d), (x, y + h, z + d), (x + w, y + h, z + d), (x + w, y, z + d)],  # oben
    ]
    return faces


def _plot_boxes(ax, boxes: list) -> None:
    for (x0, y0, z0, w, h, d) in boxes:
        faces = _box_faces(x0, y0, z0, w, h, d)
        col = Poly3DCollection(faces, facecolor=BRICK_FACE, edgecolor=BRICK_EDGE, lw=0.4)
        ax.add_collection3d(col)


def _set_axes_equal(ax) -> None:
    x_lims = ax.get_xlim3d()
    y_lims = ax.get_ylim3d()
    z_lims = ax.get_zlim3d()
    xr = x_lims[1] - x_lims[0]
    yr = y_lims[1] - y_lims[0]
    zr = z_lims[1] - z_lims[0]
    m = max(xr, yr, zr)
    mid = (
        (x_lims[0] + x_lims[1]) / 2,
        (y_lims[0] + y_lims[1]) / 2,
        (z_lims[0] + z_lims[1]) / 2,
    )
    ax.set_xlim3d(mid[0] - m / 2, mid[0] + m / 2)
    ax.set_ylim3d(mid[1] - m / 2, mid[1] + m / 2)
    ax.set_zlim3d(mid[2] - m / 2, mid[2] + m / 2)


def show_plan(plan: Plan, save_path: str | None = None) -> None:
    boxes = _plan_boxes(plan)

    fig = plt.figure(figsize=(19, 6))
    for i, (elev, azim, title) in enumerate(VIEWS, start=1):
        ax = fig.add_subplot(1, 3, i, projection="3d")
        _plot_boxes(ax, boxes)
        ax.set_xlim3d(-20, plan.outer_width + 20)
        ax.set_ylim3d(-20, plan.outer_depth + 20)
        ax.set_zlim3d(-20, plan.height + 20)
        ax.view_init(elev=elev, azim=azim)
        ax.set_title(title)
        ax.set_xlabel("Breite")
        ax.set_ylabel("Tiefe")
        ax.set_zlabel("Hoehe")
        _set_axes_equal(ax)

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path)
    plt.show()
