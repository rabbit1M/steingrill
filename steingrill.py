"""Planung einer U-foermigen Grillumfassung aus deutschen Normalformat-Ziegeln.

Die drei Waende (linke Seitenwand, Rueckwand, rechte Seitenwand) werden als
wechselnder Eckverband geplant. In jeder Lage bleiben die Steine rechteckig;
die Ecke gehoert abwechselnd der Rueckwand oder den Seitenwaenden. Halbe
Steine liegen an den freien Seitenenden und bei Bedarf am Anfang der
Rueckwandlage, damit die Fugen der benachbarten Lagen versetzt sind.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# Normalformat (NF) in mm
BRICK_L = 240
BRICK_B = 115
BRICK_H = 71
HALF_BRICK_L = 115
# Wandstaerke: halber Stein (Laeuferverband)
WALL = 115
DEFAULT_GRATE_HEIGHT = 150.0


# ---------------------------------------------------------------------------
# Raster der drei geraden Wandabschnitte
# ---------------------------------------------------------------------------
def _module(joint: float) -> float:
    """Rastereinheit: halber Stein plus Fuge."""
    return HALF_BRICK_L + joint


def clean_total(total_desired: float, joint: float) -> int:
    """Kleinste laeuferverband-faehige gerade Laenge >= `total_desired`.

    Eine solche Laenge ist mit ganzen und halben Steinen sowie den Fugen
    vollstaendig ohne Zuschnitt belegbar. Das Raster umfasst deshalb ein
    Halbsteinmodul inklusive Fuge.
    """
    mod = _module(joint)
    k = max(1, math.ceil((total_desired + joint) / mod))
    return int(round(k * mod - joint))


def _whole_run(total_desired: float, joint: float) -> int:
    """Kleinste gerade Laenge, die nur aus ganzen Steinen besteht."""
    mod = BRICK_L + joint
    k = max(1, math.ceil((total_desired + joint) / mod))
    return int(round(k * mod - joint))


def _starts_with_half(total: float, joint: float) -> bool:
    """Ob ein Rasterlauf vorne mit einem Halbstein beginnen muss."""
    modules = round((total + joint) / _module(joint))
    return modules % 2 == 1


def _lay_back(start: float, total: float, joint: float,
              half_index: int | None) -> tuple[list[tuple[float, float, bool]], float]:
    """Lege eine Rueckwand mit kontrolliert gesetztem Halbstein."""
    modules = round((total + joint) / _module(joint))
    if modules % 2 == 0:
        return _lay_straight(start, False, joint, start + total)

    whole_count = (modules - 1) // 2
    if half_index is None:
        half_index = 0
    lengths = [BRICK_L] * whole_count
    lengths.insert(half_index, HALF_BRICK_L)

    spans: list[tuple[float, float, bool]] = []
    pos = start
    for length in lengths:
        spans.append((pos, pos + length, length == HALF_BRICK_L))
        pos += length + joint
    return spans, pos


def grate_options(
    grate_width: float,
    grate_depth: float,
    clear: float,
    joint: float,
    window: int = 250,
    max_options: int = 12,
) -> list[tuple[int, int, int, int]]:
    """Rastertaugliche Rostgroessen (Breite, Tiefe, Innen-Breite, Innen-Tiefe).

    Die Wandlaengen werden fuer einen wechselnden Eckverband auf das
    Halbsteinraster gerastert. Halbsteine in der Rueckwand werden pro Lage
    versetzt, damit keine durchgehende senkrechte Fuge entsteht.
    """
    iw_des = grate_width + 2 * clear
    id_des = grate_depth + clear

    back_des = iw_des + 2 * WALL
    back_lengths = {
        clean_total(value, joint)
        for value in range(max(0, int(back_des) - window), int(back_des) + window + 1)
    }
    side_runs = {
        clean_total(value, joint)
        for value in range(max(0, int(id_des) - window), int(id_des) + window + 1)
    }
    options: list[tuple[int, int, int, int]] = []
    for back_len in back_lengths:
        iw = back_len - 2 * WALL
        if back_len < 2 * (WALL + joint) + BRICK_L:
            continue
        for side_run in side_runs:
            # Zwischen Seitenlauf und Rueckwand liegt an beiden Ecken eine
            # Fuge. `id_` ist deshalb die lichte Tiefe hinter dieser Fuge.
            id_ = side_run + joint
            gw, gd = iw - 2 * clear, id_ - clear
            if gw >= 200 and gd >= 200:
                options.append((round(gw), round(gd), iw, id_))
    options.sort(key=lambda o: (
        (o[0] < grate_width) + (o[1] < grate_depth),
        abs(o[0] - grate_width) + abs(o[1] - grate_depth),
        -o[0] - o[1],
    ))

    # Neben den naechsten Massen sollen auch die benachbarten Halbsteinraster
    # sichtbar bleiben. So verschwindet z. B. ein kleineres Rastermass nicht
    # nur deshalb aus der Liste, weil mehrere Tiefenvarianten naeher liegen.
    width_options = sorted({o[0] for o in options}, key=lambda w: abs(w - grate_width))[:4]
    depth_options = sorted({o[1] for o in options}, key=lambda d: abs(d - grate_depth))[:3]
    nearby = [o for o in options if o[0] in width_options and o[1] in depth_options]
    nearby.sort(key=lambda o: (
        (o[0] < grate_width) + (o[1] < grate_depth),
        abs(o[0] - grate_width) + abs(o[1] - grate_depth),
        -o[0] - o[1],
    ))
    return nearby[:max_options]


def num_rows(target_height: float, joint: float) -> int:
    """Schichtenanzahl, sodass n*H + (n-1)*Fuge >= Wunschhoehe."""
    return max(1, math.ceil((target_height + joint) / (BRICK_H + joint)))


def actual_height(rows: int, joint: float) -> float:
    return rows * BRICK_H + (rows - 1) * joint


# ---------------------------------------------------------------------------
# Steinbelegung der drei geraden Wandabschnitte
# ---------------------------------------------------------------------------
@dataclass
class Stone:
    """Ein Stein im aufgewickelten 1D-Lauf des U-Mauerzugs.

    pos    : Anfangsposition im gesamten U-Lauf (mm).
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
               side_len: float, back_len: float,
               back_half_index: int | None = None) -> list[Stone]:
    """Lege eine Lage als wechselnden, ueberlappungsfreien Eckverband.

    In Lage A gehoeren die Ecken zur Rueckwand. In Lage B werden die
    Seitensteine bis in die Ecken gefuehrt; die Rueckwand beginnt hinter einer
    Fuge. `total` bleibt als Teil der bisherigen Funktionsschnittstelle
    erhalten, ist fuer die lokale Belegung aber nicht erforderlich.
    """
    del total
    corner_run = WALL + joint
    stones: list[Stone] = []
    if not start_with_half:
        side_run = side_len
        back_start = 0.0
        back_run = back_len
        side_front_half = _starts_with_half(side_run, joint)
        left_spans, _ = _lay_straight(0.0, side_front_half, joint, side_run)
        back_spans, _ = _lay_back(back_start, back_run, joint, back_half_index)
        right_spans, _ = _lay_straight(0.0, False, joint, side_run)
    else:
        side_run = side_len + corner_run
        back_start = corner_run
        back_run = back_len - 2 * corner_run
        side_front_half = _starts_with_half(side_run, joint)
        left_spans, _ = _lay_straight(0.0, side_front_half, joint, side_run)
        back_spans, _ = _lay_back(back_start, back_run, joint, back_half_index)
        right_spans, _ = _lay_straight(0.0, False, joint, side_run)

    stones.extend(Stone(pos=s, length=e - s, is_half=is_half, wall=0)
                  for s, e, is_half in left_spans)
    stones.extend(Stone(pos=s, length=e - s, is_half=is_half, wall=1)
                  for s, e, is_half in back_spans)
    stones.extend(Stone(pos=side_run - e, length=e - s, is_half=is_half, wall=2)
                  for s, e, is_half in right_spans)
    return stones


def course_counts(stones: list[Stone]) -> tuple[int, int]:
    """Zaehle (ganze, halbe) Steine einer Lage."""
    whole = sum(1 for st in stones if not st.is_half)
    half = sum(1 for st in stones if st.is_half)
    return whole, half


def _back_joint_positions(course: list[Stone]) -> set[float]:
    """Positionen der Fugenmitten innerhalb der Rueckwand einer Lage."""
    back = sorted((stone for stone in course if stone.wall == 1),
                  key=lambda stone: stone.pos)
    return {
        round((left.pos + left.length + right.pos) / 2, 6)
        for left, right in zip(back, back[1:])
    }


def _back_layout_score(courses: list[list[Stone]]) -> tuple[int, int]:
    """Bewerte durchgehende und mehrfach uebereinanderliegende Rueckwandfugen."""
    counts: dict[float, int] = {}
    for course in courses:
        for position in _back_joint_positions(course):
            counts[position] = counts.get(position, 0) + 1
    max_count = max(counts.values(), default=0)
    pair_overlaps = sum(count * (count - 1) // 2 for count in counts.values())
    return max_count, pair_overlaps


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
    grate_height: float
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
    courses: list  # individuelle Belegung jeder Schicht
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
    grate_height: float = DEFAULT_GRATE_HEIGHT,
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

    # Lage A bekommt die Ecken aus der Rueckwand. Die geraden Wandabschnitte
    # werden auf das Halbsteinraster gerundet.
    # Die Seitensteine enden vor der Rueckwand; die Fuge liegt zwischen ihrem
    # Ende und der Rueckwand. Die lichte Tiefe umfasst daher den Seitenlauf
    # und diese Eckfuge.
    side_run = float(clean_total(max(0.0, inner_depth - joint), joint))
    back_len = float(clean_total(outer_width_des, joint))
    side_len = side_run + joint + WALL
    total = 2 * side_run + back_len

    rows = num_rows(target_height, joint)
    height = actual_height(rows, joint)

    back_choices: list[list[int | None]] = []
    for row in range(rows):
        is_b = row % 2 == 1
        back_run = back_len - 2 * (WALL + joint) if is_b else back_len
        modules = round((back_run + joint) / _module(joint))
        if modules % 2:
            back_choices.append(list(range((modules - 1) // 2 + 1)))
        else:
            back_choices.append([None])

    def make_courses(half_indices: list[int | None]) -> list[list[Stone]]:
        return [
            lay_course(
                total,
                start_with_half=row % 2 == 1,
                joint=joint,
                side_len=side_run,
                back_len=back_len,
                back_half_index=half_index,
            )
            for row, half_index in enumerate(half_indices)
        ]

    # Eine Variante mit wechselnden Randpositionen stellt sicher, dass auch
    # bei unguenstigen Zufallswerten keine starre Fugenlinie entsteht.
    fallback_indices = [
        choices[0] if row // 2 % 2 == 0 else choices[-1]
        for row, choices in enumerate(back_choices)
    ]
    rng = random.Random()
    best_courses = make_courses(fallback_indices)
    best_score = _back_layout_score(best_courses)
    for _ in range(19):
        half_indices = [rng.choice(choices) for choices in back_choices]
        candidate = make_courses(half_indices)
        score = _back_layout_score(candidate)
        if score < best_score or (score == best_score and rng.random() < 0.5):
            best_courses = candidate
            best_score = score
    courses = best_courses

    course_a = courses[0]
    course_b = courses[1] if rows > 1 else courses[0]
    ca_whole, ca_half = course_counts(course_a)
    cb_whole, cb_half = course_counts(course_b)

    outer_width = back_len
    outer_depth = side_len

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
        grate_height=grate_height,
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
        courses=courses,
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
        f"  Lage A Wandabschnitte: "
        f"{2 * (p.side_len - WALL - p.joint) + p.back_len:.0f} mm",
        f"  Lage B Seitenlauf: {p.side_len:.0f} mm "
        f"(inkl. {p.joint:.0f} mm Eckfugenbereich)",
        "",
        "Tatsaechliche Masze:",
        f"  Aussen: {p.outer_width:.0f} x {p.outer_depth:.0f} mm (B x T)",
        f"  Innen: {p.inner_width:.0f} x {p.inner_depth:.0f} mm",
        f"  Luft zum Mauerwerk: seitlich {(p.inner_width - p.grate_width) / 2:.0f} mm, "
        f"hinten {p.inner_depth - p.grate_depth:.0f} mm",
        f"  Hoehe: {p.rows} Schichten = {p.height:.0f} mm "
        f"(Wunschhoehe {p.target_height:.0f} mm)",
        f"  Rosthoehe: {p.grate_height:.0f} mm ueber Grundflaeche",
        "",
        "Steinbedarf (wechselnder Eckverband, jede 2. Schicht versetzt):",
        f"  Lage A (ungerade Schichten): {p.course_a_whole} ganze + "
        f"{p.course_a_half} halbe",
        f"  Lage B (gerade Schichten):   {p.course_b_whole} ganze + "
        f"{p.course_b_half} halbe",
        f"  gesamt ({p.rows} Schichten): {p.total_whole} ganze + "
        f"{p.total_half} halbe Steine",
        f"  mit {p.reserve:.0f}% Reserve: {p.total_whole_res} ganze + "
        f"{p.total_half_res} halbe Steine ({p.total_res} Steine)",
        "  Rueckwand: 20 Belegungen bewertet, beste Fugenverteilung gewaehlt.",
        "",
        "In Lage A ueberdeckt die Rueckwand die beiden Ecken.",
        "In Lage B laufen die Seitensteine durch die Ecken; die Rueckwand",
        f"beginnt mit je {p.joint:.0f} mm Fuge. Es gibt keine Ueberlappung.",
        "Halbe Steine liegen an den vorderen Seitenwandenden; in der Rueckwand",
        "werden sie lagenweise versetzt, damit keine durchgehende Fuge entsteht.",
        "Die Reserve bezieht sich auf ganze + halbe Steine.",
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
    grate_height = _ask_float(
        "Rosthoehe ueber Grundflaeche [mm]", default=DEFAULT_GRATE_HEIGHT
    )
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
            grate_height=grate_height,
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
            grate_height=grate_height,
        )
    print()
    print(plan_text(plan))

    from visualize import show_plan

    show_plan(plan)


if __name__ == "__main__":
    main()
