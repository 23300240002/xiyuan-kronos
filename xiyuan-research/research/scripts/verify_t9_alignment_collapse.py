# -*- coding: utf-8 -*-
"""C-T9-001 数值验证：边缘对齐损失导致表示坍塌

命题（待证）：
  若对齐损失 L_align 是"表示 Z 的边缘分布到某个与目标 Y 无关的固定先验 q 的散度"，
  则在 L_total = L_task + delta * L_align 中，随 delta 增大，Z 与 Y 的互信息单调下降，
  且存在有限 delta_c 使 delta > delta_c 时最优解满足 Z ⟂ Y（表示坍塌）。

本脚本用最简可解族验证该机制。**不做训练、不依赖任何外部数据。**

模型族（全部解析可算）：
  Y ~ Bernoulli(1/2)
  Z | Y=y ~ N(mu_y, sigma^2)          —— 编码器输出的条件分布
  故 p(Z) = 0.5 N(mu_0, s^2) + 0.5 N(mu_1, s^2)  （高斯混合，精确可算）
  任务损失  L_task = E[(Z-Y)^2] = 0.5(mu_0^2+s^2) + 0.5((mu_1-1)^2+s^2)
  对齐损失  L_align = KL( p(Z) || N(0,1) )        —— 边缘对齐，先验与 Y 无关
  目标      min_{mu_0,mu_1}  L_task + delta * L_align

输出：Δμ = mu_1 - mu_0 与 I(Z;Y) 随 delta 的变化。
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize
from scipy.stats import norm


def mixture_kl_to_prior(mu0: float, mu1: float, sigma: float,
                        n: int = 40001) -> float:
    """KL( 0.5 N(mu0,s^2) + 0.5 N(mu1,s^2) || N(0,1) )，数值积分。"""
    lo = min(mu0, mu1, 0.0) - 8.0 * sigma - 6.0
    hi = max(mu0, mu1, 0.0) + 8.0 * sigma + 6.0
    z = np.linspace(lo, hi, n)
    p = 0.5 * norm.pdf(z, mu0, sigma) + 0.5 * norm.pdf(z, mu1, sigma)
    q = norm.pdf(z, 0.0, 1.0)
    q = np.maximum(q, 1e-300)
    p = np.maximum(p, 1e-300)
    return float(np.trapezoid(p * np.log(p / q), z))


def mutual_information(mu0: float, mu1: float, sigma: float,
                       n: int = 40001) -> float:
    """I(Z;Y)，Z|Y 为同方差高斯。单位：nat。"""
    lo = min(mu0, mu1) - 8.0 * sigma - 2.0
    hi = max(mu0, mu1) + 8.0 * sigma + 2.0
    z = np.linspace(lo, hi, n)
    f0 = 0.5 * norm.pdf(z, mu0, sigma)
    f1 = 0.5 * norm.pdf(z, mu1, sigma)
    p = f0 + f1
    p = np.maximum(p, 1e-300)
    p1 = np.clip(f1 / p, 1e-12, 1 - 1e-12)
    h_y_given_z = -(p * (p1 * np.log(p1) + (1 - p1) * np.log(1 - p1)))
    h_cond = float(np.trapezoid(h_y_given_z, z))
    return float(np.log(2.0) - h_cond)


def objective(params, sigma: float, delta: float) -> float:
    mu0, mu1 = params
    l_task = 0.5 * (mu0 ** 2 + sigma ** 2) + 0.5 * ((mu1 - 1.0) ** 2 + sigma ** 2)
    l_align = mixture_kl_to_prior(mu0, mu1, sigma)
    return l_task + delta * l_align


def main() -> None:
    sigma = 0.20                     # 编码器噪声尺度
    deltas = [0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0]

    print(f"{'delta':>8} | {'mu_0':>8} {'mu_1':>8} | {'Δμ':>8} | "
          f"{'I(Z;Y) nats':>12} | {'任务损失':>9} | {'对齐损失':>9}")
    print("-" * 82)

    prev_dmu = None
    monotone = True
    rows = []
    for d in deltas:
        res = minimize(objective, x0=np.array([0.0, 1.0]), args=(sigma, d),
                       method="Nelder-Mead",
                       options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
        mu0, mu1 = res.x
        dmu = float(mu1 - mu0)
        mi = mutual_information(mu0, mu1, sigma)
        lt = 0.5 * (mu0 ** 2 + sigma ** 2) + 0.5 * ((mu1 - 1.0) ** 2 + sigma ** 2)
        la = mixture_kl_to_prior(mu0, mu1, sigma)
        if prev_dmu is not None and dmu > prev_dmu + 1e-6:
            monotone = False
        prev_dmu = dmu
        rows.append((d, dmu, mi))
        print(f"{d:>8.3f} | {mu0:>8.4f} {mu1:>8.4f} | {dmu:>8.4f} | "
              f"{mi:>12.6f} | {lt:>9.5f} | {la:>9.5f}")

    print("-" * 82)
    print(f"Δμ 随 delta 单调不增: {monotone}")
    print(f"delta=0    时 I(Z;Y) = {rows[0][2]:.6f} nats "
          f"（Bernoulli(1/2) 的上界 ln2 = {np.log(2):.6f}）")
    print(f"delta=100  时 I(Z;Y) = {rows[-1][2]:.6f} nats"
          f"  → 相对残余 {rows[-1][2] / np.log(2):.3%}")

    # 找出 I(Z;Y) 跌破上界 5% 的 delta
    thr = 0.05 * np.log(2)
    dc = next((d for d, _, mi in rows if mi < thr), None)
    if dc is not None:
        print(f"I(Z;Y) 首次跌破 ln2 的 5% 发生在 delta ≈ {dc}")
    else:
        print(f"sigma={sigma}：在测试的 delta 范围内未跌破 5% 阈值")

    # ---------------------------------------------------------------- 扫描
    # 初始猜想被上表推翻（sigma<<1 时不坍塌）。扫描编码器噪声尺度 sigma，
    # 找"坍塌/不坍塌"的分界——对齐目标为 N(0,1)，其尺度固定为 1。
    print("\n" + "=" * 82)
    print("扫描：坍塌是否发生，取决于 sigma 与先验尺度（=1）之比")
    print("=" * 82)
    print(f"{'sigma':>8} | {'Δμ @delta=0':>12} | {'Δμ @delta=100':>14} | "
          f"{'残余 Δμ 比例':>12} | {'I@100 / ln2':>12} | 判定")
    print("-" * 82)
    for s in [0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0, 1.4, 2.0, 3.0]:
        r0 = minimize(objective, x0=np.array([0.0, 1.0]), args=(s, 0.0),
                      method="Nelder-Mead",
                      options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
        r1 = minimize(objective, x0=np.array([0.0, 1.0]), args=(s, 100.0),
                      method="Nelder-Mead",
                      options={"xatol": 1e-8, "fatol": 1e-10, "maxiter": 4000})
        d0 = float(r0.x[1] - r0.x[0])
        d1 = float(r1.x[1] - r1.x[0])
        mi1 = mutual_information(r1.x[0], r1.x[1], s)
        ratio = d1 / d0 if d0 > 0 else float("nan")
        verdict = "坍塌" if ratio < 0.5 else ("部分" if ratio < 0.9 else "不坍塌")
        print(f"{s:>8.2f} | {d0:>12.4f} | {d1:>14.4f} | {ratio:>12.3f} | "
              f"{mi1 / np.log(2):>12.4f} | {verdict}")


if __name__ == "__main__":
    main()
