"""Planung einer U-foermigen Grillumfassung aus deutschen Normalformat-Ziegeln.

Die drei Waende (linke Seitenwand, Rueckwand, rechte Seitenwand) werden als
*ein einziger fortlaufender Mauerzug* im Läuferverband betrachtet, der zweimal
um 90° abknickt. Dadurch versetzt der Verband automatisch um die Ecken: An
jeder Ecke liegt je Lage entweder ein um 90° gedrehter Eck-Stein (der die Ecke
umgreift) oder eine Fuge, die in der naechsten Lage wieder von einem Eck-Stein
ueberdeckt wird. Es entsteht keine durchgehende Fuge von unten nach oben.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

# Normalformat (NF) in mm
BRICK_L = 240
BRICK_B = 115
BRICK_H = 71
HALF_BRICK_L = 115
# Wandstaerke: halber Stein (Laeuferverband)
WALL = 115


# ---------------------------------------------------------------------------
# Geometrie einer einzelnen Wandlaenge (gerade Strecke, keine Ecke)
# ---------------------------------------------------------------------------
def run_solution(length: float, joint: float) -> tuple[int, int, float]:
    """Kleinste Steinkombination (ganze a, halbe b), die `length` mit Fugen erreicht.

    Liefert (a, b, gebaute_laenge). Die Kombination mit der kleinsten
    Steinanzahl gewinnt, bei Gleichstand die mit der kleinsten gebauten Laenge.
    """
    length = max(length, 0.0)
    m = max(1, math.ceil((length + joint) / (BRICK_L + joint)))
    best = None
    for a in range(m, -1, -1):
        b = m - a
        built = a * BRICK_L + b * HALF_BRICK_L + (m - 1) * joint
        if built >= length:
            if best is None or built < best[2]:
                best = (a, b, built)
    assert best is not None
    return best


def grid_outer_lengths(center: float, joint: float, window: int = 200) -> list[int]:
    """Alle ohne Zuschnitt baubaren Wand-Laengen (Aussenmasse) rund um `center`."""
    vals: set[int] = set()
    for length in range(max(0, int(center) - window), int(center) + window + 1):
        _a, _b, built = run_solution(length, joint)
        if abs(built - length) < 1e-9:
            vals.add(int(round(built)))
    return sorted(vals)


def grate_options(
    grate_width: float,
    grate_depth: float,
    clear: float,
    joint: float,
    window: int = 200,
    max_options: int = 8,
) -> list[tuple[int, int, int, int]]:
    """Rastertaugliche Rostgroessen (Breite, Tiefe, Innen-Breite, Innen-Tiefe).

    Jede Option ergibt 7 mm Luft seitlich und 7 mm Luft zur Rueckwand.
    Sortiert nach Abstand zum Wunschmass.
    """
    outer_w_center = grate_width + 2 * clear + 2 * WALL
    outer_d_center = grate_depth + clear + WALL
    inner_widths = [w - 2 * WALL for w in grid_outer_lengths(outer_w_center, joint, window)]
    inner_depths = [d - WALL for d in grid_outer_lengths(outer_d_center, joint, window)]
    options: list[tuple[int, int, int, int]] = []
    for iw in inner_widths:
        for id_ in inner_depths:
            gw, gd = iw - 14, id_ - 7
            if gw >= 200 and gd >= 200:
                options.append((gw, gd, iw, id_))
    options.sort(key=lambda o: abs(o[0] - grate_width) + abs(o[1] - grate_depth))
    return options[:max_options]


def num_rows(target_height: float, joint: float) -> int:
    """Schichtenanzahl, sodass n*H + (n-1)*Fuge >= Wunschhoehe."""
    return max(1, math.ceil((target_height + joint) / (BRICK_H + joint)))


def actual_height(rows: int, joint: float) -> float:
    return rows * BRICK_H + (rows - 1) * joint


# ---------------------------------------------------------------------------
# Mauerzug der U-Form: eine durchgehende Steinfolge um beide Ecken
# ---------------------------------------------------------------------------
@dataclass
class Stone:
    """Ein Stein in der aufgewickelten 1D-Ansicht des U-Mauerzugs.

    pos    : Anfangsposition im 1D-Lauf (mm), 0 = linker vorderer Anfang.
    length : Steinlaenge (240 = ganz, 115 = halb).
    is_half: True bei halbem Stein.
    wall   : 0 = linke Seitenwand, 1 = Rueckwand, 2 = rechte Seitenwand.
    corner : 0 = kein Eck-Stein, 1 = Eck-Stein an Ecke 1 (hinten links),
             2 = Eck-Stein an Ecke 2 (hinten rechts).
    """
    pos: float
    length: float
    is_half: bool
    wall: int
    corner: int


def _lay_straight(start_pos: float, start_with_half: bool, joint: float,
                  end_pos: float) -> tuple[list[tuple[float, float, bool]], float]:
    """Lege Läufer von start_pos bis end_pos (ausschliesslich).

    Liefert (Spans, naechste_pos) mit Spans als Liste (pos, end, is_half).
    Die Wand endet entweder mit einem ganzen Stein genau auf end_pos
    (range_value = 0) oder um einen halben Stein davor (range_value = +1/2),
    passend zu Fall 1 / Fall 2.
    """
    spans: list[tuple[float, float, bool]] = []
    pos = start_pos
    if start_with_half:
        spans.append((pos, pos + HALF_BRICK_L, True))
        pos += HALF_BRICK_L + joint
    else:
        spans.append((pos, pos + BRICK_L, False))
        pos += BRICK_L + joint
    while pos < end_pos - 1e-9:
        if pos + BRICK_L <= end_pos + 1e-9:
            spans.append((pos, pos + BRICK_L, False))
            pos += BRICK_L + joint
        else:
            spans.append((pos, pos + HALF_BRICK_L, True))
            pos += HALF_BRICK_L + joint
            break
    return spans, pos


def lay_course(total: float, start_with_half: bool, joint: float,
              side_len: float, back_len: float) -> list[Stone]:
    """Lege eine Lage entlang des U-Laufs.

    Der Mauerzug beginnt an Pos 0 an der Vorderkante der linken Seitenwand,
    verlaeuft nach hinten bis Ecke 1 (pos = side_len), knickt um 90° in die
    Rueckwand, verlaeuft bis Ecke 2 (pos = side_len + back_len), knickt um 90°
    in die rechte Seitenwand und endet vorne bei pos = total.

    Eck-Konstruktion (Laeuferverband, abhaengig vom Wandlaengen-Modul):
      Fall 1 (Wand endet mit ganzem Stein genau an der Ecke): der erste Stein
              der Folgewand stoesst stumpf an (kein Eck-Stein).
      Fall 2 (Wand endet mit halbem Stein, d.h. 125 mm vor der Ecke): der
              erste Stein der Folgewand ist der Eck-Stein und beginnt an der
              Aussenkante der Vorgängerwand (e - HALF + joint), schliesst also
              die halbe Luecke der Vorgängerwand mit seiner Laengsseite.

    Der Startmodus (ganz/halb) alterniert pro Wand, sodass sich der Läufer-
    versatz automatisch ergibt: Wand 0 = start_with_half, Wand 1 = invertiert,
    Wand 2 = start_with_half.

    Annahme: side_len und back_len sind "rastertauglich" (Vielfaches von 125 mm
    minus 10 mm), damit der Versatz sauber aufgeht.
    """
    e1 = side_len
    e2 = side_len + back_len
    wall_starts = [0.0, e1, e2]
    wall_ends = [e1, e2, total]
    starts_with_half = [start_with_half, not start_with_half, start_with_half]

    stones: list[Stone] = []
    for wall, (w_start, w_end, s_half) in enumerate(
            zip(wall_starts, wall_ends, starts_with_half)):
        if wall > 0:
            prev_full = _wall_ends_full(wall_starts[wall - 1],
                                        wall_ends[wall - 1],
                                        starts_with_half[wall - 1], joint)
            if not prev_full:
                # Fall 2: Eck-Stein beginnt an der Eckenposition (= Aussenkante
                # der Vorgängerwand) und erstreckt sich als Läufer entlang der
                # Folgewand um BRICK_L.
                corner_start = w_start
                corner_end = corner_start + BRICK_L
                stones.append(Stone(pos=corner_start, length=BRICK_L,
                                    is_half=False, wall=wall, corner=wall))
                spans, _ = _lay_straight(corner_end + joint, s_half, joint, w_end)
            else:
                spans, _ = _lay_straight(w_start, s_half, joint, w_end)
        else:
            spans, _ = _lay_straight(w_start, s_half, joint, w_end)
        for (s, e, is_half) in spans:
            stones.append(Stone(pos=s, length=e - s, is_half=is_half,
                                wall=wall, corner=0))
    return stones


def _wall_ends_full(start_pos: float, end_pos: float, start_with_half: bool,
                    joint: float) -> bool:
    """True, wenn die Wand mit einem ganzen Stein genau auf end_pos endet (Fall 1);
    False, wenn ein halber Stein am Ende sitzt (Fall 2)."""
    spans, _ = _lay_straight(start_pos, start_with_half, joint, end_pos)
    last = spans[-1] if spans else None
    if last is None:
        return True
    return (not last[2]) and abs(last[1] - end_pos) < 1e-6


def course_counts(stones: list[Stone]) -> tuple[int, int, int]:
    """Zaehle (ganze, halbe, Eck-Steine) einer Lage.

    Eck-Steine sind ganze, um 90° gedrehte Steine und werden separat gezaehlt,
    nicht unter 'ganze'.
    """
    whole = 0
    half = 0
    corner = 0
    for st in stones:
        if st.corner:
            corner += 1
        elif st.is_half:
            half += 1
        else:
            whole += 1
    return whole, half, corner


# ---------------------------------------------------------------------------
# Plan
# ---------------------------------------------------------------------------
@dataclass
class Plan:
    grate_width: float
    grate_depth: float
    clear: float
    joint: float
    reserve: float
    target_height: float
    inner_width_target: float
    inner_depth_target: float
    inner_width: float
    inner_depth: float
    outer_width: float
    outer_depth: float
    side_len: float
    back_len: float
    rows: int
    height: float
    # Steinbelegung je Lage (ueber alle drei Waende):
    # Lage A beginnt mit einem ganzen Stein (ungerade Schichten),
    # Lage B beginnt mit einem halben Stein (gerade Schichten, versetzt).
    course_a: list  # list[Stone] fuer Lage A
    course_b: list  # list[Stone] fuer Lage B
    course_a_whole: int
    course_a_half: int
    course_a_corner: int
    course_b_whole: int
    course_b_half: int
    course_b_corner: int
    total_whole: int
    total_half: int
    total_corner: int
    total_whole_res: int
    total_half_res: int
    total_res: int


def build_plan(
    grate_width: float,
    grate_depth: float,
    target_height: float,
    clear: float = 10.0,
    joint: float = 10.0,
    reserve: float = 5.0,
    inner_width: float | None = None,
    inner_depth: float | None = None,
) -> Plan:
    if inner_width is None:
        inner_width = grate_width + 2 * clear
    if inner_depth is None:
        inner_depth = grate_depth + clear
    inner_width_target = inner_width
    inner_depth_target = inner_depth
    outer_width_des = inner_width + 2 * WALL
    outer_depth_des = inner_depth + WALL

    # Aussenlaengen der drei Waende rastertauglich waehlen:
    _a_r, _b_r, back_len = run_solution(outer_width_des, joint)
    _a_s, _b_s, side_len = run_solution(outer_depth_des, joint)

    total = 2 * side_len + back_len
    course_a = lay_course(total, start_with_half=False, joint=joint,
                          side_len=side_len, back_len=back_len)
    course_b = lay_course(total, start_with_half=True, joint=joint,
                          side_len=side_len, back_len=back_len)
    ca_whole, ca_half, ca_corner = course_counts(course_a)
    cb_whole, cb_half, cb_corner = course_counts(course_b)

    outer_width = back_len
    outer_depth = side_len
    rows = num_rows(target_height, joint)
    height = actual_height(rows, joint)

    cycles, remainder = divmod(rows, 2)
    total_whole = cycles * (ca_whole + cb_whole) + remainder * ca_whole
    total_half = cycles * (ca_half + cb_half) + remainder * ca_half
    total_corner = cycles * (ca_corner + cb_corner) + remainder * ca_corner
    total_whole_res = math.ceil(total_whole * (1 + reserve / 100))
    total_half_res = math.ceil(total_half * (1 + reserve / 100))
    total_res = total_whole_res + total_half_res

    return Plan(
        grate_width=grate_width,
        grate_depth=grate_depth,
        clear=clear,
        joint=joint,
        reserve=reserve,
        target_height=target_height,
        inner_width_target=inner_width_target,
        inner_depth_target=inner_depth_target,
        inner_width=outer_width - 2 * WALL,
        inner_depth=outer_depth - WALL,
        outer_width=outer_width,
        outer_depth=outer_depth,
        side_len=side_len,
        back_len=back_len,
        rows=rows,
        height=height,
        course_a=course_a,
        course_b=course_b,
        course_a_whole=ca_whole,
        course_a_half=ca_half,
        course_a_corner=ca_corner,
        course_b_whole=cb_whole,
        course_b_half=cb_half,
        course_b_corner=cb_corner,
        total_whole=total_whole,
        total_half=total_half,
        total_corner=total_corner,
        total_whole_res=total_whole_res,
        total_half_res=total_half_res,
        total_res=total_res,
    )


def plan_text(p: Plan) -> str:
    lines = [
        "=== Plan Steingrill ===",
        f"Rostmass: {p.grate_width:.0f} x {p.grate_depth:.0f} mm (B x T)",
        f"Angestrebte Innenmasze: {p.inner_width_target:.0f} x {p.inner_depth_target:.0f} mm",
        "",
        f"Gerundet auf Ziegelraster (Fuge {p.joint:.0f} mm):",
        f"  Rueckwand  ({p.back_len:.0f} mm aussen)",
        f"  Seitenwaende ({p.side_len:.0f} mm aussen, je 1x)",
        f"  U-Lauf gesamt: {2 * p.side_len + p.back_len:.0f} mm",
        "",
        "Tatsaechliche Masze:",
        f"  Aussen: {p.outer_width:.0f} x {p.outer_depth:.0f} mm (B x T)",
        f"  Innen: {p.inner_width:.0f} x {p.inner_depth:.0f} mm",
        f"  Luft zum Mauerwerk: seitlich {(p.inner_width - p.grate_width) / 2:.0f} mm, "
        f"hinten {p.inner_depth - p.grate_depth:.0f} mm",
        f"  Hoehe: {p.rows} Schichten = {p.height:.0f} mm "
        f"(Wunschhoehe {p.target_height:.0f} mm)",
        "",
        "Steinbedarf (Laeuferverband um die Ecken, jede 2. Schicht versetzt):",
        f"  Lage A (ungerade Schichten): {p.course_a_whole} ganze + "
        f"{p.course_a_half} halbe + {p.course_a_corner} Eck-Steine",
        f"  Lage B (gerade Schichten):   {p.course_b_whole} ganze + "
        f"{p.course_b_half} halbe + {p.course_b_corner} Eck-Steine",
        f"  gesamt ({p.rows} Schichten): {p.total_whole} ganze + "
        f"{p.total_half} halbe + {p.total_corner} Eck-Steine",
        f"  mit {p.reserve:.0f}% Reserve (ganze+halbe): {p.total_whole_res} ganze + "
        f"{p.total_half_res} halbe Steine ({p.total_res} Steine)",
        "",
        "Hinweis: Eck-Steine sind um 90° gedrehte ganze Steine, die die Ecke",
        "umgreifen. Sie werden als solche nicht gesondert besorgt, sondern als",
        "ganze Steine mitgeliefert. Die Reserve bezieht sich auf ganze + halbe.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Interaktive Eingabe (unveraendert)
# ---------------------------------------------------------------------------
def _ask_float(prompt: str, default: float | None = None) -> float:
    suffix = f" [Default {default:.0f}]" if default is not None else ""
    while True:
        raw = input(prompt + suffix + ": ").strip()
        if raw == "" and default is not None:
            return default
        try:
            value = float(raw)
        except ValueError:
            print(f"  Ungueltige Eingabe: '{raw}'")
            continue
        if value <= 0:
            print("  Wert muss groesser als 0 sein.")
            continue
        return value


def _ask_choice(max_option: int) -> int | None:
    while True:
        raw = input(f"Nummer waehlen (0 = Wunschmass beibehalten, 1-{max_option}): ").strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  Ungueltige Eingabe: '{raw}'")
            continue
        if value == 0:
            return None
        if 1 <= value <= max_option:
            return value
        print(f"  Bitte eine Zahl zwischen 0 und {max_option}.")


def main() -> None:
    grate_width = _ask_float("Wunsch Rost-Breite [mm]")
    grate_depth = _ask_float("Wunsch Rost-Tiefe [mm]")
    target_height = _ask_float("Wunschhoehe (Oberkante der Waende) [mm]")
    clear = _ask_float("Spielraum Rost - Wand [mm]", default=10.0)
    joint = _ask_float("Fugenbreite [mm]", default=10.0)
    reserve = _ask_float("Reserve [%]", default=5.0)

    options = grate_options(grate_width, grate_depth, clear, joint)
    print()
    print("Rastertaugliche Rostgroessen (7 mm Luft rundherum):")
    print(f"  Wunschmass: {grate_width:.0f} x {grate_depth:.0f} mm")
    print("  Nr | Rost (B x T) [mm] | Innen (B x T) [mm]")
    for i, (gw, gd, iw, id_) in enumerate(options, start=1):
        print(f"  {i:2d} | {gw:>5} x {gd:>4}          | {iw:>5} x {id_:>4}")
    choice = _ask_choice(len(options))
    if choice is not None:
        gw, gd, iw, id_ = options[choice - 1]
        grate_width, grate_depth = float(gw), float(gd)
        plan = build_plan(
            grate_width=grate_width,
            grate_depth=grate_depth,
            target_height=target_height,
            clear=clear,
            joint=joint,
            reserve=reserve,
            inner_width=float(iw),
            inner_depth=float(id_),
        )
    else:
        plan = build_plan(
            grate_width=grate_width,
            grate_depth=grate_depth,
            target_height=target_height,
            clear=clear,
            joint=joint,
            reserve=reserve,
        )
    print()
    print(plan_text(plan))

    from visualize import show_plan

    show_plan(plan)


if __name__ == "__main__":
    main()
