# palign — 流程一致性检查器

输入规范流程模型（JSON 有向图）与事件日志（CSV），对每个案例计算最优对齐与一致性得分。

## 模型格式

```json
{
  "nodes": [{"id": "s", "type": "start"},
            {"id": "a1", "type": "activity", "label": "A"},
            {"id": "g1", "type": "xor"},
            {"id": "e", "type": "end"}],
  "edges": [["s", "a1"], ["a1", "g1"], ["g1", "e"]]
}
```

节点类型：`start` / `end` / `activity`（带 label）/ `xor` / `and`。
语义按令牌流转：xor 分支任选一条出边，xor 汇合任一入边即可通过，
and 分支在每条出边各放一个令牌，and 汇合等所有入边都有令牌。

## 日志格式

CSV 含 `case_id`、`activity_name`、`timestamp` 三列，
时间格式 `MM/DD/YYYY hh:mm:ss AM/PM`；同案例按时间升序，同时间保持文件顺序。

## 用法

```python
from palign import align, check_log, load_model

model = load_model("model.json")
al = align(model, ["A", "B"])          # 单条轨迹
print(al.cost, al.score, al.moves)

results = check_log("model.json", "log.csv")   # 整份日志
for case_id, al in results.items():
    print(case_id, al.cost, al.score)
```

- `cost`：最小对齐代价（同步步 0，日志步/模型步 1，网关流转 0）；
- `score`：`1 - cost / (轨迹长度 + 模型最短完整运行活动数)`，分母为 0 时记 1.0；
- `moves`：选中的最优对齐（`sync` / `log` / `model` / `gateway` 序列）。

## 实现

对齐在 (标识, 轨迹位置) 积状态空间上用 Dijkstra 求最短路；
标识为边上令牌集合（健全性保证每边至多一个令牌），状态空间有限，
因此允许循环与纯网关环。详见 `palign/aligner.py`。

## 测试

```bash
python3 -m pytest tests/ -q
```
