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
# Raster des U-Mauerzugs: ein durchgehender Laeuferverband um beide Ecken
# ---------------------------------------------------------------------------
def _module(joint: float) -> float:
    """Rastereinheit: halber Stein + Fuge. Die gesamte U-Laenge ist ein
    Vielfaches dieser Einheit (minus eine Fuge am freien Ende)."""
    return HALF_BRICK_L + joint


def clean_total(total_desired: float, joint: float) -> int:
    """Kleinste Laeuferverband-faehige U-Laenge >= `total_desired`.

    Der Laeuferverband benoetigt total = k*Modul - Fuge (k ganze + halbe
    Steine). Nur solche Laengen ergeben halbe Steine ausschliesslich an den
    beiden freien Enden (Anfang/Ende der Seitenwaende).
    """
    mod = _module(joint)
    k = max(1, math.ceil((total_desired + joint) / mod))
    return int(round(k * mod - joint))


def grate_options(
    grate_width: float,
    grate_depth: float,
    clear: float,
    joint: float,
    window: int = 200,
    max_options: int = 8,
) -> list[tuple[int, int, int, int]]:
    """Rastertaugliche Rostgroessen (Breite, Tiefe, Innen-Breite, Innen-Tiefe).

    Nur Rostgroessen, deren U-Lauf ohne Zuschnitt aufgeht (total ist ein
    Vielfaches der Laeuferverband-Einheit). Sortiert nach Abstand zum Wunschmass.
    """
    iw_des = grate_width + 2 * clear
    id_des = grate_depth + clear
    mod = _module(joint)
    options: list[tuple[int, int, int, int]] = []
    for iw in range(max(0, int(iw_des) - window), int(iw_des) + window + 1):
        for id_ in range(max(0, int(id_des) - window), int(id_des) + window + 1):
            back_len = iw + 2 * WALL
            side_len = id_ + WALL
            total = 2 * side_len + back_len
            if abs((total + joint) % mod) > 1e-9:
                continue
            gw, gd = iw - 2 * clear, id_ - clear
            if gw >= 200 and gd >= 200:
                options.append((round(gw), round(gd), iw, id_))
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
    """Ein Stein im aufgewickelten 1D-Lauf des U-Mauerzugs.

    pos    : Anfangsposition im 1D-Lauf (mm), 0 = linker vorderer Anfang.
    length : Steinlaenge (240 = ganz, 115 = halb).
    is_half: True bei halbem Stein.
    wall   : 0 = linke Seitenwand, 1 = Rueckwand, 2 = rechte Seitenwand.
    """
    pos: float
    length: float
    is_half: bool
    wall: int


def _lay_straight(start_pos: float, start_with_half: bool, joint: float,
                  end_pos: float) -> tuple[list[tuple[float, float, bool]], float]:
    """Lege Laeufer von start_pos bis end_pos (ausschliesslich).

    Liefert (Spans, naechste_pos) mit Spans als Liste (pos, end, is_half).
    Es werden ausschliesslich ganze Steine verlegt; nur ganz am Ende kann ein
    halber Stein folgen, wenn der Rest genau einen halben Stein betraegt.
    """
    spans: list[tuple[float, float, bool]] = []
    pos = start_pos
    if start_with_half:
        spans.append((pos, pos + HALF_BRICK_L, True))
        pos += HALF_BRICK_L + joint
    while pos < end_pos - 1e-9:
        remaining = end_pos - pos
        if remaining >= BRICK_L - 1e-9:
            spans.append((pos, pos + BRICK_L, False))
            pos += BRICK_L + joint
        else:
            spans.append((pos, pos + HALF_BRICK_L, True))
            pos += HALF_BRICK_L + joint
            break
    return spans, pos


def lay_course(total: float, start_with_half: bool, joint: float,
              side_len: float, back_len: float) -> list[Stone]:
    """Lege eine Lage als einen durchgehenden Laeuferverband um die U-Form.

    Der Mauerzug beginnt an Pos 0 an der Vorderkante der linken Seitenwand,
    verlaeuft nach hinten bis Ecke 1 (pos = side_len), knickt um 90° in die
    Rueckwand, verlaeuft bis Ecke 2 (pos = side_len + back_len), knickt um 90°
    in die rechte Seitenwand und endet vorne bei pos = total.

    Die ganze Lage ist EIN fortlaufender Verband (keine getrennten Waende).
    `start_with_half` versetzt den Lauf um einen halben Stein: Lage A beginnt
    mit einem ganzen Stein, Lage B mit einem halben. Weil `total` eine
    Laeuferverband-Laenge ist, fallen halbe Steine ausschliesslich an den
    freien Enden (Anfang der linken bzw. Ende der rechten Seitenwand) an.
    An den Ecken sitzt automatisch je nach Versatz ein Stein der Seiten- oder
    der Rueckwand.
    """
    spans, _ = _lay_straight(0.0, start_with_half, joint, total)

    e1 = side_len
    e2 = side_len + back_len
    stones: list[Stone] = []
    for (s, e, is_half) in spans:
        center = s + (e - s) / 2
        if center < e1:
            wall = 0
        elif center < e2:
            wall = 1
        else:
            wall = 2
        stones.append(Stone(pos=s, length=e - s, is_half=is_half, wall=wall))
    return stones


def course_counts(stones: list[Stone]) -> tuple[int, int]:
    """Zaehle (ganze, halbe) Steine einer Lage."""
    whole = sum(1 for st in stones if not st.is_half)
    half = sum(1 for st in stones if st.is_half)
    return whole, half


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
    course_b_whole: int
    course_b_half: int
    total_whole: int
    total_half: int
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

    # U-Lauf als einen durchgehenden Laeuferverband: die Gesamtlaenge
    # total = 2*side_len + back_len muss eine Laeuferverband-Laenge sein
    # (Vielfaches der Rastereinheit minus Fuge), damit halbe Steine nur an den
    # freien Enden liegen. Aufteilung in ganzzahlige side_len/back_len waehlen,
    # die der Wunschgroesse am naechsten kommen.
    total_des = 2 * outer_depth_des + outer_width_des
    total = clean_total(total_des, joint)

    best: tuple[float, int, int] | None = None
    for side_len in range(int(outer_depth_des) - 200, int(outer_depth_des) + 200):
        back_len = total - 2 * side_len
        if back_len < outer_width_des - 1e-9 or back_len < 0:
            continue
        if side_len < outer_depth_des - 1e-9:
            continue
        score = abs(side_len - outer_depth_des) + abs(back_len - outer_width_des)
        if best is None or score < best[0]:
            best = (score, side_len, back_len)
    assert best is not None
    _score, side_len, back_len = best
    side_len = float(side_len)
    back_len = float(back_len)

    course_a = lay_course(total, start_with_half=False, joint=joint,
                          side_len=side_len, back_len=back_len)
    course_b = lay_course(total, start_with_half=True, joint=joint,
                          side_len=side_len, back_len=back_len)
    ca_whole, ca_half = course_counts(course_a)
    cb_whole, cb_half = course_counts(course_b)

    outer_width = back_len
    outer_depth = side_len
    rows = num_rows(target_height, joint)
    height = actual_height(rows, joint)

    cycles, remainder = divmod(rows, 2)
    total_whole = cycles * (ca_whole + cb_whole) + remainder * ca_whole
    total_half = cycles * (ca_half + cb_half) + remainder * ca_half
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
        course_b_whole=cb_whole,
        course_b_half=cb_half,
        total_whole=total_whole,
        total_half=total_half,
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
        f"{p.course_a_half} halbe",
        f"  Lage B (gerade Schichten):   {p.course_b_whole} ganze + "
        f"{p.course_b_half} halbe",
        f"  gesamt ({p.rows} Schichten): {p.total_whole} ganze + "
        f"{p.total_half} halbe Steine",
        f"  mit {p.reserve:.0f}% Reserve: {p.total_whole_res} ganze + "
        f"{p.total_half_res} halbe Steine ({p.total_res} Steine)",
        "",
        "Die gesamte U-Form wird als EIN fortlaufender Laeuferverband gemauert.",
        "Halbe Steine liegen nur an den freien Enden der Seitenwaende. An den",
        "Ecken sitzt je nach Versatz automatisch ein Stein der Seiten- oder der",
        "Rueckwand. Die Reserve bezieht sich auf ganze + halbe Steine.",
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
