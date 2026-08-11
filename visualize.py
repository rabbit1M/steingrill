"""Visualisierung des Grillplans als echte 3D-Figur.

Die Platzierung jeder Lage stammt aus `steingrill.lay_course` als wechselnder
Eckverband. Jeder Stein wird als genau ein rechteckiger NF-Stein in die
2D-Grundflaeche (Draufsicht) uebersetzt. Auch ein Eckstein wird nicht in
Teilflaechen zerlegt oder mit einem Nachbarstein ueberlagert.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from steingrill import BRICK_H, WALL, Plan, Stone

GRATE_TH = 8
GRATE_SPACING = 20
BRICK_FACE = "#c96a4a"
BRICK_EDGE = "#5a2d1a"
GRATE_COLOR = "#333333"

# Eine schräge Ansicht: (Hoehenwinkel, Azimut, Titel).
# Azimut -45 liegt 45 Grad zwischen Vorderansicht (-90) und Seitenansicht (0).
VIEWS = [
    (45, -45, "Schraege Ansicht"),
]


# ---------------------------------------------------------------------------
# 1D-Lauf -> 2D-Grundflaechen (Draufsicht) einer Lage
# ---------------------------------------------------------------------------
def _course_rects_by_stone(
    course: list[Stone], plan: Plan
) -> list[tuple[Stone, list[tuple[float, float, float, float]]]]:
    """Grundflaechen-Rechtecke (x, y, w, h) je Stein einer Lage.

    Ursprung vorne links. In Lage A gehoeren die Eckquadrate zur Rueckwand;
    zwischen Rueckwand und Seitensteinen bleibt die Fuge sichtbar. In Lage B
    enden die Seitensteine erst hinter der Ecke; die Rueckwand beginnt erst
    nach einer Fuge. Dadurch gibt es weder Ueberlagerungen noch geometrisch
    erzeugte Teilflaechen.
    """
    side_run = plan.side_len - WALL
    inner_depth = side_run
    by_stone: list[tuple[Stone, list[tuple[float, float, float, float]]]] = []
    for st in course:
        if st.wall == 0:
            rects = [(0.0, st.pos, float(WALL), st.length)]
        elif st.wall == 1:
            y = inner_depth
            rects = [(st.pos, y, st.length, float(WALL))]
        else:
            rects = [(plan.outer_width - WALL, st.pos, float(WALL), st.length)]
        by_stone.append((st, rects))
    return by_stone


def _course_rects(course: list[Stone], plan: Plan) -> list[tuple[float, float, float, float]]:
    """Alle Grundflaechen-Rechtecke einer Lage (flach, ohne Stein-Zuordnung)."""
    return [r for _, rects in _course_rects_by_stone(course, plan) for r in rects]


def _merge_rects(rects: list[tuple[float, float, float, float]]) -> list[tuple[float, float]]:
    """Vereinigt achsenparallele Rechtecke zu einem einfachen Polygon (x, y).

    Die Funktion bleibt als gemeinsame Polygon-Aufbereitung erhalten; die
    aktuelle Planung liefert pro Stein jedoch bereits genau ein Rechteck.
    """
    xs = sorted({round(r[0], 6) for r in rects} | {round(r[0] + r[2], 6) for r in rects})
    ys = sorted({round(r[1], 6) for r in rects} | {round(r[1] + r[3], 6) for r in rects})
    nx, ny = len(xs) - 1, len(ys) - 1
    cov = [[False] * nx for _ in range(ny)]
    for x0, y0, w, h in rects:
        i0 = xs.index(round(x0, 6))
        i1 = xs.index(round(x0 + w, 6))
        j0 = ys.index(round(y0, 6))
        j1 = ys.index(round(y0 + h, 6))
        for j in range(j0, j1):
            for i in range(i0, i1):
                cov[j][i] = True
    edges: list[tuple[tuple[int, int], tuple[int, int]]] = []
    for j in range(ny):
        for i in range(nx):
            if not cov[j][i]:
                continue
            if j == 0 or not cov[j - 1][i]:
                edges.append(((i, j), (i + 1, j)))
            if j == ny - 1 or not cov[j + 1][i]:
                edges.append(((i + 1, j + 1), (i, j + 1)))
            if i == 0 or not cov[j][i - 1]:
                edges.append(((i, j + 1), (i, j)))
            if i == nx - 1 or not cov[j][i + 1]:
                edges.append(((i + 1, j), (i + 1, j + 1)))
    out_next = {e[0]: e[1] for e in edges}
    start = edges[0][0]
    raw = [(xs[start[0]], ys[start[1]])]
    cur = start
    while True:
        cur = out_next[cur]
        if cur == start:
            break
        raw.append((xs[cur[0]], ys[cur[1]]))
    poly = []
    n = len(raw)
    for i in range(n):
        a, b, c = raw[i - 1], raw[i], raw[(i + 1) % n]
        cross = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
        if abs(cross) > 1e-6:
            poly.append(b)
    return poly


# ---------------------------------------------------------------------------
# 3D-Prismen fuer den gesamten Plan
# ---------------------------------------------------------------------------
def _plan_polys(plan: Plan) -> list[tuple[list[tuple[float, float]], float]]:
    """Alle Steine als (Grundflaechen-Polygon, z0)-Paare.

    Jeder Stein ist ein einzelnes Rechteck. _merge_rects bleibt als kleine
    gemeinsame Polygon-Aufbereitung erhalten, erzeugt aber keine Eckformen.
    """
    polys: list[tuple[list[tuple[float, float]], float]] = []
    for r, course in enumerate(plan.courses):
        z0 = r * (BRICK_H + plan.joint)
        for _, rects in _course_rects_by_stone(course, plan):
            polys.append((_merge_rects(rects), z0))
    return polys


# ---------------------------------------------------------------------------
# Rendern eines 3D-Prinmas aus einem Grundflaechen-Polygon
# ---------------------------------------------------------------------------
def _prism_faces(poly: list[tuple[float, float]], z: float, d: float):
    """Liefert die Seitenflaechen eines vertikal extrudierten Polygons."""
    top = [(x, y, z + d) for x, y in poly]
    bottom = [(x, y, z) for x, y in poly]
    faces = [bottom, top]
    n = len(poly)
    for i in range(n):
        x0, y0 = poly[i]
        x1, y1 = poly[(i + 1) % n]
        faces.append([(x0, y0, z), (x1, y1, z), (x1, y1, z + d), (x0, y0, z + d)])
    return faces


def _plot_boxes(ax, polys: list, grate_faces: list[list[tuple[float, float, float]]]) -> None:
    def add_body(faces: list, facecolor: str, edgecolors: list) -> None:
        ax.add_collection3d(
            Poly3DCollection(
                faces,
                facecolor=facecolor,
                edgecolor=edgecolors,
                lw=0.4,
                zsort="max",
            )
        )

    for poly, z0 in polys:
        brick_faces = _prism_faces(poly, z0, BRICK_H)
        # mplot3d besitzt keinen echten Tiefenpuffer. Kanten horizontaler
        # Flaechen koennen deshalb durch einen darueberliegenden Stein
        # erscheinen. Die seitlichen Kanten bleiben als Fugenlinien sichtbar.
        edgecolors = [(0, 0, 0, 0), (0, 0, 0, 0)]
        edgecolors.extend([BRICK_EDGE] * (len(brick_faces) - 2))
        add_body(brick_faces, BRICK_FACE, edgecolors)

    # Jeder Rostkoerper wird ebenfalls separat sortiert. So kann ein vorderer
    # Ziegel den Rost verdecken, ohne dass der Rost global hinter allen
    # Ziegeln liegt.
    for grate_part in grate_faces:
        add_body(grate_part, GRATE_COLOR, [GRATE_COLOR] * len(grate_part))


def _grate_faces(plan: Plan) -> list[list[tuple[float, float, float]]]:
    """Liefert Rahmen und Staebe des Rosts als duenne 3D-Koerper."""
    x0 = (plan.outer_width - plan.grate_width) / 2
    x1 = x0 + plan.grate_width
    y0 = 0.0
    y1 = plan.grate_depth

    parts = [
        (x0, y0, plan.grate_width, GRATE_TH),
        (x0, y1 - GRATE_TH, plan.grate_width, GRATE_TH),
        (x0, y0, GRATE_TH, plan.grate_depth),
        (x1 - GRATE_TH, y0, GRATE_TH, plan.grate_depth),
    ]
    for i in range(1, int(plan.grate_depth / GRATE_SPACING)):
        y = y0 + i * GRATE_SPACING
        parts.append((x0, y - GRATE_TH / 2, plan.grate_width, GRATE_TH))

    return [
        _prism_faces(
            [(x, y), (x + width, y), (x + width, y + depth), (x, y + depth)],
            plan.grate_height,
            GRATE_TH,
        )
        for x, y, width, depth in parts
    ]


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
    polys = _plan_polys(plan)

    fig = plt.figure(figsize=(9, 8))
    for i, (elev, azim, title) in enumerate(VIEWS, start=1):
        ax = fig.add_subplot(1, 1, i, projection="3d")
        ax.computed_zorder = True
        _plot_boxes(ax, polys, _grate_faces(plan))
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
