// Register-exact beam planner ("wide suffix re-solve").
// Keeps a given program up to the cover of its k-th target (random k per run), then plans the remaining targets one by one.
// For each target and each of W beam states it collects several shortest derivations from the FULL pool of values that can
// still be kept in registers (exact occupancy <= 48), scores children by length + LAMBDA * estimated cost of the next targets,
// and keeps the W best. Reuses the searcher, beam fallback and allocator of lns.cpp.
// usage: beam PUZZLES PROGRAMS OUT SECONDS_PER_PUZZLE THREADS [SEED]
// env  : W (beam width, 6)  MAXSOL (derivations per state, 6)  LAMBDA (0.4)  R (lookahead targets, 8)  SMALL (pool for 4-5 step
//        search, 60)  BEAMW (deep fallback width, 10)  KMIN/KMAX (cut point as a fraction of targets, 0.15/0.9)
#define main lns_main
#include "lns.cpp"
#undef main
#include <pthread.h>

static int W = 6, MAXSOL = 6, R = 8, SMALL = 60, DROP = 1;
static double LAMBDA = 0.4, KMIN = 0.15, KMAX = 0.9;

// ------------------------------------------------------------ exact search up to 3 steps over a large pool, many solutions
struct Full {
    vector<u64> P; u64 L; Hash HP, H1; vector<F1E> F1;
    void build(const vector<u64> &pool, u64 lim) {
        P = pool; L = lim; int n = P.size();
        HP.init(n); for (int i = 0; i < n; i++) HP.insert(P[i], i);
        F1.clear(); F1.reserve((size_t)n * n * 2);
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
    Deriv d1(int k) const { return {{F1[k].op, F1[k].i, F1[k].j}}; }
    // all derivations of minimal length <= 3 (up to cap, scanning from a random offset)
    int find(u64 t, int cap, mt19937_64 &rng, vector<Deriv> &out) {
        out.clear(); int n = P.size();
        if (HP.get(t) >= 0) { out.push_back({}); return 0; }
        int k = H1.get(t); if (k >= 0) { out.push_back(d1(k)); return 1; }
        auto full = [&]() { return (int)out.size() >= cap; };
        int off = rng() % max(1, n);
        // length 2
        for (int cc = 0; cc < n && !full(); cc++) { int c = (cc + off) % n;
            inv(t, P[c], L, [&](u64 x, char op, bool sw) { int i = H1.get(x); if (i >= 0) out.push_back(Searcher::withPool(d1(i), c, op, sw)); return full(); }); }
        auto selfs = [&](u64 tt, auto fn) {
            if (tt % 2 == 0) fn(tt / 2, '+');
            u64 r = (u64)sqrtl((long double)tt);
            for (u64 q = r > 0 ? r - 1 : 0; q <= r + 1; q++) if (q && q * q == tt) fn(q, '*');
        };
        selfs(t, [&](u64 w, char op) { int i = H1.get(w); if (i >= 0 && !full()) { Deriv d = d1(i); d.push_back({op, -1, -1}); out.push_back(d); } });
        if (!out.empty()) return 2;
        // length 3: F1 op F1
        int m = F1.size(), off1 = rng() % max(1, m);
        for (int yy = 0; yy < m && !full(); yy++) { int y = (yy + off1) % m;
            inv(t, F1[y].v, L, [&](u64 x, char op, bool sw) { int i = H1.get(x); if (i >= 0 && i != y) out.push_back(Searcher::join(d1(i), d1(y), op, sw)); return full(); }); }
        // (F1 op p) op q, and (F1 self) op q
        for (int cc = 0; cc < n && !full(); cc++) { int c = (cc + off) % n;
            inv(t, P[c], L, [&](u64 x, char op, bool sw) {
                for (int e = 0; e < n && !full(); e++)
                    inv(x, P[e], L, [&](u64 w, char op2, bool sw2) { int i = H1.get(w); if (i >= 0) out.push_back(Searcher::withPool(Searcher::withPool(d1(i), e, op2, sw2), c, op, sw)); return full(); });
                selfs(x, [&](u64 w, char op2) { int i = H1.get(w); if (i >= 0 && !full()) { Deriv d = d1(i); d.push_back({op2, -1, -1}); out.push_back(Searcher::withPool(d, c, op, sw)); } });
                return full(); }); }
        // self of a 2-step value
        selfs(t, [&](u64 w, char op) {
            if (full()) return;
            for (int c = 0; c < n && !full(); c++)
                inv(w, P[c], L, [&](u64 x, char op2, bool sw2) { int i = H1.get(x); if (i >= 0) { Deriv d = Searcher::withPool(d1(i), c, op2, sw2); int l = -(int)d.size(); d.push_back({op, l, l}); out.push_back(d); } return full(); });
        });
        return out.empty() ? -1 : 3;
    }
    // rough cost estimate of reaching t: 1, 2 or 3 (=3 or more); nv: values just added (not in this pool)
    int est(u64 t, const vector<u64> &nv) const {
        if (HP.get(t) >= 0) return 0;
        for (u64 a : nv) if (a == t) return 0;
        if (H1.get(t) >= 0) return 1;
        for (u64 a : nv) {
            bool hit = inv(t, a, L, [&](u64 x, char, bool) { if (HP.get(x) >= 0) return true; for (u64 b : nv) if (b == x) return true; return false; });
            if (hit) return 1;
        }
        int n = P.size();
        for (int c = 0; c < n; c++) if (inv(t, P[c], L, [&](u64 x, char, bool) { return H1.get(x) >= 0; })) return 2;
        for (u64 a : nv) {
            if (inv(t, a, L, [&](u64 x, char, bool) { return H1.get(x) >= 0; })) return 2;
            for (int c = 0; c < n; c++)
                if (inv(t, P[c], L, [&](u64 x, char, bool) { return inv(x, a, L, [&](u64 w, char, bool) { return HP.get(w) >= 0; }); })) return 2;
        }
        return 3;
    }
};

// ------------------------------------------------------------ beam state
struct St {
    vector<Node> nodes; int ns = 0; vector<int> last;   // last[i] = latest node index that reads node i (-1: never)
    double score = 0; int len() const { return nodes.size() - ns; }
};

static vector<int> occupancy(const St &s) {          // occ[i] for instruction i (node index >= ns): registers busy while writing i
    int N = s.nodes.size(); vector<int> diff(N + 2, 0), occ(N, 0);
    for (int w = 0; w < N; w++) {
        if (s.last[w] < 0) continue;
        int lo = max(s.ns, w + 1), hi = s.last[w] - 1;
        if (lo <= hi) { diff[lo]++; diff[hi + 1]--; }
    }
    int run = 0; for (int i = 0; i < N; i++) { run += diff[i]; occ[i] = run + 1; }
    return occ;
}

static bool addDeriv(St &s, const Deriv &d, const vector<int> &ids, u64 L) {
    int base = s.nodes.size();
    for (auto &st : d) {
        auto tr = [&](int r) { return r >= 0 ? ids[r] : base + (-r - 1); };
        Node nd{st.op, tr(st.a), tr(st.b), 0};
        if (!apply(nd.op, s.nodes[nd.a].v, s.nodes[nd.b].v, L, nd.v) || nd.v == 0) return false;
        int me = s.nodes.size();
        s.nodes.push_back(nd); s.last.push_back(-1);
        s.last[nd.a] = max(s.last[nd.a], me); s.last[nd.b] = max(s.last[nd.b], me);
    }
    auto occ = occupancy(s);
    for (int i = s.ns; i < (int)occ.size(); i++) if (occ[i] > REGS) return false;
    return true;
}

static St prefixState(const Puzzle &pz, const vector<Ins> &given, int keep, vector<u64> &todo) {
    St s; s.ns = pz.starts.size();
    Prog g; toSSA(pz, given, g);
    unordered_set<u64> ts(pz.targets.begin(), pz.targets.end());
    vector<u64> coverOrder; unordered_set<u64> seen(pz.starts.begin(), pz.starts.end());
    for (int i = g.ns; i < (int)g.nodes.size(); i++) if (ts.count(g.nodes[i].v) && seen.insert(g.nodes[i].v).second) coverOrder.push_back(g.nodes[i].v);
    int cut = g.ns, k = 0;
    if (keep > 0) for (int i = g.ns; i < (int)g.nodes.size(); i++) {
        if (ts.count(g.nodes[i].v) && find(coverOrder.begin(), coverOrder.begin() + k, g.nodes[i].v) == coverOrder.begin() + k) {
            if (k == keep) break;
            k++;
        }
        cut = i + 1;
    }
    // keep only what the kept targets need (drop helpers built for later targets: the planner may rebuild them)
    vector<char> need(cut, 0); for (int i = 0; i < g.ns; i++) need[i] = 1;
    if (!DROP) for (int i = 0; i < cut; i++) need[i] = 1;
    vector<int> st; unordered_set<u64> keptT(coverOrder.begin(), coverOrder.begin() + k);
    for (int i = g.ns; i < cut; i++) if (keptT.count(g.nodes[i].v)) st.push_back(i);
    while (!st.empty()) { int x = st.back(); st.pop_back(); if (need[x]) continue; need[x] = 1; st.push_back(g.nodes[x].a); st.push_back(g.nodes[x].b); }
    vector<int> mp(cut, -1);
    for (int i = 0; i < cut; i++) if (need[i]) {
        Node nd = g.nodes[i]; if (nd.op) { nd.a = mp[nd.a]; nd.b = mp[nd.b]; }
        mp[i] = s.nodes.size(); s.nodes.push_back(nd);
    }
    s.last.assign(s.nodes.size(), -1);
    for (int i = s.ns; i < (int)s.nodes.size(); i++) { s.last[s.nodes[i].a] = max(s.last[s.nodes[i].a], i); s.last[s.nodes[i].b] = max(s.last[s.nodes[i].b], i); }
    unordered_set<u64> have; for (auto &nd : s.nodes) have.insert(nd.v);
    todo.clear();
    for (u64 t : coverOrder) if (!have.count(t)) todo.push_back(t);
    for (u64 t : pz.targets) if (!have.count(t) && !seen.count(t) && find(todo.begin(), todo.end(), t) == todo.end()) todo.push_back(t);
    return s;
}

static vector<Ins> beamRun(const Puzzle &pz, const vector<Ins> &given, int keep, bool ascending, mt19937_64 &rng, int bound) {
    vector<u64> todo;
    static bool TR = getenv("TRACE") != nullptr;
    if (TR) fprintf(stderr, "run keep %d\n", keep);
    St s0 = prefixState(pz, given, keep, todo);
    if (TR) fprintf(stderr, "prefix %zu nodes, %zu todo\n", s0.nodes.size(), todo.size());
    if (ascending) sort(todo.begin(), todo.end());
    vector<St> beam{s0};
    Full F; Searcher S;
    for (size_t ti = 0; ti < todo.size(); ti++) {
        u64 t = todo[ti];
        if (TR) fprintf(stderr, " t%zu beam %zu\n", ti, beam.size());
        vector<u64> ahead(todo.begin() + ti + 1, todo.begin() + min(todo.size(), ti + 1 + R));
        vector<St> kids; set<pair<int, u64>> seenKid;
        for (auto &s : beam) {
            bool has = false; for (auto &nd : s.nodes) if (nd.v == t) { has = true; break; }
            if (has) { kids.push_back(s); continue; }
            if (s.len() >= bound) continue;
            // feasible pool: values whose register life can be extended to now
            auto occ = occupancy(s); int N = s.nodes.size();
            vector<int> SM(N + 1, 0); for (int i = N - 1; i >= 0; i--) SM[i] = max(SM[i + 1], i >= s.ns ? occ[i] : 0);
            vector<int> ids; unordered_set<u64> sv;
            for (int w = N - 1; w >= 0; w--) {
                int from = max({s.ns, w + 1, s.last[w]});
                if (from < N && SM[from] >= REGS) continue;
                if (sv.insert(s.nodes[w].v).second) ids.push_back(w);
            }
            vector<u64> pool; for (int i : ids) pool.push_back(s.nodes[i].v);
            F.build(pool, pz.L);
            vector<Deriv> sols; int len = F.find(t, MAXSOL, rng, sols);
            vector<int> sid = ids;               // pool indices for sols
            if (len < 0) {                       // 4-5 steps over the most recent SMALL feasible values, then the deep beam
                vector<int> sub(ids.begin(), ids.begin() + min<int>(ids.size(), SMALL));
                vector<u64> sp; for (int i : sub) sp.push_back(s.nodes[i].v);
                S.build(sp, pz.L); Deriv d;
                bool ok = S.find(t, 5, d);
                if (!ok) { vector<int> sub2(ids.begin(), ids.begin() + min<int>(ids.size(), 100)); sub = sub2; sp.clear(); for (int i : sub) sp.push_back(s.nodes[i].v);
                           ok = beamFind(sp, pz.L, t, 40, BEAMW, d); }
                if (!ok) continue;
                sols = {d}; sid = sub;
            }
            for (auto &d : sols) {
                St c = s;
                if (!addDeriv(c, d, sid, pz.L)) continue;
                vector<u64> nv; for (size_t i = s.nodes.size(); i < c.nodes.size(); i++) nv.push_back(c.nodes[i].v);
                u64 key = 1469598103934665603ULL; { vector<u64> sv2 = nv; sort(sv2.begin(), sv2.end()); for (u64 x : sv2) key = (key ^ x) * 1099511628211ULL; }
                key ^= (u64)(&s - &beam[0]) * 0x9E3779B97F4A7C15ULL;
                if (!seenKid.insert({c.len(), key}).second) continue;
                double h = 0; for (u64 a : ahead) h += F.est(a, nv);
                c.score = c.len() + LAMBDA * h + (rng() % 1000) * 1e-6;
                kids.push_back(move(c));
            }
        }
        if (kids.empty()) return {};
        sort(kids.begin(), kids.end(), [](const St &a, const St &b) { return a.score < b.score; });
        if ((int)kids.size() > W) kids.resize(W);
        beam.swap(kids);
    }
    int bi = 0; for (int i = 1; i < (int)beam.size(); i++) if (beam[i].len() < beam[bi].len()) bi = i;
    Prog p; p.nodes = beam[bi].nodes; p.ns = beam[bi].ns;
    vector<Ins> ins;
    if (!allocate(p, &ins) || validate(pz, ins) < 0) return {};
    return ins;
}

struct Job { function<void()> fn; };
static void *runJob(void *p) { ((Job *)p)->fn(); return nullptr; }

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: beam PUZZLES PROGRAMS OUT SECONDS_PER_PUZZLE THREADS [SEED]\n"); return 1; }
    setvbuf(stderr, nullptr, _IONBF, 0);
    if (getenv("TRACE")) fprintf(stderr, "start\n");
    double secs = atof(argv[4]); int threads = atoi(argv[5]); u64 seed = argc > 6 ? atoll(argv[6]) : 1;
    auto ge = [](const char *k, double d) { return getenv(k) ? atof(getenv(k)) : d; };
    W = ge("W", W); MAXSOL = ge("MAXSOL", MAXSOL); LAMBDA = ge("LAMBDA", LAMBDA); R = ge("R", R); SMALL = ge("SMALL", SMALL);
    BEAMW = ge("BEAMW", BEAMW); KMIN = ge("KMIN", KMIN); KMAX = ge("KMAX", KMAX); DROP = ge("DROP", DROP);
    vector<Puzzle> pz; map<string, int> idx;
    { ifstream f(argv[1]); string id; while (f >> id) { Puzzle p; p.id = id; int ns, nt; f >> p.L >> ns >> nt; p.starts.resize(ns); p.targets.resize(nt);
        for (auto &x : p.starts) f >> x; for (auto &x : p.targets) f >> x; idx[id] = pz.size(); pz.push_back(p); } }
    vector<vector<Ins>> progs(pz.size());
    { ifstream f(argv[2]); string id; while (f >> id) { int n; f >> n; vector<Ins> v(n); for (auto &in : v) { string op; f >> op >> in.a >> in.b >> in.d; in.op = op[0]; } if (idx.count(id)) progs[idx[id]] = v; } }
    vector<vector<Ins>> best = progs; mutex mu; atomic<int> next(0); long before = 0, runs = 0;
    for (auto &p : progs) before += p.size();
    auto dump = [&]() {
        ofstream o(string(argv[3]) + ".tmp");
        for (size_t i = 0; i < pz.size(); i++) if (!best[i].empty()) { o << pz[i].id << " " << best[i].size(); for (auto &in : best[i]) o << " " << in.op << " " << in.a << " " << in.b << " " << in.d; o << "\n"; }
        o.close(); rename((string(argv[3]) + ".tmp").c_str(), argv[3]);
    };
    if (getenv("TRACE")) fprintf(stderr, "cfg W=%d MAXSOL=%d R=%d SMALL=%d LAMBDA=%g DROP=%d KMIN=%g KMAX=%g BEAMW=%d\n", W, MAXSOL, R, SMALL, LAMBDA, DROP, KMIN, KMAX, BEAMW);
    ofstream altf; if (getenv("ALTOUT")) altf.open(getenv("ALTOUT"));
    Job job{[&]() {
        while (true) {
            int i = next++; if (i >= (int)pz.size()) break;
            if (progs[i].empty()) continue;
            mt19937_64 rng(seed * 1000003ULL + i);
            int nt = pz[i].targets.size(); vector<Ins> b = progs[i]; long r = 0; int saved = 0;
            double mysecs = secs * min(2.0, max(0.25, b.size() / 140.0));   // time scales with program size
            auto t0 = chrono::steady_clock::now();
            while (chrono::duration<double>(chrono::steady_clock::now() - t0).count() < mysecs) {
                int keep = max(1, (int)(nt * (KMIN + (KMAX - KMIN) * ((rng() % 1000) / 1000.0))));
                bool asc = rng() % 2;
                auto x = beamRun(pz[i], b, keep, asc, rng, b.size() + (getenv("VERBOSE") || altf.is_open() ? (int)(b.size() * 0.3) : 0));
                r++;
                if (altf.is_open() && !x.empty() && saved++ < 80) {   // every run's program: raw material for recombination
                    lock_guard<mutex> g(mu);
                    altf << pz[i].id << " " << x.size(); for (auto &in : x) altf << " " << in.op << " " << in.a << " " << in.b << " " << in.d; altf << "\n"; altf.flush();
                }
                if (getenv("VERBOSE")) { lock_guard<mutex> g(mu); fprintf(stderr, "  %s keep %d/%d asc %d -> %zu (best %zu)\n", pz[i].id.c_str(), keep, nt, (int)asc, x.size(), b.size()); }
                if (!x.empty() && x.size() < b.size()) {
                    lock_guard<mutex> g(mu);
                    fprintf(stderr, "%s %zu -> %zu (keep %d)\n", pz[i].id.c_str(), b.size(), x.size(), keep);
                    b = x;
                }
            }
            lock_guard<mutex> g(mu); runs += r;
            if (b.size() < best[i].size()) best[i] = b;
            if (i % 10 == 0) dump();
        }
    }};
    vector<pthread_t> th(threads);
    pthread_attr_t at; pthread_attr_init(&at); pthread_attr_setstacksize(&at, (size_t)64 << 20);
    for (auto &t : th) if (pthread_create(&t, &at, runJob, &job)) { fprintf(stderr, "thread create failed\n"); return 1; }
    for (auto &t : th) pthread_join(t, nullptr);
    dump();
    long after = 0; for (auto &p : best) after += p.size();
    fprintf(stderr, "total %ld -> %ld  runs %ld\n", before, after, runs);
}
