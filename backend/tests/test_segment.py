import math

import pytest

from app.engine.segment_tree import SegmentTree


def test_build_total_query():
    s = SegmentTree([30, 35, 20, 15], ["Price", "Perf", "Batt", "Wt"])
    assert s.total() == 100
    assert s.range_query(0, 3) == 100
    assert s.range_query(1, 2) == 55
    assert s.range_query(2, 2) == 20


def test_point_update_and_affected_path():
    s = SegmentTree([30, 35, 20, 15])
    touched = s.point_update(1, 50)
    assert s.total() == 115
    assert s.range_query(1, 1) == 50
    # root-to-leaf path: height + 1 nodes touched
    assert len(touched) == math.ceil(math.log2(4)) + 1
    assert touched[0] == 1  # starts at root


def test_update_out_of_range():
    s = SegmentTree([1, 2])
    with pytest.raises(IndexError):
        s.point_update(5, 9)


def test_empty_tree():
    s = SegmentTree()
    assert s.total() == 0.0
    assert s.range_query(0, 3) == 0.0


def test_snapshot_marks_touched():
    s = SegmentTree([10, 20, 30], ["a", "b", "c"])
    s.point_update(2, 99)
    snap = s.snapshot()
    touched = [n for n in snap["nodes"] if n["touched"]]
    assert len(touched) == len(snap["affected"]) > 0
    assert snap["total"] == 129
