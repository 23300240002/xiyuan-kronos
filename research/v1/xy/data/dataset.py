"""把长表面板转成 [code, time, 6] 张量，并切滑动窗口。

为什么不用 DataFrame 直接喂：窗口切样在 pandas 里是 O(n) 复制，
在张量上是 O(1) 视图。GPU 训练时前者会把 CPU 变成瓶颈。

产出：
    runs/tensor/daily/{x.npy, meta.json}
    runs/tensor/minute_5min/{x.npy, meta.json}

x 形状 [n_code, n_time, 6]，通道顺序 OHLCVA；缺失为 NaN。

用法：
    python -m xy.data.dataset --freq daily
    python -m xy.data.dataset --freq 5min
"""
from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from xy.paths import PANEL, RUNS, rel

CHANNELS = ["open", "high", "low", "close", "volume", "amount"]


def _pivot(df: pd.DataFrame, time_col: str) -> tuple[np.ndarray, list[str], list]:
    codes = np.sort(df["code"].unique())
    times = np.sort(df[time_col].unique())
    ci = {c: i for i, c in enumerate(codes)}
    ti = {t: i for i, t in enumerate(times)}

    x = np.full((len(codes), len(times), len(CHANNELS)), np.nan, dtype=np.float32)
    rows = df["code"].map(ci).to_numpy()
    cols = df[time_col].map(ti).to_numpy()
    for k, ch in enumerate(CHANNELS):
        x[rows, cols, k] = df[ch].to_numpy(dtype=np.float32)
    return x, codes.tolist(), times.tolist()


def build(freq: str = "daily") -> None:
    if freq == "daily":
        src = PANEL / "daily_pool.parquet"
        time_col = "trade_date"
        df = pd.read_parquet(src, columns=["code", time_col, *CHANNELS])
        df[time_col] = df[time_col].astype(str)
    else:
        src = PANEL / "minute_5min" / "all.parquet"
        time_col = "bucket"
        df = pd.read_parquet(src, columns=["code", "trade_date", time_col, *CHANNELS])
        # 时间键 = 日期 + 桶，保证跨日连续
        df[time_col] = (df["trade_date"].astype(str) + "_" +
                        df[time_col].astype(int).astype(str).str.zfill(4))
        df = df.drop(columns=["trade_date"])

    x, codes, times = _pivot(df, time_col)
    out = RUNS / "tensor" / freq
    out.mkdir(parents=True, exist_ok=True)
    np.save(out / "x.npy", x)

    meta = {
        "freq": freq,
        "shape": list(x.shape),
        "channels": CHANNELS,
        "n_code": len(codes),
        "n_time": len(times),
        "times": times,
        "time_min": str(times[0]),
        "time_max": str(times[-1]),
        "nan_ratio": float(np.isnan(x[:, :, 3]).mean()),
        "codes": codes,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[tensor] {freq}: shape={x.shape} nan={meta['nan_ratio']:.2%} "
          f"size={x.nbytes / 1e6:.0f}MB -> {rel(out)}")


class WindowIndex:
    """生成合法窗口的索引（上下文 L 根 + 未来 H 根都非缺失）。"""

    def __init__(self, x: np.ndarray, lookback: int, horizon: int, stride: int = 1):
        self.x = x
        self.L = lookback
        self.H = horizon
        valid = ~np.isnan(x[:, :, 3])            # close 非缺失
        cs = np.cumsum(valid, axis=1)
        win = np.zeros_like(cs)
        win[:, L - 1:] = cs[:, L - 1:] - np.concatenate(
            [np.zeros((cs.shape[0], 1), dtype=cs.dtype), cs[:, :-L]], axis=1
        )
        n_time = x.shape[1]
        idx = []
        for t in range(L - 1, n_time - horizon, stride):
            ok = (win[:, t] == L) & valid[:, t + horizon]
            for c in np.where(ok)[0]:
                idx.append((c, t))
        self.index = np.asarray(idx, dtype=np.int32)
        print(f"[index] L={L} H={horizon} windows={len(self.index):,}")

    def __len__(self) -> int:
        return len(self.index)

    def get(self, i: int) -> tuple[np.ndarray, float]:
        c, t = self.index[i]
        ctx = self.x[c, t - self.L + 1: t + 1]        # [L, 6]
        label = self.x[c, t + self.H, 3] / self.x[c, t, 3] - 1
        return ctx, float(label)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", default="daily", choices=["daily", "5min"])
    a = ap.parse_args()
    build(a.freq)


if __name__ == "__main__":
    main()
