# -*- coding: utf-8 -*-
"""循环 3：核验 Y3 的链式法则恒等式，并对三类 F 做区分。

待核验恒等式（协议给出）：
    I(T;F|S) = I(T;F|H) + I(T;H|S) - I(T;H|F,S),   其中 S = g(H)

推导：因为 S = g(H)，条件于 H 后 S 冗余，故 I(T;F|H,S) = I(T;F|H)。
      再由链式法则的两个展开式相减即得。本脚本用离散联合分布逐项数值核验。

三类 F（协议要求区分）：
  情形 1  F 是模型实际输入 S 的函数：  F = h(S)          → 预期 I(T;F|S) = 0
  情形 2  F = f(H)，但 H 的信息严格多于 S（S 有损）      → 预期 I(T;F|S) 可 > 0
  情形 3  F 依赖 H 之外的变量（外部信息）                → 恒等式需扩展到 (H, E)

为了同时覆盖"F 是 S 的函数"与"F 用到 S 之外的信息"，本脚本用离散枚举，
状态空间 = (T, S, F, H)，全部由 (A,B) 确定性生成。
"""
from __future__ import annotations

import itertools

import numpy as np


def joint_from_fn(T_fn, S_fn, F_fn, n_h=4):
    """H 取 n_h 个等概率状态；T/S/F 均为 H 的确定性函数。

    返回 4D 数组 p[t, s, f, h]。
    """
    p = np.zeros((2, 2, 2, n_h))
    for h in range(n_h):
        t, s, f = T_fn(h), S_fn(h), F_fn(h)
        p[t, s, f, h] += 1.0 / n_h
    return p


def _ent(arr):
    """香农熵（nats），arr 为任意维的概率数组。"""
    a = arr.ravel()
    a = a[a > 0]
    return float(-(a * np.log(a)).sum())


def _cond_ent(p, keep_axes, cond_axes):
    """H(keep | cond)：返回条件熵。p 为联合数组，轴顺序固定。"""
    # 先对既不在 keep 也不在 cond 的轴求和
    all_axes = set(range(p.ndim))
    drop = sorted(all_axes - set(keep_axes) - set(cond_axes), reverse=True)
    q = p
    for ax in drop:
        q = q.sum(axis=ax)
    # 归一到 cond 的边缘
    cond_axes2 = [a - sum(1 for d in drop if d < a) for a in cond_axes]
    marg = q.sum(axis=tuple(a for a in range(q.ndim) if a not in cond_axes2))
    marg = np.maximum(marg, 1e-300)
    # H(keep, cond)
    h_joint = _ent(q)
    h_condmarg = _ent(marg)
    return h_joint - h_condmarg


def cmi(p, X, Y, Z):
    """I(X;Y|Z) = H(X|Z) - H(X|Y,Z)。p 轴顺序为 (T=0, S=1, F=2, H=3)。

    Z 可以是单个轴号，也可以是轴号列表（联合条件）。
    """
    Zs = list(Z) if isinstance(Z, (list, tuple)) else [Z]
    Ys = list(Y) if isinstance(Y, (list, tuple)) else [Y]
    return (_cond_ent(p, [X], Zs) - _cond_ent(p, [X], Ys + Zs))


def check(name, T_fn, S_fn, F_fn, n_h=4, verbose=True):
    p = joint_from_fn(T_fn, S_fn, F_fn, n_h)
    lhs = cmi(p, 0, 2, [1])               # I(T;F|S)
    a = cmi(p, 0, 2, [3])                 # I(T;F|H)
    b = cmi(p, 0, 3, [1])                 # I(T;H|S)
    c = cmi(p, 0, 3, [2, 1])              # I(T;H|F,S)
    rhs = a + b - c
    if verbose:
        print(f"\n  [{name}]")
        print(f"    I(T;F|S)      = {lhs:+.10f}")
        print(f"    I(T;F|H)      = {a:+.10f}")
        print(f"    I(T;H|S)      = {b:+.10f}")
        print(f"    I(T;H|F,S)    = {c:+.10f}")
        print(f"    RHS           = {rhs:+.10f}")
        print(f"    |LHS-RHS|     = {abs(lhs-rhs):.2e}")
    return abs(lhs - rhs)


def main():
    print("=" * 88)
    print("循环 3 · 核验 I(T;F|S) = I(T;F|H) + I(T;H|S) - I(T;H|F,S)，S = g(H)")
    print("=" * 88)
    print("  H 取 4 个等概率状态 h ∈ {0,1,2,3}（可读作 h = 2A+B，A、B 为两个独立二元变量）")

    worst = 0.0

    # --- 情形 0：F = S（F 完全是摘要本身）
    worst = max(worst, check(
        "情形 0  F ≡ S（F 是摘要本身）",
        T_fn=lambda h: h % 2,
        S_fn=lambda h: h // 2,
        F_fn=lambda h: h // 2))

    # --- 情形 1：F 是 S 的函数，但 S 不足以预测 T
    #   A = h//2, B = h%2；S = A；F = A；T = A xor B
    worst = max(worst, check(
        "情形 1  F = h(S)（F 完全由摘要决定）→ 应 I(T;F|S)=0",
        T_fn=lambda h: (h // 2) ^ (h % 2),
        S_fn=lambda h: h // 2,
        F_fn=lambda h: h // 2))

    # --- 情形 2：F = f(H)，用到 S 之外的那一半历史
    #   S = A（有损摘要），F = B（S 之外的信息），T = A xor B
    worst = max(worst, check(
        "情形 2  F = f(H) 且用到 S 之外的历史 → I(T;F|S) 应 > 0",
        T_fn=lambda h: (h // 2) ^ (h % 2),
        S_fn=lambda h: h // 2,
        F_fn=lambda h: h % 2))

    # --- 情形 3：F = f(H)，但 T 只依赖 A（即 T 与 S 之外的成分无关）
    worst = max(worst, check(
        "情形 3  F = f(H) 但 T ⟂ F | H（F 对 T 无增量）",
        T_fn=lambda h: h // 2,
        S_fn=lambda h: h // 2,
        F_fn=lambda h: h % 2))

    # --- 情形 4：S 是 H 的有损摘要，F 是 H 的另一部分，T 依赖二者
    worst = max(worst, check(
        "情形 4  S 有损、T 依赖 S 内外两侧信息",
        T_fn=lambda h: (h // 2) ^ (h % 2),
        S_fn=lambda h: 0 if (h % 2 == 0) else 1,      # 只反映 B，丢弃 A
        F_fn=lambda h: h // 2))

    print("\n" + "-" * 88)
    print(f"  五种情形的最大 |LHS − RHS| = {worst:.2e}")
    print(f"  ⟹ 恒等式{'成立' if worst < 1e-12 else '不成立'}")

    print("\n  情形分类对照（本脚本可支持的结论）：")
    print("    情形 0/1  I(T;F|S) = 0        —— F 完全由摘要决定时，F 无增量")
    print("    情形 2/4  I(T;F|S) > 0        —— F 用到摘要之外的历史时，F 可有增量")
    print("    情形 2 同时给出：I(T;F|H) = 0 —— 但这**不**蕴含 I(T;F|S) = 0")
    print("    （这正是 C-T12-001 §3.1 修正的要点：条件集必须是 S，不是 H）")


if __name__ == "__main__":
    main()
