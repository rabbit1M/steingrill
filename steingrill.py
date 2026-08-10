"""Planung einer U-förmigen Grillumfassung aus deutschen Normalformat-Ziegeln."""

from __future__ import annotations

import math
from dataclasses import dataclass

# Normalformat (NF) in mm
BRICK_L = 240
BRICK_B = 115
BRICK_H = 71
HALF_BRICK_L = 115
# Wandstärke: halber Stein (Läuferverband)
WALL = 115


def run_solution(length: float, joint: float) -> tuple[int, int, float]:
    """Kleinste Steinkombination (ganze a, halbe b), die `length` mit Fugen erreicht.

    Liefert (a, b, gebaute_laenge). Die Kombination mit der kleinsten
    Steinanzahl gewinnt, bei Gleichstand die mit der kleinsten gebauten Länge.
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


def course_stones(length: float, joint: float) -> tuple[int, int, int, int, float]:
    """Steinbelegung zweier versetzter Lagen (Läuferverband) eines Laufs.

    Lage A beginnt mit einem ganzen Stein, Lage B ist um einen halben Stein
    versetzt. Liefert (a_A, b_A, a_B, b_B, gebaute_laenge).
    """
    a, b, built = run_solution(length, joint)
    if b:
        a_b, b_b = a, 1
    else:
        a_b, b_b = a - 1, 2
    return a, b, a_b, b_b, built


def grid_outer_lengths(center: float, joint: float, window: int = 200) -> list[int]:
    """Alle ohne Zuschnitt baubaren Wand-Längen (Außenmaße) rund um `center`."""
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
    """Rastertaugliche Rostgrößen (Breite, Tiefe, Innen-Breite, Innen-Tiefe).

    Jede Option ergibt 7 mm Luft seitlich und 7 mm Luft zur Rückwand.
    Sortiert nach Abstand zum Wunschmaß.
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
    """Schichtenanzahl, sodass n*H + (n-1)*Fuge >= Wunschhöhe."""
    return max(1, math.ceil((target_height + joint) / (BRICK_H + joint)))


def actual_height(rows: int, joint: float) -> float:
    return rows * BRICK_H + (rows - 1) * joint


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
    rows: int
    height: float
    back_a: int
    back_b: int
    back_a_b: int
    back_b_b: int
    back_len: float
    side_a: int
    side_b: int
    side_a_b: int
    side_b_b: int
    side_len: float
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

    back_a, back_b, back_a_b, back_b_b, back_len = course_stones(outer_width_des, joint)
    side_a, side_b, side_a_b, side_b_b, side_len = course_stones(outer_depth_des, joint)

    outer_width = back_len
    outer_depth = side_len
    rows = num_rows(target_height, joint)
    height = actual_height(rows, joint)

    course_a_whole = back_a + 2 * side_a
    course_a_half = back_b + 2 * side_b
    course_b_whole = back_a_b + 2 * side_a_b
    course_b_half = back_b_b + 2 * side_b_b
    cycles, remainder = divmod(rows, 2)
    total_whole = cycles * (course_a_whole + course_b_whole) + remainder * course_a_whole
    total_half = cycles * (course_a_half + course_b_half) + remainder * course_a_half
    total_whole_res = math.ceil(total_whole * (1 + reserve / 100))
    total_half_res = math.ceil(total_half * (1 + reserve / 100))

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
        rows=rows,
        height=height,
        back_a=back_a,
        back_b=back_b,
        back_a_b=back_a_b,
        back_b_b=back_b_b,
        back_len=back_len,
        side_a=side_a,
        side_b=side_b,
        side_a_b=side_a_b,
        side_b_b=side_b_b,
        side_len=side_len,
        course_a_whole=course_a_whole,
        course_a_half=course_a_half,
        course_b_whole=course_b_whole,
        course_b_half=course_b_half,
        total_whole=total_whole,
        total_half=total_half,
        total_whole_res=total_whole_res,
        total_half_res=total_half_res,
        total_res=total_whole_res + total_half_res,
    )


def plan_text(p: Plan) -> str:
    lines = [
        "=== Plan Steingrill ===",
        f"Rostmaß: {p.grate_width:.0f} x {p.grate_depth:.0f} mm (B x T)",
        f"Angestrebte Innenmaße: {p.inner_width_target:.0f} x {p.inner_depth_target:.0f} mm",
        "",
        f"Gerundet auf Ziegelraster (Fuge {p.joint:.0f} mm):",
        f"  Rückwand  ({p.back_len:.0f} mm): Lage A: {p.back_a} ganze + {p.back_b} halbe"
        f" | Lage B: {p.back_a_b} ganze + {p.back_b_b} halbe",
        f"  Seitenwand ({p.side_len:.0f} mm): Lage A: {p.side_a} ganze + {p.side_b} halbe"
        f" | Lage B: {p.side_a_b} ganze + {p.side_b_b} halbe",
        "",
        "Tatsächliche Maße:",
        f"  Außen: {p.outer_width:.0f} x {p.outer_depth:.0f} mm (B x T)",
        f"  Innen: {p.inner_width:.0f} x {p.inner_depth:.0f} mm",
        f"  Luft zum Mauerwerk: seitlich {(p.inner_width - p.grate_width) / 2:.0f} mm, "
        f"hinten {p.inner_depth - p.grate_depth:.0f} mm",
        f"  Höhe: {p.rows} Schichten = {p.height:.0f} mm "
        f"(Wunschhöhe {p.target_height:.0f} mm)",
        "",
        "Steinbedarf (Läuferverband, jede 2. Schicht um einen halben Stein versetzt):",
        f"  Lage A (ungerade Schichten): {p.course_a_whole} ganze + {p.course_a_half} halbe Steine",
        f"  Lage B (gerade Schichten): {p.course_b_whole} ganze + {p.course_b_half} halbe Steine",
        f"  gesamt ({p.rows} Schichten): {p.total_whole} ganze + {p.total_half} halbe Steine",
        f"  mit {p.reserve:.0f}% Reserve: {p.total_whole_res} ganze + "
        f"{p.total_half_res} halbe Steine ({p.total_res} Steine)",
    ]
    return "\n".join(lines)


def _ask_float(prompt: str, default: float | None = None) -> float:
    suffix = f" [Default {default:.0f}]" if default is not None else ""
    while True:
        raw = input(prompt + suffix + ": ").strip()
        if raw == "" and default is not None:
            return default
        try:
            value = float(raw)
        except ValueError:
            print(f"  Ungültige Eingabe: '{raw}'")
            continue
        if value <= 0:
            print("  Wert muss größer als 0 sein.")
            continue
        return value


def _ask_choice(max_option: int) -> int | None:
    while True:
        raw = input(f"Nummer wählen (0 = Wunschmaß beibehalten, 1-{max_option}): ").strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  Ungültige Eingabe: '{raw}'")
            continue
        if value == 0:
            return None
        if 1 <= value <= max_option:
            return value
        print(f"  Bitte eine Zahl zwischen 0 und {max_option}.")


def main() -> None:
    grate_width = _ask_float("Wunsch Rost-Breite [mm]")
    grate_depth = _ask_float("Wunsch Rost-Tiefe [mm]")
    target_height = _ask_float("Wunschhöhe (Oberkante der Wände) [mm]")
    clear = _ask_float("Spielraum Rost - Wand [mm]", default=10.0)
    joint = _ask_float("Fugenbreite [mm]", default=10.0)
    reserve = _ask_float("Reserve [%]", default=5.0)

    options = grate_options(grate_width, grate_depth, clear, joint)
    print()
    print("Rastertaugliche Rostgrößen (7 mm Luft rundherum):")
    print(f"  Wunschmaß: {grate_width:.0f} x {grate_depth:.0f} mm")
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
