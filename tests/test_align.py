"""对齐器测试。"""
from __future__ import annotations

import itertools

import pytest

from palign import align
from palign.model import Model, Node


def xor_same_label_model() -> Model:
    """start -> sp(xor) -> a1(A) -> b(B) --+
                 |                        +-> jn(xor) -> end
                 +-------> a2(A) -> c(C) -+
    两条分支都以 label A 开头，必须看后续事件才能分辨。"""
    nodes = {
        "s": Node("s", "start"),
        "sp": Node("sp", "xor"),
        "a1": Node("a1", "activity", "A"),
        "b": Node("b", "activity", "B"),
        "a2": Node("a2", "activity", "A"),
        "c": Node("c", "activity", "C"),
        "jn": Node("jn", "xor"),
        "e": Node("e", "end"),
    }
    edges = [
        ("s", "sp"), ("sp", "a1"), ("a1", "b"), ("b", "jn"),
        ("sp", "a2"), ("a2", "c"), ("c", "jn"), ("jn", "e"),
    ]
    return Model(nodes=nodes, edges=edges, start_id="s", end_id="e")


def test_xor_same_label_disambiguated_by_later_event():
    model = xor_same_label_model()
    # 轨迹 [A, C] 只能走第二支；贪心选第一支会得到 cost 2
    result = align(model, ["A", "C"])
    assert result.cost == 0
    assert result.score == pytest.approx(1.0)
    syncs = [mv for mv in result.moves if mv.kind == "sync"]
    assert [(mv.label, mv.node_id) for mv in syncs] == [("A", "a2"), ("C", "c")]

    result = align(model, ["A", "B"])
    assert result.cost == 0
    assert result.score == pytest.approx(1.0)
    syncs = [mv for mv in result.moves if mv.kind == "sync"]
    assert [(mv.label, mv.node_id) for mv in syncs] == [("A", "a1"), ("B", "b")]


def test_xor_same_label_partial_trace():
    model = xor_same_label_model()
    # 只有 [A]：任一分支都缺一个活动，最优 cost = 1
    # 分母 = 1(轨迹长) + 2(最短运行活动数) = 3
    result = align(model, ["A"])
    assert result.cost == 1
    assert result.score == pytest.approx(1.0 - 1 / 3)


def parallel_model() -> Model:
    """start -> fork(and) -> p(P) --+
                 |                 +-> join(and) -> end
                 +-------> q(Q) ---+"""
    nodes = {
        "s": Node("s", "start"),
        "fork": Node("fork", "and"),
        "p": Node("p", "activity", "P"),
        "q": Node("q", "activity", "Q"),
        "join": Node("join", "and"),
        "e": Node("e", "end"),
    }
    edges = [
        ("s", "fork"), ("fork", "p"), ("fork", "q"),
        ("p", "join"), ("q", "join"), ("join", "e"),
    ]
    return Model(nodes=nodes, edges=edges, start_id="s", end_id="e")


def test_parallel_interleavings_score_1():
    model = parallel_model()
    for trace in itertools.permutations(["P", "Q"]):
        result = align(model, list(trace))
        assert result.cost == 0, trace
        assert result.score == pytest.approx(1.0), trace


def parallel3_model() -> Model:
    """三路并行块：R、S、T 任意交错。"""
    nodes = {
        "s": Node("s", "start"),
        "fork": Node("fork", "and"),
        "r": Node("r", "activity", "R"),
        "u": Node("u", "activity", "S"),
        "t": Node("t", "activity", "T"),
        "join": Node("join", "and"),
        "e": Node("e", "end"),
    }
    edges = [("s", "fork")] + [("fork", x) for x in ("r", "u", "t")] \
        + [(x, "join") for x in ("r", "u", "t")] + [("join", "e")]
    return Model(nodes=nodes, edges=edges, start_id="s", end_id="e")


def test_parallel3_all_interleavings_score_1():
    model = parallel3_model()
    for trace in itertools.permutations(["R", "S", "T"]):
        result = align(model, list(trace))
        assert result.cost == 0, trace
        assert result.score == pytest.approx(1.0), trace
