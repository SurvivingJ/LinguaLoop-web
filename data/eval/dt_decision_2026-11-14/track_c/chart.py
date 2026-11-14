# -*- coding: utf-8 -*-
"""Static SVG: cascade-3 escalation rate vs mean QWK (gold), base = jev alone, order = jev margin vs random."""
import json
r = json.load(open("results.json"))
W, H, PW, PH, L, TOP = 900, 330, 240, 200, 60, 70
BLUE, ORANGE, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#0b0b0b", "#52514e", "#e4e3df"
s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="system-ui,sans-serif" font-size="12">',
     f'<rect width="{W}" height="{H}" fill="#fcfcfb"/>',
     f'<text x="{L}" y="24" font-size="15" font-weight="600" fill="{INK}">Escalating jev-uncertain items to the live grader barely beats random order (gold, n=30/language)</text>',
     f'<line x1="{L}" y1="44" x2="{L+24}" y2="44" stroke="{BLUE}" stroke-width="2"/><text x="{L+30}" y="48" fill="{MUTED}">most jev-uncertain first (probability margin)</text>',
     f'<line x1="{L+330}" y1="44" x2="{L+354}" y2="44" stroke="{ORANGE}" stroke-width="2" stroke-dasharray="5 4"/><text x="{L+360}" y="48" fill="{MUTED}">random order (mean of 200 shuffles)</text>']
y0, y1 = 0.3, 0.9
for pi, lang in enumerate(("en", "zh", "ja")):
    x = L + pi * (PW + 45)
    X = lambda v: x + v * PW
    Y = lambda v: TOP + PH - (v - y0) / (y1 - y0) * PH
    for g in (0.3, 0.5, 0.7, 0.9):
        s.append(f'<line x1="{x}" y1="{Y(g):.1f}" x2="{x+PW}" y2="{Y(g):.1f}" stroke="{GRID}"/>')
        if pi == 0:
            s.append(f'<text x="{x-8}" y="{Y(g)+4:.1f}" text-anchor="end" fill="{MUTED}">{g:.1f}</text>')
    for g in (0, 0.5, 1):
        s.append(f'<text x="{X(g):.1f}" y="{TOP+PH+18}" text-anchor="middle" fill="{MUTED}">{int(g*100)}%</text>')
    c = r["langs"][lang]["c3"]["jev|margin"]["curve"]
    for key, col, dash in (("random_mean_qwk", ORANGE, ' stroke-dasharray="5 4"'), ("mean_qwk", BLUE, "")):
        pts = " ".join(f"{X(p['rate']):.1f},{Y(p[key]):.1f}" for p in c)
        s.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2"{dash}/>')
    s.append(f'<text x="{x}" y="{TOP-8}" font-weight="600" fill="{INK}">{lang}</text>')
    s.append(f'<text x="{X(0)+4:.1f}" y="{Y(c[0]["mean_qwk"])-8:.1f}" fill="{MUTED}">jev alone {c[0]["mean_qwk"]:.2f}</text>')
    s.append(f'<text x="{X(1):.1f}" y="{Y(c[-1]["mean_qwk"])+16:.1f}" text-anchor="end" fill="{MUTED}">live grader {c[-1]["mean_qwk"]:.2f}</text>')
s.append(f'<text x="{L}" y="{H-8}" fill="{MUTED}">x: share of items escalated · y: mean of accuracy/fidelity/understandability QWK · differences under ~0.1 are noise</text></svg>')
open("escalation_curve.svg", "w").write("\n".join(s))
