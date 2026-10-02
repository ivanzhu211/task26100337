"""对齐算法：在 (标识, 轨迹位置) 积状态空间上求最短路。

状态 = (marking, i)：marking 为令牌分布，i 为已消费的事件数。
- 同步步：活动点火且 label 与 trace[i] 相同，代价 0，i 前进；
- 模型步：活动点火但日志没有对应事件，代价 1，i 不动；
- 日志步：trace[i] 在模型当前状态下无法同步，代价 1，仅 i 前进；
- 网关流转：代价 0，i 不动。

终点：marking == final_marking 且 i == len(trace)。
用 Dijkstra 求最小代价并回溯一条最优对齐。
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field

from .model import Model
from .semantics import (
    Marking,
    enabled_transitions,
    final_marking,
    fire,
    initial_marking,
)


@dataclass
class Move:
    kind: str  # "sync" | "log" | "model" | "gateway"
    label: str | None = None   # 活动 label（日志步/网关为 None）
    event: str | None = None   # 对应的日志事件名（模型步/网关为 None）
    node_id: str | None = None


@dataclass
class Alignment:
    cost: int
    score: float
    moves: list[Move] = field(default_factory=list)


def _min_run_activities(model: Model) -> int:
    """模型最短完整运行的活动数（活动代价 1，网关 0）。"""
    start, goal = initial_marking(model), final_marking(model)
    dist: dict[Marking, int] = {start: 0}
    heap: list[tuple[int, int, Marking]] = [(0, 0, start)]
    counter = 1
    while heap:
        d, _, marking = heapq.heappop(heap)
        if marking == goal:
            return d
        if d > dist.get(marking, 1 << 60):
            continue
        for t in enabled_transitions(model, marking):
            w = 1 if model.nodes[t.node_id].type == "activity" else 0
            nxt = fire(model, marking, t)
            nd = d + w
            if nd < dist.get(nxt, 1 << 60):
                dist[nxt] = nd
                heapq.heappush(heap, (nd, counter, nxt))
                counter += 1
    raise ValueError("模型无法到达结束状态（与健全性假设矛盾）")


def align(model: Model, trace: list[str]) -> Alignment:
    start = (initial_marking(model), 0)
    goal_marking = final_marking(model)
    n = len(trace)

    dist: dict[tuple[Marking, int], int] = {start: 0}
    parent: dict[tuple[Marking, int], tuple[tuple[Marking, int], Move]] = {}
    heap: list[tuple[int, int, tuple[Marking, int]]] = [(0, 0, start)]
    counter = 1
    goal_state: tuple[Marking, int] | None = None

    while heap:
        d, _, state = heapq.heappop(heap)
        if d > dist.get(state, 1 << 60):
            continue
        marking, i = state
        if marking == goal_marking and i == n:
            goal_state = state
            break

        def relax(nxt: tuple[Marking, int], w: int, move: Move) -> None:
            nonlocal counter
            nd = d + w
            if nd < dist.get(nxt, 1 << 60):
                dist[nxt] = nd
                parent[nxt] = (state, move)
                heapq.heappush(heap, (nd, counter, nxt))
                counter += 1

        for t in enabled_transitions(model, marking):
            node = model.nodes[t.node_id]
            nxt_marking = fire(model, marking, t)
            if node.type == "activity":
                if i < n and trace[i] == node.label:
                    relax((nxt_marking, i + 1), 0,
                          Move("sync", label=node.label, event=trace[i], node_id=node.id))
                relax((nxt_marking, i), 1,
                      Move("model", label=node.label, node_id=node.id))
            else:
                relax((nxt_marking, i), 0, Move("gateway", node_id=node.id))
        if i < n:
            relax((marking, i + 1), 1, Move("log", event=trace[i]))

    if goal_state is None:
        raise ValueError("无法完成对齐（与健全性假设矛盾）")

    moves: list[Move] = []
    state = goal_state
    while state != start:
        prev, move = parent[state]
        moves.append(move)
        state = prev
    moves.reverse()

    cost = dist[goal_state]
    min_acts = _min_run_activities(model)
    denom = n + min_acts
    score = 1.0 if denom == 0 else 1.0 - cost / denom
    return Alignment(cost=cost, score=score, moves=moves)
