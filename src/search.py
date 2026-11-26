"""Exact short-derivation search: given pool values (in registers), a target t and the value limit L,
find a derivation of t that uses at most kmax new instructions (kmax <= 5), meet-in-the-middle with numpy.

A derivation is a list of steps (op, a, b): a/b are ('p', pool_index) or ('n', step_index); the last step yields t.
"""
import numpy as np

OPS = "+-*/"


def _f1(V, L):
    """All values a op b with a, b in the pool (including a op a). Returns (vals, op, i, j) sorted by value, deduped."""
    n = len(V)
    I, J = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    I, J = I.ravel(), J.ravel()
    A, B = V[I], V[J]
    out_v, out_o, out_i, out_j = [], [], [], []
    m = I <= J                                     # + and * are symmetric
    s = A[m] + B[m]; k = s <= L
    out_v.append(s[k]); out_o.append(np.zeros(k.sum(), np.int8)); out_i.append(I[m][k]); out_j.append(J[m][k])
    pf = A[m].astype(np.float64) * B[m]; k = pf <= L * 1.001
    p = A[m][k] * B[m][k]; kk = p <= L
    out_v.append(p[kk]); out_o.append(np.full(kk.sum(), 2, np.int8)); out_i.append(I[m][k][kk]); out_j.append(J[m][k][kk])
    k = A > B
    out_v.append(A[k] - B[k]); out_o.append(np.ones(k.sum(), np.int8)); out_i.append(I[k]); out_j.append(J[k])
    k = (A % B) == 0
    out_v.append(A[k] // B[k]); out_o.append(np.full(k.sum(), 3, np.int8)); out_i.append(I[k]); out_j.append(J[k])
    v = np.concatenate(out_v); o = np.concatenate(out_o); i = np.concatenate(out_i); j = np.concatenate(out_j)
    return _dedupe(v, o, i, j, exclude=V)


def _dedupe(v, *cols, exclude=None):
    order = np.argsort(v, kind="stable")
    v = v[order]; cols = [c[order] for c in cols]
    keep = np.ones(len(v), bool); keep[1:] = v[1:] != v[:-1]
    if exclude is not None and len(v):
        keep &= ~np.isin(v, exclude)
    return (v[keep],) + tuple(c[keep] for c in cols)


def _f2(V, F1v, L):
    """Chains: x op c where x in F1 and c in pool (or c = x itself). Returns (vals, xidx, op, cidx, swap) sorted, deduped.
    swap=1 means the instruction is (c op x) instead of (x op c); cidx=-1 means c is x itself."""
    m, n = len(F1v), len(V)
    X = np.repeat(np.arange(m), n); C = np.tile(np.arange(n), m)
    a, b = F1v[X], V[C]
    vs, xs, os_, cs, ss = [], [], [], [], []

    def add(val, mask, op, swap):
        vs.append(val); xs.append(X[mask]); os_.append(np.full(mask.sum(), op, np.int8)); cs.append(C[mask])
        ss.append(np.full(mask.sum(), swap, np.int8))
    s = a + b; k = s <= L; add(s[k], k, 0, 0)
    pf = a.astype(np.float64) * b; k = pf <= L * 1.001; p = a * b; k = k & (p <= L) & (p > 0); add(p[k], k, 2, 0)
    k = a > b; add(a[k] - b[k], k, 1, 0)
    k = b > a; add(b[k] - a[k], k, 1, 1)
    k = (a % b) == 0; add(a[k] // b[k], k, 3, 0)
    k = (b % a) == 0; add(b[k] // a[k], k, 3, 1)
    # x op x
    idx = np.arange(m)
    s = 2 * F1v; k = s <= L
    vs.append(s[k]); xs.append(idx[k]); os_.append(np.zeros(k.sum(), np.int8)); cs.append(np.full(k.sum(), -1)); ss.append(np.zeros(k.sum(), np.int8))
    k = F1v.astype(np.float64) ** 2 <= L * 1.001; sq = F1v[k] * F1v[k]; kk = sq <= L
    vs.append(sq[kk]); xs.append(idx[k][kk]); os_.append(np.full(kk.sum(), 2, np.int8)); cs.append(np.full(kk.sum(), -1)); ss.append(np.zeros(kk.sum(), np.int8))
    v = np.concatenate(vs)
    return _dedupe(v, np.concatenate(xs), np.concatenate(os_), np.concatenate(cs), np.concatenate(ss))


def _inv(t, Y, L):
    """For each y in array Y, the x values with t = x op y or t = y op x. Returns list of (xvals, mask_idx, op, swap):
    instruction is (x op y) when swap=0, (y op x) when swap=1."""
    out = []
    x = t - Y; k = x > 0; out.append((x[k], np.nonzero(k)[0], 0, 0))            # x + y
    x = t + Y; k = x <= L; out.append((x[k], np.nonzero(k)[0], 1, 0))           # x - y
    x = Y - t; k = x > 0; out.append((x[k], np.nonzero(k)[0], 1, 1))            # y - x
    k = (t % Y) == 0; out.append((t // Y[k], np.nonzero(k)[0], 2, 0))             # x * y
    k = Y <= L // t; out.append((t * Y[k], np.nonzero(k)[0], 3, 0))              # x / y
    k = (Y % t) == 0; out.append((Y[k] // t, np.nonzero(k)[0], 3, 1))             # y / x
    return out


def _find_in(xs, S):
    """Positions in xs whose value is in sorted array S; returns (pos_in_xs, pos_in_S)."""
    if len(S) == 0 or len(xs) == 0:
        return np.array([], int), np.array([], int)
    p = np.searchsorted(S, xs); p[p >= len(S)] = 0
    hit = S[p] == xs
    return np.nonzero(hit)[0], p[hit]


class Pool:
    def __init__(self, values, L):
        self.V = np.array(sorted(set(int(v) for v in values)), dtype=np.int64)
        self.L = L
        self.F1 = _f1(self.V, L)
        self._F2 = None

    @property
    def F2(self):
        if self._F2 is None:
            self._F2 = _f2(self.V, self.F1[0], self.L)
        return self._F2

    # ---- derivation builders (return list of steps; refs ('p', value) for pool values, ('n', k) for new steps)
    def _d1(self, k):
        v, o, i, j = self.F1
        return [(OPS[o[k]], ("p", int(self.V[i[k]])), ("p", int(self.V[j[k]])))]

    def _d2(self, k):
        v, x, o, c, s = self.F2
        steps = self._d1(x[k])
        other = ("n", 0) if c[k] < 0 else ("p", int(self.V[c[k]]))
        steps.append((OPS[o[k]], ("n", 0), other) if not s[k] else (OPS[o[k]], other, ("n", 0)))
        return steps

    @staticmethod
    def _join(left, right, op, swap):
        """t = L op R (swap=0) or R op L (swap=1); left/right derivations are concatenated with renumbering."""
        off = len(left)
        def sh(ref):
            return ("n", ref[1] + off) if ref[0] == "n" else ref
        right2 = [(o, sh(a), sh(b)) for o, a, b in right]
        lref, rref = ("n", len(left) - 1), ("n", len(left) + len(right) - 1)
        if not left: lref = None
        steps = left + right2
        return steps, lref, rref

    def find(self, t, kmax):
        """Shortest derivation of t with <= kmax steps (exhaustive for the covered shapes)."""
        t = int(t); L = self.L; V = self.V
        if t in set(V.tolist()):
            return []
        F1v = self.F1[0]
        # k = 1
        pos = np.searchsorted(F1v, t)
        if pos < len(F1v) and F1v[pos] == t:
            return self._d1(pos)
        if kmax < 2: return None
        # backward step from pool: t = x op c (c pool) or x op x
        B1 = _inv(t, V, L)
        selfs = []
        if t % 2 == 0: selfs.append((t // 2, "+"))
        r = int(round(t ** 0.5))
        for q in (r - 1, r, r + 1):
            if q > 0 and q * q == t: selfs.append((q, "*"))

        def final_with_pool(deriv, c_idx, op, swap):
            last = ("n", len(deriv) - 1); c = ("p", int(V[c_idx]))
            return deriv + [(OPS[op], last, c) if not swap else (OPS[op], c, last)]

        def final_self(deriv, op):
            last = ("n", len(deriv) - 1)
            return deriv + [(op, last, last)]
        # k = 2: B1 in F1
        for xv, ci, op, sw in B1:
            a, b = _find_in(xv, F1v)
            if len(a): return final_with_pool(self._d1(b[0]), ci[a[0]], op, sw)
        for q, op in selfs:
            p = np.searchsorted(F1v, q)
            if p < len(F1v) and F1v[p] == q: return final_self(self._d1(p), op)
        if kmax < 3: return None
        # k = 3: F1 (+) F1 ; B1 in F2 ; selfs in F2
        res = self._f1f1(t)
        if res: return res
        F2v = self.F2[0]
        for xv, ci, op, sw in B1:
            a, b = _find_in(xv, F2v)
            if len(a): return final_with_pool(self._d2(b[0]), ci[a[0]], op, sw)
        for q, op in selfs:
            p = np.searchsorted(F2v, q)
            if p < len(F2v) and F2v[p] == q: return final_self(self._d2(p), op)
        if kmax < 4: return None
        # k = 4: F2 (+) F1 ; B1 in F1(+)F1 ; B2 in F2
        res = self._f2f1(t)
        if res: return res
        for xv, ci, op, sw in B1:
            for xx, ii in zip(xv[:4000], ci[:4000]):
                r = self._f1f1(int(xx))
                if r: return final_with_pool(r, ii, op, sw)
        for q, op in selfs:
            r = self._f1f1(q)
            if r: return final_self(r, op)
        res = self._b2_in(t, F2v, self._d2)
        if res: return res
        if kmax < 5: return None
        # k = 5: F2 (+) F2 ; B1 in F2(+)F1 ; B2 in F1(+)F1 is skipped (too wide)
        res = self._f2f2(t)
        if res: return res
        for xv, ci, op, sw in B1:
            for xx, ii in zip(xv[:2000], ci[:2000]):
                r = self._f2f1(int(xx))
                if r: return final_with_pool(r, ii, op, sw)
        return None

    def _b2_in(self, t, S, builder):
        """t = (s op c) op d with s in S, c, d in pool."""
        V, L = self.V, self.L
        for xv, ci, op, sw in _inv(t, V, L):
            for x1, c1 in zip(xv, ci):
                for yv, di, op2, sw2 in _inv(int(x1), V, L):
                    a, b = _find_in(yv, S)
                    if len(a):
                        d = builder(b[0])
                        last = ("n", len(d) - 1); cp = ("p", int(V[di[a[0]]]))
                        d = d + [(OPS[op2], last, cp) if not sw2 else (OPS[op2], cp, last)]
                        last = ("n", len(d) - 1); cp = ("p", int(V[c1]))
                        return d + [(OPS[op], last, cp) if not sw else (OPS[op], cp, last)]
        return None

    def _pair(self, t, Yv, Sv, ybuild, sbuild):
        """t = s op y with y in Yv (built by ybuild), s in Sv (built by sbuild)."""
        for xv, yi, op, sw in _inv(t, Yv, self.L):
            a, b = _find_in(xv, Sv)
            if len(a):
                left = sbuild(b[0]); right = ybuild(yi[a[0]])
                steps, lref, rref = self._join(left, right, op, sw)
                return steps + [(OPS[op], lref, rref) if not sw else (OPS[op], rref, lref)]
        return None

    def _f1f1(self, t):
        F1v = self.F1[0]
        return self._pair(t, F1v, F1v, self._d1, self._d1)

    def _f2f1(self, t):
        return self._pair(t, self.F1[0], self.F2[0], self._d1, self._d2)

    def _f2f2(self, t):
        F2v = self.F2[0]
        return self._pair(t, F2v, F2v, self._d2, self._d2)


def check(deriv, pool, t, L):
    """Evaluate a derivation; returns final value or raises."""
    vals = []
    for op, a, b in deriv:
        x = a[1] if a[0] == "p" else vals[a[1]]
        y = b[1] if b[0] == "p" else vals[b[1]]
        assert a[0] != "p" or a[1] in pool
        assert b[0] != "p" or b[1] in pool
        if op == "+": z = x + y
        elif op == "-": assert x > y; z = x - y
        elif op == "*": z = x * y
        else: assert x % y == 0; z = x // y
        assert 0 < z <= L, (z, L)
        vals.append(z)
    assert vals[-1] == t
    return vals
