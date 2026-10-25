"""把 M1 微观特征面板转成与 K 线张量严格对齐的 [code, time, F] 张量。

对齐要求（否则三臂消融就废了）：
- 票池、时间轴与 `runs/tensor/5min/meta.json` **完全一致**；
- 缺失填 NaN，由窗口索引负责剔除；
- 通道顺序固定并写入 meta，训练时不得改变。

用法：
    python -m xy.data.micro_tensor
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from xy.paths import PANEL, RUNS

FEATURES = ["vol_imb", "ln_trades", "ln_avg_size", "ret", "path_eff",
            "vwap_dev", "amihud", "open_pos", "tail_pos", "big_ratio",
            "corr_pv", "hhi"]


def build() -> None:
    k_meta = json.loads((RUNS / "tensor" / "5min" / "meta.json").read_text(encoding="utf-8"))
    codes = k_meta["codes"]
    times = k_meta["times"]                      # "YYYY-MM-DD_HHMM"
    ci = {c: i for i, c in enumerate(codes)}
    ti = {t: i for i, t in enumerate(times)}

    d = pd.read_parquet(PANEL / "micro_m1_5min" / "all.parquet")
    # 时间键：trade_date(YYYY-MM-DD) + "_" + bucket(HHMM)
    d["tkey"] = d["trade_date"].astype(str) + "_" + d["bucket"].astype(int).astype(str).str.zfill(4)
    d["code"] = d["code"].astype(str)

    n_code, n_time, n_f = len(codes), len(times), len(FEATURES)
    x = np.full((n_code, n_time, n_f), np.nan, dtype=np.float32)

    # 只保留两侧都有的 (code, time)
    m = d["code"].isin(ci) & d["tkey"].isin(ti)
    dd = d[m]
    rows = dd["code"].map(ci).to_numpy()
    cols = dd["tkey"].map(ti).to_numpy()
    for k, f in enumerate(FEATURES):
        x[rows, cols, k] = dd[f].to_numpy(dtype=np.float32)

    out = RUNS / "tensor" / "micro_5min"
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "x.npy", x)
    meta = {
        "freq": "micro_5min",
        "shape": list(x.shape),
        "features": FEATURES,
        "n_code": n_code,
        "n_time": n_time,
        "aligned_with": "5min",
        "nan_ratio": float(np.isnan(x).mean()),
        "matched_rows": int(len(dd)),
        "source_rows": int(len(d)),
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[micro] shape={x.shape} nan={meta['nan_ratio']:.2%} "
          f"matched={len(dd):,}/{len(d):,} ({len(dd) / max(len(d), 1):.1%}) "
          f"size={x.nbytes / 1e6:.0f}MB -> {out}")
    if len(dd) / max(len(d), 1) < 0.9:
        print("[micro] ⚠️ 匹配率低于 90%，检查票池或时间键格式是否一致")


if __name__ == "__main__":
    build()
