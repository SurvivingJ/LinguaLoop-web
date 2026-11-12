import json, sys, math, statistics as st
def pct(xs, p):
    xs = sorted(xs); k = (len(xs)-1)*p/100; f = math.floor(k); c = math.ceil(k)
    return xs[f] if f == c else xs[f] + (xs[c]-xs[f])*(k-f)
def summ(xs):
    return dict(n=len(xs), mean=st.mean(xs), median=st.median(xs), p90=pct(xs,90), p95=pct(xs,95), p99=pct(xs,99), min=min(xs), max=max(xs))
def row(name, s): return f"| {name} | {s['n']} | " + " | ".join(f"{s[k]:.1f}" for k in ('mean','median','p90','p95','p99','min','max')) + " |"
HDR = "| | n | mean | median | p90 | p95 | p99 | min | max |\n|---|---|---|---|---|---|---|---|---|"
if __name__ == '__main__':
    d = json.load(open(sys.argv[1])); key = sys.argv[2] if len(sys.argv) > 2 else None
    print(HDR)
    for k, v in d.items():
        xs = v[key] if key else v
        print(row(k, summ(xs)))
