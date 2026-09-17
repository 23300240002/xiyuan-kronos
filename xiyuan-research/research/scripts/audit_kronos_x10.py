"""Read-only smoke audit for the real KronosLocal context interface.

This script does not train a model or construct a cross-modal toy model.  It
checks that the locally stored tokenizer and Kronos-small weights can produce
the token-level context returned by ``decode_s1``.  The context is an interface
candidate for X-10, not a claim that alignment is already defined.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import torch


_root_env = os.environ.get("KRONOS_DIR")
if not _root_env:
    raise RuntimeError("set KRONOS_DIR to the local KronosLocal checkout root")
ROOT = Path(_root_env)
REPO = ROOT / "deps" / "Kronos"
TOKENIZER = ROOT / "deps" / "tokenizer_base"
MODEL = ROOT / "kronos_small" / "weights"


def main() -> None:
    if not (TOKENIZER / "config.json").exists():
        raise FileNotFoundError(f"missing tokenizer config: {TOKENIZER}")
    if not (MODEL / "config.json").exists():
        raise FileNotFoundError(f"missing model config: {MODEL}")

    sys.path.insert(0, str(REPO))
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    from model import Kronos, KronosTokenizer  # noqa: WPS433

    torch.manual_seed(0)
    tokenizer = KronosTokenizer.from_pretrained(str(TOKENIZER)).eval()
    model = Kronos.from_pretrained(str(MODEL)).eval()

    # Eight observed bars and five calendar features.  No future bar is passed.
    x = torch.arange(8 * 6, dtype=torch.float32).reshape(1, 8, 6) / 10.0
    stamp = torch.zeros(1, 8, 5, dtype=torch.float32)

    with torch.no_grad():
        s1_ids, s2_ids = tokenizer.encode(x, half=True)
        logits_1, context_1 = model.decode_s1(s1_ids, s2_ids, stamp=stamp)
        logits_2, context_2 = model.decode_s1(s1_ids, s2_ids, stamp=stamp)

    expected_d_model = int(model.d_model)
    assert context_1.shape == (1, 8, expected_d_model), context_1.shape
    assert logits_1.shape[:2] == (1, 8), logits_1.shape
    assert torch.equal(s1_ids, s1_ids.long()) and torch.equal(s2_ids, s2_ids.long())
    repeat_gap = (context_1 - context_2).abs().max().item()
    assert repeat_gap == 0.0, repeat_gap

    print(f"token_ids: {tuple(s1_ids.shape)}, {tuple(s2_ids.shape)}")
    print(f"context: {tuple(context_1.shape)}")
    print(f"s1_logits: {tuple(logits_1.shape)}")
    print(f"d_model: {expected_d_model}")
    print(f"repeat_max_abs_diff: {repeat_gap:.1e}")
    print("X10_CONTEXT_SMOKE: PASS")


if __name__ == "__main__":
    main()

