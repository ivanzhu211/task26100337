"""对齐算法：在 (日志位置, 令牌分布) 状态空间上做 Dijkstra 搜索。"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Optional

from .model import Model

Marking = frozenset  # frozenset[(src_id, dst_id)]，每条边至多一个令牌


@dataclass
class AlignmentResult:
    cost: float
    score: float
    moves: list[tuple]


def _fire_gateway_moves(model: Model, marking: Marking):
    """产出所有可发生的网关流转：(新 marking, 记录用 move)。"""
    results = []
    for node in model.nodes.values():
        if node.type not in ("xor", "and"):
            continue
        incoming = model.incoming[node.id]
        outgoing = model.outgoing[node.id]
        if node.type == "xor":
            if len(incoming) > 1:  # 汇合：任一入边有令牌即可
                for edge in incoming:
                    if edge in marking:
                        new = (marking - {edge}) | {outgoing[0]}
                        results.append((new, ("gateway", node.id)))
            else:  # 分支：任选一条出边
                (in_edge,) = incoming
                if in_edge in marking:
                    for out_edge in outgoing:
                        new = (marking - {in_edge}) | {out_edge}
                        results.append((new, ("gateway", node.id)))
        else:  # and
            if len(incoming) > 1:  # 汇合：所有入边都有令牌
                if all(edge in marking for edge in incoming):
                    new = (marking - set(incoming)) | {outgoing[0]}
                    results.append((new, ("gateway", node.id)))
            else:  # 分支：每条出边各放一个令牌
                (in_edge,) = incoming
                if in_edge in marking:
                    new = (marking - {in_edge}) | set(outgoing)
                    results.append((new, ("gateway", node.id)))
    return results


def _enabled_activities(model: Model, marking: Marking):
    """产出所有可执行的活动：(节点, 新 marking)。"""
    results = []
    for node in model.nodes.values():
        if node.type != "activity":
            continue
        (in_edge,) = model.incoming[node.id]
        if in_edge in marking:
            (out_edge,) = model.outgoing[node.id]
            results.append((node, (marking - {in_edge}) | {out_edge}))
    return results


def _dijkstra(model: Model, trace: list[str]):
    """返回 (最小代价,  predecessor 表, 终点状态)。"""
    start_state = (0, model.initial_marking())
    goal_marking = model.final_marking()
    dist = {start_state: 0}
    pred: dict[tuple, tuple] = {}
    queue = [(0, 0, start_state)]
    counter = 0
    goal_state: Optional[tuple] = None

    while queue:
        cost, _, state = heapq.heappop(queue)
        if cost > dist.get(state, float("inf")):
            continue
        pos, marking = state
        if pos == len(trace) and marking == goal_marking:
            goal_state = state
            break
        # 日志步：事件在模型中没有对应
        if pos < len(trace):
            nxt = (pos + 1, marking)
            counter = _relax(queue, dist, pred, state, nxt, cost + 1,
                             ("log", trace[pos]), counter)
        # 网关流转（0 代价）
        for new_marking, move in _fire_gateway_moves(model, marking):
            nxt = (pos, new_marking)
            counter = _relax(queue, dist, pred, state, nxt, cost, move, counter)
        # 活动：同步步或模型步
        for node, new_marking in _enabled_activities(model, marking):
            if pos < len(trace) and trace[pos] == node.label:
                nxt = (pos + 1, new_marking)
                counter = _relax(queue, dist, pred, state, nxt, cost,
                                 ("sync", node.label), counter)
            nxt = (pos, new_marking)
            counter = _relax(queue, dist, pred, state, nxt, cost + 1,
                             ("model", node.label), counter)

    if goal_state is None:
        raise RuntimeError("no alignment found (model may be unsound)")
    return dist[goal_state], pred, goal_state


def _relax(queue, dist, pred, src, dst, new_cost, move, counter):
    if new_cost < dist.get(dst, float("inf")):
        dist[dst] = new_cost
        pred[dst] = (src, move)
        counter += 1
        heapq.heappush(queue, (new_cost, counter, dst))
    return counter


def _reconstruct(pred, goal_state) -> list[tuple]:
    moves = []
    state = goal_state
    while state in pred:
        state, move = pred[state]
        moves.append(move)
    moves.reverse()
    return moves


def min_run_activities(model: Model) -> int:
    """模型最短完整运行包含的活动数（网关 0 代价）。"""
    start = model.initial_marking()
    goal = model.final_marking()
    dist = {start: 0}
    queue = [(0, 0, start)]
    counter = 0
    while queue:
        cost, _, marking = heapq.heappop(queue)
        if cost > dist.get(marking, float("inf")):
            continue
        if marking == goal:
            return cost
        for new_marking, _ in _fire_gateway_moves(model, marking):
            if cost < dist.get(new_marking, float("inf")):
                dist[new_marking] = cost
                counter += 1
                heapq.heappush(queue, (cost, counter, new_marking))
        for _, new_marking in _enabled_activities(model, marking):
            if cost + 1 < dist.get(new_marking, float("inf")):
                dist[new_marking] = cost + 1
                counter += 1
                heapq.heappush(queue, (cost + 1, counter, new_marking))
    raise RuntimeError("no complete run found (model may be unsound)")


def align(model: Model, trace: list[str]) -> AlignmentResult:
    """计算单条轨迹与模型的最优对齐。"""
    cost, pred, goal_state = _dijkstra(model, list(trace))
    moves = _reconstruct(pred, goal_state)
    denominator = len(trace) + min_run_activities(model)
    score = 1.0 if denominator == 0 else 1.0 - cost / denominator
    return AlignmentResult(cost=cost, score=score, moves=moves)
