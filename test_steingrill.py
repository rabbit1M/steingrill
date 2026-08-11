"""Tests fuer die Raster- und Belegungslogik des Steingrill-Planers."""

from steingrill import (
    BRICK_L,
    HALF_BRICK_L,
    build_plan,
    clean_total,
    grate_options,
    num_rows,
    actual_height,
)
from visualize import _course_rects_by_stone


def test_clean_total_uses_half_brick_raster():
    assert clean_total(240, 10) == 240
    assert clean_total(241, 10) == 365
    assert clean_total(490, 10) == 490


def test_num_rows():
    assert num_rows(400, 10) == 6
    assert actual_height(6, 10) == 476


def test_grate_options_rasterize_half_brick_runs():
    options = grate_options(400, 400, clear=10, joint=10)
    assert options
    for _gw, _gd, inner_width, inner_depth in options:
        assert clean_total(inner_width + 2 * 115, 10) == inner_width + 2 * 115
        assert clean_total(inner_depth - 10, 10) + 10 == inner_depth


def test_example_has_no_corner_special_sizes():
    plan = build_plan(
        grate_width=400,
        grate_depth=400,
        target_height=400,
        clear=10,
        joint=10,
        reserve=5,
        inner_width=422,
        inner_depth=429,
    )

    assert (plan.outer_width, plan.outer_depth) == (740, 615)
    assert (plan.inner_width, plan.inner_depth) == (510, 500)
    assert (plan.course_a_whole, plan.course_a_half) == (7, 0)
    assert (plan.course_b_whole, plan.course_b_half) == (6, 2)

    for course in (plan.course_a, plan.course_b):
        assert all(st.length in (BRICK_L, HALF_BRICK_L) for st in course)
        half_positions = [i for i, st in enumerate(course) if st.is_half]
        assert half_positions in ([], [0], [len(course) - 1], [0, len(course) - 1])
        for _stone, rects in _course_rects_by_stone(course, plan):
            assert len(rects) == 1
            _x, _y, width, depth = rects[0]
            assert width in (115, BRICK_L)
            assert depth in (115, BRICK_L)

        rects = [r for _stone, stone_rects in _course_rects_by_stone(course, plan)
                 for r in stone_rects]
        for i, (x0, y0, w0, h0) in enumerate(rects):
            for x1, y1, w1, h1 in rects[i + 1:]:
                x_disjoint = min(x0 + w0, x1 + w1) <= max(x0, x1)
                y_disjoint = min(y0 + h0, y1 + h1) <= max(y0, y1)
                assert x_disjoint or y_disjoint


def test_corner_joint_between_side_and_back_wall():
    plan = build_plan(400, 400, 400, inner_width=422, inner_depth=429)
    side_stones = [st for st in plan.course_a if st.wall == 0]
    side_end = max(st.pos + st.length for st in side_stones)
    back_start = next(
        rect[1]
        for st, rects in _course_rects_by_stone(plan.course_a, plan)
        if st.wall == 1
        for rect in rects
    )

    assert side_end == 490
    assert back_start - side_end == plan.joint


def test_build_plan_reserve():
    plan = build_plan(400, 400, 400, reserve=0)
    assert plan.total_whole_res == plan.total_whole
    assert plan.total_half_res == plan.total_half


def test_grate_height_is_configurable():
    assert build_plan(400, 400, 400).grate_height == 150
    assert build_plan(400, 400, 400, grate_height=275).grate_height == 275


def test_grate_options_distribute_back_halves():
    options = grate_options(600, 300, clear=10, joint=10)
    option = next(option for option in options if 350 <= option[1] <= 370)
    plan = build_plan(
        option[0], option[1], 400, clear=10, joint=10,
        inner_width=option[2], inner_depth=option[3],
    )
    assert plan.outer_width == option[2] + 2 * 115
    assert plan.inner_width == option[2]
    back_joint_counts = {}
    back_half_starts = []
    for course in plan.courses:
        back_halves = [stone for stone in course if stone.wall == 1 and stone.is_half]
        assert len(back_halves) <= 1
        if back_halves:
            back_half_starts.append(back_halves[0].pos)
        back_stones = sorted(
            (stone for stone in course if stone.wall == 1),
            key=lambda stone: stone.pos,
        )
        for position in {
            round((left.pos + left.length + right.pos) / 2, 6)
            for left, right in zip(back_stones, back_stones[1:])
        }:
            back_joint_counts[position] = back_joint_counts.get(position, 0) + 1
        assert all(
            stone.pos == 0
            for stone in course
            if stone.is_half and stone.wall in (0, 2)
        )
    assert max(back_joint_counts.values()) < len(plan.courses)
    assert len(set(back_half_starts)) > 1


def test_reported_back_wall_has_staggered_joints():
    option = next(option for option in grate_options(600, 400, 10, 10)
                  if option[:2] == (615, 490))
    plan = build_plan(
        option[0], option[1], 400, clear=10, joint=10,
        inner_width=option[2], inner_depth=option[3],
    )

    joint_counts = {}
    for course in plan.courses:
        back = sorted((stone for stone in course if stone.wall == 1),
                      key=lambda stone: stone.pos)
        for position in {
            round((left.pos + left.length + right.pos) / 2, 6)
            for left, right in zip(back, back[1:])
        }:
            joint_counts[position] = joint_counts.get(position, 0) + 1
    assert max(joint_counts.values()) < len(plan.courses)
