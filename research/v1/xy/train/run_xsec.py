"""截面注意力模型（MASTER, AAAI-24 的核心思想）。

**本项目的缺口**：现有三臂模型对每个 (票, 时刻) **独立**预测，
模型从来没见过同一时刻的其他股票。但我们的指标是**截面** RankIC——
衡量的是"同一时刻谁比谁强"。MASTER 在每个时刻对全部股票做 inter-stock
attention，让模型学到相对强弱。

本脚本：
    冻结 Kronos → 每股池化 → **截面自注意力（500 只票之间）** → 头 → 预测
标签用截面 z-score（`xsec_label`），与截面注意力天然配对。

**效率设计（关键）**：主干冻结 ⇒ 池化特征可**一次性预计算**并缓存。
- 逐时刻现算：564 次前向/epoch，每次 500×240 token，且要随机读 memmap（实测 11 分钟/epoch）
- 预计算缓存：全部时刻一次性批量前向（约 2 分钟），之后每 epoch 只训 1.2M 参数的头（秒级）
一个 batch = 一个时刻 × 全部 500 只票，与 MASTER 的"每日截面"一致。

用法：
    python -m xy.train.run_xsec --seeds 0 1 2 --stride 40
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
import torch
import torch.nn as nn

from xy.eval.ic import pooled_ic
from xy.model.backbone import FrozenKronos
from xy.paths import RUNS
from xy.train.run_arm import xsec_label


class XsecModel(nn.Module):
    """池化特征 → 截面自注意力 → 逐股预测。"""

    def __init__(self, d_in: int = 1536, d_hidden: int = 256, n_heads: int = 4,
                 n_layers: int = 1, dropout: float = 0.3, residual: bool = True):
        super().__init__()
        self.proj = nn.Linear(d_in, d_hidden)
        layer = nn.TransformerEncoderLayer(d_hidden, n_heads, 4 * d_hidden,
                                           batch_first=True, dropout=dropout,
                                           norm_first=True)
        self.enc = nn.TransformerEncoder(layer, n_layers)
        self.ln = nn.LayerNorm(d_hidden)
        self.residual = residual
        self.head = nn.Sequential(
            nn.Linear(d_hidden, d_hidden // 4), nn.GELU(),
            nn.Dropout(dropout), nn.Linear(d_hidden // 4, 1))

    def forward(self, e: torch.Tensor) -> torch.Tensor:
        """e: [S, d_in]（一个时刻的全部股票）→ [S]"""
        z = self.proj(e).unsqueeze(0)               # [1, S, d]
        a = self.enc(z)
        z = self.ln(z + a) if self.residual else self.ln(a)
        return self.head(z.squeeze(0)).squeeze(-1)


@torch.no_grad()
def precompute(backbone, x, n_code: int, timestamps, lookback: int, dev: str,
               chunk: int = 4, xm=None):
    """一次性算出所有时刻的池化特征。

    返回 dict: t -> (feat [S, 3d], ok [S])
    """
    cache = {}
    t0 = time.time()
    for i in range(0, len(timestamps), chunk):
        ts = timestamps[i:i + chunk]
        wins = np.stack([[x[c, t - lookback + 1: t + 1] for c in range(n_code)]
                         for t in ts])                     # [T, S, L, F]
        T, S, L, F = wins.shape
        flat = np.ascontiguousarray(wins.reshape(T * S, L, F), dtype=np.float32)
        ok = np.isfinite(flat).all(axis=(1, 2))
        if xm is not None:
            # 微观侧同样要全有限（m1 有约 0.8% NaN；l2 覆盖率极低）
            mw_all = np.stack([[xm[c, t - lookback + 1: t + 1] for c in range(n_code)]
                               for t in ts]).reshape(T * S, L, -1)
            ok &= np.isfinite(mw_all).all(axis=(1, 2))
        if ok.sum() == 0:
            for j, t in enumerate(ts):
                cache[t] = (np.zeros((S, 1), np.float32), np.zeros(S, bool))
            continue
        xb = torch.from_numpy(flat[ok]).to(dev)
        h = backbone.hidden(xb)
        parts = [h[:, -1], h[:, -60:].mean(1), h[:, -60:].std(1)]
        if xm is not None:
            # 微观特征同样池化（末点 + 尾部均值 + 尾部标准差）
            mf = np.ascontiguousarray(mw_all, dtype=np.float32)[ok]
            mb = torch.from_numpy(mf).to(dev)
            parts += [mb[:, -1], mb[:, -60:].mean(1), mb[:, -60:].std(1)]
            del mb, mf, mw_all
        feat = torch.cat(parts, dim=-1).float().cpu().numpy()
        full = np.zeros((T * S, feat.shape[1]), dtype=np.float32)
        full[ok] = feat
        for j, t in enumerate(ts):
            cache[t] = (full[j * S:(j + 1) * S], ok[j * S:(j + 1) * S])
        del xb, h, feat
        if dev.startswith("cuda"):
            torch.cuda.empty_cache()
        if (i // chunk) % 20 == 0:
            print(f"  [xsec] 预计算 {i + len(ts):,}/{len(timestamps):,} 时刻 "
                  f"({time.time() - t0:.0f}s)", flush=True)
    print(f"[xsec] 预计算完成 {len(timestamps):,} 时刻，"
          f"{time.time() - t0:.0f}s", flush=True)
    return cache


def run(seeds, device, lookback: int, horizon: int, stride: int, epochs: int,
        lr: float, d_hidden: int, n_heads: int, dropout: float, wd: float,
        residual: bool, micro: str = "none"):
    x = np.load(RUNS / "tensor" / "5min" / "x.npy")        # 全量入内存（370MB）
    meta = json.loads((RUNS / "tensor" / "5min" / "meta.json").read_text())
    n_code, n_time = meta["n_code"], meta["n_time"]

    print("[xsec] 计算截面 z-score 标签 ...", flush=True)
    yz = xsec_label(x, horizon)

    n_train = int(n_time * 0.7)
    train_ts = list(range(lookback - 1, n_train - horizon, stride))
    val_ts = list(range(n_train, n_time - horizon, max(stride * 4, 20)))
    test_ts = list(range(int(n_time * 0.85), n_time - horizon, 5))
    print(f"[xsec] 时刻数：train={len(train_ts):,} val={len(val_ts):,} "
          f"test={len(test_ts):,}（每时刻 {n_code} 只票）", flush=True)

    backbone = FrozenKronos(size="small", device=device)
    dev = str(backbone.device)

    xm = None
    if micro != "none":
        key = f"micro_{micro}_5min"
        xm = np.load(RUNS / "tensor" / key / "x.npy")
        print(f"[xsec] 接入微观张量 {key} shape={xm.shape}", flush=True)
    print("[xsec] 预计算池化特征（主干冻结，只需算一次）...", flush=True)
    cache = precompute(backbone, x, n_code, train_ts + val_ts + test_ts,
                       lookback, dev, xm=xm)

    results = []
    for seed in seeds:
        torch.manual_seed(seed)
        np.random.seed(seed)
        d_in = backbone.d_model * 3 + (xm.shape[2] * 3 if xm is not None else 0)
        model = XsecModel(d_in, d_hidden, n_heads, 1, dropout, residual).to(dev)
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
        best, best_state, bad, hist = -9e9, None, 0, []

        for ep in range(epochs):
            model.train()
            perm = np.random.permutation(len(train_ts))
            tot, nb = 0.0, 0
            t0 = time.time()
            for j in perm:
                t = train_ts[j]
                feat, ok = cache[t]
                if ok.sum() < 50:
                    continue
                y = torch.from_numpy(yz[ok, t]).to(dev)
                m = torch.isfinite(y)
                if m.sum() < 50:
                    continue
                fe = torch.from_numpy(feat[ok]).to(dev)
                pred = model(fe[m])
                loss = nn.functional.mse_loss(pred, y[m])
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 3.0)
                opt.step()
                tot += float(loss)
                nb += 1

            model.eval()
            ps, rs = [], []
            with torch.no_grad():
                for t in val_ts:
                    feat, ok = cache[t]
                    if ok.sum() < 50:
                        continue
                    y = torch.from_numpy(yz[ok, t]).to(dev)
                    m = torch.isfinite(y)
                    if m.sum() < 50:
                        continue
                    fe = torch.from_numpy(feat[ok]).to(dev)
                    ps.append(model(fe[m]).cpu().numpy())
                    rs.append(y[m].cpu().numpy())
            if not ps:
                break
            p, r = np.concatenate(ps), np.concatenate(rs)
            ic = float(np.corrcoef(p, r)[0, 1]) if len(p) > 10 else np.nan
            hist.append({"epoch": ep, "train_loss": tot / max(nb, 1),
                         "val_ic": ic, "sec": round(time.time() - t0, 1)})
            print(f"  ep{ep:02d} loss={tot / max(nb, 1):.5f} val_IC={ic:+.4f} "
                  f"({time.time() - t0:.0f}s)", flush=True)
            if ic > best + 1e-4:
                best, bad = ic, 0
                best_state = {k: v.detach().cpu().clone()
                              for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= 3:
                    print(f"  早停（best={best:+.4f}）", flush=True)
                    break

        if best_state is not None:
            model.load_state_dict(best_state)

        model.eval()
        ps, rs, ics = [], [], []
        with torch.no_grad():
            for t in test_ts:
                feat, ok = cache[t]
                if ok.sum() < 50:
                    continue
                y = torch.from_numpy(yz[ok, t]).to(dev)
                m = torch.isfinite(y)
                if m.sum() < 50:
                    continue
                fe = torch.from_numpy(feat[ok]).to(dev)
                pr = model(fe[m]).cpu().numpy()
                yy = y[m].cpu().numpy()
                ps.append(pr)
                rs.append(yy)
                ics.append(np.corrcoef(pr, yy)[0, 1])
        p, r = np.concatenate(ps), np.concatenate(rs)
        out = {
            "model": "xsec_attention", "seed": seed,
            "lookback": lookback, "horizon": horizon, "stride": stride,
            "d_hidden": d_hidden, "n_heads": n_heads, "residual": residual,
            "label": "xsec_z", "micro": micro,
            "best_val_ic": best, "history": hist,
            "test_ic": float(pooled_ic(p, r, rank=False)),
            "test_rank_ic": float(pooled_ic(p, r, rank=True)),
            "test_daily_ic_mean": float(np.nanmean(ics)),
            "test_daily_ic_std": float(np.nanstd(ics)),
            "n_test": int(len(p)), "n_test_days": len(ics),
            "n_params": int(sum(q.numel() for q in model.parameters())),
        }
        d = RUNS / "xsec" / f"{micro}_s{seed}"
        d.mkdir(parents=True, exist_ok=True)
        (d / "result.json").write_text(json.dumps(out, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
        results.append(out)
        print(f"[xsec] seed {seed}: test_IC={out['test_ic']:+.5f} "
              f"RankIC={out['test_rank_ic']:+.5f} "
              f"日IC均值={out['test_daily_ic_mean']:+.4f} -> {d}", flush=True)

    if results:
        ics = [q["test_ic"] for q in results]
        rcs = [q["test_rank_ic"] for q in results]
        dics = [q["test_daily_ic_mean"] for q in results]
        print(f"\n=== 汇总（{len(results)} 种子）===")
        print(f"pooled IC {np.mean(ics):+.5f} ± {np.std(ics):.5f}")
        print(f"pooled RankIC {np.mean(rcs):+.5f} ± {np.std(rcs):.5f}")
        print(f"日度 IC 均值 {np.mean(dics):+.5f} ± {np.std(dics):.5f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[0])
    ap.add_argument("--device", default=None)
    ap.add_argument("--lookback", type=int, default=240)
    ap.add_argument("--horizon", type=int, default=24)
    ap.add_argument("--stride", type=int, default=40)
    ap.add_argument("--epochs", type=int, default=10)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--d-hidden", type=int, default=256)
    ap.add_argument("--n-heads", type=int, default=4)
    ap.add_argument("--dropout", type=float, default=0.3)
    ap.add_argument("--wd", type=float, default=0.1)
    ap.add_argument("--no-residual", action="store_true")
    ap.add_argument("--micro", default="none", choices=["none", "m1", "l2", "sde", "m1sde"],
                    help="额外接入的微观张量（与 K 线池化特征拼接）")
    a = ap.parse_args()
    run(a.seeds, a.device, a.lookback, a.horizon, a.stride, a.epochs, a.lr,
        a.d_hidden, a.n_heads, a.dropout, a.wd, not a.no_residual, a.micro)


if __name__ == "__main__":
    main()
