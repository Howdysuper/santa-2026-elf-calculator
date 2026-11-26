// Constructive planner: repeatedly build the cheapest remaining target from the current registers.
// Reuses the searcher and allocator from lns.cpp. Output format like lns.
// usage: build PUZZLES OUT THREADS RESTARTS SEED [IDS_FILE]
#define main lns_main
#include "lns.cpp"
#undef main

struct Plan { vector<Node> nodes; int ns; };

// recursive fallback: t = y + r or y*c + r with y the nearest reachable value (pool, F1, F2); r rebuilt recursively
struct Reach { vector<pair<u64, int>> sorted; };   // (value, code): code >=0 pool idx, else -(1+F1 idx) or -(1+|F1|+F2 idx)
static void buildReach(Searcher &S, Reach &R) {
    S.buildF2(); R.sorted.clear(); R.sorted.reserve(S.P.size() + S.F1.size() + S.F2.size());
    for (size_t i = 0; i < S.P.size(); i++) R.sorted.push_back({S.P[i], (int)i});
    for (size_t i = 0; i < S.F1.size(); i++) R.sorted.push_back({S.F1[i].v, -(1 + (int)i)});
    for (size_t i = 0; i < S.F2.size(); i++) R.sorted.push_back({S.F2[i].v, -(1 + (int)S.F1.size() + (int)i)});
    sort(R.sorted.begin(), R.sorted.end());
}
static Deriv codeDeriv(Searcher &S, int code) {
    if (code >= 0) return {};
    int k = -code - 1;
    if (k < (int)S.F1.size()) return S.d1(k);
    return S.d2(k - S.F1.size());
}
static Deriv concat(const Deriv &l, const Deriv &r) {   // append r renumbered; returns l+r
    Deriv d = l; int off = l.size();
    for (auto s : r) { if (s.a < 0) s.a -= off; if (s.b < 0) s.b -= off; d.push_back(s); }
    return d;
}
static int lastRef(const Deriv &d, int poolIdx) { return d.empty() ? poolIdx : -(int)d.size(); }

static bool fallback(Searcher &S, Reach &R, u64 t, int depth, Deriv &out) {
    if (S.find(t, 4, out)) return true;
    if (depth > 12) return false;
    // option A: t = y + r, y = largest reachable <= t
    auto it = upper_bound(R.sorted.begin(), R.sorted.end(), make_pair(t, INT_MAX));
    if (it == R.sorted.begin()) return false;
    --it;
    u64 bestR = t - it->first; int bestCode = it->second; u64 bestC = 0; int bestCi = -1;
    // option B: t = y*c + r for pool value c > 1
    for (size_t ci = 0; ci < S.P.size(); ci++) {
        u64 c = S.P[ci]; if (c < 2) continue;
        u64 qv = t / c;
        auto j = upper_bound(R.sorted.begin(), R.sorted.end(), make_pair(qv, INT_MAX));
        if (j == R.sorted.begin()) continue; --j;
        u64 rr = t - j->first * c;
        if (rr < bestR) { bestR = rr; bestCode = j->second; bestC = c; bestCi = ci; }
    }
    Deriv dy = codeDeriv(S, bestCode);
    int yref = lastRef(dy, bestCode);
    Deriv d = dy;
    if (bestCi >= 0) { d.push_back({'*', yref, bestCi}); yref = -(int)d.size(); }
    if (bestR == 0) { out = d; return !d.empty(); }
    Deriv dr;
    int rpool = S.HP.get(bestR);
    if (rpool < 0 && !fallback(S, R, bestR, depth + 1, dr)) return false;
    Deriv all = concat(d, dr);
    int rref = dr.empty() ? rpool : -(int)all.size();
    all.push_back({'+', yref, rref});
    out = all; return true;
}

static vector<Ins> construct(const Puzzle &pz, mt19937_64 &rng, double noise) {
    Prog p; p.ns = pz.starts.size();
    for (auto s : pz.starts) p.nodes.push_back({0, -1, -1, s});
    set<u64> todo(pz.targets.begin(), pz.targets.end());
    for (auto s : pz.starts) todo.erase(s);
    // simple register model: keep the 48 most recently used node ids
    vector<int> live; for (int i = 0; i < p.ns; i++) live.push_back(i);
    vector<long> lastUse(p.ns, 0); long clock = 1;
    Searcher S;
    while (!todo.empty()) {
        vector<u64> pool; for (int id : live) pool.push_back(p.nodes[id].v);
        S.build(pool, pz.L);
        // cheapest target (k <= 3 scan for all, then deeper for the best few)
        u64 bt = 0; Deriv bd; double bscore = 1e18;
        for (int K = 1; K <= 5 && bscore > 1e17; K++) {
            for (u64 t : todo) {
                Deriv d;
                if (S.find(t, K, d) && (int)d.size() == K) {
                    double sc = d.size() + noise * (rng() % 1000) / 1000.0;
                    if (sc < bscore) { bscore = sc; bt = t; bd = d; }
                }
            }
            if (K == 3 && bscore > 1e17 && todo.size() > 8) {   // only the smallest few targets go deeper
                // keep the search affordable: restrict to 8 random targets
            }
        }
        if (bscore > 1e17) {
            u64 t = *todo.begin();
            Reach R; buildReach(S, R);
            if (!fallback(S, R, t, 0, bd)) return {};
            bt = t;
        }
        // append nodes
        vector<int> ids;
        for (auto &st : bd) {
            auto tr = [&](int r) { return r >= 0 ? live[r] : ids[-r - 1]; };
            Node nd{st.op, tr(st.a), tr(st.b), 0};
            if (!apply(nd.op, p.nodes[nd.a].v, p.nodes[nd.b].v, pz.L, nd.v)) return {};
            lastUse[nd.a] = clock; lastUse[nd.b] = clock; clock++;
            p.nodes.push_back(nd); lastUse.push_back(clock++); ids.push_back(p.nodes.size() - 1);
            live.push_back(p.nodes.size() - 1);
        }
        for (u64 v = 0; v < 1; v++) {}
        todo.erase(bt);
        for (auto &nd : p.nodes) todo.erase(nd.v);
        // dedupe live by value and trim to REGS by least recent use
        { unordered_set<u64> sv; vector<int> nl; for (int k = live.size() - 1; k >= 0; k--) if (sv.insert(p.nodes[live[k]].v).second) nl.push_back(live[k]); live = nl; }
        if ((int)live.size() > REGS) {
            sort(live.begin(), live.end(), [&](int a, int b) { return lastUse[a] > lastUse[b]; });
            live.resize(REGS);
        }
    }
    vector<Ins> ins;
    if (!allocate(p, &ins)) return {};
    if (validate(pz, ins) < 0) return {};
    return ins;
}

int main(int argc, char **argv) {
    if (argc < 6) { fprintf(stderr, "usage: build PUZZLES OUT THREADS RESTARTS SEED [IDS]\n"); return 1; }
    int threads = atoi(argv[3]), restarts = atoi(argv[4]); u64 seed = atoll(argv[5]);
    vector<Puzzle> pz;
    { ifstream f(argv[1]); string id; while (f >> id) { Puzzle p; p.id = id; int ns, nt; f >> p.L >> ns >> nt; p.starts.resize(ns); p.targets.resize(nt);
        for (auto &x : p.starts) f >> x; for (auto &x : p.targets) f >> x; pz.push_back(p); } }
    if (argc > 6) { set<string> keep; ifstream f(argv[6]); string s; while (f >> s) keep.insert(s);
        vector<Puzzle> q; for (auto &p : pz) if (keep.count(p.id)) q.push_back(p); pz = q; }
    vector<vector<Ins>> best(pz.size()); mutex mu; atomic<int> next(0);
    auto dump = [&]() {
        ofstream o(string(argv[2]) + ".tmp");
        for (size_t i = 0; i < pz.size(); i++) if (!best[i].empty()) { o << pz[i].id << " " << best[i].size(); for (auto &in : best[i]) o << " " << in.op << " " << in.a << " " << in.b << " " << in.d; o << "\n"; }
        o.close(); rename((string(argv[2]) + ".tmp").c_str(), argv[2]);
    };
    vector<thread> th;
    for (int t = 0; t < threads; t++) th.emplace_back([&]() {
        while (true) {
            int i = next++; if (i >= (int)pz.size()) break;
            mt19937_64 rng(seed * 7919 + i);
            vector<Ins> b;
            for (int r = 0; r < restarts; r++) {
                auto x = construct(pz[i], rng, r == 0 ? 0.0 : 0.9);
                if (!x.empty() && (b.empty() || x.size() < b.size())) b = x;
            }
            lock_guard<mutex> g(mu); best[i] = b;
            fprintf(stderr, "%s %zu\n", pz[i].id.c_str(), b.size());
            if (i % 10 == 0) dump();
        }
    });
    for (auto &x : th) x.join();
    dump();
}
