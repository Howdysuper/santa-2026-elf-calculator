// Elf Calculator: cumulative-benefit planner with beam search (after Hcub, Voronenko & Pueschel 2007).
// Keeps a given scaffold (prefix recipes), then builds the remaining targets. A target one step away is built at once; otherwise
// each beam state is expanded by its K best one-step values, scored by the total reduction of the targets' remaining costs.
// Children are ranked by instructions so far + sum of remaining costs; the best W distinct states survive.
// input : stdin lines  "id L ns nt starts... targets... | n c op a b ... [cap]"   (scaffold recipes as values)
// output: stdout lines "id n c op a b ..."  (prefix + plan, in build order)
// env   : HSEC seconds per puzzle (10), W beam width (1 = greedy), K expansions per state (4), NOISE (0.3), FAR (4), SEED, DEBUG
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64; typedef unsigned __int128 u128;

static u64 L;
static inline bool ap(char op, u64 x, u64 y, u64 &z) {
    switch (op) {
        case '+': z = x + y; return z >= x && z <= L;
        case '-': if (x <= y) return false; z = x - y; return true;
        case '*': { u128 p = (u128)x * y; if (p > L) return false; z = (u64)p; return true; }
        case '/': if (!y || x % y) return false; z = x / y; return z >= 1;
    }
    return false;
}
static inline int inv(u64 t, u64 p, u64 *ys) {          // all y with  y op p = t  or  p op y = t
    int n = 0;
    if (t > p) ys[n++] = t - p;
    if (t <= L - p) ys[n++] = t + p;
    if (p > t) ys[n++] = p - t;
    if (t % p == 0) ys[n++] = t / p;
    { u128 q = (u128)t * p; if (q <= L) ys[n++] = (u64)q; }
    if (p % t == 0) ys[n++] = p / t;
    return n;
}
// open-addressing map u64 -> int (value 0 never used as a key; values are >= 1)
struct OA {
    vector<u64> k; vector<int> v; u64 mask = 0; size_t n = 0;
    void init(size_t cap) { size_t s = 64; while (s < 2 * cap) s <<= 1; k.assign(s, 0); v.assign(s, -1); mask = s - 1; n = 0; }
    static inline u64 h(u64 x) { x ^= x >> 31; x *= 0x9E3779B97F4A7C15ULL; x ^= x >> 29; return x; }
    inline bool put(u64 key, int val) {                   // keeps the first value
        if (2 * (n + 1) > k.size()) grow();
        u64 i = h(key) & mask;
        while (k[i]) { if (k[i] == key) return false; i = (i + 1) & mask; }
        k[i] = key; v[i] = val; n++; return true;
    }
    inline int get(u64 key) const { u64 i = h(key) & mask; while (k[i]) { if (k[i] == key) return v[i]; i = (i + 1) & mask; } return -1; }
    void grow() { vector<u64> ok = k; vector<int> ov = v; init(ok.size()); for (size_t i = 0; i < ok.size(); i++) if (ok[i]) put(ok[i], ov[i]); }
};
struct Rec { u64 c, a, b; char op; };
struct State { vector<Rec> recs; vector<u64> V, R; double est = 0; u64 sig = 0; };

static double FAR = 4, NOISE = 0.3;
static int K = 4;

struct Ctx {                                           // per-state derived data
    OA inV, D1; vector<Rec> d1r; vector<u64> X;
    void build(const State &s) {
        inV.init(s.V.size() + 8); for (size_t i = 0; i < s.V.size(); i++) inV.put(s.V[i], (int)i);
        D1.init(4 * s.V.size() * s.V.size() + 64); d1r.clear();
        for (size_t i = 0; i < s.V.size(); i++) for (size_t j = 0; j < s.V.size(); j++) {
            u64 a = s.V[i], b = s.V[j], z;
            for (char op : {'+', '*', '-', '/'}) {
                if ((op == '+' || op == '*') && j < i) continue;
                if (ap(op, a, b, z) && inV.get(z) < 0 && D1.put(z, (int)d1r.size())) d1r.push_back({z, a, b, op});
            }
        }
        X = s.V; for (auto &r : d1r) X.push_back(r.c);
    }
    inline int lvl(u64 v) const { return inV.get(v) >= 0 ? 0 : D1.get(v) >= 0 ? 1 : -1; }
};

// remaining-cost of every target and the score of every candidate (index into d1r) for state s
static double score(const State &s, Ctx &cx, vector<pair<double, int>> &cand, mt19937_64 &rng) {
    unordered_map<int, double> S; S.reserve(4096);
    u64 ys[6], ys2[6]; double total = 0;
    unordered_map<int, double> after; after.reserve(512);
    for (u64 t : s.R) {
        double cost = FAR; after.clear();
        auto rep = [&](double k, int c1, int c2) {
            cost = min(cost, k);
            for (int c : {c1, c2}) if (c >= 0) { auto it = after.find(c); if (it == after.end() || it->second > k - 1) after[c] = k - 1; }
        };
        for (u64 p : s.V) { int n = inv(t, p, ys); for (int k = 0; k < n; k++) { int d = cx.D1.get(ys[k]); if (d >= 0) rep(2, d, -1); } }
        for (u64 x : s.V) {                                     // x built; y = round(t/x) built or one step away covers x one step away too
            if (x < 2) continue;
            u64 y0 = t / x;
            for (u64 y : {y0, y0 + 1}) {
                if (y < 2) continue;
                u128 pr = (u128)x * y; if (pr > L) continue;
                u64 prod = (u64)pr, o = t > prod ? t - prod : prod - t;
                int ly = cx.lvl(y); if (ly < 0) continue;
                int lo = o ? cx.lvl(o) : 0; if (lo < 0) continue;
                int lx = cx.lvl(x), lp = cx.lvl(prod);
                double k = (lx == 1) + (ly == 1 && y != x) + (lo == 1) + (lp == 0 ? 0 : 1) + (o ? 1 : 0);
                if (k < 2) continue;
                int ix = lx == 1 ? cx.D1.get(x) : -1, iy = (ly == 1 && y != x) ? cx.D1.get(y) : -1, io = lo == 1 ? cx.D1.get(o) : -1;
                int ip = (lx == 0 && ly == 0 && lp == 1) ? cx.D1.get(prod) : -1;
                int c1 = ix >= 0 ? ix : iy >= 0 ? iy : io >= 0 ? io : ip;
                int c2 = (ix >= 0 && iy >= 0) ? iy : ((ix >= 0 || iy >= 0) && io >= 0 ? io : -1);
                rep(k, c1, c2);
            }
        }
        if (cost > 2) {
            for (size_t j = 0; j < cx.d1r.size(); j++) {           // t = c op x, c and x both one step away
                u64 x = cx.d1r[j].c; int n = inv(t, x, ys);
                for (int k = 0; k < n; k++) if (ys[k] != x) { int d = cx.D1.get(ys[k]); if (d >= 0) rep(3, d, (int)j); }
            }
        }
        if (cost > 3) {
            for (u64 p : s.V) {                                     // t = y op p, y = z op q, z one step away
                int n = inv(t, p, ys);
                for (int k = 0; k < n; k++) {
                    u64 y = ys[k]; if (cx.lvl(y) >= 0) continue;
                    for (u64 q : s.V) { int m = inv(y, q, ys2); for (int l = 0; l < m; l++) { int d = cx.D1.get(ys2[l]); if (d >= 0) rep(3, d, -1); } }
                }
            }
        }
        total += cost;
        for (auto &kv : after) if (cost - kv.second > 0) S[kv.first] += cost - kv.second;
    }
    uniform_real_distribution<double> U(0, 1);
    cand.clear();
    for (auto &kv : S) cand.push_back({kv.second * (1 + NOISE * U(rng)), kv.first});
    partial_sort(cand.begin(), cand.begin() + min<size_t>(K, cand.size()), cand.end(), [](auto &a, auto &b) { return a.first > b.first; });
    if (cand.size() > (size_t)K) cand.resize(K);
    return total;
}

static void add(State &s, const Rec &r) {
    s.recs.push_back(r); s.V.push_back(r.c);
    auto it = find(s.R.begin(), s.R.end(), r.c); if (it != s.R.end()) s.R.erase(it);
    s.sig ^= OA::h(r.c * 0x9E3779B97F4A7C15ULL + 7);
}
// build every target that is one step away; returns false if nothing to do
static void close1(State &s, Ctx &cx) {
    for (bool again = true; again && !s.R.empty();) {
        again = false; cx.build(s);
        for (u64 t : s.R) { int d = cx.D1.get(t); if (d >= 0) { add(s, cx.d1r[d]); again = true; break; } }
    }
}
// fallback for a state where no candidate helps: anchor a far target on its nearest value and add the difference as sub-target
static bool fallback(State &s, Ctx &cx, mt19937_64 &rng) {
    uniform_real_distribution<double> U(0, 1);
    double bb = 1e18; u64 bt = 0, bv = 0, bq = 0; int fromD1 = -1;
    auto inR = [&](u64 v) { return find(s.R.begin(), s.R.end(), v) != s.R.end(); };
    for (u64 t : s.R) {
        for (size_t i = 0; i < cx.X.size(); i++) {
            u64 v = cx.X[i]; if (v == t) continue;
            u64 d = t > v ? t - v : v - t;
            if ((d >= t / 2 && t > 64) || cx.inV.get(d) >= 0 || inR(d)) continue;
            double sc = (log2((double)d + 1) + (i >= s.V.size() ? 7 : 0)) * (1 + NOISE * U(rng));
            if (sc < bb) { bb = sc; bt = t; bv = v; bq = 0; fromD1 = i >= s.V.size() ? cx.D1.get(v) : -1; }
        }
        for (u64 p : s.V) if (p >= 2 && t % p == 0) {
            u64 q = t / p; if (cx.inV.get(q) >= 0 || inR(q)) continue;
            double sc = log2((double)q + 1) * (1 + NOISE * U(rng));
            if (sc < bb) { bb = sc; bt = t; bq = q; fromD1 = -1; }
        }
    }
    if (!bt) return false;
    if (bq) { s.R.push_back(bq); return true; }
    if (fromD1 >= 0) add(s, cx.d1r[fromD1]);
    u64 d = bt > bv ? bt - bv : bv - bt;
    if (cx.inV.get(d) < 0 && !inR(d)) s.R.push_back(d);
    return true;
}

static State beam(const vector<u64> &starts, const vector<u64> &targets, const vector<Rec> &prefix, int W, size_t cap, mt19937_64 &rng) {
    State s0; s0.V = starts;
    { unordered_set<u64> seen(starts.begin(), starts.end());
      for (auto &r : prefix) { s0.recs.push_back(r); if (seen.insert(r.c).second) s0.V.push_back(r.c); }
      for (u64 t : targets) if (!seen.count(t)) s0.R.push_back(t); }
    Ctx cx; close1(s0, cx);
    vector<State> B{s0}; State best; bool found = false;
    vector<pair<double, int>> cand;
    while (!B.empty()) {
        vector<State> kids;
        for (auto &s : B) {
            if (s.R.empty()) { if (!found || s.recs.size() < best.recs.size()) { best = s; found = true; } continue; }
            if (s.recs.size() >= cap || (found && s.recs.size() + 1 >= best.recs.size())) continue;
            cx.build(s);
            score(s, cx, cand, rng);
            if (cand.empty()) { State c = s; if (fallback(c, cx, rng)) { Ctx c2; close1(c, c2); kids.push_back(move(c)); } continue; }
            for (auto &pc : cand) { State c = s; add(c, cx.d1r[pc.second]); kids.push_back(move(c)); }
        }
        if (kids.empty()) break;
        for (auto &c : kids) { close1(c, cx); }
        if ((int)kids.size() > W) {                                // rank by length + remaining cost; drop duplicate value sets
            for (auto &c : kids) { if (c.R.empty()) { c.est = c.recs.size(); continue; } vector<pair<double,int>> tmp; cx.build(c); int k0 = K; K = 0; c.est = c.recs.size() + score(c, cx, tmp, rng); K = k0; }
            sort(kids.begin(), kids.end(), [](const State &a, const State &b) { return a.est < b.est; });
            vector<State> keep; unordered_set<u64> sigs;
            for (auto &c : kids) { if ((int)keep.size() >= W) break; if (sigs.insert(c.sig).second) keep.push_back(move(c)); }
            kids.swap(keep);
        }
        B.swap(kids);
    }
    return found ? best : State{};
}

int main() {
    double secs = getenv("HSEC") ? atof(getenv("HSEC")) : 10; NOISE = getenv("NOISE") ? atof(getenv("NOISE")) : 0.3;
    FAR = getenv("FAR") ? atof(getenv("FAR")) : 4; K = getenv("K") ? atoi(getenv("K")) : 4;
    int W = getenv("W") ? atoi(getenv("W")) : 1; u64 seed = getenv("SEED") ? atoll(getenv("SEED")) : 1;
    string line;
    while (getline(cin, line)) {
        istringstream in(line); string id; int ns, nt, n; in >> id >> L >> ns >> nt;
        vector<u64> st(ns), tg(nt); for (auto &x : st) in >> x; for (auto &x : tg) in >> x;
        string bar; in >> bar >> n; vector<Rec> pre(n);
        for (auto &r : pre) { string op; in >> r.c >> op >> r.a >> r.b; r.op = op[0]; }
        size_t cap = 4000; in >> cap;
        mt19937_64 rng(seed); State best; size_t bestn = SIZE_MAX; int runs = 0;
        auto t0 = chrono::steady_clock::now();
        do {
            double nz = NOISE; if (!runs) NOISE = 0;
            State p = beam(st, tg, pre, W, min(cap, bestn), rng);
            NOISE = nz; runs++;
            if (!p.recs.empty() && p.recs.size() < bestn) { bestn = p.recs.size(); best = p; }
        } while (chrono::duration<double>(chrono::steady_clock::now() - t0).count() < secs);
        cout << id << " " << best.recs.size();
        for (auto &r : best.recs) cout << " " << r.c << " " << r.op << " " << r.a << " " << r.b;
        cout << "\n" << flush;
        fprintf(stderr, "%s plan %zu (%d runs, %.1fs)\n", id.c_str(), best.recs.size(), runs, chrono::duration<double>(chrono::steady_clock::now() - t0).count());
    }
}
