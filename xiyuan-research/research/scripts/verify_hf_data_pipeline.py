"""Deterministic tests for hf_data_pipeline v2 (2026-09-17 repair layer).

Fixtures deliberately cover the v1 blind spots (crosswalk R-6):
multi-asset panels, data gaps, stale features, sparse/empty windows,
maker-vs-aggressor side semantics, classified-volume denominators,
contiguity-checked forward labels, and the CKS window-sum of OFI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[2]   # repo root (课题/)
sys.path.insert(0, str(PROJECT / "scripts"))
from hf_data_pipeline import (  # noqa: E402
    aggregate_orderbook,
    aggregate_trades,
    align_features_to_kline,
    clean_orderbook,
    clean_trades,
    make_future_labels,
    normalise_kline,
)


def book_df(times, bq0=10.0, aq0=10.0, bid0=99.0, ask0=101.0, levels=5, pad_from=None):
    rows = []
    for i, t in enumerate(times):
        row = {"timestamp": t}
        for L in range(levels):
            padded = pad_from is not None and L >= pad_from
            row[f"bid_price_{L}"] = 0.0 if padded else bid0 - L - i * 0.01
            row[f"ask_price_{L}"] = 0.0 if padded else ask0 + L + i * 0.01
            row[f"bid_volume_{L}"] = 0.0 if padded else bq0 + L
            row[f"ask_volume_{L}"] = 0.0 if padded else aq0 + L
        rows.append(row)
    return pd.DataFrame(rows)


def manual_ofi(bps, bqs, aps, aqs):
    e = []
    for n in range(len(bps)):
        if n == 0:
            e.append(np.nan)
            continue
        v = (int(bps[n] >= bps[n - 1]) * bqs[n] - int(bps[n] <= bps[n - 1]) * bqs[n - 1]
             - int(aps[n] <= aps[n - 1]) * aqs[n] + int(aps[n] >= aps[n - 1]) * aqs[n - 1])
        e.append(v)
    return e


def main():
    checks = []

    # --- T1 OFI 全窗求和 = CKS 定义（跨窗口边界事件保留）------------------
    times = pd.date_range("2026-01-01 09:30:20", periods=8, freq="10s")
    bps = [99.0 - i * 0.01 for i in range(8)]
    bqs = [10.0 + (1 if i % 2 else -1) for i in range(8)]
    aps = [101.0 + i * 0.01 for i in range(8)]
    aqs = [10.0 + (2 if i % 2 else -2) for i in range(8)]
    raw = pd.DataFrame({
        "timestamp": times,
        **{f"bid_price_{L}": [b - L for b in bps] for L in range(5)},
        **{f"bid_volume_{L}": [q for q in bqs] for L in range(5)},
        **{f"ask_price_{L}": [a + L for a in aps] for L in range(5)},
        **{f"ask_volume_{L}": [q for q in aqs] for L in range(5)},
    })
    clean, rep = clean_orderbook(raw, assume_tz="UTC")
    feat = aggregate_orderbook(clean, window="1min", min_snapshots=3, rv_grid=None)  # bin2 只有 3 个事件，门槛取 3 才能两窗都入
    e = manual_ofi(bps, bqs, aps, aqs)
    total_valid = np.nansum(e[1:])
    assert abs(feat["event_ofi"].fillna(0).sum() - total_valid) < 1e-9, "OFI 窗和 != 全序列有效 e_n 之和"
    # times: 09:30:20..09:31:30 @10s → bin (09:30,09:31] holds idx0..4 (valid e_n: idx1..4 = 4 条)
    assert feat.loc[feat.cutoff_time == pd.Timestamp("2026-01-01 09:31:00", tz="UTC"), "ofi_contributing"].iloc[0] == 4
    assert int(feat["ofi_contributing"].sum()) == 7
    checks.append("T1 OFI full-window sum (CKS)")

    # --- T2 空/稀疏窗 = NaN 不是 0；全网格行存在 ---------------------------
    sparse = book_df(pd.date_range("2026-01-01 10:00:30", periods=2, freq="1s"))
    s2, _ = clean_orderbook(sparse, assume_tz="UTC")
    sf = aggregate_orderbook(s2, window="1min", min_snapshots=4, rv_grid=None)
    assert len(sf) >= 1 and sf["rv"].isna().all() and sf["mid_return"].isna().all()
    assert (sf["rv"].dropna() > 0).all(), "非 NaN 的 rv 不得为 0"
    gap_book = pd.concat([book_df(pd.date_range("2026-01-01 11:00:10", periods=5, freq="5s")),
                          book_df(pd.date_range("2026-01-01 11:06:10", periods=5, freq="5s"))], ignore_index=True)
    g2, gre = clean_orderbook(gap_book, assume_tz="UTC", max_gap="30s")
    assert gre.gap_flags == 1
    gf = aggregate_orderbook(g2, window="1min", min_snapshots=4, rv_grid=None)
    empty_bins = gf[gf["snapshot_count"] == 0]
    assert len(empty_bins) == 5, "11:02..11:06 应为 5 个全 NaN 空格子"
    assert empty_bins["event_ofi"].isna().all()
    checks.append("T2 sparse/empty windows -> NaN, full grid")

    # --- T3 缺口后第一条 e_n 不可测（NaN），不计入窗和 ---------------------
    assert int(gf["ofi_contributing"].fillna(0).sum()) == 8, "两条 gap 后首事件应被排除"
    checks.append("T3 post-gap e_n excluded")

    # --- T4 空层填充不被销毁；locked/crossed 分列 -------------------------
    padded, preP = clean_orderbook(book_df(pd.date_range("2026-01-01 12:00:10", periods=6, freq="5s"), pad_from=3), assume_tz="UTC")
    assert preP.dropped_bad_price == 0 and len(padded) == 6 and padded["levels"].min() == 3
    lk = book_df(pd.date_range("2026-01-01 12:10:10", periods=6, freq="5s"))
    lk.loc[2, ["bid_price_0", "ask_price_0"]] = 100.5
    _, lkr = clean_orderbook(lk, assume_tz="UTC")
    assert lkr.dropped_locked == 1 and lkr.dropped_bad_price == 0, "锁定单列计数不与坏价混"
    cr = book_df(pd.date_range("2026-01-01 12:20:10", periods=6, freq="5s"))
    cr.loc[1, "bid_price_0"] = 105.0
    _, crr = clean_orderbook(cr, assume_tz="UTC")
    assert crr.dropped_crossed == 1 and crr.dropped_bad_price == 0
    checks.append("T4 padded levels survive; locked/crossed separated")

    # --- T5 mid_return bar 口径链 ----------------------------------------
    t5 = pd.concat([book_df(pd.date_range("2026-01-01 13:00:10", periods=4, freq="10s"), bid0=99.0, ask0=101.0),
                    book_df(pd.date_range("2026-01-01 13:01:10", periods=4, freq="10s"), bid0=99.4, ask0=101.4)],
                   ignore_index=True)
    c5, _ = clean_orderbook(t5, assume_tz="UTC")
    f5 = aggregate_orderbook(c5, window="1min", min_snapshots=3, rv_grid=None)
    mids = f5["mid_price_last"].to_numpy()
    assert np.isnan(f5["mid_return"].iloc[0])
    assert abs(f5["mid_return"].iloc[1] - np.log(mids[1] / mids[0])) < 1e-12
    checks.append("T5 mid_return chained bar close-to-close")

    # --- T6 trades: maker 反号 / classified 分母 / 全网格 ------------------
    tr = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01 09:30:05", periods=6, freq="5s"),
        "price": [100.0] * 6, "volume": [10.0] * 6,
        "side": ["buy", "sell", "buy", "buy", None, "sell"],
    })
    ag, _ = clean_trades(tr, side_col="side", side_semantics="aggressor", assume_tz="UTC")
    mk, _ = clean_trades(tr, side_col="side", side_semantics="maker", assume_tz="UTC")
    first, second = mk.loc[0, "aggressor_side"], ag.loc[0, "aggressor_side"]
    assert (first, second) == ("sell", "buy"), "maker 语义必须翻号"
    ft = aggregate_trades(mk, window="1min")
    classified = 50.0  # 5 of 6 trades have a finite side
    man_signed = sum(v * (1 if s == "buy" else -1 if s == "sell" else 0)
                     for v, s in zip(tr["volume"], mk["aggressor_side"]))
    assert abs(ft["signed_volume"].iloc[0] - man_signed) < 1e-12
    assert abs(ft["classified_volume_share"].iloc[0] - classified / 60.0) < 1e-12
    assert abs(ft["signed_volume_imbalance"].iloc[0] - man_signed / classified) < 1e-12, "分母=已判定量"
    ab, _ = clean_trades(tr, side_col=None, side_semantics="absent", assume_tz="UTC")
    assert "aggressor_side" not in ab.columns
    bad_cfg = None
    try:
        clean_trades(tr, side_col="side", side_semantics="aggressor", assume_tz="UTC", price_col="nope")
    except ValueError:
        bad_cfg = "raises"
    assert bad_cfg == "raises"
    checks.append("T6 trades maker-flip + classified denominator")

    # --- T7 多资产 align 可用 + 陈旧有界 + 缺 asset_id 报错 ---------------
    times7 = pd.date_range("2026-01-05 09:31", periods=10, freq="1min", tz="UTC")
    kl = pd.DataFrame({"asset_id": ["A"] * 10 + ["B"] * 10, "cutoff_time": list(times7) + list(times7),
                       "open": 1.0, "high": 1.1, "low": 0.9, "close": 1.0 + np.arange(20) * 1e-4, "volume": 1.0})
    fe = pd.DataFrame({"asset_id": ["A"] * 10 + ["B"] * 10, "cutoff_time": list(times7) + list(times7),
                       "event_ofi": np.arange(20.0), "rv": np.arange(20.0) * 1e-6})
    al = align_features_to_kline(kl, fe)
    assert len(al) == 20 and al["hf_available"].all()
    stale = fe.copy()
    stale.loc[stale.asset_id == "A", "cutoff_time"] = times7 - pd.Timedelta("3h")
    al2 = align_features_to_kline(kl, stale)
    assert not al2[al2.asset_id == "A"]["hf_available"].any(), "3h 陈旧必须 False"
    try:
        align_features_to_kline(kl, fe.drop(columns=["asset_id"]))
        raise AssertionError("多资产缺 asset_id 应报错")
    except ValueError:
        pass
    checks.append("T7 multi-asset align + staleness cap + guard")

    # --- T8 normalise_kline: 必填语义 + 缺口统计 + NaT -------------------
    k8 = pd.DataFrame({"timestamp": ["2026-01-05 09:31", "2026-01-05 09:32", "2026-01-05 09:34", "bad"],
                       "open": [1, 1, 1, 1], "high": [2, 2, 2, 2], "low": [0.5, 0.5, 0.5, 0.5],
                       "close": [1.5, 1.6, 1.7, 1.5], "volume": [10, 20, 30, 40]})
    n8 = normalise_kline(k8, assume_tz="Asia/Shanghai", timestamp_semantics="bar_end", bar_frequency="1min", asset_id="X")
    assert len(n8) == 3 and n8.attrs["missing_bars"] == 1 and n8.attrs["dropped_nat"] == 1
    try:
        normalise_kline(k8, timestamp_semantics="bar_end")
        raise AssertionError("assume_tz 必须必填")
    except TypeError:
        pass
    checks.append("T8 required semantics + gap stats")

    # --- T9 标签: h=1 非零退化 + 缺口 NaN + h=2 真值 ---------------------
    kl9 = pd.DataFrame({"asset_id": ["A"] * 6,
                        "cutoff_time": pd.date_range("2026-01-05 09:31", periods=6, freq="1min", tz="UTC"),
                        "close": np.arange(1.0, 7.0)})
    r = np.log(np.arange(2.0, 7.0) / np.arange(1.0, 6.0))
    l1 = make_future_labels(kl9, horizon=1)
    assert abs(l1["target_rv_sqrt"].iloc[0] - abs(r[0])) < 1e-12, "h=1 标签 = |r|，不得为 0"
    assert np.isnan(l1["target_rv_sqrt"].iloc[-1])
    l2 = make_future_labels(kl9, horizon=2)
    assert abs(l2["target_rv"].iloc[0] - (r[0] ** 2 + r[1] ** 2)) < 1e-12
    gap9 = kl9.drop(index=2).reset_index(drop=True)
    l2g = make_future_labels(gap9, horizon=2)
    assert not l2g["label_ok_contiguity"].iloc[1], "删除中间 bar 后标签窗不再连续"
    assert np.isnan(l2g["target_rv"].iloc[1])
    checks.append("T9 RV labels + contiguity guard")

    print("HF_DATA_PIPELINE_V2: PASS")
    for c in checks:
        print(" -", c)


if __name__ == "__main__":
    main()
