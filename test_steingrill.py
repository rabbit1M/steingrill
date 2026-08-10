"""Tests der Berechnungslogik des Steingrill-Planers."""

from steingrill import (
    actual_height,
    build_plan,
    course_stones,
    grate_options,
    grid_outer_lengths,
    num_rows,
    run_solution,
)


def test_run_solution_whole_only():
    assert run_solution(240, 10) == (1, 0, 240)


def test_run_solution_half_only():
    assert run_solution(115, 10) == (0, 1, 115)


def test_run_solution_exact_grid():
    assert run_solution(1240, 10) == (5, 0, 1240)


def test_run_solution_with_half_brick():
    assert run_solution(1365, 10) == (5, 1, 1365)


def test_run_solution_rounds_up():
    assert run_solution(1260, 10) == (5, 1, 1365)


def test_run_solution_minimizes_waste():
    assert run_solution(400, 10) == (2, 0, 490)


def test_run_solution_minimizes_stones():
    assert run_solution(500, 10) == (2, 1, 615)


def test_num_rows_exact():
    assert num_rows(800, 10) == 10
    assert actual_height(10, 10) == 800


def test_num_rows_rounds_up():
    assert num_rows(801, 10) == 11


def test_course_stones_even_k():
    assert course_stones(740, 10) == (3, 0, 2, 2, 740)


def test_course_stones_odd_k():
    assert course_stones(615, 10) == (2, 1, 2, 1, 615)


def test_build_plan_counts():
    p = build_plan(
        grate_width=500, grate_depth=400, target_height=800,
        clear=10, joint=10, reserve=5,
    )
    assert (p.back_a, p.back_b) == (3, 1)
    assert (p.side_a, p.side_b) == (2, 1)
    assert p.rows == 10
    assert p.course_a_whole == 3 + 2 * 2
    assert p.course_a_half == 1 + 2 * 1
    assert p.course_b_whole == p.course_a_whole
    assert p.course_b_half == p.course_a_half
    assert p.total_whole == 70
    assert p.total_half == 30
    assert p.total_whole_res == 74
    assert p.total_half_res == 32
    assert p.total_res == 106


def test_build_plan_running_bond_even_k():
    p = build_plan(
        grate_width=496, grate_depth=493, target_height=800,
        clear=10, joint=10, reserve=5,
        inner_width=510, inner_depth=500,
    )
    assert (p.back_a, p.back_b, p.back_a_b, p.back_b_b) == (3, 0, 2, 2)
    assert (p.side_a, p.side_b, p.side_a_b, p.side_b_b) == (2, 1, 2, 1)
    assert p.rows == 10
    assert p.course_a_whole == 7
    assert p.course_a_half == 2
    assert p.course_b_whole == 6
    assert p.course_b_half == 4
    assert p.total_whole == 65
    assert p.total_half == 30
    assert p.total_whole_res == 69
    assert p.total_half_res == 32
    assert p.total_res == 101


def test_build_plan_running_bond_odd_rows():
    p = build_plan(
        grate_width=496, grate_depth=493, target_height=801,
        clear=10, joint=10, reserve=5,
        inner_width=510, inner_depth=500,
    )
    assert p.rows == 11
    assert p.total_whole == 65 + 7
    assert p.total_half == 30 + 2


def test_build_plan_dimensions():
    p = build_plan(
        grate_width=500, grate_depth=400, target_height=800,
        clear=10, joint=10, reserve=5,
    )
    assert p.outer_width == p.back_len
    assert p.outer_depth == p.side_len
    assert p.inner_width == p.outer_width - 2 * 115
    assert p.inner_depth == p.outer_depth - 115


def test_build_plan_zero_reserve():
    p = build_plan(
        grate_width=500, grate_depth=400, target_height=800,
        clear=10, joint=10, reserve=0,
    )
    assert p.total_whole_res == p.total_whole
    assert p.total_half_res == p.total_half


def test_grid_outer_lengths():
    assert grid_outer_lengths(750, 10, window=200) == [615, 740, 865]


def test_grate_options_near_wish():
    opts = grate_options(500, 400, clear=10, joint=10, window=200)
    grates = [(o[0], o[1]) for o in opts]
    assert (496, 368) in grates
    assert (496, 493) in grates


def test_grate_options_sorted_by_distance():
    opts = grate_options(500, 400, clear=10, joint=10, window=200)
    distances = [abs(o[0] - 500) + abs(o[1] - 400) for o in opts]
    assert distances == sorted(distances)


def test_grate_options_limited():
    opts = grate_options(500, 400, clear=10, joint=10, window=200)
    assert len(opts) <= 8
