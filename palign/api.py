"""对外 API：align 与 check_log。"""
from __future__ import annotations

from .aligner import Alignment, Move, align
from .logreader import read_log
from .model import Model, load_model

__all__ = ["align", "check_log", "Alignment", "Move", "Model", "load_model"]


def check_log(model_path: str, csv_path: str) -> dict[str, Alignment]:
    """对日志中每个案例计算最优对齐，返回 {case_id: Alignment}。"""
    model = load_model(model_path)
    traces = read_log(csv_path)
    return {case_id: align(model, trace) for case_id, trace in traces.items()}
