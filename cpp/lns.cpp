// Elf Calculator: large-neighbourhood search over existing programs.
// Input : puzzles.txt  (id L ns nt starts... targets...)   programs.txt (id n  op a b d ...)
// Output: out.txt (id n op a b d ...) for every puzzle (best found), rewritten periodically.
// usage : lns PUZZLES PROGRAMS OUT SECONDS_PER_PUZZLE THREADS [SEED]
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64;
typedef unsigned __int128 u128;

static const int REGS = 48;
static int BEAMW = 10;
static int MAXPOOL = 0;   // >48: pool also holds dead earlier values
static int WMAX = 4, SLACK = 0, DRIFT = 4; static double TEMP = 0;
static int CUTPROB = 0, CUTMAX = 6;   // percent of moves that cut a helper and its dependents

struct Puzzle { string id; u64 L; vector<u64> starts, targets; };
struct Ins { char op; int a, b, d; };
struct Node { char op; int a, b; u64 v; };   // op==0: starting value

static inline bool apply(char op, u64 x, u64 y, u64 L, u64 &z) {
    switch (op) {
        case '+': z = x + y; return z <= L;
        case '-': if (x <= y) return false; z = x - y; return true;
        case '*': { u128 p = (u128)x * y; if (p > L) return false; z = (u64)p; return true; }
        case '/': if (x % y) return false; z = x / y; return true;
    }
    return false;
}

// ---------------------------------------------------------------- open-addressing hash value -> index
struct Hash {
    vector<u64> k; vector<int> v; u64 mask = 0;
    void init(size_t n) { size_t s = 16; while (s < 2 * n + 16) s <<= 1; k.assign(s, 0); v.assign(s, -1); mask = s - 1; }
    static inline u64 h(u64 x) { x ^= x >> 33; x *= 0xff51afd7ed558ccdULL; x ^= x >> 33; return x; }
    bool insert(u64 key, int val) {             // keeps the first value for a key
        u64 i = h(key) & mask;
        while (k[i]) { if (k[i] == key) return false; i = (i + 1) & mask; }
        k[i] = key; v[i] = val; return true;
    }
    inline int get(u64 key) const {
        u64 i = h(key) & mask;
        while (k[i]) { if (k[i] == key) return v[i]; i = (i + 1) & mask; }
        return -1;
    }
};

// ---------------------------------------------------------------- exact short-derivation search
// refs: >= 0 pool index, < 0 new step -(k+1)
struct Step { char op; int a, b; };
typedef vector<Step> Deriv;

struct F1E { u64 v; char op; int i, j; };
struct F2E { u64 v; int x; char op; int c; bool sw; };   // c = -1: x op x

template <class CB>
static inline bool inv(u64 t, u64 y, u64 L, CB cb) {
    // cb(x, op, swap) ; instruction is (x op y) if !swap else (y op x). Return true to stop.
    if (t > y && cb(t - y, '+', false)) return true;
    if (t + y <= L && cb(t + y, '-', false)) return true;
    if (y > t && cb(y - t, '-', true)) return true;
    if (t % y == 0 && cb(t / y, '*', false)) return true;
    if (y <= L / t && cb(t * y, '/', false)) return true;
    if (y % t == 0 && cb(y / t, '/', true)) return true;
    return false;
}

struct Searcher {
    vector<u64> P; u64 L;
    vector<F1E> F1; Hash H1, HP;
    vector<F2E> F2; Hash H2; bool f2built = false;

    void build(const vector<u64> &pool, u64 lim) {
        P = pool; L = lim; F1.clear(); f2built = false; F2.clear();
        HP.init(P.size()); for (int i = 0; i < (int)P.size(); i++) HP.insert(P[i], i);
        int n = P.size();
        F1.reserve(n * n * 2);
        for (int i = 0; i < n; i++) for (int j = 0; j < n; j++) {
            u64 z;
            if (i <= j) {
                if (apply('+', P[i], P[j], L, z)) F1.push_back({z, '+', i, j});
                if (apply('*', P[i], P[j], L, z)) F1.push_back({z, '*', i, j});
            }
            if (apply('-', P[i], P[j], L, z)) F1.push_back({z, '-', i, j});
            if (apply('/', P[i], P[j], L, z)) F1.push_back({z, '/', i, j});
        }
        H1.init(F1.size());
        vector<F1E> u; u.reserve(F1.size());
        for (auto &e : F1) if (HP.get(e.v) < 0 && H1.insert(e.v, u.size())) u.push_back(e);
        F1.swap(u);
    }
    void buildF2() {
        if (f2built) return; f2built = true;
        int m = F1.size(), n = P.size();
        F2.clear(); F2.reserve((size_t)m * n * 3);
        H2.init((size_t)m * n * 3);
        auto add = [&](u64 v, int x, char op, int c, bool sw) {
            if (HP.get(v) >= 0 || H1.get(v) >= 0) return;
            if (H2.insert(v, F2.size())) F2.push_back({v, x, op, c, sw});
        };
        for (int x = 0; x < m; x++) {
            u64 a = F1[x].v, z;
            if (apply('+', a, a, L, z)) add(z, x, '+', -1, false);
            if (apply('*', a, a, L, z)) add(z, x, '*', -1, false);
            for (int c = 0; c < n; c++) {
                u64 b = P[c];
                if (apply('+', a, b, L, z)) add(z, x, '+', c, false);
                if (apply('*', a, b, L, z)) add(z, x, '*', c, false);
                if (apply('-', a, b, L, z)) add(z, x, '-', c, false);
                if (apply('-', b, a, L, z)) add(z, x, '-', c, true);
                if (apply('/', a, b, L, z)) add(z, x, '/', c, false);
                if (apply('/', b, a, L, z)) add(z, x, '/', c, true);
            }
        }
    }
    Deriv d1(int k) { return {{F1[k].op, F1[k].i, F1[k].j}}; }
    Deriv d2(int k) {
        Deriv d = d1(F2[k].x); int other = F2[k].c < 0 ? -1 : F2[k].c;
        if (!F2[k].sw) d.push_back({F2[k].op, -1, other}); else d.push_back({F2[k].op, other, -1});
        return d;
    }
    static Deriv join(const Deriv &l, const Deriv &r, char op, bool sw) {
        // final = (lastL op lastR) or (lastR op lastL)
        Deriv d = l; int off = l.size();
        for (auto s : r) { if (s.a < 0) s.a -= off; if (s.b < 0) s.b -= off; d.push_back(s); }
        int lr = -(int)l.size(), rr = -(int)(l.size() + r.size());
        if (!sw) d.push_back({op, lr, rr}); else d.push_back({op, rr, lr});
        return d;
    }
    static Deriv withPool(Deriv d, int c, char op, bool sw) {
        int last = -(int)d.size();
        if (!sw) d.push_back({op, last, c}); else d.push_back({op, c, last});
        return d;
    }
    // t = x op y, y from list Y (builder by), x in hash HX (builder bx)
    template <class GY, class BX, class BY>
    bool pairSearch(u64 t, int ny, GY gy, const Hash &HX, BX bx, BY by, Deriv &out) {
        for (int yi = 0; yi < ny; yi++) {
            u64 y = gy(yi);
            bool hit = inv(t, y, L, [&](u64 x, char op, bool sw) {
                int xi = HX.get(x); if (xi < 0) return false;
                out = join(bx(xi), by(yi), op, sw); return true;
            });
            if (hit) return true;
        }
        return false;
    }
    bool f1f1(u64 t, Deriv &o) { return pairSearch(t, F1.size(), [&](int i) { return F1[i].v; }, H1, [&](int i) { return d1(i); }, [&](int i) { return d1(i); }, o); }
    bool f2f1(u64 t, Deriv &o) { return pairSearch(t, F1.size(), [&](int i) { return F1[i].v; }, H2, [&](int i) { return d2(i); }, [&](int i) { return d1(i); }, o); }
    bool f2f2(u64 t, Deriv &o) { return pairSearch(t, F2.size(), [&](int i) { return F2[i].v; }, H2, [&](int i) { return d2(i); }, [&](int i) { return d2(i); }, o); }

    // returns true and the derivation with <= K steps
    bool find(u64 t, int K, Deriv &out) {
        out.clear();
        if (HP.get(t) >= 0) return true;
        if (K < 1) return false;
        int k = H1.get(t); if (k >= 0) { out = d1(k); return true; }
        if (K < 2) return false;
        int n = P.size();
        auto selfs = [&](auto fn) -> bool {     // t = w + w or w * w
            if (t % 2 == 0 && fn(t / 2, '+')) return true;
            u64 r = (u64)sqrtl((long double)t);
            for (u64 q = r > 0 ? r - 1 : 0; q <= r + 1; q++) if (q && q * q == t && fn(q, '*')) return true;
            return false;
        };
        // k=2
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char op, bool sw) { int i = H1.get(x); if (i < 0) return false; out = withPool(d1(i), c, op, sw); return true; })) return true;
        if (selfs([&](u64 w, char op) { int i = H1.get(w); if (i < 0) return false; out = d1(i); out.push_back({op, -1, -1}); return true; })) return true;
        if (K < 3) return false;
        // k=3
        if (f1f1(t, out)) return true;
        buildF2();
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char op, bool sw) { int i = H2.get(x); if (i < 0) return false; out = withPool(d2(i), c, op, sw); return true; })) return true;
        if (selfs([&](u64 w, char op) { int i = H2.get(w); if (i < 0) return false; out = d2(i); out.push_back({op, -2, -2}); return true; })) return true;
        if (K < 4) return false;
        // k=4
        if (f2f1(t, out)) return true;
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char op, bool sw) { Deriv d; if (!f1f1(x, d)) return false; out = withPool(d, c, op, sw); return true; })) return true;
        if (selfs([&](u64 w, char op) { Deriv d; if (!f1f1(w, d)) return false; int l = -(int)d.size(); d.push_back({op, l, l}); out = d; return true; })) return true;
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char op, bool sw) {
                for (int e = 0; e < n; e++) if (inv(x, P[e], L, [&](u64 w, char op2, bool sw2) { int i = H2.get(w); if (i < 0) return false; out = withPool(withPool(d2(i), e, op2, sw2), c, op, sw); return true; })) return true;
                return false; })) return true;
        if (K < 5) return false;
        // k=5
        if (f2f2(t, out)) return true;
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char op, bool sw) { Deriv d; if (!f2f1(x, d)) return false; out = withPool(d, c, op, sw); return true; })) return true;
        if (selfs([&](u64 w, char op) { Deriv d; if (!f2f1(w, d)) return false; int l = -(int)d.size(); d.push_back({op, l, l}); out = d; return true; })) return true;
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char op, bool sw) {
                for (int e = 0; e < n; e++) if (inv(x, P[e], L, [&](u64 w, char op2, bool sw2) {
                        for (int g = 0; g < n; g++) if (inv(w, P[g], L, [&](u64 u, char op3, bool sw3) { int i = H2.get(u); if (i < 0) return false; out = withPool(withPool(withPool(d2(i), g, op3, sw3), e, op2, sw2), c, op, sw); return true; })) return true;
                        return false; })) return true;
                return false; })) return true;
        return false;
    }
};

// Backward beam search (target = child*factor +/- atom over a 0/1/2-step dictionary).
// Adapted from the public solver by Tony Li / konbu17 (Kaggle notebooks, Apache 2.0): leaves are the pool.
namespace kb {
using Int = int64_t;
static double ALPHA = 0.18;
struct Expr {
    Int v;
    int a = -1, b = -1;
    char op = 0;
    int cost = 0;
};
Int apply(char op, Int a, Int b) {
    if (op == '+')
        return a + b;
    if (op == '-')
        return a - b;
    if (op == '/')
        return a / b;
    return a * b; // All callers check the puzzle limit before multiplying.
}

// Integer-key index reused between targets. Zero is outside the calculator domain.
struct Index {
    vector<Int> keys;
    vector<int> ids, used;
    size_t mask;
    Index(int bits) : keys(1u << bits), ids(keys.size()), mask(keys.size() - 1) {}
    size_t slot(Int v) const {
        uint64_t h = uint64_t(v) * 0x9e3779b97f4a7c15ULL;
        h ^= h >> 31;
        size_t i = h & mask;
        while (keys[i] && keys[i] != v)
            i = (i + 1) & mask;
        return i;
    }
    int get(Int v) const {
        size_t i = slot(v);
        return keys[i] ? ids[i] : -1;
    }
    bool insert(Int v, int id) {
        size_t i = slot(v);
        if (keys[i] || used.size() * 8 > keys.size() * 7) // never let the table fill up
            return false;
        used.push_back(i);
        keys[i] = v;
        ids[i] = id;
        return true;
    }
    void clear() {
        for (int i : used)
            keys[i] = 0;
        used.clear();
    }
};

struct Dictionary {
    Int limit;
    Index index{21};
    vector<Expr> e;
    array<vector<pair<Int, int>>, 3> sorted;
    int n0 = 0, n1 = 0;
    explicit Dictionary(Int limit) : limit(limit) {}
    void add(Int v, int a, int b, char op, int cost) {
        if (v > 0 && v <= limit && index.insert(v, e.size()))
            e.push_back({v, a, b, op, cost});
    }
    void combine(int i, int j, int cost) {
        Int a = e[i].v, b = e[j].v;
        add(a + b, i, j, '+', cost);
        if (a != b)
            add(abs(a - b), a > b ? i : j, a > b ? j : i, '-', cost);
        if (a <= limit / b)
            add(a * b, i, j, '*', cost);
        if (a > b && a % b == 0)
            add(a / b, i, j, '/', cost);
        if (b > a && b % a == 0)
            add(b / a, j, i, '/', cost);
    }
    void build(const vector<Int> &leaves) {
        index.clear();
        e.clear();
        for (auto &s : sorted)
            s.clear();
        for (Int v : leaves)
            add(v, -1, -1, 0, 0);
        n0 = e.size();
        for (int i = 0; i < n0; i++)
            for (int j = 0; j <= i; j++)
                combine(i, j, 1);
        n1 = e.size();
        for (int i = n0; i < n1; i++)
            for (int j = 0; j < n0; j++)
                combine(i, j, 2);
        for (int i = 0; i < int(e.size()); i++)
            sorted[e[i].cost].emplace_back(e[i].v, i);
        for (auto &s : sorted)
            sort(s.begin(), s.end());
    }
};
// A reduction encodes parent = (child * factor) +/- atom, or atom - child.
struct Link {
    int factor = -1, atom = -1;
    char op = '+';
};
struct State {
    Int v;
    int cost = 0, parent = -1;
    Link link;
    double rank = 0;
};

struct Search {
    Dictionary &d;
    int width, best = 1000, end = -1, terminal = -1;
    vector<State> history, next;
    unordered_map<Int, int> visited;
    Search(Dictionary &d, int width) : d(d), width(width) {}
    int expr_cost(int id) const { return id < 0 ? 0 : 1 + d.e[id].cost; }
    void offer(int p, Int v, int f, int a, char op) {
        if (v <= 0 || v > d.limit)
            return;
        int cost = history[p].cost + expr_cost(f) + expr_cost(a);
        if (cost >= best)
            return;
        int t = d.index.get(v);
        if (t >= 0) {
            if (cost + d.e[t].cost < best) {
                best = cost + d.e[t].cost;
                end = history.size();
                terminal = t;
                history.push_back({v, cost, p, {f, a, op}});
            }
            return;
        }
        if (cost + 3 >= best || v >= history[p].v)
            return;
        // Comparisons happen across instruction costs and residual sizes.
        double rank = cost + ALPHA * log2(double(v));
        if (int(next.size()) == width && rank >= next.back().rank)
            return;
        auto prev = visited.find(v);
        if (prev != visited.end() && prev->second <= cost)
            return;
        for (auto it = next.begin(); it != next.end(); ++it)
            if (it->v == v) {
                if (it->cost <= cost)
                    return;
                next.erase(it);
                break;
            }
        State s{v, cost, p, {f, a, op}, rank};
        auto it = upper_bound(next.begin(), next.end(), rank,
                              [](double k, const State &x) { return k < x.rank; });
        next.insert(it, s);
        if (int(next.size()) > width)
            next.pop_back();
    }
    void expand(int p) {
        Int v = history[p].v;
        for (auto &arr : d.sorted) {
            auto it = lower_bound(arr.begin(), arr.end(), make_pair(v, -1));
            for (int k = -4; k < 4; k++) {
                auto pos = (it - arr.begin()) + k;
                if (pos < 0 || pos >= int(arr.size()))
                    continue;
                auto [a, id] = arr[pos];
                offer(p, abs(v - a), -1, id, v > a ? '+' : 'r');
            }
        }
        for (int i = 0; i < d.n1; i++) {
            Int a = d.e[i].v;
            if (a == 1)
                continue;
            Int diff = abs(v - a);
            if (diff) {
                if (d.index.get(diff) >= 0)
                    offer(p, diff, -1, i, v > a ? '+' : 'r');
                if (v > a && (diff & 15) == 0)
                    shifted(p, diff, i, '+');
                if (a > v && (diff & 15) == 0)
                    shifted(p, diff, i, 'r');
            }
            if (a + v <= d.limit) {
                if (d.index.get(a + v) >= 0)
                    offer(p, a + v, -1, i, '-');
                if (((a + v) & 15) == 0)
                    shifted(p, a + v, i, '-');
            }
            if (a >= v)
                continue;
            Int q = v / a, r = v % a;
            if (!r) {
                offer(p, q, i, -1, '+');
                continue;
            }
            int rid = d.index.get(r);
            if (rid >= 0)
                offer(p, q, i, rid, '+');
            if (a - r <= d.limit - v) {
                rid = d.index.get(a - r);
                if (rid >= 0)
                    offer(p, q + 1, i, rid, '-');
            }
            // Approximate the quotient by a cached expression, then synthesize the error.
            if (i < d.n0 && q > 64) {
                for (auto &arr : d.sorted) {
                    auto it = lower_bound(arr.begin(), arr.end(), make_pair(q, -1));
                    for (int k = -1; k <= 0; k++) {
                        auto pos = (it - arr.begin()) + k;
                        if (pos < 0 || pos >= int(arr.size()))
                            continue;
                        auto [b, bi] = arr[pos];
                        if (b > d.limit / a)
                            continue;
                        Int mul = a * b;
                        if (mul == v)
                            continue;
                        int id = d.index.get(mul);
                        if (id >= 0)
                            offer(p, abs(mul - v), -1, id, mul < v ? '+' : 'r');
                    }
                }
            }
        }
    }
    void shifted(int p, Int diff, int atom, char op) {
        int k = __builtin_ctzll(diff);
        while (k >= 4) {
            int f = d.index.get(Int(1) << k);
            if (f >= 0) {
                offer(p, diff >> k, f, atom, op);
                break;
            }
            k--;
        }
    }
    void run(Int target) {
        history.push_back({target, 0, -1, {}});
        int id = d.index.get(target);
        if (id >= 0) {
            end = 0;
            terminal = id;
            best = d.e[id].cost;
            return;
        }
        vector<int> front{0};
        for (int depth = 0; depth < 20 && !front.empty(); depth++) {
            next.clear();
            for (int p : front)
                if (history[p].cost + 3 < best)
                    expand(p);
            front.clear();
            for (State s : next) {
                if (s.cost + 3 >= best)
                    continue;
                visited[s.v] = s.cost;
                front.push_back(history.size());
                history.push_back(s);
            }
        }
    }
};

// Materialize into a Deriv over pool indices. Returns false if anything is inconsistent.
struct Builder {
    const vector<u64> &pool; unordered_map<u64, int> ref; Deriv d; u64 L; bool ok = true;
    Builder(const vector<u64> &p, u64 L) : pool(p), L(L) { for (size_t i = 0; i < p.size(); i++) ref.emplace(p[i], (int)i); }
    int get(u64 v) { auto it = ref.find(v); return it == ref.end() ? INT_MIN : it->second; }
    int make(char op, int ra, int rb, u64 va, u64 vb) {
        u64 z; if (!::apply(op, va, vb, L, z)) { ok = false; return INT_MIN; }
        int r = get(z); if (r != INT_MIN) return r;
        d.push_back({op, ra, rb}); r = -(int)d.size(); ref[z] = r; return r;
    }
    pair<int, u64> mat(Dictionary &dc, int id) {
        const Expr &e = dc.e[id];
        int r = get((u64)e.v); if (r != INT_MIN) return {r, (u64)e.v};
        if (e.a < 0) { ok = false; return {0, 0}; }
        auto L1 = mat(dc, e.a); auto R1 = mat(dc, e.b);
        if (!ok) return {0, 0};
        return {make(e.op, L1.first, R1.first, L1.second, R1.second), (u64)e.v};
    }
};
}  // namespace kb

static thread_local kb::Dictionary *KBD = nullptr;
static bool beamFind(const vector<u64> &pool, u64 L, u64 t, int budget, int width, Deriv &out) {
    if (!KBD) KBD = new kb::Dictionary((kb::Int)L);
    KBD->limit = (kb::Int)L;
    vector<kb::Int> leaves(pool.begin(), pool.end());
    KBD->build(leaves);
    kb::Search s(*KBD, width); s.best = budget + 1;
    s.run((kb::Int)t);
    if (s.end < 0) return false;
    kb::Builder B(pool, L);
    auto cur = B.mat(*KBD, s.terminal);
    for (int p = s.end; B.ok && s.history[p].parent >= 0; p = s.history[p].parent) {
        kb::Link l = s.history[p].link;
        if (l.factor >= 0) { auto f = B.mat(*KBD, l.factor); cur = {B.make('*', cur.first, f.first, cur.second, f.second), cur.second * f.second}; }
        if (l.atom >= 0) {
            auto a = B.mat(*KBD, l.atom);
            if (l.op == 'r') cur = {B.make('-', a.first, cur.first, a.second, cur.second), a.second - cur.second};
            else if (l.op == '+') cur = {B.make('+', cur.first, a.first, cur.second, a.second), cur.second + a.second};
            else cur = {B.make('-', cur.first, a.first, cur.second, a.second), cur.second - a.second};
        }
    }
    if (!B.ok || cur.second != t || (int)B.d.size() > budget || B.d.empty()) return false;
    out = B.d; return true;
}

// ---------------------------------------------------------------- SSA program + register allocation
struct Prog { vector<Node> nodes; int ns; };

static bool toSSA(const Puzzle &pz, const vector<Ins> &prog, Prog &out) {
    out.nodes.clear(); out.ns = pz.starts.size();
    vector<int> reg(REGS, -1);
    for (int i = 0; i < out.ns; i++) { out.nodes.push_back({0, -1, -1, pz.starts[i]}); reg[i] = i; }
    for (auto &in : prog) {
        int a = reg[in.a], b = reg[in.b];
        if (a < 0 || b < 0) return false;
        u64 z; if (!apply(in.op, out.nodes[a].v, out.nodes[b].v, pz.L, z)) return false;
        out.nodes.push_back({in.op, a, b, z}); reg[in.d] = out.nodes.size() - 1;
    }
    return true;
}

// Allocate registers (overwrite the dead register written longest ago). Optionally stop at node `upto`
// and return register contents there. Returns false if more than REGS values must be live.
static bool allocate(const Prog &p, vector<Ins> *outIns, int upto = -1, vector<int> *regsAt = nullptr) {
    int N = p.nodes.size();
    vector<int> last(N, -1);
    for (int i = p.ns; i < N; i++) { last[p.nodes[i].a] = i; last[p.nodes[i].b] = i; }
    vector<int> reg(REGS, -1), when(REGS, -1), where(N, -1);
    for (int i = 0; i < p.ns; i++) { reg[i] = i; where[i] = i; when[i] = -1; }
    if (outIns) outIns->clear();
    for (int i = p.ns; i < N; i++) {
        if (i == upto && regsAt) { *regsAt = reg; return true; }
        const Node &nd = p.nodes[i];
        int ra = where[nd.a], rb = where[nd.b];
        if (ra < 0 || rb < 0 || reg[ra] != nd.a || reg[rb] != nd.b) return false;
        int best = -1, bw = INT_MAX;
        for (int r = 0; r < REGS; r++) {
            int v = reg[r];
            bool dead = v < 0 || last[v] <= i;          // value not needed after this instruction
            if (dead) { int w = v < 0 ? -2 : when[r]; if (w < bw) { bw = w; best = r; } }
        }
        if (best < 0) return false;
        if (reg[best] >= 0) where[reg[best]] = -1;
        reg[best] = i; where[i] = best; when[best] = i;
        if (outIns) outIns->push_back({nd.op, ra, rb, best});
    }
    if (upto >= 0 && regsAt) *regsAt = reg;
    return true;
}

static int validate(const Puzzle &pz, const vector<Ins> &prog) {
    vector<u64> R(REGS, 0); vector<bool> def(REGS, false);
    for (size_t i = 0; i < pz.starts.size(); i++) { R[i] = pz.starts[i]; def[i] = true; }
    unordered_set<u64> need(pz.targets.begin(), pz.targets.end());
    for (auto s : pz.starts) need.erase(s);
    for (auto &in : prog) {
        if (in.a < 0 || in.a >= REGS || in.b < 0 || in.b >= REGS || in.d < 0 || in.d >= REGS) return -1;
        if (!def[in.a] || !def[in.b]) return -1;
        u64 z; if (!apply(in.op, R[in.a], R[in.b], pz.L, z) || z == 0) return -1;
        R[in.d] = z; def[in.d] = true; need.erase(z);
    }
    if (!need.empty() || prog.size() > 4096) return -1;
    return prog.size();
}

// ---------------------------------------------------------------- LNS
struct Result { vector<Ins> prog; };
static map<pair<int, int>, long> STATS; static mutex STATMU; static bool STATS_ON = getenv("ELF_STATS") != nullptr;

static int MAXALT = 0, ALTSLACK = 0;
static vector<Ins> improve(const Puzzle &pz, vector<Ins> prog, double seconds, u64 seed, long &moves, long &accepted, vector<vector<Ins>> *alts = nullptr) {
    unordered_set<u64> altSeen;
    mt19937_64 rng(seed);
    Prog cur; if (!toSSA(pz, prog, cur)) return prog;
    vector<Ins> best = prog; int bestLen = prog.size(); int curLen = bestLen;
    unordered_set<u64> tset(pz.targets.begin(), pz.targets.end());
    Searcher S;
    auto t0 = chrono::steady_clock::now();
    while (chrono::duration<double>(chrono::steady_clock::now() - t0).count() < seconds) {
        moves++;
        int N = cur.nodes.size();
        // first-cover node of each target (in node order)
        unordered_map<u64, int> cover;
        for (int i = 0; i < N; i++) if (tset.count(cur.nodes[i].v) && !cover.count(cur.nodes[i].v)) cover[cur.nodes[i].v] = i;
        vector<pair<int, u64>> order;
        for (auto &kv : cover) if (kv.second >= cur.ns) order.push_back({kv.second, kv.first});
        sort(order.begin(), order.end());
        if (order.empty()) break;
        int m = 1 + rng() % WMAX; m = min<int>(m, order.size());
        int s0 = rng() % (order.size() - m + 1);
        vector<int> pick;
        if (CUTPROB > 0 && (int)(rng() % 100) < CUTPROB) {
            // helper cut: a random computed node and every node depending on it; their targets form the window
            int h = cur.ns + rng() % (N - cur.ns);
            vector<char> dep(N, 0); dep[h] = 1;
            for (int i = h + 1; i < N; i++) if (cur.nodes[i].op && (dep[cur.nodes[i].a] || dep[cur.nodes[i].b])) dep[i] = 1;
            for (size_t k = 0; k < order.size(); k++) if (dep[order[k].first]) pick.push_back(k);
            if (pick.empty() || (int)pick.size() > CUTMAX) continue;
            s0 = pick[0];
        } else if (rng() % 2) { for (int k = s0; k < s0 + m; k++) pick.push_back(k); }
        else { vector<int> all(order.size()); iota(all.begin(), all.end(), 0); shuffle(all.begin(), all.end(), rng);
               pick.assign(all.begin(), all.begin() + m); sort(pick.begin(), pick.end()); s0 = pick[0]; }
        unordered_set<u64> win; for (int k : pick) win.insert(order[k].second);
        // keep: starts + ancestors of cover nodes of non-window targets
        vector<char> keep(N, 0);
        for (int i = 0; i < cur.ns; i++) keep[i] = 1;
        vector<int> st;
        for (auto &kv : cover) if (!win.count(kv.first)) st.push_back(kv.second);
        while (!st.empty()) { int x = st.back(); st.pop_back(); if (keep[x]) continue; keep[x] = 1; st.push_back(cur.nodes[x].a); st.push_back(cur.nodes[x].b); }
        int removed = 0; for (int i = 0; i < N; i++) if (!keep[i]) removed++;
        // targets in window still to produce
        unordered_set<u64> kv; for (int i = 0; i < N; i++) if (keep[i]) kv.insert(cur.nodes[i].v);
        vector<u64> todo; for (int k : pick) if (!kv.count(order[k].second)) todo.push_back(order[k].second);
        // reduced program and insertion point
        int qorig = order[s0].first;
        Prog red; red.ns = cur.ns; vector<int> mp(N, -1);
        int q = -1;
        for (int i = 0; i < N; i++) {
            if (q < 0 && i >= qorig) q = red.nodes.size();
            if (!keep[i]) continue;
            Node nd = cur.nodes[i]; if (nd.op) { nd.a = mp[nd.a]; nd.b = mp[nd.b]; }
            mp[i] = red.nodes.size(); red.nodes.push_back(nd);
        }
        if (q < 0) q = red.nodes.size();
        if (rng() % 2) q += rng() % ((int)red.nodes.size() - q + 1);   // place later: different register contents
        q = max(q, red.ns);
        vector<int> regsAt;
        if (!allocate(red, nullptr, q, &regsAt)) continue;
        vector<int> poolNodes; { unordered_set<u64> seen; for (int r : regsAt) if (r >= 0 && seen.insert(red.nodes[r].v).second) poolNodes.push_back(r); }
        if (MAXPOOL > (int)poolNodes.size()) {        // also offer dead earlier values (kept alive if registers allow)
            unordered_set<u64> seen; for (int r : poolNodes) seen.insert(red.nodes[r].v);
            vector<int> extra; for (int i = 0; i < q; i++) if (seen.insert(red.nodes[i].v).second) extra.push_back(i);
            shuffle(extra.begin(), extra.end(), rng);
            for (int x : extra) { if ((int)poolNodes.size() >= MAXPOOL) break; poolNodes.push_back(x); }
        }
        shuffle(poolNodes.begin(), poolNodes.end(), rng);
        shuffle(todo.begin(), todo.end(), rng);
        int allowance = removed + SLACK;              // equal length allowed (plateau move); SLACK > 0: annealing
        vector<Node> added; bool ok = true; int used = 0;
        for (size_t ti = 0; ti < todo.size() && ok; ti++) {
            vector<u64> pool; for (int r : poolNodes) pool.push_back(red.nodes[r].v);
            for (auto &a : added) pool.push_back(a.v);
            // dedupe pool (keep first)
            vector<int> ref; { unordered_set<u64> sn; vector<u64> pp; vector<int> rr;
                for (size_t i = 0; i < pool.size(); i++) if (sn.insert(pool[i]).second) { pp.push_back(pool[i]); rr.push_back(i); }
                pool = pp; ref = rr; }
            bool already = false; for (auto v : pool) if (v == todo[ti]) { already = true; break; }
            if (already) continue;
            int budget = allowance - used - (int)(todo.size() - ti - 1);
            if (budget < 1) { ok = false; break; }
            S.build(pool, pz.L);
            Deriv d;
            bool fnd = S.find(todo[ti], min(budget, 5), d);
            if (!fnd && budget >= 4) fnd = beamFind(pool, pz.L, todo[ti], budget, BEAMW, d);
            if (STATS_ON && todo.size() == 1) { lock_guard<mutex> g(STATMU); STATS[{removed, fnd ? (int)d.size() : -1}]++; }
            if (!fnd || (int)d.size() > budget) { ok = false; break; }
            // translate derivation into nodes; refs: pool index -> (red node or added node)
            int base = added.size();
            for (auto &stp : d) {
                auto tr = [&](int r) -> int {     // encode: >=0 red node id, <0 added index -(k+1)
                    if (r < 0) return -(base + (-r - 1) + 1);
                    int pi = ref[r];
                    if (pi < (int)poolNodes.size()) return poolNodes[pi];
                    return -((pi - (int)poolNodes.size()) + 1);
                };
                Node nd; nd.op = stp.op; nd.a = tr(stp.a); nd.b = tr(stp.b);
                auto val = [&](int x) { return x >= 0 ? red.nodes[x].v : added[-x - 1].v; };
                if (!apply(nd.op, val(nd.a), val(nd.b), pz.L, nd.v)) { ok = false; break; }
                added.push_back(nd);
            }
            used = added.size();
        }
        if (!ok) continue;
        int newLen = (N - cur.ns) - removed + added.size();
        if (newLen > curLen) {                           // annealing: accept worse with prob exp(-d/TEMP), never too far from best
            if (TEMP <= 0 || newLen > bestLen + DRIFT) continue;
            if ((rng() % 1000000) / 1e6 >= exp(-(newLen - curLen) / TEMP)) continue;
        } else if (newLen == curLen && (rng() % 4)) continue;   // accept 1 in 4 plateau moves
        // assemble candidate
        Prog cand; cand.ns = red.ns;
        int R = red.nodes.size(); vector<int> mp2(R, -1);
        for (int i = 0; i < q; i++) { mp2[i] = i; cand.nodes.push_back(red.nodes[i]); }
        int baseAdd = cand.nodes.size();
        for (auto nd : added) {
            nd.a = nd.a >= 0 ? mp2[nd.a] : baseAdd + (-nd.a - 1);
            nd.b = nd.b >= 0 ? mp2[nd.b] : baseAdd + (-nd.b - 1);
            cand.nodes.push_back(nd);
        }
        for (int i = q; i < R; i++) {
            Node nd = red.nodes[i];
            if (nd.op) { nd.a = mp2[nd.a]; nd.b = mp2[nd.b]; }
            mp2[i] = cand.nodes.size(); cand.nodes.push_back(nd);
        }
        bool bad = false; for (auto &nd : cand.nodes) if (nd.op && (nd.a < 0 || nd.b < 0)) bad = true;
        if (bad) continue;
        vector<Ins> ins;
        if (!allocate(cand, &ins)) continue;
        int len = validate(pz, ins);
        if (len < 0) continue;
        accepted++;
        cur = cand; curLen = len;
        if (len < bestLen) { bestLen = len; best = ins; if (alts && !ALTSLACK) { alts->clear(); altSeen.clear(); } }
        if (alts && len <= bestLen + ALTSLACK && (int)alts->size() < MAXALT) {   // distinct near-best variants for recombination
            vector<u64> vs; for (auto &nd : cand.nodes) vs.push_back(nd.v); sort(vs.begin(), vs.end());
            u64 hsh = 1469598103934665603ULL; for (u64 x : vs) hsh = (hsh ^ x) * 1099511628211ULL;
            if (altSeen.insert(hsh).second) alts->push_back(ins);
        }
    }
    return best;
}

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: lns PUZZLES PROGRAMS OUT SECONDS THREADS [SEED]\n"); return 1; }
    double secs = atof(argv[4]); int threads = atoi(argv[5]); if (getenv("BEAMW")) BEAMW = atoi(getenv("BEAMW")); if (getenv("MAXPOOL")) MAXPOOL = atoi(getenv("MAXPOOL")); if (getenv("CUTPROB")) CUTPROB = atoi(getenv("CUTPROB")); if (getenv("WMAX")) WMAX = atoi(getenv("WMAX")); if (getenv("SLACK")) SLACK = atoi(getenv("SLACK")); if (getenv("DRIFT")) DRIFT = atoi(getenv("DRIFT")); if (getenv("TEMP")) TEMP = atof(getenv("TEMP")); if (getenv("CUTMAX")) CUTMAX = atoi(getenv("CUTMAX")); u64 seed = argc > 6 ? atoll(argv[6]) : 1;
    vector<Puzzle> pz; map<string, int> idx;
    { ifstream f(argv[1]); string id; while (f >> id) { Puzzle p; p.id = id; int ns, nt; f >> p.L >> ns >> nt; p.starts.resize(ns); p.targets.resize(nt);
        for (auto &x : p.starts) f >> x; for (auto &x : p.targets) f >> x; idx[id] = pz.size(); pz.push_back(p); } }
    vector<vector<Ins>> progs(pz.size());
    { ifstream f(argv[2]); string id; while (f >> id) { int n; f >> n; vector<Ins> v(n); for (auto &in : v) { string op; f >> op >> in.a >> in.b >> in.d; in.op = op[0]; } if (idx.count(id)) progs[idx[id]] = v; } }
    vector<vector<Ins>> best = progs; mutex mu; atomic<int> next(0); long totMoves = 0, totAcc = 0;
    long before = 0; for (auto &p : progs) before += p.size();
    auto dump = [&]() {
        ofstream o(string(argv[3]) + ".tmp");
        for (size_t i = 0; i < pz.size(); i++) { o << pz[i].id << " " << best[i].size(); for (auto &in : best[i]) o << " " << in.op << " " << in.a << " " << in.b << " " << in.d; o << "\n"; }
        o.close(); remove(argv[3]); rename((string(argv[3]) + ".tmp").c_str(), argv[3]);
    };
    if (getenv("MAXALT")) MAXALT = atoi(getenv("MAXALT")); if (getenv("ALTSLACK")) ALTSLACK = atoi(getenv("ALTSLACK"));
    ofstream altf; if (MAXALT > 0 && getenv("ALTOUT")) altf.open(getenv("ALTOUT"));
    vector<thread> th;
    for (int t = 0; t < threads; t++) th.emplace_back([&, t]() {
        while (true) {
            int i = next++; if (i >= (int)pz.size()) break;
            if (progs[i].empty()) continue;
            long mv = 0, ac = 0; vector<vector<Ins>> alts;
            auto r = improve(pz[i], progs[i], secs, seed * 1000003ULL + i, mv, ac, MAXALT > 0 ? &alts : nullptr);
            lock_guard<mutex> g(mu);
            totMoves += mv; totAcc += ac;
            if (altf.is_open()) for (auto &a : alts) { altf << pz[i].id << " " << a.size(); for (auto &in : a) altf << " " << in.op << " " << in.a << " " << in.b << " " << in.d; altf << "\n"; }
            if (altf.is_open()) altf.flush();
            if (validate(pz[i], r) >= 0 && r.size() < best[i].size()) {
                fprintf(stderr, "%s %zu -> %zu\n", pz[i].id.c_str(), progs[i].size(), r.size());
                best[i] = r;
            }
            if (i % 20 == 0) dump();
        }
    });
    for (auto &x : th) x.join();
    dump();
    long after = 0; for (auto &p : best) after += p.size();
    fprintf(stderr, "total %ld -> %ld  moves %ld accepted %ld\n", before, after, totMoves, totAcc);
    if (STATS_ON) for (auto &kv : STATS) fprintf(stderr, "removed %d found %d : %ld\n", kv.first.first, kv.first.second, kv.second);
}
