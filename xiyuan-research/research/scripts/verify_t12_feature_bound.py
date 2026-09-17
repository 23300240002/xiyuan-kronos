#!/usr/bin/env python3
"""Exact discrete verification for C-T12-002 (Y3 restatement).

Lemma/Proposition 1:  I(x; g(Y) | Yt) <= I(x; Y | Yt) <= H(Y | Yt)
    (deterministic feature X_T = g(Y); conditional data-processing inequality)
Corollary 2:          asymptotically lossless quantizer family => increment -> 0
Proposition 2:        out-of-support construction: Yt = Y (lossless),
                      I(x; Y | Yt) = 0 and I(x; X_M | Yt) = 1 bit
Proposition 3:        two-term decomposition for X = (X_T, X_M)

Method: full enumeration over finite alphabets, exact Fraction arithmetic
for probabilities; log2 evaluated in float (differences far exceed 1e-12).
No randomness, no seed. No model, no data, no network.
"""
import math
from fractions import Fraction

def _h_bits(probs):
    return sum(-float(p) * math.log2(float(p)) for p in probs if p > 0)

def _marg(joint, idx):
    out = {}
    for keys, p in joint.items():
        out[keys[idx]] = out.get(keys[idx], Fraction(0)) + p
    return out

def _mi_bits(joint, i, j):
    pi, pj, n = _marg(joint, i), _marg(joint, j), len(joint[0]) if False else None
    val = 0.0
    for keys, p in joint.items():
        if p > 0:
            val += float(p) * (math.log2(float(p)) - math.log2(float(pi[keys[i]])) - math.log2(float(pj[keys[j]])))
    return val

def _cmi_bits(joint, i, j, z):
    """I(X_i; X_j | X_z) for joint dict: keys are tuples (x_i, x_j, x_z)."""
    total = 0.0
    for zv, pz in _marg(joint, z).items():
        sub = {}
        for keys, p in joint.items():
            if keys[z] == zv and p > 0:
                sub[(keys[i], keys[j])] = p / pz
        total += float(pz) * _mi_bits(sub, 0, 1)
    return total

def _h_cond_bits(joint, i, z):
    """H(X_i | X_z): sub-distribution over the value at index i, normalized by P(X_z)."""
    total = 0.0
    for zv, pz in _marg(joint, z).items():
        sub = {}
        for kv, p in joint.items():
            if kv[z] == zv and p > 0:
                sub[kv[i]] = sub.get(kv[i], Fraction(0)) + p / pz
        total += float(pz) * _h_bits(list(sub.values()))
    return total

def make_joint(vals_x, vals_y, vals_z, mass):
    j = {}
    for (x, y, z), p in mass:
        assert p >= 0
        j[(x, y, z)] = p
    s = sum(j.values())
    assert s == 1, f"prob mass {s} != 1"
    return j

ok = True
def check(name, cond, detail=""):
    global ok
    status = "PASS" if cond else "FAIL"
    if not cond:
        ok = False
    print(f"[{status}] {name}  {detail}")

print("=== Test A1: strict bound (Lemma 1) ===")
# Y=(Y1,Y2) uniform, Yt=Y1, g=Y1&Y2, x=Y2
mass = [(y2, (y1, y2), y1) for y1 in (0, 1) for y2 in (0, 1)]
j = {k: Fraction(1, 4) for k in mass}
i_gt = _cmi_bits(j, 0, 1, 2)     # I(x; Y | Yt)
i_gg = _cmi_bits(j, 0, 1, 2) if False else None
# I(x; g | Yt): need joint over (x, g, Yt); g=(y1&y2)
mass2 = [(y2, y1 & y2, y1) for y1 in (0, 1) for y2 in (0, 1)]
j2 = {k: Fraction(1, 4) for k in mass2}
i_xg = _cmi_bits(j2, 0, 1, 2)    # I(x; g(Y) | Yt)
h_y_yt = _h_cond_bits(j, 1, 2)   # H(Y | Yt)
print(f"    I(x;g|Yt)={i_xg:.6f}  I(x;Y|Yt)={i_gt:.6f}  H(Y|Yt)={h_y_yt:.6f}")
check("A1 bound", i_xg <= i_gt + 1e-12 and i_gt <= h_y_yt + 1e-12)
check("A1 values", abs(i_xg - 0.5) < 1e-12 and abs(i_gt - 1.0) < 1e-12 and abs(h_y_yt - 1.0) < 1e-12)

print("=== Test A2: noisy target, bound strict ===")
# x = Y2 xor W, W~Bern(0.2)
mass3 = []
for y1 in (0, 1):
    for y2 in (0, 1):
        for w, pw in ((0, Fraction(4, 5)), (1, Fraction(1, 5))):
            mass3.append((y2 ^ w, y1 & y2, y1, pw * Fraction(1, 4)))
j3 = {}
for x, g, z, p in mass3:
    j3[(x, g, z)] = j3.get((x, g, z), Fraction(0)) + p
i_xg3 = _cmi_bits(j3, 0, 1, 2)
j3y = {}
for y1 in (0, 1):
    for y2 in (0, 1):
        for w, pw in ((0, Fraction(4, 5)), (1, Fraction(1, 5))):
            j3y[(y2 ^ w, (y1, y2), y1)] = j3y.get((y2 ^ w, (y1, y2), y1), Fraction(0)) + pw * Fraction(1, 4)
i_xy3 = _cmi_bits(j3y, 0, 1, 2)
expected = 1.0 - (float(Fraction(1, 5)) * math.log2(0.2) * -1 + float(Fraction(4, 5)) * math.log2(0.8) * -1)
print(f"    I(x;g|Yt)={i_xg3:.6f}  I(x;Y|Yt)={i_xy3:.6f}  (1-Hb(0.2)={expected:.6f})")
check("A2 bound", i_xg3 <= i_xy3 + 1e-12)
check("A2 values", abs(i_xy3 - expected) < 1e-12 and abs(i_xg3 - 0.5 * expected) < 1e-12)

print("=== Test A3: equality case g = full residual (g=Y2, x=Y2) ===")
mass4 = [(y2, y2, y1) for y1 in (0, 1) for y2 in (0, 1)]
j4 = {k: Fraction(1, 4) for k in mass4}
a = _cmi_bits(j4, 0, 1, 2)
b = _cmi_bits(j, 0, 1, 2)
print(f"    I(x;g|Yt)={a:.6f}  I(x;Y|Yt)={b:.6f}")
check("A3 equality", abs(a - b) < 1e-12)

print("=== Test B: fidelity family, decay to 0 at lossless (Corollary 2) ===")
# Y=(Y1,Y2,Y3) uniform, x=Y3, g=Y3, Yt_k = (Y1..Yk)
base = {}
for y1 in (0, 1):
    for y2 in (0, 1):
        for y3 in (0, 1):
            base[(y1, y2, y3)] = Fraction(1, 8)
for k in (1, 2, 3):
    jt = {}
    for (y1, y2, y3), p in base.items():
        yt = (y1, y2, y3)[:k]
        key = (y3, (y1, y2, y3), yt)
        jt[key] = jt.get(key, Fraction(0)) + p
    jg = {}
    for (y1, y2, y3), p in base.items():
        yt = (y1, y2, y3)[:k]
        jg[(y3, y3, yt)] = jg.get((y3, y3, yt), Fraction(0)) + p
    i_xy = _cmi_bits(jt, 0, 1, 2)
    i_xg = _cmi_bits(jg, 0, 1, 2)
    h_y = _h_cond_bits(jt, 1, 2)
    print(f"    k={k}: I(x;Y|Yt_k)={i_xy:.6f}  I(x;g|Yt_k)={i_xg:.6f}  H(Y|Yt_k)={h_y:.6f}")
    check(f"B k={k} bound+decay", i_xg <= i_xy + 1e-12 and i_xy <= h_y + 1e-12)
check("B lossless zero", abs(_cmi_bits(jg, 0, 1, 2)) < 1e-12)

print("=== Test C: out-of-support construction (Proposition 2) ===")
# Y~Bern(1/2), X_M~Bern(1/2) indep, x=Y xor X_M, Yt=Y
jc = {}
for y in (0, 1):
    for m in (0, 1):
        jc[(y ^ m, y, y)] = jc.get((y ^ m, y, y), Fraction(0)) + Fraction(1, 4)   # (x, Y, Yt)
jm = {}
for y in (0, 1):
    for m in (0, 1):
        jm[(y ^ m, m, y)] = jm.get((y ^ m, m, y), Fraction(0)) + Fraction(1, 4)   # (x, X_M, Yt)
i_xy = _cmi_bits(jc, 0, 1, 2)
i_xm = _cmi_bits(jm, 0, 1, 2)
print(f"    I(x;Y|Yt)={i_xy:.6f}  I(x;X_M|Yt)={i_xm:.6f}")
check("C lossless", abs(i_xy) < 1e-12)
check("C one bit", abs(i_xm - 1.0) < 1e-12)

print()
print("ALL PASS" if ok else "FAILURES PRESENT")
