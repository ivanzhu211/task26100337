"""令牌流转语义：标识(marking)、可点火变迁、点火。

标识用 frozenset[int] 表示，元素是边上令牌（edges 列表的下标）。
变迁 = (节点, 消耗的边集合, 产生的边集合)，由节点类型决定：

- activity：消耗唯一入边，产生唯一出边；
- xor 分支：消耗入边，在任选一条出边上放令牌（每条出边一个变迁）；
- xor 汇合：任一入边有令牌即可过（每条有令牌的入边一个变迁）；
- and 分支：消耗入边，在每条出边上各放一个令牌；
- and 汇合：所有入边都有令牌时一起消耗，产生唯一出边。
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import Model

Marking = frozenset[int]


@dataclass(frozen=True)
class Transition:
    node_id: str
    consume: frozenset[int]
    produce: frozenset[int]


def initial_marking(model: Model) -> Marking:
    return frozenset(model.out_edges(model.start_id))


def final_marking(model: Model) -> Marking:
    return frozenset(model.in_edges(model.end_id))


def enabled_transitions(model: Model, marking: Marking) -> list[Transition]:
    result: list[Transition] = []
    for node in model.nodes.values():
        ins = model.in_edges(node.id)
        outs = model.out_edges(node.id)
        if node.type == "activity":
            if ins[0] in marking:
                result.append(Transition(node.id, frozenset(ins), frozenset(outs)))
        elif node.type == "xor":
            if len(ins) == 1:  # 分支
                if ins[0] in marking:
                    for o in outs:
                        result.append(Transition(node.id, frozenset(ins), frozenset({o})))
            else:  # 汇合
                for i in ins:
                    if i in marking:
                        result.append(Transition(node.id, frozenset({i}), frozenset(outs)))
        elif node.type == "and":
            if len(ins) == 1:  # 分支
                if ins[0] in marking:
                    result.append(Transition(node.id, frozenset(ins), frozenset(outs)))
            else:  # 汇合
                if all(i in marking for i in ins):
                    result.append(Transition(node.id, frozenset(ins), frozenset(outs)))
    return result


def fire(model: Model, marking: Marking, transition: Transition) -> Marking:
    return (marking - transition.consume) | transition.produce
