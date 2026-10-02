"""流程模型：JSON 有向图的解析与校验。

JSON 格式：
{
  "nodes": [{"id": "n1", "type": "start"},
            {"id": "a1", "type": "activity", "label": "A"},
            {"id": "g1", "type": "xor"}, ...],
  "edges": [["n1", "a1"], ["a1", "g1"], ...]
}
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Node:
    id: str
    type: str  # "start" | "end" | "activity" | "xor" | "and"
    label: str | None = None


@dataclass
class Model:
    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[tuple[str, str]] = field(default_factory=list)
    start_id: str = ""
    end_id: str = ""

    def out_edges(self, node_id: str) -> list[int]:
        return [i for i, (s, _) in enumerate(self.edges) if s == node_id]

    def in_edges(self, node_id: str) -> list[int]:
        return [i for i, (_, t) in enumerate(self.edges) if t == node_id]


def _validate(model: Model) -> None:
    starts = [n for n in model.nodes.values() if n.type == "start"]
    ends = [n for n in model.nodes.values() if n.type == "end"]
    if len(starts) != 1 or len(ends) != 1:
        raise ValueError("模型必须恰好各有一个 start 和 end 节点")
    for node in model.nodes.values():
        indeg = len(model.in_edges(node.id))
        outdeg = len(model.out_edges(node.id))
        if node.type == "start" and (indeg != 0 or outdeg != 1):
            raise ValueError(f"start 节点 {node.id} 必须 0 入 1 出")
        if node.type == "end" and (indeg != 1 or outdeg != 0):
            raise ValueError(f"end 节点 {node.id} 必须 1 入 0 出")
        if node.type == "activity":
            if not node.label:
                raise ValueError(f"activity 节点 {node.id} 缺少 label")
            if indeg != 1 or outdeg != 1:
                raise ValueError(f"activity 节点 {node.id} 必须 1 入 1 出")
        if node.type in ("xor", "and"):
            branch = indeg == 1 and outdeg >= 2
            join = indeg >= 2 and outdeg == 1
            if not (branch or join):
                raise ValueError(f"网关 {node.id} 必须是分支(1入多出)或汇合(多入1出)")


def load_model(path: str) -> Model:
    """从 JSON 文件加载并校验模型。"""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    nodes: dict[str, Node] = {}
    for raw in data["nodes"]:
        node = Node(id=raw["id"], type=raw["type"], label=raw.get("label"))
        if node.id in nodes:
            raise ValueError(f"节点 id 重复: {node.id}")
        if node.type not in ("start", "end", "activity", "xor", "and"):
            raise ValueError(f"未知节点类型: {node.type}")
        nodes[node.id] = node
    edges: list[tuple[str, str]] = []
    for src, dst in data["edges"]:
        if src not in nodes or dst not in nodes:
            raise ValueError(f"边引用了不存在的节点: {src} -> {dst}")
        edges.append((src, dst))
    dup = [e for e, c in Counter(edges).items() if c > 1]
    if dup:
        raise ValueError(f"存在重复边: {dup[0]}")
    model = Model(nodes=nodes, edges=edges)
    model.start_id = next(n.id for n in nodes.values() if n.type == "start")
    model.end_id = next(n.id for n in nodes.values() if n.type == "end")
    _validate(model)
    return model
