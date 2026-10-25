"""P4 · 波动率预测任务（论文三任务之二）。

口径与论文 Appendix.tex:211 对齐：
    label = RV = Σ_{i=t+1}^{t+H} (log p_{i+1} − log p_i)²     （H = 24 根 5min = 2 小时）
    预测 log(RV)（尺度稳定），评估时还原到原量纲算 MAE 与 R²。

模型：冻结 Kronos-small 出隐状态 → 与 arm-1 完全相同的池化
（末点 + 尾部 60 根均值 + 尾部 60 根标准差）→ MLP → 1 维。
不接微观分支——本任务测的是"冻结表示里有没有波动率信息"，
与 P2（微观增量）是两个独立问题。

用法：
    python -m xy.train.run_vol --freq 5min --seeds 0 1 2
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

from xy.model.backbone import FrozenKronos
from xy.paths import RUNS


class VolHead(nn.Module):
    """与 arm-1 的 Head 同构，输出 1 维 log-RV。"""

    def __init__(self, d_in: int = 1536, d_hidden: int = 64, p: float = 0.3):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(d_in, d_hidden), nn.GELU(), nn.Dropout(p),
            nn.Linear(d_hidden, 1),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:
        last = h[:, -1]
        tail = h[:, -60:]
        feat = torch.cat([last, tail.mean(1), tail.std(1)], dim=-1)
        return self.net(feat).squeeze(-1)


def rv_labels(x: np.ndarray, horizon: int) -> np.ndarray:
    """每个时间点的未来 H 根已实现波动率。x: [n_code, n_time, 6]（通道 3 = close）。"""
    close = x[:, :, 3]
    with np.errstate(divide="ignore", invalid="ignore"):
        logp = np.log(np.where(close > 0, close, np.nan))
    r = np.diff(logp, axis=1)                      # [n_code, n_time-1]
    r2 = r * r
    cs = np.cumsum(r2, axis=1)
    cs = np.concatenate([np.zeros((r2.shape[0], 1)), cs], axis=1)   # cs[:,t] = 前 t 根收益平方和
    n = cs.shape[1]
    out = np.full_like(cs, np.nan)
    idx = np.arange(n)
    valid = idx + horizon <= n - 1
    out[:, valid] = cs[:, idx[valid] + horizon] - cs[:, idx[valid]]
    return out


def load_tensor(freq: str):
    d = RUNS / "tensor" / freq
    return np.load(d / "x.npy", mmap_mode="r"), json.loads((d / "meta.json").read_text())


def make_batch(x, rv, idx, lookback, device):
    xs, ys = [], []
    for c, t in idx:
        win = np.asarray(x[c, t - lookback + 1: t + 1], dtype=np.float32)
        if not np.isfinite(win).all():
            continue
        y = float(rv[c, t])
        if not np.isfinite(y) or y <= 0:
            continue
        xs.append(win)
        ys.append(y)
    if not xs:
        return None, None
    return (torch.from_numpy(np.stack(xs)).to(device),
            torch.tensor(ys, dtype=torch.float32, device=device))


def run(freq: str, epochs: int, seed: int, device, lookback: int, horizon: int,
        batch: int, lr: float, head_hidden: int, dropout: float, wd: float,
        stride: int) -> dict:
    torch.manual_seed(seed)
    np.random.seed(seed)

    x, meta = load_tensor(freq)
    n_code, n_time = meta["n_code"], meta["n_time"]
    print(f"[vol] 计算 RV 标签（H={horizon}）...", flush=True)
    rv = rv_labels(x, horizon)
    print(f"[vol] RV 有限值占比 {np.isfinite(rv).mean():.3%}", flush=True)

    backbone = FrozenKronos(size="small", device=device)
    device = str(backbone.device)
    model = VolHead(backbone.d_model * 3, head_hidden, dropout).to(device)

    n_train_time = int(n_time * 0.7)
    train_idx = [(c, t) for c in range(n_code)
                 for t in range(lookback - 1, n_train_time - horizon, stride)]
    val_idx = [(c, t) for c in range(n_code)
               for t in range(n_train_time, n_time - horizon, max(stride * 4, 20))]
    print(f"[vol] train={len(train_idx):,} val={len(val_idx):,}", flush=True)

    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    best, best_state, bad, hist = -9e9, None, 0, []

    for ep in range(epochs):
        model.train()
        perm = np.random.permutation(len(train_idx))
        tot, nb = 0.0, 0
        t0 = time.time()
        for i in range(0, len(perm), batch):
            sel = [train_idx[j] for j in perm[i:i + batch]]
            b = make_batch(x, rv, sel, lookback, device)
            if b[0] is None:
                continue
            xb, yb = b
            with torch.no_grad():
                h = backbone.hidden(xb)
            pred = model(h)
            loss = nn.functional.mse_loss(pred, torch.log(yb))
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
            opt.step()
            tot += float(loss)
            nb += 1

        model.eval()
        ps, rs = [], []
        with torch.no_grad():
            for i in range(0, len(val_idx), batch * 4):
                b = make_batch(x, rv, val_idx[i:i + batch * 4], lookback, device)
                if b[0] is None:
                    continue
                xb, yb = b
                h = backbone.hidden(xb)
                ps.append(model(h).cpu().numpy())
                rs.append(yb.cpu().numpy())
        if not ps:
            break
        p = np.concatenate(ps)
        r = np.concatenate(rs)
        pred_rv = np.exp(p)
        mae = float(np.mean(np.abs(pred_rv - r)))
        ss = np.sum((r - r.mean()) ** 2)
        r2 = float(1 - np.sum((r - pred_rv) ** 2) / ss) if ss > 0 else np.nan
        # 用 R² 作为早停依据（论文报 MAE + R²）
        hist.append({"epoch": ep, "train_loss": tot / max(nb, 1),
                     "val_mae": mae, "val_r2": r2, "sec": round(time.time() - t0, 1)})
        print(f"  ep{ep:02d} loss={tot / max(nb, 1):.6f} val_MAE={mae:.3e} "
              f"val_R²={r2:+.4f} ({time.time() - t0:.0f}s)", flush=True)
        if r2 > best + 1e-4:
            best, bad = r2, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            bad += 1
            if bad >= 3:
                print(f"  早停：R² 连续 {bad} 轮未改善（best={best:+.4f}）", flush=True)
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    # 基线对照：用"历史平均 RV"预测的 MAE/R²（零模型）
    d = RUNS / "vol" / f"vol_{freq}_s{seed}"
    d.mkdir(parents=True, exist_ok=True)
    out = {
        "task": "volatility", "freq": freq, "seed": seed,
        "lookback": lookback, "horizon": horizon,
        "best_val_r2": best, "history": hist,
        "n_train": len(train_idx), "n_val": len(val_idx),
        "n_params": int(sum(p.numel() for p in model.parameters())),
        "label": "RV = sum (log p_{i+1} - log p_i)^2 over next H bars",
    }
    (d / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
    print(f"[vol] -> {d}/result.json")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--freq", default="5min", choices=["daily", "5min", "1min", "15min"])
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--device", default=None)
    ap.add_argument("--lookback", type=int, default=240)
    ap.add_argument("--horizon", type=int, default=24)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--head-hidden", type=int, default=64)
    ap.add_argument("--dropout", type=float, default=0.3)
    ap.add_argument("--wd", type=float, default=0.1)
    ap.add_argument("--stride", type=int, default=40)
    a = ap.parse_args()
    for s in a.seeds:
        run(a.freq, a.epochs, s, a.device, a.lookback, a.horizon, a.batch,
            a.lr, a.head_hidden, a.dropout, a.wd, a.stride)


if __name__ == "__main__":
    main()
