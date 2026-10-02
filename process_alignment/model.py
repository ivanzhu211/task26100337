"""流程模型：JSON 有向图的加载与校验。"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Node:
    id: str
    type: str  # "start" | "end" | "activity" | "xor" | "and"
    label: Optional[str] = None


@dataclass
class Model:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    outgoing: dict[str, list[str]] = field(default_factory=dict)
    incoming: dict[str, list[str]] = field(default_factory=dict)
    start_id: str = ""
    end_id: str = ""

    def initial_marking(self) -> frozenset[tuple[str, str]]:
        """start 的唯一出边上放一个令牌。"""
        src, dst = self.outgoing[self.start_id][0]
        return frozenset({(src, dst)})

    def final_marking(self) -> frozenset[tuple[str, str]]:
        """只剩 end 的唯一入边上有令牌。"""
        src, dst = self.incoming[self.end_id][0]
        return frozenset({(src, dst)})


def load_model(path: str) -> Model:
    """从 JSON 文件加载模型。

    JSON 格式::

        {
          "nodes": [{"id": "...", "type": "start|end|activity|xor|and",
                      "label": "..."}],   # label 仅 activity 需要
          "edges": [["src_id", "dst_id"], ...]
        }
    """
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    nodes = {}
    for raw in data["nodes"]:
        node = Node(id=raw["id"], type=raw["type"], label=raw.get("label"))
        if node.id in nodes:
            raise ValueError(f"duplicate node id: {node.id}")
        if node.type == "activity" and not node.label:
            raise ValueError(f"activity node {node.id} missing label")
        nodes[node.id] = node

    edges = [tuple(e) for e in data["edges"]]
    outgoing: dict[str, list[tuple[str, str]]] = {nid: [] for nid in nodes}
    incoming: dict[str, list[tuple[str, str]]] = {nid: [] for nid in nodes}
    for src, dst in edges:
        if src not in nodes or dst not in nodes:
            raise ValueError(f"edge references unknown node: {src} -> {dst}")
        outgoing[src].append((src, dst))
        incoming[dst].append((src, dst))

    starts = [n for n in nodes.values() if n.type == "start"]
    ends = [n for n in nodes.values() if n.type == "end"]
    model = Model(
        nodes=nodes,
        edges=edges,
        outgoing=outgoing,
        incoming=incoming,
        start_id=starts[0].id if len(starts) == 1 else "",
        end_id=ends[0].id if len(ends) == 1 else "",
    )
    validate_model(model)
    return model


def validate_model(model: Model) -> None:
    """校验结构约束。"""
    starts = [n for n in model.nodes.values() if n.type == "start"]
    ends = [n for n in model.nodes.values() if n.type == "end"]
    if len(starts) != 1:
        raise ValueError(f"expected exactly 1 start node, got {len(starts)}")
    if len(ends) != 1:
        raise ValueError(f"expected exactly 1 end node, got {len(ends)}")

    for node in model.nodes.values():
        out_deg = len(model.outgoing[node.id])
        in_deg = len(model.incoming[node.id])
        if node.type == "start":
            if in_deg != 0 or out_deg != 1:
                raise ValueError("start must have 0 incoming and 1 outgoing edge")
        elif node.type == "end":
            if in_deg != 1 or out_deg != 0:
                raise ValueError("end must have 1 incoming and 0 outgoing edges")
        elif node.type == "activity":
            if in_deg != 1 or out_deg != 1:
                raise ValueError(f"activity {node.id} must have exactly 1 in / 1 out")
        elif node.type in ("xor", "and"):
            is_split = in_deg == 1 and out_deg > 1
            is_join = in_deg > 1 and out_deg == 1
            if not (is_split or is_join):
                raise ValueError(
                    f"gateway {node.id} must be a split (1-in/n-out) or join (n-in/1-out)"
                )
        else:
            raise ValueError(f"unknown node type: {node.type}")
