// hubs.cpp - hidden atom ("hub") scan. For each puzzle and each h in [HMIN, HMAX), count targets T >= h^2/8 with
// min(T mod h, h - T mod h) <= E (structured targets are k*M + c with h | M and |c| small). Score = z-score vs chance.
// Output per puzzle: id then the top K hubs as h:count:z, after removing multiples/near-duplicates of better hubs.
// usage: hubs PUZZLES IDS(- for all) OUT [E=2600] [K=12] [THREADS=8]
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64;
int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage\n"); return 1; }
    u64 E = argc > 4 ? atoll(argv[4]) : 2600; int K = argc > 5 ? atoi(argv[5]) : 12; int TH = argc > 6 ? atoi(argv[6]) : 8;
    const u64 HMIN = 1 << 13, HMAX = 1 << 23;
    vector<pair<string, vector<u64>>> P; set<string> want;
    if (string(argv[2]) != "-") { ifstream f(argv[2]); string s; while (f >> s) want.insert(s); }
    { ifstream f(argv[1]); string line;
      while (getline(f, line)) { istringstream ss(line); string id; u64 L; int ns, nt; ss >> id >> L >> ns >> nt; vector<u64> st(ns), t(nt);
        for (auto &x : st) ss >> x; for (auto &x : t) ss >> x; if (want.empty() || want.count(id)) P.push_back({id, t}); } }
    vector<string> out(P.size()); atomic<int> nx(0);
    auto work = [&]() {
        vector<int> cnt(HMAX); vector<double> ex(HMAX);
        while (true) {
            int k = nx++; if (k >= (int)P.size()) break;
            auto &T = P[k].second;
            fill(cnt.begin(), cnt.end(), 0); fill(ex.begin(), ex.end(), 0.0);
            for (u64 t : T) {
                long double rt = sqrtl((long double)t * 8);
                u64 hmax = min<u64>(HMAX, (u64)rt + 1);
                for (u64 h = HMIN; h < hmax; h++) {
                    u64 r = t % h; u64 m = min(r, h - r);
                    if (m <= E) cnt[h]++;
                    ex[h] += (2.0 * E + 1) / h;
                }
            }
            vector<pair<double, u64>> sc;
            for (u64 h = HMIN; h < HMAX; h++) if (cnt[h] >= 3) { double z = (cnt[h] - ex[h]) / sqrt(ex[h] + 0.5); if (z > 4) sc.push_back({z, h}); }
            sort(sc.rbegin(), sc.rend());
            vector<pair<u64, pair<int, double>>> pick;
            for (auto &[z, h] : sc) {
                bool dup = false;
                for (auto &p : pick) { u64 a = p.first; if (h % a == 0 || a % h == 0 || (h > a ? h - a : a - h) * 2000 < a) { dup = true; break; } }
                if (dup) continue;
                pick.push_back({h, {cnt[h], z}}); if ((int)pick.size() >= K) break;
            }
            string s = P[k].first;
            for (auto &p : pick) { char b[96]; snprintf(b, sizeof b, " %llu:%d:%.1f", (unsigned long long)p.first, p.second.first, p.second.second); s += b; }
            out[k] = s;
        }
    };
    vector<thread> th; for (int t = 0; t < TH; t++) th.emplace_back(work); for (auto &t : th) t.join();
    ofstream o(argv[3]); for (auto &s : out) o << s << "\n";
}
