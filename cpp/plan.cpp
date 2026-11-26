// From-scratch planner: targets in ascending order; each one by the shortest exact derivation (<= 5 steps)
// from every value built so far, else the backward beam (deep). Reuses the searcher and allocator of lns.cpp.
// usage: plan PUZZLES OUT THREADS [POOLCAP] [IDS_FILE]
#define main lns_main
#include "lns.cpp"
#undef main

static int POOLCAP = 200;

static int KEEP = 0;   // keep the given program up to (and including) the cover of its KEEP-th target
static vector<Ins> plan(const Puzzle &pz, const vector<Ins> &given, int &ssaLen) {
    Prog p; p.ns = pz.starts.size();
    for (auto s : pz.starts) p.nodes.push_back({0, -1, -1, s});
    if (KEEP > 0 && !given.empty()) {
        Prog g; if (!toSSA(pz, given, g)) { ssaLen = -1; return {}; }
        unordered_set<u64> ts(pz.targets.begin(), pz.targets.end()), seen(pz.starts.begin(), pz.starts.end());
        int k = 0, cut = g.ns;
        for (int i = g.ns; i < (int)g.nodes.size() && k < KEEP; i++) { if (ts.count(g.nodes[i].v) && seen.insert(g.nodes[i].v).second) k++; cut = i + 1; }
        p.nodes.assign(g.nodes.begin(), g.nodes.begin() + cut);
    }
    unordered_map<u64, int> have; for (int i = 0; i < (int)p.nodes.size(); i++) have.emplace(p.nodes[i].v, i);
    vector<u64> T = pz.targets; sort(T.begin(), T.end());
    Searcher S;
    for (u64 t : T) {
        if (have.count(t)) continue;
        vector<int> ids;                          // pool: starts + most recent values, deduped
        { unordered_set<u64> seen;
          for (int i = 0; i < p.ns; i++) if (seen.insert(p.nodes[i].v).second) ids.push_back(i);
          for (int i = (int)p.nodes.size() - 1; i >= p.ns && (int)ids.size() < POOLCAP; i--) if (seen.insert(p.nodes[i].v).second) ids.push_back(i); }
        vector<u64> pool; for (int i : ids) pool.push_back(p.nodes[i].v);
        S.build(pool, pz.L);
        Deriv d;
        bool ok = S.find(t, 5, d);
        if (!ok) ok = beamFind(pool, pz.L, t, 40, BEAMW, d);
        if (!ok) { ssaLen = -1; return {}; }
        int base = p.nodes.size();
        for (auto &st : d) {
            auto tr = [&](int r) { return r >= 0 ? ids[r] : base + (-r - 1); };
            Node nd{st.op, tr(st.a), tr(st.b), 0};
            if (!apply(nd.op, p.nodes[nd.a].v, p.nodes[nd.b].v, pz.L, nd.v)) { ssaLen = -1; return {}; }
            p.nodes.push_back(nd); have.emplace(nd.v, p.nodes.size() - 1);
        }
    }
    ssaLen = p.nodes.size() - p.ns;
    vector<Ins> ins;
    if (!allocate(p, &ins) || validate(pz, ins) < 0) return {};
    return ins;
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: plan PUZZLES OUT THREADS [POOLCAP] [IDS]\n"); return 1; }
    int threads = atoi(argv[3]); if (argc > 4) POOLCAP = atoi(argv[4]); if (getenv("BEAMW")) BEAMW = atoi(getenv("BEAMW")); if (getenv("KEEP")) KEEP = atoi(getenv("KEEP"));
    vector<Puzzle> pz;
    { ifstream f(argv[1]); string id; while (f >> id) { Puzzle p; p.id = id; int ns, nt; f >> p.L >> ns >> nt; p.starts.resize(ns); p.targets.resize(nt);
        for (auto &x : p.starts) f >> x; for (auto &x : p.targets) f >> x; pz.push_back(p); } }
    if (argc > 5) { set<string> keep; ifstream f(argv[5]); string s; while (f >> s) keep.insert(s);
        vector<Puzzle> q; for (auto &p : pz) if (keep.count(p.id)) q.push_back(p); pz = q; }
    map<string, vector<Ins>> given;
    if (getenv("PROGS")) { ifstream f(getenv("PROGS")); string id; while (f >> id) { int n; f >> n; vector<Ins> v(n); for (auto &in : v) { string op; f >> op >> in.a >> in.b >> in.d; in.op = op[0]; } given[id] = v; } }
    vector<vector<Ins>> best(pz.size()); mutex mu; atomic<int> next(0);
    vector<thread> th;
    for (int t = 0; t < threads; t++) th.emplace_back([&]() {
        while (true) {
            int i = next++; if (i >= (int)pz.size()) break;
            vector<Ins> gv; { lock_guard<mutex> g(mu); if (given.count(pz[i].id)) gv = given[pz[i].id]; }
            int ssa = 0; auto b = plan(pz[i], gv, ssa);
            lock_guard<mutex> g(mu); best[i] = b;
            fprintf(stderr, "%s ssa %d prog %zu given %zu\n", pz[i].id.c_str(), ssa, b.size(), gv.size());
        }
    });
    for (auto &x : th) x.join();
    ofstream o(argv[2]);
    for (size_t i = 0; i < pz.size(); i++) if (!best[i].empty()) { o << pz[i].id << " " << best[i].size(); for (auto &in : best[i]) o << " " << in.op << " " << in.a << " " << in.b << " " << in.d; o << "\n"; }
}
