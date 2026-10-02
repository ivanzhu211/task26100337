import json
import os
import tempfile
import unittest

from process_alignment import align, check_log, load_model


def write_json(data):
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(data, fh)
    fh.close()
    return fh.name


XOR_MODEL = {
    "nodes": [
        {"id": "s", "type": "start"},
        {"id": "x1", "type": "xor"},
        {"id": "a1", "type": "activity", "label": "A"},
        {"id": "b1", "type": "activity", "label": "B"},
        {"id": "a2", "type": "activity", "label": "A"},
        {"id": "c1", "type": "activity", "label": "C"},
        {"id": "x2", "type": "xor"},
        {"id": "e", "type": "end"},
    ],
    "edges": [
        ["s", "x1"],
        ["x1", "a1"], ["a1", "b1"], ["b1", "x2"],
        ["x1", "a2"], ["a2", "c1"], ["c1", "x2"],
        ["x2", "e"],
    ],
}

PAR_MODEL = {
    "nodes": [
        {"id": "s", "type": "start"},
        {"id": "p1", "type": "and"},
        {"id": "a", "type": "activity", "label": "A"},
        {"id": "b", "type": "activity", "label": "B"},
        {"id": "p2", "type": "and"},
        {"id": "e", "type": "end"},
    ],
    "edges": [
        ["s", "p1"],
        ["p1", "a"], ["p1", "b"],
        ["a", "p2"], ["b", "p2"],
        ["p2", "e"],
    ],
}


class XorDisambiguationTest(unittest.TestCase):
    """两条分支以同一 label 开头，必须看后续事件才能选对分支。"""

    @classmethod
    def setUpClass(cls):
        cls.model_path = write_json(XOR_MODEL)
        cls.model = load_model(cls.model_path)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.model_path)

    def test_upper_branch(self):
        result = align(self.model, ["A", "B"])
        self.assertEqual(result.cost, 0)
        self.assertEqual(result.score, 1.0)
        syncs = [m for m in result.moves if m[0] == "sync"]
        self.assertEqual(syncs, [("sync", "A"), ("sync", "B")])

    def test_lower_branch(self):
        result = align(self.model, ["A", "C"])
        self.assertEqual(result.cost, 0)
        self.assertEqual(result.score, 1.0)

    def test_deviating_trace(self):
        # A,B 后再多一个 C：最优代价为 1（C 作为日志步）
        result = align(self.model, ["A", "B", "C"])
        self.assertEqual(result.cost, 1)
        # 分母 = 3（轨迹长）+ 2（最短运行活动数 A,B 或 A,C）
        self.assertAlmostEqual(result.score, 1 - 1 / 5)

    def test_missing_activity(self):
        # 只有 A：缺一个活动，最优代价为 1（模型步）
        result = align(self.model, ["A"])
        self.assertEqual(result.cost, 1)
        self.assertAlmostEqual(result.score, 1 - 1 / 3)


class ParallelInterleavingTest(unittest.TestCase):
    """并行块内任意顺序交错的轨迹必须得分 1.0。"""

    @classmethod
    def setUpClass(cls):
        cls.model_path = write_json(PAR_MODEL)
        cls.model = load_model(cls.model_path)

    @classmethod
    def tearDownClass(cls):
        os.unlink(cls.model_path)

    def test_both_orders_perfect(self):
        for trace in (["A", "B"], ["B", "A"]):
            with self.subTest(trace=trace):
                result = align(self.model, trace)
                self.assertEqual(result.cost, 0)
                self.assertEqual(result.score, 1.0)


class CheckLogTest(unittest.TestCase):
    def test_end_to_end(self):
        model_path = write_json(PAR_MODEL)
        csv_text = (
            "case_id,activity_name,timestamp\n"
            "1,A,01/01/2024 09:00:00 AM\n"
            "1,B,01/01/2024 10:00:00 AM\n"
            "2,B,01/02/2024 09:00:00 AM\n"
            "2,A,01/02/2024 08:00:00 AM\n"
            "3,A,01/03/2024 09:00:00 AM\n"
            "3,X,01/03/2024 09:30:00 AM\n"
            "3,B,01/03/2024 10:00:00 AM\n"
        )
        fh = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False)
        fh.write(csv_text)
        fh.close()
        try:
            results = check_log(model_path, fh.name)
        finally:
            os.unlink(model_path)
            os.unlink(fh.name)

        self.assertEqual(set(results), {"1", "2", "3"})
        # 案例 2 的事件在文件中乱序，按时间重排后为 A,B
        self.assertEqual(results["1"].score, 1.0)
        self.assertEqual(results["2"].score, 1.0)
        # 案例 3 多一个未知事件 X：cost 1，分母 3 + 2
        self.assertEqual(results["3"].cost, 1)
        self.assertAlmostEqual(results["3"].score, 1 - 1 / 5)


if __name__ == "__main__":
    unittest.main()
