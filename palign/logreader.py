"""CSV 事件日志读取。

CSV 需包含 case_id、activity_name、timestamp 三列，
timestamp 格式为 "MM/DD/YYYY hh:mm:ss AM/PM"。
同一案例的事件按时间升序排列，时间相同保持文件中的先后顺序
（Python 的 sorted 是稳定排序，按时间键排序即可）。
"""
from __future__ import annotations

import csv
from datetime import datetime

_TS_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def read_log(csv_path: str) -> dict[str, list[str]]:
    """返回 {case_id: [activity_name, ...]}，按时间升序、同时间保持文件顺序。"""
    rows: list[tuple[str, str, datetime]] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = {"case_id", "activity_name", "timestamp"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"CSV 缺少列: {sorted(missing)}")
        for lineno, row in enumerate(reader, start=2):
            try:
                ts = datetime.strptime(row["timestamp"].strip(), _TS_FORMAT)
            except ValueError as exc:
                raise ValueError(f"第 {lineno} 行时间格式错误: {row['timestamp']!r}") from exc
            rows.append((row["case_id"], row["activity_name"], ts))
    rows.sort(key=lambda r: r[2])
    traces: dict[str, list[str]] = {}
    for case_id, activity, _ in rows:
        traces.setdefault(case_id, []).append(activity)
    return traces
