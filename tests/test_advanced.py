"""进阶场景：循环、纯网关环、嵌套并行、check_log 端到端。"""
from __future__ import annotations

import json

import pytest

from palign import align, check_log
from palign.model import Model, Node


def loop_model() -> Model:
    """start -> jn(xor 汇合) -> a(A) -> sp(xor 分支) -> end
                          ^                    |
                          +--------------------+
    循环体 A 可执行任意 >=1 次。"""
    nodes = {
        "s": Node("s", "start"),
        "jn": Node("jn", "xor"),
        "a": Node("a", "activity", "A"),
        "sp": Node("sp", "xor"),
        "e": Node("e", "end"),
    }
    edges = [
        ("s", "jn"), ("jn", "a"), ("a", "sp"),
        ("sp", "e"), ("sp", "jn"),
    ]
    return Model(nodes=nodes, edges=edges, start_id="s", end_id="e")


def test_loop_repeated_activity():
    model = loop_model()
    for k in (1, 2, 5):
        result = align(model, ["A"] * k)
        assert result.cost == 0, k
        assert result.score == pytest.approx(1.0), k


def test_loop_extra_and_missing_events():
    model = loop_model()
    # 日志多出一个 B：1 个日志步
    result = align(model, ["A", "B", "A"])
    assert result.cost == 1
    assert result.score == pytest.approx(1.0 - 1 / (3 + 1))


def gateway_only_cycle_model() -> Model:
    """start -> sp(xor) --+----------> jn(xor) -> end
                 |                    ^
                 +--> a(A) -----------+
    sp 到 jn 的直连边与 sp->a->jn 构成不含活动的旁路。"""
    nodes = {
        "s": Node("s", "start"),
        "sp": Node("sp", "xor"),
        "a": Node("a", "activity", "A"),
        "jn": Node("jn", "xor"),
        "e": Node("e", "end"),
    }
    edges = [
        ("s", "sp"), ("sp", "a"), ("a", "jn"),
        ("sp", "jn"), ("jn", "e"),
    ]
    return Model(nodes=nodes, edges=edges, start_id="s", end_id="e")


def test_gateway_only_path_allows_empty_trace():
    model = gateway_only_cycle_model()
    result = align(model, [])
    assert result.cost == 0
    assert result.score == 1.0  # 分母为 0 时记 1.0


def test_gateway_only_path_with_activity():
    model = gateway_only_cycle_model()
    result = align(model, ["A"])
    assert result.cost == 0
    assert result.score == pytest.approx(1.0)


def nested_model() -> Model:
    """循环里嵌套并行块：jn -> fork -> {P, Q} -> join -> sp -> (end | 回环)。"""
    nodes = {
        "s": Node("s", "start"),
        "jn": Node("jn", "xor"),
        "fork": Node("fork", "and"),
        "p": Node("p", "activity", "P"),
        "q": Node("q", "activity", "Q"),
        "join": Node("join", "and"),
        "sp": Node("sp", "xor"),
        "e": Node("e", "end"),
    }
    edges = [
        ("s", "jn"), ("jn", "fork"),
        ("fork", "p"), ("fork", "q"),
        ("p", "join"), ("q", "join"),
        ("join", "sp"), ("sp", "e"), ("sp", "jn"),
    ]
    return Model(nodes=nodes, edges=edges, start_id="s", end_id="e")


def test_nested_parallel_in_loop():
    model = nested_model()
    result = align(model, ["P", "Q", "Q", "P"])
    assert result.cost == 0
    assert result.score == pytest.approx(1.0)


def test_check_log_end_to_end(tmp_path):
    model = {
        "nodes": [
            {"id": "s", "type": "start"},
            {"id": "sp", "type": "xor"},
            {"id": "a1", "type": "activity", "label": "A"},
            {"id": "b", "type": "activity", "label": "B"},
            {"id": "a2", "type": "activity", "label": "A"},
            {"id": "c", "type": "activity", "label": "C"},
            {"id": "jn", "type": "xor"},
            {"id": "e", "type": "end"},
        ],
        "edges": [
            ["s", "sp"], ["sp", "a1"], ["a1", "b"], ["b", "jn"],
            ["sp", "a2"], ["a2", "c"], ["c", "jn"], ["jn", "e"],
        ],
    }
    model_path = tmp_path / "model.json"
    model_path.write_text(json.dumps(model), encoding="utf-8")
    csv_path = tmp_path / "log.csv"
    csv_path.write_text(
        "case_id,activity_name,timestamp\n"
        "c1,A,01/02/2024 09:00:00 AM\n"
        "c1,C,01/02/2024 09:05:00 AM\n"
        "c2,A,01/02/2024 10:00:00 AM\n"
        "c2,B,01/02/2024 10:05:00 AM\n"
        "c3,A,01/02/2024 11:00:00 AM\n",
        encoding="utf-8",
    )
    results = check_log(str(model_path), str(csv_path))
    assert set(results) == {"c1", "c2", "c3"}
    assert results["c1"].cost == 0 and results["c1"].score == pytest.approx(1.0)
    assert results["c2"].cost == 0 and results["c2"].score == pytest.approx(1.0)
    assert results["c3"].cost == 1
    assert results["c3"].score == pytest.approx(1.0 - 1 / 3)
