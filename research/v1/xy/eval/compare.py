"""汇总三臂结果 → 一页对比表（含零分布门槛判定）。

用法：
    python -m xy.eval.compare
"""
from __future__ import annotations

import json

from xy.paths import REPORTS, RUNS

# 由 xy.eval.report 在真实测试段上实测得到（194 日 / 100 万行）
NULL_Q = 0.00166


def main() -> None:
    rows = []
    for d in sorted((RUNS / "arm").glob("arm*_s*")):
        f = d / "result.json"
        if not f.exists():
            continue
        r = json.loads(f.read_text(encoding="utf-8"))
        hist = r.get("history") or []
        best = r.get("best_val_ic")
        rows.append({
            "arm": r["arm"], "freq": r["freq"], "seed": r["seed"],
            "params": r.get("n_params"),
            "epochs": len(hist),
            "best_val_ic": best,
            "final_loss": hist[-1]["train_loss"] if hist else None,
            "verdict": ("超出噪声" if best is not None and abs(best) > NULL_Q else "与噪声不可区分"),
        })

    L = ["# P1 · 三臂结果汇总\n",
         f"> 判定线：|IC| > {NULL_Q}（测试段 194 日 / 100 万行的零分布 95% 分位，实测）\n"]
    if not rows:
        L.append("_尚无结果。_")
    else:
        L.append("| arm | 频段 | seed | 可训练参数 | epochs | best val IC | 末轮 loss | 判定 |")
        L.append("|---|---|---|---|---|---|---|---|")
        for r in rows:
            L.append(f"| {r['arm']} | {r['freq']} | {r['seed']} | {r['params']:,} | "
                     f"{r['epochs']} | {r['best_val_ic']:+.4f} | {r['final_loss']:.5f} | {r['verdict']} |")
        L.append("")
        L.append("**注意**：val IC 是单一验证段的池化 Pearson，只作训练监控，不作结论；")
        L.append("正式结论需在独立测试段上用 pooled RankIC + block bootstrap。")

    out = REPORTS / "01_P1_三臂汇总.md"
    out.write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
