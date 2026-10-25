"""冻结 Kronos 主干：归一化 → tokenize → 取隐状态。

官方口径（`kronos.py:519-556` 的 KronosPredictor.predict）：
    x_mean, x_std = mean/std(x, axis=时间)      # 逐样本、逐通道
    x = clip((x - x_mean) / (x_std + 1e-5), -5, 5)
    s1_ids, s2_ids = tokenizer.encode(x, half=True)
    logits, h = model.decode_s1(s1_ids, s2_ids, stamp)   # h: [B, T, d_model]

本模块只做前向、不训练；所有参数 requires_grad=False。

自检：
    python -m xy.model.backbone --selftest
"""
from __future__ import annotations

import argparse
import sys
import time

import numpy as np
import torch

from xy.paths import KRONOS_LOCAL

SMALL = KRONOS_LOCAL / "kronos_small" / "weights"
BASE = KRONOS_LOCAL / "kronos_base" / "weights"
TOKENIZER = KRONOS_LOCAL / "deps" / "tokenizer_base"


def _import_kronos():
    """把 deps/Kronos 加进 sys.path，导入官方实现（不改它）。"""
    p = str(KRONOS_LOCAL / "deps" / "Kronos")
    if p not in sys.path:
        sys.path.insert(0, p)
    from model.kronos import Kronos, KronosTokenizer  # noqa: E402
    return Kronos, KronosTokenizer


class FrozenKronos:
    def __init__(self, size: str = "small", device: str | None = None,
                 max_context: int = 512, clip: float = 5.0, dtype=torch.float32):
        Kronos, KronosTokenizer = _import_kronos()
        self.tok = KronosTokenizer.from_pretrained(str(TOKENIZER))
        self.model = Kronos.from_pretrained(str(SMALL if size == "small" else BASE))

        if device is None:
            device = "cuda:0" if torch.cuda.is_available() else (
                "mps" if torch.backends.mps.is_available() else "cpu")
        self.device = torch.device(device)
        self.dtype = dtype

        self.tok.to(self.device).eval()
        self.model.to(self.device).eval()
        for p in self.tok.parameters():
            p.requires_grad_(False)
        for p in self.model.parameters():
            p.requires_grad_(False)

        self.max_context = max_context
        self.clip = clip
        self.d_model = self.model.d_model

    # ---------------------------------------------------------------- 归一化
    def normalize(self, x: torch.Tensor) -> torch.Tensor:
        """x: [B, T, 6] 原始量纲 → 官方口径的标准化输入。"""
        mu = x.mean(dim=1, keepdim=True)
        sd = x.std(dim=1, keepdim=True, unbiased=False)
        z = (x - mu) / (sd + 1e-5)
        return torch.clip(z, -self.clip, self.clip)

    # ---------------------------------------------------------------- 前向
    @torch.no_grad()
    def hidden(self, x: torch.Tensor, stamp: torch.Tensor | None = None) -> torch.Tensor:
        """x: [B, T, 6] 原始量纲。返回 [B, T, d_model] 隐状态（末位即 context）。"""
        x = x.to(self.device, dtype=self.dtype)
        if x.shape[1] > self.max_context:
            x = x[:, -self.max_context:]
        z = self.normalize(x)

        s1, s2 = self.tok.encode(z, half=True)
        if stamp is not None:
            stamp = stamp.to(self.device, dtype=self.dtype)[:, -x.shape[1]:]
        _, h = self.model.decode_s1(s1, s2, stamp)
        return h


def selftest(size: str = "small", batch: int = 8, length: int = 512) -> None:
    m = FrozenKronos(size=size)
    print(f"device={m.device}  d_model={m.d_model}  params="
          f"{sum(p.numel() for p in m.model.parameters()) / 1e6:.1f}M")

    x = torch.rand(batch, length, 6) * 100 + 10
    t0 = time.time()
    h = m.hidden(x)
    dt = time.time() - t0
    print(f"forward: x={tuple(x.shape)} -> h={tuple(h.shape)}  {dt * 1000:.0f} ms  "
          f"({batch * length / dt / 1000:.0f}k tok/s)")

    h2 = m.hidden(x)
    assert torch.allclose(h, h2, atol=1e-5), "两次前向结果不一致"
    assert h.shape[-1] == m.d_model
    assert not h.requires_grad
    print("SELFTEST PASS")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--size", default="small", choices=["small", "base"])
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--length", type=int, default=512)
    a = ap.parse_args()
    if a.selftest:
        selftest(a.size, a.batch, a.length)
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
