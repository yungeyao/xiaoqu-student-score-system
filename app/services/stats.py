"""成绩统计核心算法。

统计口径统一在这里定义，三级（班级 / 年级 / 全校）统计都复用它：

* 缺考用 ``is not None`` 严格判断 —— 0 分是有效成绩，只有 NULL 才是缺考。
* ``stu_cnt`` 应考人数（含缺考），``chengji_cnt`` 实考人数。
* 除参试率外，所有率的分母都是实考人数。
* 样本标准差（除以 n-1）；n < 2 时返回 None 而不是除零。
* 偶数个数据的中位数取中间两个数的平均，四分位用 (n-1) 线性插值。
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Optional, Sequence

Number = float


# ------------------------------------------------------------------ 基础统计


def _clean(scores: Iterable[Optional[Number]]) -> list[Number]:
    """剔除缺考 (None), 保留 0 分。"""
    return [float(s) for s in scores if s is not None]


def average(values: Sequence[Number]) -> Optional[Number]:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def variance(values: Sequence[Number], sample: bool = True) -> Optional[Number]:
    """方差。sample=True 用 n-1 (样本方差), False 用 n (总体方差)。"""
    n = len(values)
    if n == 0 or (sample and n < 2):
        return None
    avg = sum(values) / n
    divisor = (n - 1) if sample else n
    return sum((v - avg) ** 2 for v in values) / divisor


def std_dev(values: Sequence[Number], sample: bool = True) -> Optional[Number]:
    """标准差。默认按样本口径 (n-1)。"""
    var = variance(values, sample=sample)
    if var is None:
        return None
    return round(math.sqrt(var), 2)


def median(values: Sequence[Number]) -> Optional[Number]:
    """中位数。"""
    if not values:
        return None
    arr = sorted(values)
    n = len(arr)
    if n == 1:
        return round(arr[0], 2)
    if n == 2:
        return round((arr[0] + arr[1]) / 2, 2)
    if n % 2 == 1:
        return round(arr[(n - 1) // 2], 2)
    # 偶数个：中间两个数的平均
    return round((arr[n // 2 - 1] + arr[n // 2]) / 2, 2)


def mode(values: Sequence[Number], min_freq: int = 3) -> Optional[str]:
    """众数。

    出现次数不足 ``min_freq`` 次时不返回众数（默认 3 次，避免一两个巧合值撑起指标）；
    并列众数按数值降序用「、」拼接。
    """
    if not values:
        return None
    counter = Counter(values)
    if not counter:
        return None
    top = max(counter.values())
    if top < min_freq:
        return None
    picked = sorted((v for v, c in counter.items() if c == top), reverse=True)
    return ", ".join(str(_fmt(v)) for v in picked)


def _fmt(v: Number) -> object:
    """整数去掉小数点, 例如 90.0 -> 90。"""
    return int(v) if float(v).is_integer() else round(v, 1)


def quartile(values: Sequence[Number], q: float) -> Optional[Number]:
    """四分位数，采用 (n-1) 线性插值法。

    ``q`` 取 0.25 / 0.5 / 0.75。样本少于 5 个时四分位区分度不足，返回 None。
    """
    arr = sorted(values)
    n = len(arr)
    if n < 5:
        return None
    pos = 1 + (n - 1) * q  # 1-based 位置
    if pos.is_integer():
        return round(arr[int(pos) - 1], 2)
    floor_pos = math.floor(pos)
    frac = pos - floor_pos
    # 0-based：arr[floor_pos - 1] 是下界，arr[floor_pos] 是上界
    value = arr[floor_pos] * frac + arr[floor_pos - 1] * (1 - frac)
    return round(value, 2)


def rate(values: Sequence[Number], line: Optional[Number]) -> Optional[int]:
    """统计达到分数线的人数。"""
    if line is None:
        return None
    return sum(1 for v in values if v >= line)


def ratio(numerator: Optional[int], denominator: Optional[int]) -> Optional[Number]:
    """百分比, 分母为 0 或 None 时返回 None。"""
    if numerator is None or not denominator:
        return None
    return round(numerator / denominator * 100, 2)


# ------------------------------------------------------------------ 排名


def rank_values(pairs: Sequence[tuple[int, Optional[Number]]]) -> dict[int, tuple[int, Optional[Number]]]:
    """并列同名次排名，返回 {id: (paixu, weizhi)}。

    规则：
      * 降序排列；
      * 名次 ``rank`` 只在成绩发生变化时跳号，同分并列；
      * 位置百分位 ``weizhi = (cnt - rank) / (cnt - 1) * 100``；
      * 只有 1 人时 paixu=1、weizhi=100。
    """
    valid = [(cid, float(score)) for cid, score in pairs if score is not None]
    cnt = len(valid)
    result: dict[int, tuple[int, Optional[Number]]] = {}
    if cnt == 0:
        return result

    valid.sort(key=lambda x: x[1], reverse=True)

    if cnt == 1:
        result[valid[0][0]] = (1, 100.0)
        return result

    rank = 0
    prev: Optional[float] = None
    for i, (cid, score) in enumerate(valid, start=1):
        if prev is None or score != prev:
            rank = i
            prev = score
        weizhi = round((cnt - rank) / (cnt - 1) * 100, 2)
        result[cid] = (rank, weizhi)
    return result


def standard_score(
    defen: Optional[Number], avg: Optional[Number], std: Optional[Number]
) -> Optional[Number]:
    """标准分 Z = (得分 − 全区平均分) / 全区标准差。"""
    if defen is None or avg is None or std is None or std == 0:
        return None
    return round((float(defen) - float(avg)) / float(std), 2)


# ------------------------------------------------------------------ 汇总入口


def tongji_subject(
    scores: Iterable[Optional[Number]],
    manfen: Number = 100,
    youxiu: Optional[Number] = None,
    lianghao: Optional[Number] = None,
    jige: Optional[Number] = None,
) -> dict:
    """单学科统计，返回与 tongji_* 表字段一一对应的字典。

    ``scores`` 为该范围内每个学生的得分列表，None 表示缺考。
    """
    raw = list(scores)
    values = _clean(raw)

    stu_cnt = len(raw)
    chengji_cnt = len(values)
    if chengji_cnt == 0:
        return {
            "stu_cnt": stu_cnt,
            "chengji_cnt": 0,
            "sum": None,
            "avg": None,
            "defenlv": None,
            "biaozhuncha": None,
            "youxiu": None,
            "lianghao": None,
            "jige": None,
            "youxiulv": None,
            "lianghaolv": None,
            "jigelv": None,
            "canshilv": 0.0,
            "chashenglv": None,
            "max": None,
            "min": None,
            "q1": None,
            "q2": None,
            "q3": None,
            "zhongshu": None,
            "zhongweishu": None,
        }

    total = round(sum(values), 1)
    avg = average(values)
    std = std_dev(values, sample=True)

    youxiu_cnt = rate(values, youxiu)
    lianghao_cnt = rate(values, lianghao)
    jige_cnt = rate(values, jige)

    return {
        "stu_cnt": stu_cnt,
        "chengji_cnt": chengji_cnt,
        "sum": total,
        "avg": avg,
        "defenlv": round(avg / manfen * 100, 2) if manfen else None,
        "biaozhuncha": std,
        "youxiu": youxiu_cnt,
        "lianghao": lianghao_cnt,
        "jige": jige_cnt,
        "youxiulv": ratio(youxiu_cnt, chengji_cnt),
        "lianghaolv": ratio(lianghao_cnt, chengji_cnt),
        "jigelv": ratio(jige_cnt, chengji_cnt),
        "canshilv": ratio(chengji_cnt, stu_cnt),
        "chashenglv": round((chengji_cnt - (jige_cnt or 0)) / chengji_cnt * 100, 2),
        "max": round(max(values), 1),
        "min": round(min(values), 1),
        "q1": quartile(values, 0.25),
        "q2": quartile(values, 0.5),
        "q3": quartile(values, 0.75),
        "zhongshu": mode(values),
        "zhongweishu": median(values),
    }
