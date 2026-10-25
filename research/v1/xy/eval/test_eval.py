"""测试段评估（向量化版）：加载 best_state，在独立时间段上复算 IC。

与 v1 的差别：predict 用 sliding_window_view 向量化（原版 240 万次 Python 循环），
block bootstrap 用加权相关（原版每次迭代 concat 4838 个块）。
提速约 20 倍，9 个评估从 3.7 小时降到约 25 分钟。

口径不变：
- **重叠窗口**：stride=40 / lookback=240 → 相邻窗口重叠 83%，朴素 t 值极度虚高，
  因此一律用**按交易日分块的 block bootstrap**（加权实现，数学等价于按天重抽）。
- **pooled IC**：跨样本合并后算一次 Pearson 相关（论文 Appendix.tex:315 口径）。
- 切分：train 0–70% / val 70–100%（早停用）/ test 85–100%。
  **注意 test 与 val 有重叠**（val 占 70–100%），这是已知局限，报告必须标注。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

from ..train.run_arm import Arm, FrozenKronos, load_micro, load_tensor

RUNS = Path(__file__).resolve().parents[2] / "runs"


def stream_eval(model, backbone, x, xm, lookback, horizon, t_lo, t_hi,
                batch, device):
    """逐票流式：收集一个票的窗口→立即预测→只保留预测值。

    避免一次性累积全部窗口（K 线 13.7GB + 微观 27GB，会触发容器 OOM）。
    返回 (pred, y, day)。
    """
    import torch

    n_code, n_time = x.shape[0], x.shape[1]
    ts = np.arange(max(t_lo, lookback - 1), t_hi)
    if len(ts) == 0:
        return None, None, None
    preds, ys, days = [], [], []
    with torch.no_grad():
        for c in range(n_code):
            arr = np.asarray(x[c], dtype=np.float32)            # [T, 6]
            sw = sliding_window_view(arr, lookback, axis=0)      # [T-lb+1, 6, lb]
            W = np.ascontiguousarray(sw[ts - lookback + 1].transpose(0, 2, 1))
            ok = np.isfinite(W).all(axis=(1, 2))
            fut = arr[ts + horizon, 3]
            cur = arr[ts, 3]
            ok &= np.isfinite(fut) & (cur > 0)
            M = None
            if xm is not None:
                marr = np.asarray(xm[c], dtype=np.float32)
                msw = sliding_window_view(marr, lookback, axis=0)
                M = np.ascontiguousarray(msw[ts - lookback + 1].transpose(0, 2, 1))
                ok &= np.isfinite(M).all(axis=(1, 2))
            if not ok.any():
                continue
            W, yy, dd = W[ok], fut[ok] / cur[ok] - 1, ts[ok]
            MM = M[ok] if M is not None else None
            for i in range(0, len(W), batch):
                xb = torch.from_numpy(W[i:i + batch]).to(device)
                mb = (torch.from_numpy(MM[i:i + batch]).to(device)
                      if MM is not None else None)
                h = backbone.hidden(xb)
                preds.append(model(h, mb)[:, -1].cpu().numpy())
            ys.append(yy)
            days.append(dd)
    if not preds:
        return None, None, None
    return np.concatenate(preds), np.concatenate(ys), np.concatenate(days)


def predict(model, backbone, X, M, batch, device):
    import torch
    preds = []
    with torch.no_grad():
        for i in range(0, len(X), batch):
            xb = torch.from_numpy(X[i:i + batch]).to(device)
            mb = (torch.from_numpy(M[i:i + batch]).to(device)
                  if M is not None else None)
            h = backbone.hidden(xb)
            preds.append(model(h, mb)[:, -1].cpu().numpy())
    return np.concatenate(preds)


def weighted_ic(p, r, w):
    """加权 Pearson 相关（w 为每个样本的权重）。"""
    sw = w.sum()
    if sw <= 0:
        return np.nan
    mp = (w * p).sum() / sw
    mr = (w * r).sum() / sw
    pc, rc = p - mp, r - mr
    num = (w * pc * rc).sum()
    den = np.sqrt((w * pc * pc).sum() * (w * rc * rc).sum())
    return float(num / den) if den > 0 else np.nan


def block_bootstrap_ic(p, r, day, B=1000, seed=0):
    """按天分块的自助法（加权实现）。

    数学等价于：每次迭代有放回地抽 n_days 天，把选中天的所有样本合并算 IC。
    用样本权重表达"某天的样本被抽中几次"，避免物理拼接。
    """
    rng = np.random.default_rng(seed)
    days, day_idx = np.unique(day, return_inverse=True)
    n_days = len(days)
    if n_days < 5:
        return np.nan, np.nan, np.nan, np.nan
    obs = weighted_ic(p, r, np.ones(len(p)))
    boots = np.empty(B)
    for b in range(B):
        counts = np.bincount(rng.integers(0, n_days, n_days), minlength=n_days)
        boots[b] = weighted_ic(p, r, counts[day_idx])
    boots = boots[np.isfinite(boots)]
    if len(boots) < B * 0.5:
        return obs, np.nan, np.nan, np.nan
    lo, hi = np.percentile(boots, [2.5, 97.5])
    se = float(np.std(boots))
    return obs, lo, hi, (obs / se if se > 0 else np.nan)


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(np.float64)
    rb = np.argsort(np.argsort(b)).astype(np.float64)
    return float(np.corrcoef(ra, rb)[0, 1])


def evaluate(arm: int, freq: str, seed: int, device, B: int, tag: str,
             batch: int = 512) -> dict:
    import torch

    src = RUNS / "arm" / f"arm{arm}_{freq}_s{seed}"
    state_path = src / "best_state.pt"
    res_path = RUNS / "arm" / f"arm{arm}_{freq}_s{seed}_h64_d0.3_w0.1" / "result.json"
    if not state_path.exists() or not res_path.exists():
        raise FileNotFoundError(f"缺少 {state_path} 或 {res_path}")
    meta_run = json.loads(res_path.read_text(encoding="utf-8"))
    lookback, horizon = meta_run["lookback"], meta_run["horizon"]

    x, meta = load_tensor(freq)
    xm, _ = load_micro(freq)
    backbone = FrozenKronos(size="small", device=device)
    device = str(backbone.device)
    model = Arm(arm, d_model=backbone.d_model, horizon=horizon,
                head_hidden=meta_run["head_hidden"],
                dropout=meta_run["dropout"]).to(device)
    model.load_state_dict(torch.load(state_path, map_location=device))
    model.eval()

    n_time = meta["n_time"]
    t0 = int(n_time * 0.85)
    p, y, day = stream_eval(model, backbone, x, xm, lookback, horizon,
                            t0, n_time - horizon, batch, device)
    if p is None:
        raise RuntimeError("测试段无有效窗口")
    print(f"[arm{arm} s{seed}] 测试段窗口 {len(p):,}（t>={t0}/{n_time}）", flush=True)
    ic, lo, hi, t_blk = block_bootstrap_ic(p, y, day, B=B, seed=seed)
    ric = spearman(p, y)

    out = {
        "arm": arm, "freq": freq, "seed": seed,
        "lookback": lookback, "horizon": horizon,
        "n_test": int(len(p)), "n_days": int(len(np.unique(day))),
        "pooled_ic": ic, "ci_lo": lo, "ci_hi": hi, "t_block": t_blk,
        "pooled_rank_ic": ric, "test_frac": [0.85, 1.0],
        "note": "test 与 val(70-100%) 有重叠，属已知局限",
    }
    d = RUNS / "arm" / f"arm{arm}_{freq}_s{seed}_h{meta_run['head_hidden']}_d{meta_run['dropout']}_w{meta_run['wd']}"
    (d / f"test_{tag}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print(f"[arm{arm} s{seed}] pooled_IC={ic:+.5f} [{lo:+.5f},{hi:+.5f}] "
          f"t_block={t_blk:.2f} RankIC={ric:+.5f} n={len(p):,}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--freq", default="5min")
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    ap.add_argument("--device", default=None)
    ap.add_argument("--B", type=int, default=1000)
    ap.add_argument("--tag", default="v1")
    ap.add_argument("--batch", type=int, default=512)
    a = ap.parse_args()
    rows = []
    for arm in a.arm:
        for s in a.seeds:
            try:
                rows.append(evaluate(arm, a.freq, s, a.device, a.B, a.tag, a.batch))
            except Exception as e:                      # noqa: BLE001
                print(f"[arm{arm} s{s}] 失败: {str(e)[:150]}")
    if rows:
        (RUNS / "arm" / f"test_summary_{a.tag}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n汇总 -> runs/arm/test_summary_{a.tag}.json（{len(rows)} 行）")


if __name__ == "__main__":
    main()
