"""Tests fuer die Raster- und Belegungslogik des Steingrill-Planers."""

from steingrill import (
    BRICK_L,
    HALF_BRICK_L,
    build_plan,
    clean_total,
    grate_options,
    num_rows,
    actual_height,
    _whole_run,
)
from visualize import _course_rects_by_stone


def test_clean_total_uses_only_brick_raster():
    assert clean_total(240, 10) == 240
    assert clean_total(241, 10) == 365
    assert clean_total(490, 10) == 490


def test_num_rows():
    assert num_rows(400, 10) == 6
    assert actual_height(6, 10) == 476


def test_grate_options_rasterize_whole_corner_runs():
    options = grate_options(400, 400, clear=10, joint=10)
    assert options
    for _gw, _gd, inner_width, inner_depth in options:
        assert _whole_run(inner_width + 2 * 115, 10) == inner_width + 2 * 115
        assert _whole_run(inner_depth, 10) == inner_depth


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

    assert (plan.outer_width, plan.outer_depth) == (740, 605)
    assert (plan.inner_width, plan.inner_depth) == (510, 490)
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


def test_build_plan_reserve():
    plan = build_plan(400, 400, 400, reserve=0)
    assert plan.total_whole_res == plan.total_whole
    assert plan.total_half_res == plan.total_half
