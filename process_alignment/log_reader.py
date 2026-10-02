"""CSV 事件日志读取。"""
from __future__ import annotations

import csv
from datetime import datetime

TIMESTAMP_FORMAT = "%m/%d/%Y %I:%M:%S %p"


def read_log(csv_path: str) -> dict[str, list[str]]:
    """读取 CSV，返回 case_id -> 按时间升序排列的活动名列表。

    CSV 需包含 case_id、activity_name、timestamp 三列，
    timestamp 格式为 "MM/DD/YYYY hh:mm:ss AM/PM"。
    时间相同的事件保持文件中的先后顺序（稳定排序）。
    """
    events: dict[str, list[tuple[datetime, int, str]]] = {}
    with open(csv_path, "r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for order, row in enumerate(reader):
            case_id = row["case_id"]
            timestamp = datetime.strptime(row["timestamp"].strip(), TIMESTAMP_FORMAT)
            events.setdefault(case_id, []).append(
                (timestamp, order, row["activity_name"])
            )

    traces: dict[str, list[str]] = {}
    for case_id, case_events in events.items():
        case_events.sort(key=lambda item: (item[0], item[1]))
        traces[case_id] = [name for _, _, name in case_events]
    return traces
