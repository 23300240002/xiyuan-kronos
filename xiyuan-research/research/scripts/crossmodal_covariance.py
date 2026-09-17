# -*- coding: utf-8 -*-
"""循环 2+3：含噪跨模态诊断模型 —— 从协方差矩阵独立推导（无 quad、无蒙特卡洛）

模型（由协议给定的关系 R_H = lambda + (1-lambda) R, lambda=(v+theta)/(2(1+v)) 反推而来）：
    T, P_H, P_L, xi_H, xi_L  iid N(0,1)
    Z_H = sqrt(1-theta) T + sqrt(theta) P_H + sqrt(nu) xi_H
    Z_L = sqrt(1-theta) T + sqrt(theta) P_L + sqrt(nu) xi_L

直接可得（无需任何数值积分）：
    Var(Z_i) = 1 + nu
    Cov(T, Z_i) = sqrt(1-theta)
    Cov(Z_H, Z_L) = 1 - theta
    D = E[(Z_H - Z_L)^2] = 2(theta + nu)
    R_H = 1 - Cov(T,Z_H)^2 / Var(Z_H) = (nu + theta)/(1 + nu)
    R   = 1 - c^T Sigma^{-1} c                       （双路 Bayes 平方风险，线性头）
        = (nu + theta)/(2 + nu - theta)

本脚本**只做线性代数**（2x2 求逆、行列式），不使用积分。
"""
from __future__ import annotations

import numpy as np


def quantities(theta: float, nu: float):
    """由协方差矩阵直接给出全部量。"""
    th, v = float(theta), float(nu)
    c1 = np.sqrt(max(1.0 - th, 0.0))          # Cov(T, Z_i)
    v1 = 1.0 + v                              # Var(Z_i)
    c12 = 1.0 - th                            # Cov(Z_H, Z_L)

    D = 2.0 * (th + v)
    R_H = 1.0 - c1 ** 2 / v1

    # 2x2 线性系统（双路最优线性头）
    S = np.array([[v1, c12], [c12, v1]])
    cvec = np.array([c1, c1])
    expl = float(cvec @ np.linalg.solve(S, cvec))     # 解释方差
    R = 1.0 - expl
    cond_var = R                                       # T|Z_H,Z_L 的后验方差 = R（高斯）
    det = float(np.linalg.det(S))

    # 互信息（全部高斯，闭式）
    I_single = -0.5 * np.log(1.0 - c1 ** 2 / v1)
    I_joint = -0.5 * np.log(R)
    dI = I_joint - I_single                            # = I(T;Z_L | Z_H)
    return dict(theta=th, nu=v, D=D, R=R, R_H=R_H, det=det,
                cond_var=cond_var, I_single=I_single, I_joint=I_joint, dI=dI,
                rho_TZ2=c1 ** 2 / v1, rho_12=c12 / v1)


def lam(theta: float, nu: float) -> float:
    return (nu + theta) / (2.0 * (1.0 + nu))


def main():
    print("=" * 104)
    print("循环 2 · 含噪跨模态诊断模型：从协方差矩阵独立推导")
    print("=" * 104)

    # [2.1] 验证 R_H = lambda + (1-lambda) R 以及 R 的闭式
    print("\n[2.1] 验证 R_H = lambda + (1-lambda)R，  lambda=(nu+theta)/(2(1+nu))")
    print(f"{'nu':>6} {'theta':>7} | {'R_H 直算':>12} | {'lambda+(1-lambda)R':>19} "
          f"| {'绝对差':>10} | {'R 闭式':>12} | {'R 直算':>12}")
    worst = 0.0
    for nu in [0.25, 1.0, 4.0]:
        for th in [0.0, 0.25, 0.5, 0.75, 1.0]:
            q = quantities(th, nu)
            l = lam(th, nu)
            lhs = q["R_H"]
            rhs = l + (1 - l) * q["R"]
            R_cf = (nu + th) / (2 + nu - th)
            worst = max(worst, abs(lhs - rhs), abs(R_cf - q["R"]))
            if nu == 1.0:
                print(f"{nu:>6.2f} {th:>7.2f} | {lhs:>12.8f} | {rhs:>19.8f} "
                      f"| {abs(lhs-rhs):>10.2e} | {R_cf:>12.8f} | {q['R']:>12.8f}")
    print(f"  → 全部 (nu,theta) 组合上的最大偏差 = {worst:.2e}")

    # [2.2] gamma=0 的解析最优
    print("\n[2.2] 一致性权重 gamma=0 的解析最优")
    for nu in [0.25, 1.0, 4.0]:
        # R 随 theta 严格增；D 随 theta 严格增 ⟹ 两者同在 theta=0 取最小
        Rs = [quantities(t, nu)["R"] for t in np.linspace(0, 1, 101)]
        Ds = [quantities(t, nu)["D"] for t in np.linspace(0, 1, 101)]
        print(f"  nu={nu}: R 单调增={all(np.diff(Rs) > 0)}，D 单调增={all(np.diff(Ds) > 0)}"
              f"  ⟹ theta*=0，R*=nu/(2+nu)={nu/(2+nu):.10f}"
              f"（实算 {quantities(0.0, nu)['R']:.10f}）")

    # [2.3] Delta I 的闭式与单调性
    print("\n[2.3] Delta I 的闭式： dI = (1/2) ln[(2+nu-theta)/(1+nu)]")
    print(f"{'nu':>6} | {'theta=0':>12} {'theta=0.5':>12} {'theta=1':>12} | "
          f"{'闭式@0':>12} | 关于 theta 单调")
    for nu in [0.25, 1.0, 4.0]:
        vals = [quantities(t, nu)["dI"] for t in [0.0, 0.5, 1.0]]
        cf0 = 0.5 * np.log((2 + nu) / (1 + nu))
        ds = [quantities(t, nu)["dI"] for t in np.linspace(0, 1, 201)]
        mono = all(np.diff(ds) <= 1e-14)
        print(f"{nu:>6.2f} | {vals[0]:>12.8f} {vals[1]:>12.8f} {vals[2]:>12.8f} | "
              f"{cf0:>12.8f} | {mono}")

    print("\n[2.4] 全局最优路径上的 Delta I（gamma 取为一致性权重）")
    print("  由于 R 与 D 都随 theta 严格增，任意 gamma>=0 的最优都是 theta*=0")
    print("  ⟹ Delta I 沿 delta 路径为**常数** = (1/2)ln[(2+nu)/(1+nu)]")
    print("  ⟹ 『Delta I 随 delta 不增』成立，但以『不增的退化情形（恒定）』成立，")
    print("     本模型**不提供**关于真实互补性权衡的证据 —— 因私有成分 P_H,P_L 与 T 无关。")
    for nu in [0.25, 1.0, 4.0]:
        print(f"    nu={nu}: dI 常数 = {quantities(0.0, nu)['dI']:.10f}"
              f"  （纯去噪增益，非私有信号贡献）")

    print("\n" + "=" * 104)
    print("循环 3 · 回归测试（全部由协方差直接计算，无积分）")
    print("=" * 104)

    ok = True
    # T1 条件方差为正
    bad = []
    for nu in [0.1, 0.5, 1.0, 2.0, 5.0]:
        for th in np.linspace(0, 1, 21):
            if quantities(th, nu)["cond_var"] <= 0:
                bad.append((nu, th))
    print(f"T1 条件方差 > 0            : 违例 {len(bad)} 处  "
          f"{'PASS' if not bad else 'FAIL'}")
    ok &= not bad

    # T2 R <= R_H <= 1
    bad = []
    for nu in [0.1, 0.5, 1.0, 2.0, 5.0]:
        for th in np.linspace(0, 1, 21):
            q = quantities(th, nu)
            if not (q["R"] <= q["R_H"] + 1e-12 <= 1.0 + 1e-12):
                bad.append((nu, th, q["R"], q["R_H"]))
    print(f"T2 R <= R_H <= 1           : 违例 {len(bad)} 处  "
          f"{'PASS' if not bad else 'FAIL'}")
    ok &= not bad

    # T3 0 <= dI <= I_joint
    bad = []
    for nu in [0.1, 0.5, 1.0, 2.0, 5.0]:
        for th in np.linspace(0, 1, 21):
            q = quantities(th, nu)
            if not (-1e-12 <= q["dI"] <= q["I_joint"] + 1e-12):
                bad.append((nu, th, q["dI"], q["I_joint"]))
    print(f"T3 0 <= dI <= I(T;Z_H,Z_L) : 违例 {len(bad)} 处  "
          f"{'PASS' if not bad else 'FAIL'}")
    ok &= not bad

    # T4 gamma=0 的解析最优
    good = all(abs(quantities(0.0, nu)["R"] - nu / (2 + nu)) < 1e-12
               for nu in [0.25, 1.0, 4.0])
    print(f"T4 gamma=0: theta*=0, R*=nu/(2+nu) : {'PASS' if good else 'FAIL'}")
    ok &= good

    # T5 边缘分布相同但配对损失不同
    print("T5 边缘分布相同、配对损失不同：")
    # 模型 A：Z_H=T+xi_H, Z_L=T+xi_L (nu=1)       → Cov(Z_H,Z_L)=1
    # 模型 B：Z_H=T+xi_H, Z_L=T'+xi_L (nu=1)      → Cov(Z_H,Z_L)=0（T' 为独立副本）
    def direct(v1, c1, c12):
        S = np.array([[v1, c12], [c12, v1]])
        cvec = np.array([c1, c1])
        expl = float(cvec @ np.linalg.solve(S, cvec))
        return 1 - expl, 2 * (v1 - c12)

    RA, DA = direct(2.0, 1.0, 1.0)
    RB, DB = direct(2.0, 1.0, 0.0)
    print(f"    A: Var(Z)=2, Cov(T,Z)=1, Cov(Z_H,Z_L)=1 → R={RA:.6f}, D={DA:.6f}")
    print(f"    B: Var(Z)=2, Cov(T,Z)=1, Cov(Z_H,Z_L)=0 → R={RB:.6f}, D={DB:.6f}")
    diff = abs(RA - RB) > 1e-6 and abs(DA - DB) > 1e-6
    print(f"    边缘 (T,Z_H)、(T,Z_L) 完全相同，但 R 与 D 都不同  "
          f"{'PASS' if diff else 'FAIL'}")
    ok &= diff

    # T6 dI 包含去噪收益，不等同于私有信号贡献
    q = quantities(0.0, 1.0)
    print(f"T6 theta=0（无任何私有成分）时 dI = {q['dI']:.8f} > 0")
    print(f"    ⟹ dI 在纯冗余（两路同看 T）+ 独立噪声下也为正")
    print(f"    ⟹ dI 度量的是**去噪增益**，不能读作私有信号的贡献  "
          f"{'PASS' if q['dI'] > 0 else 'FAIL'}")
    ok &= (q["dI"] > 0)

    print(f"\n  循环 3 总判定：{'全部通过' if ok else '存在失败'}")


if __name__ == "__main__":
    main()
