// pal.cpp - helper/palette set optimizer on top of a given program.
// Model: the program is an ordered list L of "kept" values (targets + helpers). Each kept value is derived from the
// starts and earlier kept values with an exact shortest derivation of 1..3 instructions (temps are not kept).
// cost(L) = sum of derivation lengths. Start: L = distinct values of the given program (cost = its length).
// Moves: remove a kept non-target helper; insert a new helper m (m = inverse-op of a target/helper that costs >= 2 and an
// earlier kept value), placed before its first beneficiary. Program is emitted + register-allocated (<= 48 live) per eval.
// usage: pal PUZZLES PROGRAMS IDSFILE OUT SEC THREADS SEED     (IDSFILE: one id per line, or "-" for all)
// env: MAXD3 (1: allow 3-instruction derivations), TOPK (candidate inserts per round), PLATEAU (prob % of accepting 0-moves)
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64; typedef __int128 i128;
static thread_local bool PENMODE_FAST = false; static bool FACTOR = false;

struct Puz { string id; u64 L; vector<u64> starts, targets; };
struct Ins { int op, a, b, d; };

static inline bool app(int op, u64 a, u64 b, u64 lim, u64 &c) {
    switch (op) {
    case 0: c = a + b; return c <= lim;
    case 1: if (a <= b) return false; c = a - b; return true;
    case 2: { i128 p = (i128)a * b; if (p > (i128)lim) return false; c = (u64)p; return true; }
    case 3: if (b == 0 || a % b) return false; c = a / b; return true;
    }
    return false;
}
static const char OPC[4] = {'+', '-', '*', '/'};

// ---- open addressing map u64 -> u32 ----
struct HMap {
    vector<u64> k; vector<uint32_t> v; vector<int> used; size_t mask = 0;
    void init(int bits) { k.assign((size_t)1 << bits, 0); v.assign((size_t)1 << bits, 0); mask = ((size_t)1 << bits) - 1; used.clear(); }
    static inline size_t h(u64 x) { x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33; x *= 0xc4ceb9fe1a85ec53ULL; x ^= x >> 33; return (size_t)x; }
    void clear() { for (int i : used) k[i] = 0; used.clear(); }
    inline bool insert(u64 key, uint32_t val) { // keep first
        size_t i = h(key) & mask;
        while (k[i]) { if (k[i] == key) return false; i = (i + 1) & mask; }
        if (used.size() * 2 > mask) return false; // full guard
        k[i] = key; v[i] = val; used.push_back((int)i); return true;
    }
    inline bool find(u64 key, uint32_t &val) const {
        size_t i = h(key) & mask;
        while (k[i]) { if (k[i] == key) { val = v[i]; return true; } i = (i + 1) & mask; }
        return false;
    }
};

// Derivation: up to 3 instructions; operand refs: >=0 S index, -1 temp0, -2 temp1
struct Der { int n = 0; int op[6], a[6], b[6]; };
// ---- 64-bit factorization (Miller-Rabin + Pollard-Brent) ----
static inline u64 mulm(u64 a, u64 b, u64 m) { return (u64)((unsigned __int128)a * b % m); }
static u64 powm(u64 a, u64 e, u64 m) { u64 r = 1; a %= m; while (e) { if (e & 1) r = mulm(r, a, m); a = mulm(a, a, m); e >>= 1; } return r; }
static bool isPrime(u64 n) {
    if (n < 2) return false; for (u64 p : {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}) { if (n % p == 0) return n == p; }
    u64 d = n - 1; int s = 0; while (!(d & 1)) { d >>= 1; s++; }
    for (u64 a : {2, 325, 9375, 28178, 450775, 9780504, 1795265022}) { if (a % n == 0) continue; u64 x = powm(a, d, n); if (x == 1 || x == n - 1) continue;
        bool ok = false; for (int r = 1; r < s; r++) { x = mulm(x, x, n); if (x == n - 1) { ok = true; break; } } if (!ok) return false; }
    return true;
}
static u64 rho(u64 n, u64 c) {
    if (n % 2 == 0) return 2;
    u64 x = 2, y = 2, d = 1, q = 1, ys = 0; int m = 64; u64 r = 1;
    auto f = [&](u64 v) { return (mulm(v, v, n) + c) % n; };
    do { x = y; for (u64 i = 0; i < r; i++) y = f(y); u64 k = 0;
        do { ys = y; for (int i = 0; i < m && i < (int)(r - k); i++) { y = f(y); q = mulm(q, x > y ? x - y : y - x, n); } d = std::gcd(q, n); k += m; } while (k < r && d == 1);
        r <<= 1; } while (d == 1 && r < (1u << 22));
    if (d == n) { do { ys = f(ys); d = std::gcd(x > ys ? x - ys : ys - x, n); } while (d == 1); }
    return d;
}
static void factorRec(u64 n, std::vector<u64> &out) {
    if (n == 1) return; if (isPrime(n)) { out.push_back(n); return; }
    for (u64 p : {2, 3, 5, 7, 11, 13}) if (n % p == 0) { out.push_back(p); factorRec(n / p, out); return; }
    u64 d = n; for (u64 c = 1; d == n || d == 1; c++) d = rho(n, c);
    factorRec(d, out); factorRec(n / d, out);
}
static void divisors(u64 n, std::vector<u64> &dv, size_t cap) {
    std::vector<u64> pf; factorRec(n, pf); std::sort(pf.begin(), pf.end());
    dv.assign(1, 1);
    for (size_t i = 0; i < pf.size();) { size_t j = i; while (j < pf.size() && pf[j] == pf[i]) j++; size_t sz = dv.size(); u64 pw = 1;
        for (size_t e = i; e < j; e++) { pw *= pf[i]; for (size_t t = 0; t < sz; t++) dv.push_back(dv[t] * pw); if (dv.size() > cap) return; } i = j; }
}
static inline uint32_t pk(int op, int i, int j) { return (uint32_t)op | ((uint32_t)i << 2) | ((uint32_t)j << 17); }
static inline void upk(uint32_t p, int &op, int &i, int &j) { op = p & 3; i = (p >> 2) & 32767; j = (p >> 17) & 32767; }

struct Ctx {
    const Puz *pz; u64 lim; int maxd;
    vector<u64> S; HMap sidx; HMap F1; vector<u64> F1keys;
    void reset(int bits) { sidx.init(12); F1.init(bits); }
    void add(u64 x) {
        int k = (int)S.size(); S.push_back(x); sidx.insert(x, (uint32_t)k);
        for (int s = 0; s <= k; s++) {
            u64 y = S[s], c;
            for (int op = 0; op < 4; op++) {
                if (app(op, x, y, lim, c)) { if (F1.insert(c, pk(op, k, s))) F1keys.push_back(c); }
                if (s != k && op != 0 && op != 2 && app(op, y, x, lim, c)) { if (F1.insert(c, pk(op, s, k))) F1keys.push_back(c); }
            }
        }
    }
    // inverse: v = z OP y (yfirst=false) or v = y OP z (yfirst=true); returns z
    static inline int inv(u64 v, u64 y, u64 lim, int f, u64 &z, int &op, bool &yfirst) {
        switch (f) {
        case 0: if (v <= y) return 0; z = v - y; op = 0; yfirst = false; return 1;          // v = z + y
        case 1: z = v + y; if (z > lim || z < v) return 0; op = 1; yfirst = false; return 1; // v = z - y
        case 2: if (y <= v) return 0; z = y - v; op = 1; yfirst = true; return 1;           // v = y - z
        case 3: if (v % y) return 0; z = v / y; op = 2; yfirst = false; return 1;           // v = z * y
        case 4: { i128 p = (i128)v * y; if (p > (i128)lim) return 0; z = (u64)p; op = 3; yfirst = false; return 1; } // v = z / y
        case 5: if (y % v) return 0; z = y / v; op = 3; yfirst = true; return 1;            // v = y / z
        }
        return 0;
    }
    // ---- depth 4/5 support: F2c = { t1 = t0 op y : t0 in F1, y in S[0..ns) } built lazily once per evaluation ----
    HMap F2; vector<u64> F2keys; struct F2E { uint32_t f1; int op, y; bool yf; }; vector<F2E> F2e; int f2built = -1;
    void buildF2() {
        if (F2.mask == 0) F2.init(23);
        F2.clear(); F2keys.clear(); F2e.clear();
        int ns = min((int)S.size(), F2CAP);
        for (u64 z : F1keys) {
            uint32_t p; F1.find(z, p); int op, i, j; upk(p, op, i, j); if (i >= ns || j >= ns) continue;
            for (int s = 0; s < ns; s++) {
                u64 y = S[s], c;
                for (int o = 0; o < 4; o++) {
                    if (app(o, z, y, lim, c) && F2.insert(c, (uint32_t)F2e.size())) { F2e.push_back({p, o, s, false}); F2keys.push_back(c); }
                    if ((o == 1 || o == 3) && app(o, y, z, lim, c) && F2.insert(c, (uint32_t)F2e.size())) { F2e.push_back({p, o, s, true}); F2keys.push_back(c); }
                }
            }
            if (F2e.size() > 3500000) break;
        }
        f2built = ns;
    }
    int F2CAP = 40;
    // put F2 entry e as instructions q, q+1 of D (temps -(q+1), -(q+2))
    void putF2(Der &D, int q, const F2E &e) {
        int op, i, j; upk(e.f1, op, i, j); D.op[q] = op; D.a[q] = i; D.b[q] = j;
        D.op[q + 1] = e.op; if (e.yf) { D.a[q + 1] = e.y; D.b[q + 1] = -(q + 1); } else { D.a[q + 1] = -(q + 1); D.b[q + 1] = e.y; }
    }
    // value cost class for factor splits: 0 = kept (S), 1 = F1, 2 = F2c, 9 = none
    inline int vclass(u64 x, uint32_t &p) { if (sidx.find(x, p)) return 0; if (F1.find(x, p)) return 1; if (f2built >= 0 && F2.find(x, p)) return 2; return 9; }
    // emit value of class c (packed p) as instructions starting at q; returns ref to its result
    int putV(Der &D, int &q, int c, uint32_t p) {
        if (c == 0) return (int)p;
        if (c == 1) { int op, i, j; upk(p, op, i, j); D.op[q] = op; D.a[q] = i; D.b[q] = j; q++; return -q; }
        putF2(D, q, F2e[p]); q += 2; return -q;
    }
    // v = a*b (+/-) r, r in S or 0, a,b in S/F1/F2c; depth <= lim
    int factorSplit(u64 v, Der &D, int lim2) {
        int n = (int)S.size(); int bestd = 99; vector<u64> dv; dv.reserve(4096);
        int bs = -2, bfr = 0; u64 ba = 0, bb = 0; int bca = 0, bcb = 0; uint32_t bpa = 0, bpb = 0;
        for (int s = -1; s < n; s++) {
            for (int sg = 0; sg < (s < 0 ? 1 : 2); sg++) {
                u64 w;
                if (s < 0) w = v; else { u64 r = S[s]; if (sg == 0) { if (r >= v) continue; w = v - r; } else { w = v + r; if (w > lim || w < v) continue; } }
                if (w < 4) continue;
                int extra = s < 0 ? 0 : 1;
                if (extra + 1 + 0 >= bestd) continue;
                divisors(w, dv, 4000);
                for (u64 a : dv) {
                    if (a < 2 || a * a > w) continue;
                    u64 b = w / a; uint32_t pa, pb;
                    int ca = vclass(a, pa); if (ca == 9) continue; int cb = vclass(b, pb); if (cb == 9) continue;
                    int d = ca + cb + 1 + extra;
                    if (d < bestd && d <= lim2) { bestd = d; bs = s; bfr = sg; ba = a; bb = b; bca = ca; bcb = cb; bpa = pa; bpb = pb; }
                }
            }
        }
        if (bestd > lim2) return 99;
        int q = 0; int ra = putV(D, q, bca, bpa); int rb = putV(D, q, bcb, bpb);
        D.op[q] = 2; D.a[q] = ra; D.b[q] = rb; q++;
        if (bs >= 0) { D.op[q] = bfr == 0 ? 0 : 1; D.a[q] = -q; D.b[q] = bs; q++; }
        D.n = q; return q;
    }
    int deep(u64 v, Der &D) {
        if (maxd < 4) return 99;
        if (f2built < 0) buildF2();
        Der DF; int fd = 99; if (FACTOR) { fd = factorSplit(v, DF, PENMODE_FAST ? 4 : min(maxd, 6)); if (fd <= 4) { D = DF; return fd; } }
        uint32_t p, p2; int n = (int)S.size();
        // d4b: v = t1 OP t2, t1 in F2c, t2 in F1
        for (u64 z1 : F1keys) for (int f = 0; f < 6; f++) {
            u64 w; int o; bool yf; if (!inv(v, z1, lim, f, w, o, yf)) continue;
            if (F2.find(w, p2)) {
                putF2(D, 0, F2e[p2]); F1.find(z1, p); int op, i, j; upk(p, op, i, j); D.op[2] = op; D.a[2] = i; D.b[2] = j;
                D.op[3] = o; if (yf) { D.a[3] = -3; D.b[3] = -2; } else { D.a[3] = -2; D.b[3] = -3; } D.n = 4; return 4;
            }
        }
        // d4c: v = (t1 OP y) OP y2, t1 in F2c
        for (int s2 = 0; s2 < n; s2++) for (int f2 = 0; f2 < 6; f2++) {
            u64 w; int o2; bool yf2; if (!inv(v, S[s2], lim, f2, w, o2, yf2)) continue;
            for (int s = 0; s < n; s++) for (int f = 0; f < 6; f++) {
                u64 w2; int o; bool yf; if (!inv(w, S[s], lim, f, w2, o, yf)) continue;
                if (F2.find(w2, p2)) {
                    putF2(D, 0, F2e[p2]);
                    D.op[2] = o; if (yf) { D.a[2] = s; D.b[2] = -2; } else { D.a[2] = -2; D.b[2] = s; }
                    D.op[3] = o2; if (yf2) { D.a[3] = s2; D.b[3] = -3; } else { D.a[3] = -3; D.b[3] = s2; }
                    D.n = 4; return 4;
                }
            }
        }
        if (fd == 5) { D = DF; return 5; }
        if (maxd < 5 || PENMODE_FAST) return 99;
        // d5: v = A OP B, A, B in F2c
        for (size_t q = 0; q < F2keys.size(); q++) {
            u64 a = F2keys[q];
            for (int f = 0; f < 6; f++) {
                u64 w; int o; bool yf; if (!inv(v, a, lim, f, w, o, yf)) continue;
                if (F2.find(w, p2)) {
                    putF2(D, 0, F2e[q]); putF2(D, 2, F2e[p2]);
                    D.op[4] = o; if (yf) { D.a[4] = -2; D.b[4] = -4; } else { D.a[4] = -4; D.b[4] = -2; } D.n = 5; return 5;
                }
            }
        }
        if (fd == 6) { D = DF; return 6; }
        return 99;
    }
    int dist(u64 v, Der &D) {
        uint32_t p; int op, i, j;
        if (F1.find(v, p)) { upk(p, op, i, j); D.n = 1; D.op[0] = op; D.a[0] = i; D.b[0] = j; return 1; }
        int n = (int)S.size();
        // d2: v = t0 OP y, t0 in F1
        for (int s = 0; s < n; s++) {
            u64 y = S[s];
            for (int f = 0; f < 6; f++) {
                u64 z; int o; bool yf;
                if (!inv(v, y, lim, f, z, o, yf)) continue;
                if (F1.find(z, p)) {
                    upk(p, op, i, j); D.n = 2; D.op[0] = op; D.a[0] = i; D.b[0] = j;
                    D.op[1] = o; if (yf) { D.a[1] = s; D.b[1] = -1; } else { D.a[1] = -1; D.b[1] = s; }
                    return 2;
                }
            }
        }
        // d2: v = t0+t0 or t0*t0
        if (v % 2 == 0 && F1.find(v / 2, p)) { upk(p, op, i, j); D.n = 2; D.op[0] = op; D.a[0] = i; D.b[0] = j; D.op[1] = 0; D.a[1] = -1; D.b[1] = -1; return 2; }
        { u64 r = (u64)sqrtl((long double)v); while (r * r > v) r--; while ((r + 1) * (r + 1) <= v) r++;
          if (r * r == v && F1.find(r, p)) { upk(p, op, i, j); D.n = 2; D.op[0] = op; D.a[0] = i; D.b[0] = j; D.op[1] = 2; D.a[1] = -1; D.b[1] = -1; return 2; } }
        if (maxd < 3) return 99;
        // d3a: v = t0 OP t1, both in F1
        for (u64 z1 : F1keys) {
            for (int f = 0; f < 6; f++) {
                u64 z2; int o; bool yf;
                if (!inv(v, z1, lim, f, z2, o, yf)) continue;
                uint32_t p2;
                if (F1.find(z2, p2)) {
                    F1.find(z1, p);
                    upk(p, op, i, j); D.op[0] = op; D.a[0] = i; D.b[0] = j;
                    upk(p2, op, i, j); D.op[1] = op; D.a[1] = i; D.b[1] = j;
                    D.n = 3; D.op[2] = o; if (yf) { D.a[2] = -1; D.b[2] = -2; } else { D.a[2] = -2; D.b[2] = -1; }
                    return 3;
                }
            }
        }
        // d3b: v = t1 OP y', t1 = t0 OP y, t0 in F1
        for (int s2 = 0; s2 < n; s2++) {
            u64 y2 = S[s2];
            for (int f2 = 0; f2 < 6; f2++) {
                u64 w; int o2; bool yf2;
                if (!inv(v, y2, lim, f2, w, o2, yf2)) continue;
                for (int s = 0; s < n; s++) {
                    u64 y = S[s];
                    for (int f = 0; f < 6; f++) {
                        u64 z; int o; bool yf;
                        if (!inv(w, y, lim, f, z, o, yf)) continue;
                        if (F1.find(z, p)) {
                            upk(p, op, i, j); D.op[0] = op; D.a[0] = i; D.b[0] = j;
                            D.op[1] = o; if (yf) { D.a[1] = s; D.b[1] = -1; } else { D.a[1] = -1; D.b[1] = s; }
                            D.op[2] = o2; if (yf2) { D.a[2] = s2; D.b[2] = -2; } else { D.a[2] = -2; D.b[2] = s2; }
                            D.n = 3; return 3;
                        }
                    }
                }
            }
        }
        return deep(v, D);
    }
};

struct Item { u64 v; bool target; };
static map<string, unordered_set<u64>> KEEPS; static map<string, vector<u64>> ITEMS; static bool INJECT = false;
struct EvalOut { int cost = 1 << 30; int pen = 0; vector<Ins> prog; vector<int> dcost; vector<int> spos; };
static thread_local bool PENMODE = false; static const int PEN = 8;

// emit + register allocation. vals: value ids. returns false if > 48 live.
static bool emit(const Puz &pz, const vector<array<int, 4>> &ins, int nvals, int nstart, vector<Ins> &out) {
    // ins: op, srcA id, srcB id, dst id
    int m = (int)ins.size();
    vector<int> last(nvals, -1);
    for (int k = 0; k < m; k++) { last[ins[k][1]] = k; last[ins[k][2]] = k; }
    vector<int> reg(nvals, -1); vector<int> owner(48, -1);
    for (int s = 0; s < nstart; s++) { reg[s] = s; owner[s] = s; }
    for (int s = 0; s < nstart; s++) if (last[s] < 0) { owner[s] = -1; }
    out.clear(); out.reserve(m);
    for (int k = 0; k < m; k++) {
        int a = ins[k][1], b = ins[k][2], d = ins[k][3];
        int ra = reg[a], rb = reg[b];
        if (ra < 0 || rb < 0) return false;
        if (last[a] == k) owner[ra] = -1;
        if (last[b] == k) owner[rb] = -1;
        int rd = -1;
        for (int r = 0; r < 48; r++) if (owner[r] < 0) { rd = r; break; }
        if (rd < 0) return false;
        // values never read later still occupy until overwritten; mark free immediately
        owner[rd] = (last[d] > k) ? d : -1;
        reg[d] = rd;
        out.push_back({ins[k][0], ra, rb, rd});
    }
    return true;
}

static EvalOut evaluate(const Puz &pz, const vector<Item> &L, int maxd, Ctx &C) {
    EvalOut E;
    C.S.clear(); C.F1keys.clear(); C.F1.clear(); C.sidx.clear(); C.pz = &pz; C.lim = pz.L; C.maxd = maxd; C.f2built = -1;
    for (u64 s : pz.starts) { uint32_t dummy; if (!C.sidx.find(s, dummy)) C.add(s); else C.S.push_back(s); } // keep index alignment
    int nstart = (int)pz.starts.size();
    // value ids: S index for kept values; temps get ids after. We map S index -> id = S index (S grows), temps -> 100000+
    vector<array<int, 4>> ins; ins.reserve(L.size() * 2);
    vector<int> tempIdBase; int ntemp = 0;
    E.dcost.assign(L.size(), 0); E.spos.assign(L.size(), 0);
    int cost = 0, npen = 0;
    vector<pair<int, Der>> ders; ders.reserve(L.size());
    for (size_t t = 0; t < L.size(); t++) {
        u64 v = L[t].v; uint32_t tmp;
        E.spos[t] = (int)C.S.size();
        if (C.sidx.find(v, tmp)) { E.dcost[t] = 0; continue; }
        Der D; int d = C.dist(v, D);
        if (d > 6) {
            if (!PENMODE) { E.cost = 1 << 30; return E; }
            E.dcost[t] = PEN; cost += PEN; npen++; C.add(v); continue; // pretend it exists; fixed later by helpers
        }
        E.dcost[t] = d; cost += d;
        ders.push_back({(int)C.S.size(), D});
        C.add(v);
    }
    if (npen) { E.cost = cost; E.pen = npen; return E; }
    // build id-level instruction list. kept value with S index k has id k. temps: id = NS + counter
    int NS = (int)C.S.size();
    for (auto &pr : ders) {
        int sidx = pr.first; const Der &D = pr.second;
        int tid[5] = {-1, -1, -1, -1, -1};
        for (int q = 0; q < D.n; q++) {
            auto ref = [&](int r) { return r >= 0 ? r : tid[-r - 1]; };
            int a = ref(D.a[q]), b = ref(D.b[q]);
            int dst;
            if (q == D.n - 1) dst = sidx; else { dst = NS + ntemp++; tid[q] = dst; }
            // for d3a, temps are t0 (q=0) and t1 (q=1); for d3b t0 (q=0), t1 (q=1): refs -1 -> tid[0], -2 -> tid[1]
            ins.push_back({D.op[q], a, b, dst});
        }
    }
    vector<Ins> prog;
    if (!emit(pz, ins, NS + ntemp, nstart, prog)) { E.cost = (1 << 29) + cost; return E; }
    E.cost = cost; E.prog = move(prog);
    return E;
}

static bool replayOK(const Puz &pz, const vector<Ins> &prog) {
    vector<u64> R(48, 0); vector<char> def(48, 0);
    for (size_t k = 0; k < pz.starts.size(); k++) { R[k] = pz.starts[k]; def[k] = 1; }
    unordered_set<u64> need(pz.targets.begin(), pz.targets.end());
    for (u64 s : pz.starts) need.erase(s);
    for (auto &I : prog) {
        if (!def[I.a] || !def[I.b]) return false;
        u64 c; if (!app(I.op, R[I.a], R[I.b], pz.L, c) || c < 1) return false;
        R[I.d] = c; def[I.d] = 1; need.erase(c);
    }
    return need.empty();
}

static vector<Item> fromProgram(const Puz &pz, const vector<Ins> &prog) {
    vector<u64> R(48, 0);
    for (size_t k = 0; k < pz.starts.size(); k++) R[k] = pz.starts[k];
    unordered_set<u64> T(pz.targets.begin(), pz.targets.end()), seen(pz.starts.begin(), pz.starts.end());
    vector<Item> L;
    for (auto &I : prog) {
        u64 c; app(I.op, R[I.a], R[I.b], pz.L, c); R[I.d] = c;
        if (seen.count(c)) continue; seen.insert(c);
        L.push_back({c, (bool)T.count(c)});
    }
    return L;
}

int main(int argc, char **argv) {
    if (argc < 8) { fprintf(stderr, "usage: pal PUZZLES PROGRAMS IDS OUT SEC THREADS SEED\n"); return 1; }
    double SEC = atof(argv[5]); int TH = atoi(argv[6]); unsigned SEED = atoi(argv[7]);
    int MAXD = getenv("MAXD") ? atoi(getenv("MAXD")) : 3;
    int TOPK = getenv("TOPK") ? atoi(getenv("TOPK")) : 40;
    int PLATEAU = getenv("PLATEAU") ? atoi(getenv("PLATEAU")) : 30;
    map<string, Puz> P; map<string, vector<Ins>> G;
    { ifstream f(argv[1]); string line;
      while (getline(f, line)) { istringstream ss(line); Puz p; int ns, nt; ss >> p.id >> p.L >> ns >> nt; p.starts.resize(ns); p.targets.resize(nt);
        for (auto &x : p.starts) ss >> x; for (auto &x : p.targets) ss >> x; P[p.id] = p; } }
    { ifstream f(argv[2]); string line;
      while (getline(f, line)) { istringstream ss(line); string id; int n; ss >> id >> n; vector<Ins> v(n);
        for (auto &I : v) { string o; ss >> o >> I.a >> I.b >> I.d; I.op = string("+-*/").find(o[0]); } G[id] = v; } }
    vector<string> ids;
    if (string(argv[3]) == "-") { for (auto &kv : G) ids.push_back(kv.first); }
    else { ifstream f(argv[3]); string s; while (f >> s) if (G.count(s)) ids.push_back(s); }
    if (getenv("KEEP")) { ifstream f(getenv("KEEP")); string line;
        while (getline(f, line)) { istringstream ss(line); string id; ss >> id; u64 v; while (ss >> v) KEEPS[id].insert(v); } }
    INJECT = getenv("INJECT") != nullptr; FACTOR = getenv("FACTOR") != nullptr;
    if (getenv("ITEMS")) { ifstream f(getenv("ITEMS")); string line;
        while (getline(f, line)) { istringstream ss(line); string id; ss >> id; u64 v; while (ss >> v) ITEMS[id].push_back(v); } }
    mutex mu; atomic<int> next(0); map<string, vector<Ins>> best = G; int totalGain = 0;
    auto dump = [&]() {
        ofstream o(string(argv[4]) + ".tmp");
        for (auto &id : ids) { auto &v = best[id]; o << id << " " << v.size(); for (auto &I : v) o << " " << OPC[I.op] << " " << I.a << " " << I.b << " " << I.d; o << "\n"; }
        o.close(); remove(argv[4]); rename((string(argv[4]) + ".tmp").c_str(), argv[4]);
    };
    auto worker = [&](int tid) {
        mt19937_64 rng(SEED * 1000003ULL + tid);
        Ctx C; C.reset(20);
        while (true) {
            int k = next++; if (k >= (int)ids.size()) break;
            const string id = ids[k]; const Puz &pz = P[id]; const vector<Ins> &g = G[id];
            auto t0 = chrono::steady_clock::now();
            auto el = [&]() { return chrono::duration<double>(chrono::steady_clock::now() - t0).count(); };
            vector<Item> L = fromProgram(pz, g);
            int base = (int)g.size();
            if (INJECT && ITEMS.count(id)) { // frontier values + injected helpers placed just before the first target
                unordered_set<u64> have; for (auto &it : L) have.insert(it.v);
                for (u64 s : pz.starts) have.insert(s);
                size_t ft = 0; while (ft < L.size() && !L[ft].target) ft++;
                vector<Item> ins; for (u64 v : ITEMS[id]) if (!have.count(v)) { have.insert(v); ins.push_back({v, false}); }
                L.insert(L.begin() + ft, ins.begin(), ins.end());
            } else if (ITEMS.count(id)) { // explicit start: given ordered helper values, then all targets ascending
                unordered_set<u64> T(pz.targets.begin(), pz.targets.end()), seen(pz.starts.begin(), pz.starts.end());
                L.clear();
                for (u64 v : ITEMS[id]) if (!seen.count(v)) { seen.insert(v); L.push_back({v, (bool)T.count(v)}); }
                vector<u64> ts(pz.targets.begin(), pz.targets.end()); sort(ts.begin(), ts.end());
                for (u64 v : ts) if (!seen.count(v)) { seen.insert(v); L.push_back({v, true}); }
            }
            if (KEEPS.count(id)) { // reduced start: keep only listed values (+targets), repair to feasibility
                const auto &ks = KEEPS[id]; vector<Item> L2;
                for (auto &it : L) if (it.target || ks.count(it.v)) L2.push_back(it);
                L = L2;
            }
            auto candList = [&](const vector<Item> &LL, const EvalOut &EE, int K) {
                // requires C.S filled by the evaluation that produced EE
                unordered_map<u64, pair<int, int>> cand;
                auto addc = [&](u64 z, int w, int t) { if (z < 1 || z > pz.L) return; auto it = cand.find(z);
                    if (it == cand.end()) cand[z] = {w, t}; else { it->second.first += w; it->second.second = min(it->second.second, t); } };
                for (size_t t = 0; t < LL.size(); t++) {
                    int d = EE.dcost[t]; if (d < 2) continue;
                    u64 v = LL[t].v; int n = EE.spos[t];
                    if (d >= 4 && v < (1ULL << 34)) { // deep item (e.g. an atom): factor candidates v = q*w + c
                        for (int c = -40; c <= 40; c++) {
                            i128 w = (i128)v - c; if (w < 4) continue; u64 ww = (u64)w;
                            for (u64 q = 2; q <= 2048 && q * q <= ww; q++) if (ww % q == 0) { addc(q, d - 1, (int)t); addc(ww / q, d - 1, (int)t); }
                            if (c != 0) addc((u64)(c < 0 ? -c : c), 1, (int)t);
                        }
                    }
                    for (int s = 0; s < n; s++) {
                        u64 y = C.S[s];
                        for (int f = 0; f < 6; f++) { u64 z; int o; bool yf; if (!Ctx::inv(v, y, pz.L, f, z, o, yf)) continue; addc(z, d - 1, (int)t); }
                        // structured candidates: v = k*y + c with y a big kept value: offer k and |c|
                        if (y >= (1u << 12) && y < v) {
                            u64 q = v / y;
                            for (u64 kk = (q > 1 ? q - 0 : 1); kk <= q + 1; kk++) {
                                i128 c = (i128)v - (i128)kk * y; i128 ac = c < 0 ? -c : c;
                                if (ac < (1 << 16) && ac > 0) addc((u64)ac, 3 * (d - 1), (int)t);
                                if (kk > 1 && kk < (1u << 24) && ac < (1 << 16)) addc(kk, 3 * (d - 1), (int)t);
                            }
                        }
                    }
                }
                vector<pair<int, u64>> cl; cl.reserve(cand.size()); for (auto &kv : cand) cl.push_back({kv.second.first, kv.first});
                int k = min<int>(K, (int)cl.size());
                partial_sort(cl.begin(), cl.begin() + k, cl.end(), [](auto &a, auto &b) { return a.first > b.first; });
                vector<pair<u64, int>> out; for (int q = 0; q < k; q++) out.push_back({cl[q].second, cand[cl[q].second].second});
                return out;
            };
            int RK = getenv("RK") ? atoi(getenv("RK")) : 15, KMAXR = getenv("KMAXR") ? atoi(getenv("KMAXR")) : 8;
            int evals = 1, moves = 0, regBetter = 0;
            PENMODE = true;
            EvalOut cur = evaluate(pz, L, MAXD, C);
            int repairs = 0; PENMODE_FAST = true;
            while (cur.pen > 0 && el() < SEC) { // greedy repair: insert the helper that lowers (cost + penalties) most
                auto cands = candList(L, cur, RK * 6);
                int bc = cur.cost; vector<Item> bL;
                for (auto &cd : cands) {
                    vector<Item> L3 = L; L3.insert(L3.begin() + min<int>(cd.second, (int)L3.size()), Item{cd.first, false});
                    EvalOut e3 = evaluate(pz, L3, MAXD, C); evals++;
                    if (e3.cost < bc) { bc = e3.cost; bL = L3; }
                }
                if (bL.empty()) break;
                L = bL; cur = evaluate(pz, L, MAXD, C); evals++; repairs++;
            }
            if (getenv("DEBUG") && cur.pen) { lock_guard<mutex> lk(mu); fprintf(stderr, "%s unresolved:", id.c_str());
                for (size_t t = 0; t < L.size(); t++) if (cur.dcost[t] == PEN) fprintf(stderr, " %llu%s@%d", (unsigned long long)L[t].v, L[t].target ? "T" : "", cur.spos[t]);
                fprintf(stderr, "\n"); }
            PENMODE = false; PENMODE_FAST = false;
            cur = evaluate(pz, L, MAXD, C);
            int start = cur.cost;
            if (cur.cost >= (1 << 29)) { lock_guard<mutex> lk(mu); fprintf(stderr, "%s base %d: initial eval failed (%d) after %d repairs\n", id.c_str(), base, cur.cost, repairs); continue; }
            if (repairs) { lock_guard<mutex> lk(mu); fprintf(stderr, "%s repaired with %d inserts -> %d (base %d) %.0fs\n", id.c_str(), repairs, cur.cost, base, el()); }
            vector<Item> bestL = L; EvalOut bestE = cur;
            double T0 = getenv("T0") ? atof(getenv("T0")) : 0.6;
            bool needC = true; vector<pair<u64, int>> cl2;
            int lnsIt = 0, lnsAcc = 0;
            while (getenv("LNS") && el() < SEC) {
                lnsIt++;
                vector<Item> L2 = L;
                vector<int> nonT; for (size_t t = 0; t < L2.size(); t++) if (!L2[t].target) nonT.push_back((int)t);
                if (nonT.empty()) break;
                int k = 1 + (int)(rng() % KMAXR);
                // ruin: either random helpers or a contiguous window of helpers
                vector<int> kill;
                if (rng() % 2) { shuffle(nonT.begin(), nonT.end(), rng); for (int q = 0; q < k && q < (int)nonT.size(); q++) kill.push_back(nonT[q]); }
                else { int st = (int)(rng() % nonT.size()); for (int q = 0; q < k && st + q < (int)nonT.size(); q++) kill.push_back(nonT[st + q]); }
                sort(kill.rbegin(), kill.rend());
                for (int x : kill) L2.erase(L2.begin() + x);
                PENMODE = true;
                EvalOut e = evaluate(pz, L2, MAXD, C); evals++;
                for (int rep = 0; rep < 3 * KMAXR + 4 && el() < SEC; rep++) {
                    auto cands = candList(L2, e, RK);
                    int bestc = e.cost; vector<Item> bestL2; EvalOut bestE2;
                    for (auto &cd : cands) {
                        vector<Item> L3 = L2; int pos = min<int>(cd.second, (int)L3.size());
                        L3.insert(L3.begin() + pos, Item{cd.first, false});
                        EvalOut e3 = evaluate(pz, L3, MAXD, C); evals++;
                        if (e3.cost < bestc) { bestc = e3.cost; bestL2 = L3; bestE2 = e3; }
                    }
                    if (bestL2.empty()) break;
                    L2 = bestL2; e = evaluate(pz, L2, MAXD, C); evals++; // refill C.S for next candList
                }
                PENMODE = false;
                if (e.pen) continue;
                EvalOut ef = evaluate(pz, L2, MAXD, C); evals++;
                if (ef.cost >= (1 << 29)) { if (ef.cost < (1 << 30) && ef.cost - (1 << 29) < cur.cost) regBetter++; continue; }
                if (ef.cost < cur.cost || (ef.cost == cur.cost && rng() % 2)) {
                    if (ef.cost < cur.cost) lnsAcc++;
                    L = L2; cur = ef; moves++;
                    if (cur.cost < bestE.cost) { bestE = cur; bestL = L; }
                }
            }
            if (getenv("LNS") && getenv("DEBUG")) fprintf(stderr, "  lns iters %d improving %d\n", lnsIt, lnsAcc);
            while (getenv("SA") && el() < SEC) {
                if (needC) {
                    unordered_map<u64, pair<int, int>> cand;
                    EvalOut tmp = evaluate(pz, L, MAXD, C); evals++;
                    for (size_t t = 0; t < L.size(); t++) {
                        int d = tmp.dcost[t]; if (d < 2) continue;
                        u64 v = L[t].v; int n = tmp.spos[t];
                        for (int s = 0; s < n; s++) {
                            u64 y = C.S[s];
                            for (int f = 0; f < 6; f++) { u64 z; int o; bool yf; if (!Ctx::inv(v, y, pz.L, f, z, o, yf)) continue;
                                auto it = cand.find(z);
                                if (it == cand.end()) cand[z] = {d - 1, (int)t}; else { it->second.first += d - 1; it->second.second = min(it->second.second, (int)t); } }
                        }
                    }
                    vector<pair<int, u64>> cl; for (auto &kv : cand) cl.push_back({kv.second.first, kv.first});
                    sort(cl.rbegin(), cl.rend());
                    cl2.clear(); for (int q = 0; q < (int)cl.size() && q < TOPK; q++) cl2.push_back({cl[q].second, cand[cl[q].second].second});
                    needC = false;
                }
                double T = T0 * (1.0 - el() / SEC) + 0.02;
                vector<Item> L2 = L;
                vector<int> nonT; for (size_t t = 0; t < L2.size(); t++) if (!L2[t].target) nonT.push_back((int)t);
                int r = (int)(rng() % 100);
                bool doRem = r < 45 || (r >= 90), doIns = r >= 45;
                if (doRem && !nonT.empty()) L2.erase(L2.begin() + nonT[rng() % nonT.size()]);
                if (doIns && !cl2.empty()) {
                    int q = (int)(rng() % cl2.size()); if (rng() % 2) q = (int)(rng() % min<size_t>(cl2.size(), 8));
                    int pos = min<int>(cl2[q].second, (int)L2.size());
                    L2.insert(L2.begin() + pos, Item{cl2[q].first, false});
                }
                EvalOut e = evaluate(pz, L2, MAXD, C); evals++;
                if (e.cost >= (1 << 29)) { if (e.cost < (1 << 30) && e.cost - (1 << 29) < cur.cost) regBetter++; continue; }
                int dlt = e.cost - cur.cost;
                if (dlt <= 0 || (double)(rng() % 1000000) / 1e6 < exp(-dlt / T)) {
                    L = L2; cur = e; moves++; needC = true;
                    if (cur.cost < bestE.cost) { bestE = cur; bestL = L; }
                }
            }
            while (!getenv("SA") && el() < SEC) {
                // candidate inserts from items costing >= 2
                unordered_map<u64, pair<int, int>> cand; // m -> (score, earliest position)
                // need S of current eval: re-evaluate to fill C.S (evaluate leaves C.S = full S of cur)
                EvalOut tmp = evaluate(pz, L, MAXD, C); evals++;
                for (size_t t = 0; t < L.size(); t++) {
                    int d = tmp.dcost[t]; if (d < 2) continue;
                    u64 v = L[t].v; int n = tmp.spos[t];
                    for (int s = 0; s < n; s++) {
                        u64 y = C.S[s];
                        for (int f = 0; f < 6; f++) { u64 z; int o; bool yf; if (!Ctx::inv(v, y, pz.L, f, z, o, yf)) continue;
                            auto it = cand.find(z);
                            if (it == cand.end()) cand[z] = {d - 1, (int)t}; else { it->second.first += d - 1; it->second.second = min(it->second.second, (int)t); } }
                    }
                }
                vector<pair<int, u64>> cl; for (auto &kv : cand) cl.push_back({kv.second.first, kv.first});
                sort(cl.rbegin(), cl.rend());
                // build move list: removals (non-target items) + top inserts
                struct Mv { int type; int pos; u64 m; };
                vector<Mv> mv;
                for (size_t t = 0; t < L.size(); t++) if (!L[t].target) mv.push_back({0, (int)t, 0});
                for (int q = 0; q < (int)cl.size() && q < TOPK; q++) mv.push_back({1, cand[cl[q].second].second, cl[q].second});
                shuffle(mv.begin(), mv.end(), rng);
                bool improved = false; int zeroMoves = 0;
                for (auto &M : mv) {
                    if (el() >= SEC) break;
                    vector<Item> L2 = L;
                    if (M.type == 0) L2.erase(L2.begin() + M.pos);
                    else {
                        // insert m before first beneficiary; try that position, if infeasible try earlier spots
                        L2.insert(L2.begin() + M.pos, Item{M.m, false});
                    }
                    EvalOut e = evaluate(pz, L2, MAXD, C); evals++;
                    if (e.cost < cur.cost) { L = L2; cur = e; improved = true; moves++; break; }
                    if (e.cost == cur.cost && (int)(rng() % 100) < PLATEAU) { L = L2; cur = e; zeroMoves++; moves++; break; }
                }
                if (cur.cost < bestE.cost) { bestE = cur; bestL = L; }
                if (!improved && zeroMoves == 0) break; // local optimum, nothing accepted
            }
            if (getenv("ALTOUT") && bestE.cost < (1 << 29) && replayOK(pz, bestE.prog)) { // keep every constructed program as a recombination variant
                lock_guard<mutex> lk(mu); ofstream ao(getenv("ALTOUT"), ios::app);
                ao << id << " " << bestE.prog.size(); for (auto &I : bestE.prog) ao << " " << OPC[I.op] << " " << I.a << " " << I.b << " " << I.d; ao << "\n";
            }
            int gain = 0;
            if (getenv("DEBUG")) {
                int nt = 0; for (auto &it : bestL) nt += it.target;
                fprintf(stderr, "  dbg items %zu targets %d progsize %zu replay %d\n", bestL.size(), nt, bestE.prog.size(), (int)replayOK(pz, bestE.prog));
            }
            if (bestE.cost < base && replayOK(pz, bestE.prog)) {
                gain = base - bestE.cost;
                lock_guard<mutex> lk(mu); best[id] = bestE.prog; totalGain += gain;
            }
            { lock_guard<mutex> lk(mu);
              fprintf(stderr, "%s base %d init %d best %d gain %d evals %d moves %d regBetter %d %.0fs\n", id.c_str(), base, start, bestE.cost, gain, evals, moves, regBetter, el());
              if (k % 10 == 9) dump(); }
        }
    };
    vector<thread> th; for (int t = 0; t < TH; t++) th.emplace_back(worker, t);
    for (auto &t : th) t.join();
    dump();
    fprintf(stderr, "total gain %d\n", totalGain);
}
