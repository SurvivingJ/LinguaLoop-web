import json
r = json.load(open("results.json")); L = r["langs"]
f3 = lambda x: "n/a" if x != x else f"{x:.3f}"
f2 = lambda x: "n/a" if x != x else f"{x:.2f}"
out = []
names = [("jev_alone", "jev alone (Sept frozen)"), ("live_grader_recorded", "live grader (recorded 2026-10-08)"), ("llm_pair_alone", "cheap LLM alone, per changed sentence"),
         ("c1_frozen", "C1 jev gate → LLM"), ("c2_frozen", "C2 LLM recall pass → (jev verify)"), ("c2_verified_frozen", "C2 with jev verifier forced on")]
out.append("### T1\n")
out.append("| L2 | pipeline (silver-frozen config) | acc | fid | und | mean | P | R | minor R | sev exact | subtype | changed sentences to stage 2 | $/item | latency p50 / p95 (s) |")
out.append("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for l in ("en", "zh", "ja"):
    for k, nm in names:
        m = L[l][k]; q = m["qwk"]; d = m["detect"]; c = m["cfg"]
        cs = ", ".join(f"{a}={b}" for a, b in c.items()) if c else ""
        out.append(f"| {l} | {nm}{' — ' + cs if cs else ''} | {f3(q['accuracy'])} | {f3(q['fidelity'])} | {f3(q['understandability'])} | **{f3(m['mean_qwk'])}** | {f2(d['precision'])} | {f2(d['recall'])} | {f2(d['minor_recall'])} | {f2(m['severity_exact'])} | {f2(m['subtype_acc'])} | {m['pct_diff_pairs_stage2']:.0%} | {m['usd_per_item']:.6f} | {m['lat_p50']:.2f} / {m['lat_p95']:.2f} |")
out.append("\n### T2\n")
out.append("| L2 | gate (escalate if jev signal ≥) | changed sentences escalated | all sentences escalated | items with a stage-2 call | P | R | minor R | sev exact | mean QWK | $/item | latency p50 / p95 (s) |")
out.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
for l in ("en", "zh", "ja"):
    for x in L[l]["c1_gate_curve"]:
        g = "jev-flagged only" if x["gate"] == "flag" else x["gate"]
        out.append(f"| {l} | {g}{' **(frozen)**' if x['is_frozen'] else ''} | {x['pct_diff_pairs_stage2']:.0%} | {x['pct_all_pairs_stage2']:.0%} | {x['pct_items_stage2']:.0%} | {f2(x['precision'])} | {f2(x['recall'])} | {f2(x['minor_recall'])} | {f2(x['severity_exact'])} | {f3(x['mean_qwk'])} | {x['usd_per_item']:.6f} | {x['lat_p50']:.2f} / {x['lat_p95']:.2f} |")
out.append("\n### T3\n")
out.append("| L2 | verifier | τ_v | P | R | minor R | mean QWK | $/item |")
out.append("|---|---|---|---|---|---|---|---|")
for l in ("en", "zh", "ja"):
    for x in L[l]["c2_verify_curve"]:
        if x["verify"] == "pair_sig" and x["tau_v"] == 0: continue
        v = "none" if x["tau_v"] == 0 else ("claim-specific jev yes/no" if x["verify"] == "claim" else "Sept per-sentence jev signal")
        out.append(f"| {l} | {v} | {x['tau_v']} | {f2(x['precision'])} | {f2(x['recall'])} | {f2(x['minor_recall'])} | {f3(x['mean_qwk'])} | {x['usd_per_item']:.6f} |")
out.append("\n### T4\n")
out.append("| L2 | items escalated | mean QWK, most-uncertain first | mean QWK, random order | acc / fid / und | $/item | latency p50 / p95 (s) |")
out.append("|---|---|---|---|---|---|---|")
for l in ("en", "zh", "ja"):
    for x in L[l]["c3"]["jev|margin"]["curve"]:
        if x["k"] % 6: continue
        q = x["qwk"]
        out.append(f"| {l} | {x['rate']:.0%} | {f3(x['mean_qwk'])} | {f3(x['random_mean_qwk'])} | {f2(q['accuracy'])} / {f2(q['fidelity'])} / {f2(q['understandability'])} | {x['usd_per_item']:.5f} | {x['lat_p50']:.1f} / {x['lat_p95']:.1f} |")
out.append("\n### T4b\n")
out.append("| L2 | base | uncertainty score | silver-frozen threshold → gold items escalated | gold mean QWK at that point | base alone | $/item |")
out.append("|---|---|---|---|---|---|---|")
for l in ("en", "zh", "ja"):
    for k, v in L[l]["c3"].items():
        b, kind = k.split("|"); fp = v["frozen_point"]
        out.append(f"| {l} | {'jev alone' if b=='jev' else 'C1 frozen'} | {kind} | {fp['rate']:.0%} | {f3(fp['mean_qwk'])} | {f3(v['curve'][0]['mean_qwk'])} | {fp['usd_per_item']:.5f} |")
out.append("\n### T5\n")
out.append("| pipeline (per-language frozen configs, pooled n=90) | acc | fid | und | mean QWK [95% CI] | Δ vs jev alone [95% CI] | Δ vs live [95% CI] | $/item |")
out.append("|---|---|---|---|---|---|---|---|")
for k, o in r["pooled_n90"].items():
    out.append(f"| {k} | {f3(o['qwk']['accuracy'])} | {f3(o['qwk']['fidelity'])} | {f3(o['qwk']['understandability'])} | {f3(o['mean_qwk'])} [{o['ci95'][0]:.2f}, {o['ci95'][1]:.2f}] | {o['diff_vs_jev'][0]:+.3f} [{o['diff_vs_jev'][1]:+.2f}, {o['diff_vs_jev'][2]:+.2f}] | {o['diff_vs_live'][0]:+.3f} [{o['diff_vs_live'][1]:+.2f}, {o['diff_vs_live'][2]:+.2f}] | {o['usd_per_item']:.6f} |")
out.append("\n### T6\n")
out.append("| config (post-hoc, same for all languages) | silver en | silver zh | silver ja | gold en | gold zh | gold ja |")
out.append("|---|---|---|---|---|---|---|")
for k, d in r["posthoc_not_frozen"].items():
    out.append(f"| {k} | " + " | ".join(f2(d[s][l]["mean_qwk"]) for s in ("silver", "gold") for l in ("en", "zh", "ja")) + " |")
out.append("\n### T7\n")
out.append("| L2 | comparison (mean QWK) | Δ | 95% CI (paired bootstrap) |")
out.append("|---|---|---|---|")
for l in ("en", "zh", "ja"):
    for k, v in L[l]["paired_bootstrap_mean_qwk"].items():
        if "verified" in k: continue
        out.append(f"| {l} | {k.replace('__minus__', ' − ')} | {v['mean_diff']:+.3f} | [{v['ci95'][0]:+.2f}, {v['ci95'][1]:+.2f}] |")
open("tables.md", "w").write("\n".join(out))
