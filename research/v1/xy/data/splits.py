"""walk-forward 切分 + purge + embargo。

现有 KronosLocal 的协议是固定切分（VAL=2021-2022 / TEST=2023-2026），
对「重叠 horizon」没有处理。本模块补上：

    fold:  |--- train ---|-- purge --|-- val --|-- purge --|-- test --|

purge 段长度 = ceil(H / bars_per_day) 天，保证训练集最后一个样本的
label 不会跨进验证/测试段（否则 label 泄漏）。

用法：
    python -m xy.data.splits --selftest
    python -m xy.data.splits --from-panel      # 用真实交易日打印折叠
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

from xy.paths import PANEL


def make_folds(
    dates: list[str],
    horizon_days: int = 1,
    train: int = 250,
    val: int = 40,
    test: int = 40,
    step: int = 40,
    embargo: int = 1,
) -> list[dict]:
    """滚动生成折叠。dates 必须是升序、无重复的交易日列表。"""
    dates = sorted(set(dates))
    purge = max(1, horizon_days) + embargo
    folds = []
    start = 0
    while True:
        i_tr0 = start
        i_tr1 = i_tr0 + train
        i_va0 = i_tr1 + purge
        i_va1 = i_va0 + val
        i_te0 = i_va1 + purge
        i_te1 = i_te0 + test
        if i_te1 > len(dates):
            break
        folds.append({
            "train": (dates[i_tr0], dates[i_tr1 - 1]),
            "val": (dates[i_va0], dates[i_va1 - 1]),
            "test": (dates[i_te0], dates[i_te1 - 1]),
            "n_train": train, "n_val": val, "n_test": test, "purge": purge,
        })
        start += step
    return folds


def assign(dates: pd.Series, folds: list[dict]) -> pd.Series:
    """把每个交易日标到 fold 的 train/val/test/purge 上（多折叠取最后一次出现）。"""
    lab = pd.Series("none", index=dates.index)
    for k, f in enumerate(folds):
        for part in ("train", "val", "test"):
            lo, hi = f[part]
            lab[(dates >= lo) & (dates <= hi)] = f"f{k}_{part}"
    return lab


def selftest() -> None:
    dates = pd.bdate_range("2024-01-01", periods=600).strftime("%Y-%m-%d").tolist()
    folds = make_folds(dates, horizon_days=2, train=250, val=40, test=40, step=40)
    print(f"折叠数 {len(folds)}")
    for k, f in enumerate(folds[:3]):
        print(f"  f{k}: train {f['train'][0]}→{f['train'][1]}  "
              f"val {f['val'][0]}→{f['val'][1]}  test {f['test'][0]}→{f['test'][1]}  purge={f['purge']}")

    # 断言：train 末与 val 首之间至少隔 purge 个交易日
    d = pd.Series(dates)
    for f in folds:
        gap = d[(d > f["train"][1]) & (d < f["val"][0])].shape[0]
        assert gap == f["purge"], f"purge 不符：{gap} != {f['purge']}"
        gap2 = d[(d > f["val"][1]) & (d < f["test"][0])].shape[0]
        assert gap2 == f["purge"]
    print("SELFTEST PASS（purge 间隔正确）")


def from_panel() -> None:
    p = PANEL / "daily_pool.parquet"
    if not p.exists():
        print("daily_pool.parquet 不存在，先跑 xy.data.pool")
        return
    dates = pd.read_parquet(p, columns=["trade_date"]).trade_date.astype(str).unique().tolist()
    print(f"交易日 {len(dates)}：{min(dates)} → {max(dates)}")
    for hd in (1, 5):
        folds = make_folds(dates, horizon_days=hd, train=250, val=40, test=40, step=40)
        print(f"\nH={hd} 日，折叠 {len(folds)} 个")
        for k, f in enumerate(folds):
            print(f"  f{k}: train {f['train'][0]}→{f['train'][1]} | "
                  f"val {f['val'][0]}→{f['val'][1]} | test {f['test'][0]}→{f['test'][1]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--from-panel", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    elif a.from_panel:
        from_panel()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
