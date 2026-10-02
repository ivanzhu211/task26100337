from .model import Model, Node, load_model
from .aligner import AlignmentResult, align, min_run_activities
from .log_reader import read_log


def check_log(model_path: str, csv_path: str) -> dict[str, AlignmentResult]:
    """对日志中每个案例计算最优对齐与一致性得分。"""
    model = load_model(model_path)
    traces = read_log(csv_path)
    return {case_id: align(model, trace) for case_id, trace in traces.items()}


__all__ = [
    "Model",
    "Node",
    "load_model",
    "AlignmentResult",
    "align",
    "min_run_activities",
    "read_log",
    "check_log",
]
