"""L2 十档特征 → 与 K 线对齐的 5min 张量（真正的 L2 预测头的输入）。

读取 `parsed_multi/`（每个文件 = 一日期 × 一票的 3 秒快照），
按 5min 桶聚合并对齐到 `runs/tensor/5min` 的 (codes, times)。
L2 覆盖之外的日期填 NaN（窗口索引负责剔除）。

特征（7 维，全部是订单簿**状态**，OHLCV 无法推断）：
    imb1  一档买卖量失衡 (bid1-ask1)/(bid1+ask1)
    imb5  五档失衡
    imb10 十档失衡
    ofi   订单流不平衡（Cont-Kukanov）
    slope5 五档深度斜率
    spread 买卖价差 / 中间价
    dmid  桶内中间价变动（快照变动之和 = 桶级 mid 收益）

聚合口径：状态特征取桶内均值，dmid 取桶内和（等价于桶级 mid 收益）。

用法（在 GPU 服务器上跑，数据在那边）：
    python -m xy.data.l2_tensor --parsed $W/l2/parsed_multi
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

from xy.paths import RUNS

FEATURES = ["imb1", "imb5", "imb10", "ofi", "slope5", "spread"]
SUM_FEATURES = ["dmid"]
ALL_FEATURES = FEATURES + SUM_FEATURES
FREQ = 5


def bar_of(sec: np.ndarray) -> np.ndarray:
    """当日秒数 → 5min 桶起点（分钟数，与 K 线侧 bucket 一致）。"""
    minute = (sec // 60).astype(int)
    return (minute // FREQ) * FREQ


def build(parsed: str, out_name: str = "micro_l2_5min") -> None:
    k_meta = json.loads((RUNS / "tensor" / "5min" / "meta.json").read_text(encoding="utf-8"))
    codes = k_meta["codes"]
    times = k_meta["times"]
    ci = {c: i for i, c in enumerate(codes)}
    ti = {t: i for i, t in enumerate(times)}

    n_code, n_time, n_f = len(codes), len(times), len(ALL_FEATURES)
    x = np.full((n_code, n_time, n_f), np.nan, dtype=np.float32)

    files = sorted(Path(parsed).glob("*.parquet"))
    print(f"[l2t] {len(files):,} 个文件", flush=True)
    t0 = time.time()
    matched = 0
    for i, f in enumerate(files, 1):
        stem = f.stem                       # YYYYMMDD_CODE.SZ
        date_tag, code = stem.split("_", 1)
        code = code.split(".")[0]           # 去掉交易所后缀：000001.SZ -> 000001
        if code not in ci:
            continue
        d = pd.read_parquet(f)
        if len(d) == 0:
            continue
        t = d["t"].to_numpy()
        # 连续竞价：09:30–11:30, 13:00–15:00（当日秒）
        keep = ((t >= 34200) & (t <= 41400)) | ((t >= 46800) & (t <= 54000))
        d = d[keep]
        if len(d) == 0:
            continue
        bucket = bar_of(t[keep])
        date_str = f"{date_tag[:4]}-{date_tag[4:6]}-{date_tag[6:]}"
        g = d.groupby(bucket)
        # 状态特征取均值
        agg = g[FEATURES].mean()
        # dmid 取和（桶级 mid 收益）
        agg["dmid"] = g["dmid"].sum()
        cidx = ci[code]
        for b, row in agg.iterrows():
            key = f"{date_str}_{b:04d}"
            tidx = ti.get(key)
            if tidx is None:
                continue
            for k, feat in enumerate(ALL_FEATURES):
                v = row[feat]
                if pd.notna(v):
                    x[cidx, tidx, k] = np.float32(v)
            matched += 1
        if i % 10000 == 0:
            print(f"[l2t] {i:,}/{len(files):,}  匹配 {matched:,}  "
                  f"({time.time() - t0:.0f}s)", flush=True)

    out = RUNS / "tensor" / out_name
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "x.npy", x)
    n_l2_days = int(np.isfinite(x[:, :, 0]).any(axis=0).sum() // 48)
    meta = {
        "freq": out_name,
        "shape": list(x.shape),
        "features": ALL_FEATURES,
        "n_code": n_code,
        "n_time": n_time,
        "aligned_with": "5min",
        "nan_ratio": float(np.isnan(x).mean()),
        "matched_bars": matched,
        "n_l2_days": n_l2_days,
        "source": "parsed_multi (3s 十档快照 → 5min 桶聚合)",
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[l2t] shape={x.shape} nan={meta['nan_ratio']:.2%} "
          f"匹配桶={matched:,} L2 天数={n_l2_days} "
          f"size={x.nbytes / 1e6:.0f}MB -> {out} ({time.time() - t0:.0f}s)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed", required=True, help="parsed_multi 目录")
    ap.add_argument("--out", default="micro_l2_5min")
    a = ap.parse_args()
    build(a.parsed, a.out)


if __name__ == "__main__":
    main()
