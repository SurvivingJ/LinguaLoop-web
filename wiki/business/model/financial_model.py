"""LinguaDojo financial model v2 (post red-team). Run: python3 -I wiki/business/model/financial_model.py
Basis: operating P&L by month; cumulative cash INCLUDES lifetime-seat cash when received
(cash basis for lifetime); break-even and ramen months EXCLUDE lifetime cash."""
# ---------- unit economics (A$/month, ex-GST) ----------
SOLO_ARPU_SUB = 0.40*16.35 + 0.45*11.29 + 0.15*7.50
SOLO_ADDON = 0.60; SOLO_FEES = 0.95; SOLO_VAR = 0.75; SOLO_INFRA = 0.08
SCHOOL_ACV = 1700.0; SCHOOL_FEES = 17.0; SCHOOL_VAR = 50.0
TUTOR_ARPU = 54/1.1; TUTOR_FEES = 1.57; TUTOR_VAR = 1.0   # A$39 + 5x A$3, GST-incl, 15 students
PRO_ARPU = 17.50; PRO_FEES = 0.65; PRO_VAR = 3.0
PASS_NET = 79/1.1; PASS_FEES = 1.60; PASS_VAR = 4.0
LIFETIME_NET = 449/1.1*0.95

base = dict(name='base', signups0=400, g1=0.08, g2=0.03, conv=0.03, churn=0.09,
    launch_payers=40, lifetime=25, school_prep=13, school_launch=19,
    schools_by_year={2029: 12}, school_churn=0.15,
    tutor_launch=19, tutor_new=2, tutor_churn=0.05,
    trans_launch=25, trans_new=4, trans_churn=0.05, pass_new=4, var_cac=22.0, arpu_mult=1.0)
cons = dict(base, name='conservative', signups0=200, g1=0.06, g2=0.02, conv=0.02, churn=0.11,
    launch_payers=20, lifetime=10, school_prep=99, school_launch=99, schools_by_year={},
    tutor_launch=99, trans_launch=99, var_cac=28.0)
opt = dict(base, name='optimistic', signups0=600, g1=0.10, g2=0.04, conv=0.045, churn=0.07,
    launch_payers=100, lifetime=60, school_prep=7, school_launch=16,
    schools_by_year={2028: 6, 2029: 30}, school_churn=0.10,
    tutor_launch=13, tutor_new=4, trans_launch=19, trans_new=8, trans_churn=0.04, pass_new=6, var_cac=18.0)
Q_SHARE = {1: .6, 2: .2, 3: .05, 4: .15}
def annual_adds(year, n):
    d = {}
    for moy in range(1, 13):
        q = (moy-1)//3 + 1
        d[(year-2027)*12 + moy] = n*Q_SHARE[q]/3
    return d
def merge(*ds):
    out = {}
    for d in ds:
        for k, v in d.items(): out[k] = out.get(k, 0) + v
    return out

def fixed_cost(m, schools, payers, s):
    f = 1750.0                         # Y1 base incl. A$150 contingency/contractor cover
    if m > 12: f += 300
    if m > 24: f += 400
    f += SOLO_INFRA*payers
    one = 0.0
    if m == 1: one += 3000             # AI content gap fill zh/ja/en
    if 1 <= m <= 6: one += 7000/6      # native QA of core catalogue + answer explanations
    if m == 2: one += 2000             # Children's Online Privacy Code / age-gate legal review
    p = s['school_prep']
    if p <= m <= p+5: one += 10000/6
    if m == p+2: one += 5000
    if m == p+3: one += 7500
    if m == p+27: one += 7500
    if m >= s['school_launch']: f += 875
    if schools >= 25: f += 500
    t = s['trans_launch']
    if t-3 <= m <= t-1: one += s.get('trans_oneoff', 8000)/3
    if m >= t: f += s.get('trans_fixed', 650)
    if m > s.get('cut_month', 999): f -= s.get('cut_amount', 0)
    return f, one

def run(s, horizon=36):
    signups = s['signups0']; payers = schools = tutors = trans = 0.0
    cum = 0.0; rows = []; cum_min = 0.0; be = ramen = None; trough_m = 0
    for m in range(1, horizon+1):
        year = 2027 + (m-1)//12; moy = (m-1) % 12 + 1; q = (moy-1)//3 + 1
        if m > 1: signups *= (1+s['g1']) if m <= 24 else (1+s['g2'])
        new = signups*s['conv'] + (s['launch_payers']/3 if m <= 3 else 0)
        payers = payers*(1-s['churn']) + new
        add = s.get('school_adds', {}).get(m, 0.0)
        if moy == 1 and m > 12: schools *= (1-s['school_churn'])
        schools += add
        if m >= s['tutor_launch']: tutors = tutors*(1-s['tutor_churn']) + s['tutor_new']
        if m >= s['trans_launch']: trans = trans*(1-s['trans_churn']) + s['trans_new']
        passes = s['pass_new'] if m >= s['trans_launch'] else 0
        life_cash = (s['lifetime']/6)*LIFETIME_NET if m <= 6 else 0
        life_users = s['lifetime']*min(m, 6)/6
        am = s['arpu_mult']
        rev_rec = payers*(SOLO_ARPU_SUB*am+SOLO_ADDON) + schools*SCHOOL_ACV*am/12 + tutors*TUTOR_ARPU*am \
                  + trans*PRO_ARPU*am + passes*PASS_NET*am
        mrr = payers*(SOLO_ARPU_SUB*am+SOLO_ADDON) + schools*SCHOOL_ACV*am/12 + tutors*TUTOR_ARPU*am + trans*PRO_ARPU*am
        var = payers*(SOLO_FEES+SOLO_VAR) + life_users*SOLO_VAR + schools*(SCHOOL_FEES+SCHOOL_VAR)/12 \
              + tutors*(TUTOR_FEES+TUTOR_VAR) + trans*(PRO_FEES+PRO_VAR) + passes*(PASS_FEES+PASS_VAR)
        acq = new*s['var_cac'] + (s['tutor_new']*50 if m >= s['tutor_launch'] else 0) \
              + ((s['trans_new']+passes)*30 if m >= s['trans_launch'] else 0)
        f, one = fixed_cost(m, schools, payers, s)
        rev = rev_rec + life_cash; cost = var+acq+f+one; net = rev-cost
        cum += net
        if cum < cum_min: cum_min = cum; trough_m = m
        op = rev_rec - (var+acq+f)
        if be is None and m > 3 and op >= 0: be = m
        if ramen is None and op >= 7467: ramen = m
        rows.append(dict(m=m, year=year, q=q, payers=payers, schools=schools, tutors=tutors, trans=trans,
                         mrr=mrr, rev=rev, cost=cost, net=net, cum=cum, op=op))
    return rows, dict(be=be, ramen=ramen, trough=cum_min, trough_m=trough_m, cum36=cum,
                      mrr36=rows[-1]['mrr'], payers36=rows[-1]['payers'])

def quarterly(rows):
    out = []
    for i in range(0, len(rows), 3):
        r = rows[i:i+3]; l = r[-1]
        out.append(dict(label=f"Q{l['q']}'{str(l['year'])[2:]}", payers=l['payers'], schools=l['schools'],
            tutors=l['tutors'], trans=l['trans'], mrr=l['mrr'], rev=sum(x['rev'] for x in r),
            cost=sum(x['cost'] for x in r), net=sum(x['net'] for x in r), cum=l['cum']))
    return out

base = dict(base, school_prep=19, school_launch=25, school_adds={31: 1, 32: 1, 34: 1},
    tutor_launch=13, tutor_new=2, trans_launch=31, trans_oneoff=4000, trans_fixed=250, trans_new=4, pass_new=4)
cons = dict(base, name='conservative', signups0=200, g1=0.06, g2=0.02, conv=0.02, churn=0.11,
    launch_payers=20, lifetime=10, school_prep=99, school_launch=99, school_adds={},
    tutor_launch=13, tutor_new=1, trans_launch=99, var_cac=28.0, cut_month=6, cut_amount=780)
opt = dict(base, name='optimistic', signups0=600, g1=0.10, g2=0.04, conv=0.045, churn=0.07,
    launch_payers=100, lifetime=60, school_prep=7, school_launch=13,
    school_adds=merge({19: 1, 20: 1, 22: 1, 23: 1}, annual_adds(2029, 20)), school_churn=0.10,
    tutor_launch=13, tutor_new=4, trans_launch=19, trans_oneoff=8000, trans_fixed=650,
    trans_new=8, trans_churn=0.04, pass_new=6, var_cac=18.0)

if __name__ == '__main__':
    print('solo contrib', round(SOLO_ARPU_SUB+SOLO_ADDON-SOLO_FEES-SOLO_VAR-SOLO_INFRA, 2))
    for s in (cons, base, opt):
        rows, sm = run(s)
        print('\n==', s['name'], {k: (round(v) if isinstance(v, float) else v) for k, v in sm.items()})
        for y in (2027, 2028, 2029):
            yr = [r for r in rows if r['year'] == y]
            print(y, 'rev', round(sum(r['rev'] for r in yr)), 'cost', round(sum(r['cost'] for r in yr)))
        first175 = next((r['m'] for r in rows if r['payers'] >= 175), None)
        print('payers M6', round(rows[5]['payers']), 'M12', round(rows[11]['payers']), 'first>=175', first175)
        print('| Qtr | Solo payers | Schools | Tutors | Translators | MRR end | Revenue | Costs | Net | Cumulative cash |')
        print('|---|---|---|---|---|---|---|---|---|---|')
        for q in quarterly(rows):
            print(f"| {q['label']} | {q['payers']:,.0f} | {q['schools']:.0f} | {q['tutors']:.0f} | {q['trans']:.0f} | {q['mrr']:,.0f} | {q['rev']:,.0f} | {q['cost']:,.0f} | {q['net']:,.0f} | {q['cum']:,.0f} |")
    _, b = run(base)
    print('\n== sensitivity (base)', round(b['cum36']), round(b['trough']), b['be'], b['ramen'])
    tests = {'churn 7%': dict(churn=0.07), 'churn 11%': dict(churn=0.11),
        'conv 2%': dict(conv=0.02), 'conv 4%': dict(conv=0.04),
        'g1 6%': dict(g1=0.06), 'g1 10%': dict(g1=0.10),
        'signups 250': dict(signups0=250), 'signups 600': dict(signups0=600),
        'ARPU -15%': dict(arpu_mult=0.85), 'ARPU +15%': dict(arpu_mult=1.15),
        'schools off': dict(school_prep=99, school_launch=99, school_adds={}),
        'trans off': dict(trans_launch=99), 'trans full A$8k/650': dict(trans_oneoff=8000, trans_fixed=650),
        'tutors x2': dict(tutor_new=4), 'cons no cut': dict(),
        'CAC x2': dict(var_cac=44), 'lifetime 0': dict(lifetime=0)}
    for k, v in tests.items():
        _, r = run(dict(base, **v))
        print(f"{k:12s} cum36 {r['cum36']:>9,.0f} d {r['cum36']-b['cum36']:>9,.0f} trough {r['trough']:>8,.0f} be {r['be']} ramen {r['ramen']} mrr36 {r['mrr36']:,.0f}")
