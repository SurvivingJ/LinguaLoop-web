"""Generate name studies: two marks + palettes per candidate name, with phone mockups of the app.

Run: python3 wiki/design/brand/gen_names.py
Writes name-studies.html and names/<slug>/<dir>-{mark,app-icon}.svg next to this file.
"""
import html
import itertools
import os

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUT}/names", exist_ok=True)
_uid = itertools.count()


# ---------------------------------------------------------------- marks (viewBox 0 0 100 100)
def m_courses(c):  # Linguatim A: an L laid like courses of text, foot in accent
    bars = "".join(f'<rect x="26" y="{y}" width="20" height="12" rx="1" fill="{c["ink"]}"/>' for y in (10, 26, 42, 58))
    return bars + f'<rect x="26" y="74" width="50" height="12" rx="1" fill="{c["acc"]}"/>'


def m_lt(c):  # Linguatim B: lt ligature, crossbar in accent
    return (f'<path d="M30 10 V70 Q30 86 46 86" fill="none" stroke="{c["ink"]}" stroke-width="11" stroke-linecap="butt"/>'
            f'<path d="M64 20 V70 Q64 86 80 86" fill="none" stroke="{c["ink"]}" stroke-width="11"/>'
            f'<path d="M44 38 H86" stroke="{c["acc"]}" stroke-width="10"/>')


def m_polish(c):  # Labor Limae A: handwritten loops worked down into one clean line
    return (f'<path d="M6 62 C 14 62, 22 50, 22 34 C 22 22, 12 24, 14 38 C 16 52, 26 62, 34 60 C 40 58, 42 48, 40 42 '
            f'C 38 36, 32 40, 36 50 C 39 58, 46 62, 52 60 C 56 59, 57 54, 55 52 C 53 50, 50 54, 54 58 C 57 61, 62 61, 66 61 H 82" '
            f'fill="none" stroke="{c["ink"]}" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="89" cy="61" r="6.5" fill="{c["acc"]}"/>')


def m_ll(c):  # Labor Limae B: two Ls turned into each other
    return (f'<path d="M12 12 H31 V69 H62 V88 H12 Z" fill="{c["ink"]}"/>'
            f'<path d="M88 88 H69 V31 H38 V12 H88 Z" fill="{c["acc"]}"/>')


def m_arch(c):  # LinguaDojo A: the D turned into a doorway, an L on the threshold
    return (f'<path d="M20 92 V48 A30 30 0 0 1 80 48 V92" fill="none" stroke="{c["ink"]}" stroke-width="10"/>'
            f'<path d="M41 52 V77 H63" fill="none" stroke="{c["acc"]}" stroke-width="9"/>')


def _ld_core(c, s=1.0, dx=0, dy=0):
    return (f'<g transform="translate({dx} {dy}) scale({s})">'
            f'<path d="M25 8.5 V86 H47 A36 36 0 0 0 47 14" fill="none" stroke="{c["ink"]}" stroke-width="11"/></g>')


def m_badge(c):  # LinguaDojo B: the motto struck around the monogram, like a coin
    i = next(_uid)
    return (f'<defs><path id="motto-{i}" d="M50 50 m-37 0 a37 37 0 1 1 74 0 a37 37 0 1 1 -74 0"/></defs>'
            f'<circle cx="50" cy="50" r="47" fill="none" stroke="{c["acc"]}" stroke-width="3"/>'
            f'<circle cx="50" cy="50" r="27" fill="none" stroke="{c["acc"]}" stroke-width="1.5"/>'
            f'<text font-family="Gloock, Georgia, serif" font-size="9.6" letter-spacing="1.5" fill="{c["ink"]}">'
            f'<textPath href="#motto-{i}" startOffset="0">USUS · MAGISTER · OPTIMUS ·</textPath></text>'
            + _ld_core(c, 0.42, 29.5, 29))


def m_badge_icon(c):
    return _ld_core(c, 0.86, 5, 7)


def m_square(c):  # Lingwright A: a try-square (an L that measures)
    ticks = "".join(
        f'<rect x="{x}" y="70" width="2.6" height="{7 if k % 2 else 10}" fill="{c["bg"]}"/>'
        for k, x in enumerate(range(42, 88, 7)))
    return (f'<rect x="14" y="12" width="20" height="76" rx="2" fill="{c["acc"]}"/>'
            f'<circle cx="24" cy="26" r="2.6" fill="{c["bg"]}"/><circle cx="24" cy="56" r="2.6" fill="{c["bg"]}"/>'
            f'<rect x="34" y="70" width="56" height="14" fill="{c["ink"]}"/>' + ticks)


def m_dovetail(c):  # Lingwright B: a dovetail joint, two pieces locked together
    tails = [((44, 27), (63, 19), (63, 45), (44, 37)), ((44, 63), (63, 55), (63, 81), (44, 73))]
    out = f'<rect x="46" y="14" width="40" height="72" fill="{c["acc"]}"/><rect x="14" y="14" width="30" height="72" fill="{c["ink"]}"/>'
    for t in tails:
        pts = " ".join(f"{x},{y}" for x, y in t)
        out += f'<polygon points="{pts}" fill="{c["ink"]}" stroke="{c["bg"]}" stroke-width="2.5" stroke-linejoin="miter"/>'
        out += f'<rect x="40" y="{t[0][1] + 1.5}" width="5.5" height="{t[3][1] - t[0][1] - 3}" fill="{c["ink"]}"/>'
    return out


def m_e_acute(c):  # Étude A: É, the acute accent as the teacher's mark
    return (f'<path d="M22 28 H76 V40 H38 V51 H68 V63 H38 V76 H78 V88 H22 Z" fill="{c["ink"]}"/>'
            f'<polygon points="42,22 54,22 72,5 58,5" fill="{c["acc"]}"/>')


def m_repeat(c):  # Étude B: the repeat sign, practice as a loop
    return (f'<rect x="20" y="12" width="15" height="76" fill="{c["ink"]}"/>'
            f'<rect x="43" y="12" width="6" height="76" fill="{c["ink"]}"/>'
            f'<circle cx="66" cy="38" r="8" fill="{c["acc"]}"/><circle cx="66" cy="62" r="8" fill="{c["acc"]}"/>')


# ---------------------------------------------------------------- palettes / names
def ui(bg, surface, ink, muted, line, acc, acc_ink, hi, good, bad, dark=False):
    return dict(bg=bg, surface=surface, ink=ink, muted=muted, line=line, acc=acc,
                acc_ink=acc_ink, hi=hi, good=good, bad=bad, dark=dark)


NAMES = [
    dict(slug="linguatim", name="Linguatim", say="lin-GWAH-tim", origin="Round one · coined Latin",
         means="“Language by language,” built like verbatim (word by word) and gradatim (step by step).",
         tagline="Language, step by step.",
         domains=".app and .io free · .com registered March 2026",
         dirs=[
             dict(key="a", title="Courses", palette="Lapis & Limestone", font="Instrument Sans",
                  fam="'Instrument Sans', 'Helvetica Neue', sans-serif", wstyle="font-weight:600;letter-spacing:-0.03em",
                  word="linguatim", mark=m_courses,
                  why="An L laid in courses, like lines of text stacked one on another, with the foot in gold. Each block is one day's work.",
                  sw=[("Lapis", "#22397A"), ("Limestone", "#ECE8DE"), ("Gold fleck", "#C9A23F")],
                  tile=dict(bg="#ECE8DE", ink="#22397A", acc="#C9A23F"),
                  icon=dict(bg="#22397A", ink="#ECE8DE", acc="#C9A23F"),
                  ui=ui("#ECE8DE", "#F8F5EE", "#1B2340", "#5E6276", "#D8D2C4", "#22397A", "#F4F1E8", "#A9842A", "#2F7A4F", "#B23A2E")),
             dict(key="b", title="Ligature", palette="Juniper & Frost", font="Literata",
                  fam="'Literata', Georgia, serif", wstyle="font-weight:600;letter-spacing:-0.01em",
                  word="Linguatim", mark=m_lt,
                  why="The l and t of the name share one crossbar, the way a typesetter would join them. The juniper-berry blue on the crossbar is the only accent.",
                  sw=[("Juniper", "#2F5D50"), ("Frost", "#E9EEEA"), ("Berry bloom", "#6F86C2")],
                  tile=dict(bg="#E9EEEA", ink="#2F5D50", acc="#6F86C2"),
                  icon=dict(bg="#17302A", ink="#E9EEEA", acc="#9FB1E3"),
                  ui=ui("#0F1C19", "#172824", "#E3ECE7", "#93A69E", "#24382F", "#7FB8A4", "#0D1D18", "#9FB1E3", "#74C08A", "#EE8C7C", dark=True)),
         ]),
    dict(slug="labor-limae", name="Labor Limae", say="LAH-bor LEE-my", origin="Round one · Horace, Ars Poetica",
         means="“The work of the file”: Horace's phrase for the slow, careful revision that finishes good writing.",
         tagline="The work of the file.",
         domains=".app and .io free · .com parked on Sedo, likely for sale",
         dirs=[
             dict(key="a", title="Filed Smooth", palette="Iron & Linen", font="Cormorant Garamond",
                  fam="'Cormorant Garamond', Georgia, serif", wstyle="font-weight:600;letter-spacing:0",
                  word="Labor Limae", mark=m_polish,
                  why="Handwritten loops, which also read as the two Ls, worked down until they become one clean line ending in a rust-red point. Draft, revision, done, in a single stroke.",
                  sw=[("Ironstone", "#33312C"), ("Linen", "#EFE8DA"), ("Rust", "#A8492A")],
                  tile=dict(bg="#EFE8DA", ink="#33312C", acc="#A8492A"),
                  icon=dict(bg="#33312C", ink="#EFE8DA", acc="#D9744F"),
                  ui=ui("#EFE8DA", "#F9F5EC", "#2A2824", "#6B655A", "#DCD3C1", "#33312C", "#F4EEE2", "#A8492A", "#4E7A3A", "#A8492A")),
             dict(key="b", title="Two Ls", palette="Walnut & Brass", font="Spectral",
                  fam="'Spectral', Georgia, serif", wstyle="font-weight:500;letter-spacing:0.14em;text-transform:uppercase;font-size:0.78em",
                  word="Labor Limae", mark=m_ll,
                  why="The two Ls of the name, one turned into the other, closing into a square. Capitals spaced like a Roman inscription, in walnut and brass.",
                  sw=[("Walnut", "#4A3324"), ("Parchment", "#F2EBDD"), ("Brass", "#B8913A")],
                  tile=dict(bg="#F2EBDD", ink="#4A3324", acc="#B8913A"),
                  icon=dict(bg="#2A1E15", ink="#EDE3D2", acc="#C9A24E"),
                  ui=ui("#1C1611", "#261E17", "#EDE3D2", "#A8998A", "#3A2E24", "#C9A24E", "#1C1611", "#E0C27A", "#8DBA74", "#E08A6E", dark=True)),
         ]),
    dict(slug="linguadojo", name="LinguaDojo", say="LING-gwah-DOH-joh", origin="Keep the name · add a Latin motto",
         means="The current name. Lingua is already Latin; the motto Usus magister optimus means “practice is the best teacher.”",
         tagline="Usus magister optimus.",
         domains=".com owned · .app and .io free",
         dirs=[
             dict(key="a", title="Doorway", palette="Delft & Dune", font="Fraunces",
                  fam="'Fraunces', Georgia, serif", wstyle="font-weight:600;letter-spacing:-0.01em;font-variation-settings:'SOFT' 50,'opsz' 96",
                  word="LinguaDojo", mark=m_arch,
                  why="The D turned upright into a doorway, the entrance to the training hall, with the L in sand on the threshold. It uses your cobalt, bone and sand palette.",
                  sw=[("Cobalt", "#2346A0"), ("Bone", "#EFE9DC"), ("Dune sand", "#C9A673")],
                  tile=dict(bg="#EFE9DC", ink="#2346A0", acc="#C9A673"),
                  icon=dict(bg="#2346A0", ink="#EFE9DC", acc="#D2B98A"),
                  ui=ui("#EFE9DC", "#FAF7F0", "#18213D", "#5D6378", "#DCD3C1", "#2346A0", "#F5F1E8", "#9C7A45", "#2F7A4F", "#B23A2E")),
             dict(key="b", title="Coin", palette="Persimmon", font="Gloock",
                  fam="'Gloock', Georgia, serif", wstyle="letter-spacing:0",
                  word="LinguaDojo", mark=m_badge, icon_mark=m_badge_icon,
                  why="The motto struck around the single-stroke monogram like the edge of a Roman coin. The app icon drops the lettering and keeps the monogram.",
                  sw=[("Vermillion", "#DD3F26"), ("Rice paper", "#F6EFE1"), ("Lamp black", "#1D1A17")],
                  tile=dict(bg="#F6EFE1", ink="#1D1A17", acc="#DD3F26"),
                  icon=dict(bg="#DD3F26", ink="#F6EFE1", acc="#F6EFE1"),
                  ui=ui("#171412", "#221D1A", "#F1E9DC", "#A89C8E", "#352D28", "#E8553B", "#1A0D09", "#F3B39F", "#7DBE8A", "#F07A62", dark=True)),
         ]),
    dict(slug="lingwright", name="Lingwright", say="LING-rite", origin="Round two · English craft word",
         means="A maker of language, built like playwright, shipwright and wheelwright: someone who builds things carefully, by hand.",
         tagline="Language, made by hand.",
         domains=".com, .app and .io all free",
         dirs=[
             dict(key="a", title="Try Square", palette="Oak & Graphite", font="Archivo",
                  fam="'Archivo', 'Helvetica Neue', sans-serif", wstyle="font-weight:700;letter-spacing:-0.02em;font-stretch:112%",
                  word="Lingwright", mark=m_square,
                  why="The L is a carpenter's try-square: an oak stock and a graphite blade marked off like a ruler. It is a tool for checking your work, which is what the app does.",
                  sw=[("Graphite", "#2A2B2E"), ("Sawdust", "#F1E9DB"), ("Oak", "#C68B48")],
                  tile=dict(bg="#F1E9DB", ink="#2A2B2E", acc="#C68B48"),
                  icon=dict(bg="#2A2B2E", ink="#F1E9DB", acc="#C68B48"),
                  ui=ui("#F1E9DB", "#FBF7EF", "#232427", "#66645E", "#DDD3C2", "#2A2B2E", "#F6F0E4", "#9C6427", "#3F7A44", "#B1452F")),
             dict(key="b", title="Dovetail", palette="Spruce & Copper", font="Bitter",
                  fam="'Bitter', Georgia, serif", wstyle="font-weight:600;letter-spacing:-0.01em",
                  word="Lingwright", mark=m_dovetail,
                  why="A dovetail joint: two pieces locked together so they can't be pulled apart. Your language and the one you're learning, joined by translation.",
                  sw=[("Spruce", "#1F4A43"), ("Pale birch", "#EEF0EA"), ("Copper", "#C06B3E")],
                  tile=dict(bg="#EEF0EA", ink="#1F4A43", acc="#C06B3E"),
                  icon=dict(bg="#1F4A43", ink="#EEF0EA", acc="#D98458"),
                  ui=ui("#0E1A18", "#162623", "#E4ECE8", "#94A7A1", "#24372F", "#D98458", "#1A0E07", "#8CC2B4", "#7CC49A", "#F08F7A", dark=True)),
         ]),
    dict(slug="etude", name="Étude", say="AY-tood", origin="Round two · music practice",
         means="A short piece written to drill one technique, which is exactly what each ladder exercise does. Read the same way in English, French and Spanish.",
         tagline="One technique at a time.",
         domains="Bare word taken on all three · etudelab.io, lingetude.com free",
         dirs=[
             dict(key="a", title="The Accent", palette="Fig & Pistachio", font="Bodoni Moda",
                  fam="'Bodoni Moda', Georgia, serif", wstyle="font-weight:600;letter-spacing:0;font-variation-settings:'opsz' 96",
                  word="Étude", mark=m_e_acute,
                  why="An É whose accent is drawn in pistachio, set apart like a teacher's mark above the work. The type is high-contrast, in the style of engraved sheet music.",
                  sw=[("Fig", "#4B2445"), ("Linen grey", "#F0EEE8"), ("Pistachio", "#8FAE52")],
                  tile=dict(bg="#F0EEE8", ink="#4B2445", acc="#8FAE52"),
                  icon=dict(bg="#4B2445", ink="#F0EEE8", acc="#A9C27A"),
                  ui=ui("#F0EEE8", "#FBFAF6", "#2A1828", "#6C6070", "#DDD6DB", "#4B2445", "#F6F0F4", "#6E8A36", "#4F8A3C", "#B53B4B")),
             dict(key="b", title="Repeat Sign", palette="Lake & Reed", font="Hanken Grotesk",
                  fam="'Hanken Grotesk', 'Helvetica Neue', sans-serif", wstyle="font-weight:600;letter-spacing:-0.025em",
                  word="étude", mark=m_repeat,
                  why="The musical sign for “repeat from here”: a thick bar, a thin bar and two dots. It is a practice loop drawn with notation everyone already knows.",
                  sw=[("Deep lake", "#173A4E"), ("Mist", "#E9EEF0"), ("Reed gold", "#D1A94A")],
                  tile=dict(bg="#E9EEF0", ink="#173A4E", acc="#D1A94A"),
                  icon=dict(bg="#173A4E", ink="#E9EEF0", acc="#D9B45A"),
                  ui=ui("#0D1820", "#15242E", "#E3EBEF", "#93A6B1", "#22343F", "#D9B45A", "#1A1405", "#8FC1DA", "#7FC59A", "#EE8B7B", dark=True)),
         ]),
]


def svg(inner, cls="", size=None):
    sz = f' width="{size}" height="{size}"' if size else ""
    return f'<svg viewBox="0 0 100 100"{sz} class="{cls}" aria-hidden="true">{inner}</svg>'


# ---------------------------------------------------------------- phone screens
ICONS = {
    "Today": '<circle cx="12" cy="12" r="8" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="12" r="3" fill="currentColor"/>',
    "Practice": '<path d="M5 12a7 7 0 0 1 12-5l2 2M19 12a7 7 0 0 1-12 5l-2-2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M19 4v5h-5M5 20v-5h5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>',
    "Tests": '<rect x="5" y="3" width="14" height="18" rx="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M9 8h6M9 12h6M9 16h3" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
    "Me": '<circle cx="12" cy="8" r="4" fill="none" stroke="currentColor" stroke-width="2"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>',
}
STATUS = ('<div class="status"><span>9:41</span><span class="sb">'
          '<svg viewBox="0 0 18 12" width="17" height="11"><rect x="0" y="8" width="3" height="4" rx="1" fill="currentColor"/><rect x="5" y="5" width="3" height="7" rx="1" fill="currentColor"/><rect x="10" y="2" width="3" height="10" rx="1" fill="currentColor"/><rect x="15" y="0" width="3" height="12" rx="1" fill="currentColor"/></svg>'
          '<svg viewBox="0 0 26 12" width="24" height="11"><rect x="0.5" y="0.5" width="22" height="11" rx="3" fill="none" stroke="currentColor"/><rect x="2" y="2" width="16" height="8" rx="1.5" fill="currentColor"/><rect x="23.5" y="4" width="2" height="4" rx="1" fill="currentColor"/></svg>'
          '</span></div>')


def tokens(u, fam):
    return (f"--bg:{u['bg']};--sf:{u['surface']};--ink:{u['ink']};--mu:{u['muted']};--ln:{u['line']};"
            f"--ac:{u['acc']};--aci:{u['acc_ink']};--hi:{u['hi']};--ok:{u['good']};--no:{u['bad']};--hf:{fam}")


def tabs(active):
    return '<nav class="tabs">' + "".join(
        f'<span class="tab{" on" if t == active else ""}"><svg viewBox="0 0 24 24" width="22" height="22">{ic}</svg>{t}</span>'
        for t, ic in ICONS.items()) + "</nav>"


def today_screen(N, D):
    u = D["ui"]
    m = D.get("icon_mark", D["mark"])(dict(bg=u["surface"], ink=u["ink"], acc=u["hi"]))
    check = '<svg viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="10" fill="var(--ok)"/><path d="M5.5 10.5l3 3 6-6.5" fill="none" stroke="var(--sf)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    ring = '<svg viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="8" fill="none" stroke="var(--ln)" stroke-width="2.5"/><path d="M10 2a8 8 0 0 1 7.6 5.5" fill="none" stroke="var(--hi)" stroke-width="2.5" stroke-linecap="round"/></svg>'
    dot = '<svg viewBox="0 0 20 20" width="20" height="20"><circle cx="10" cy="10" r="8" fill="none" stroke="var(--ln)" stroke-width="2.5"/></svg>'
    rows = [(check, "Flashcard review", "14 cards · done", "6 min", "done"),
            (ring, "New-word drill", "5 new words · 2 of 5", "8 min", "cur"),
            (dot, "Listening test", "Matched to your level", "7 min", ""),
            (dot, "Measure words", "Ladder ready", "4 min", "")]
    li = "".join(f'<li class="{c}"><span class="st">{i}</span><span class="rt"><b>{t}</b><small>{s}</small></span><em>{mn}</em></li>'
                 for i, t, s, mn, c in rows)
    return f'''<div class="phone{' dark' if u['dark'] else ''}" style="{tokens(u, D['fam'])}"><div class="screen">{STATUS}
<header class="appbar"><span class="ab-mark">{svg(m)}</span><span class="ab-word" style="font-family:var(--hf);{D['wstyle']}">{D['word']}</span><span class="avatar">A</span></header>
<div class="body">
  <p class="eyebrow">Tuesday · Chinese</p>
  <h4 class="h">Today’s session</h4>
  <div class="hero"><div class="hero-top"><span><b>11</b> of 25 min</span><span>1 of 4 done</span></div>
    <div class="bar"><i style="width:44%"></i></div>
    <span class="btn">Continue session</span></div>
  <p class="sect">Up next</p>
  <ul class="rows">{li}</ul>
  <p class="motto" style="font-family:var(--hf)">{N['tagline']}</p>
</div>{tabs("Today")}</div></div>'''


def exercise_screen(N, D):
    u = D["ui"]
    opts = [("都", "dōu", "ok", "Correct"), ("也", "yě", "no", "Your answer"), ("还", "hái", "", ""), ("就", "jiù", "", "")]
    og = "".join(f'<span class="opt {k}"><b>{h}</b><small>{p}</small>{f"<i>{t}</i>" if t else ""}</span>' for h, p, k, t in opts)
    return f'''<div class="phone{' dark' if u['dark'] else ''}" style="{tokens(u, D['fam'])}"><div class="screen">{STATUS}
<header class="exbar"><span class="x" aria-hidden="true">✕</span><span class="bar"><i style="width:35%"></i></span><span class="count">7 / 20</span></header>
<div class="body">
  <p class="eyebrow hi">Missing word</p>
  <p class="prompt">Choose the word that completes the sentence.</p>
  <div class="sent"><p class="zh">我每个周末<span class="blank">都</span>去图书馆。</p><p class="gl">I go to the library every weekend.</p></div>
  <div class="opts">{og}</div>
  <div class="fb"><p class="fb-h"><span>Not quite.</span> 都 dōu, “every, all”</p>
  <p>English “every weekend” has no matching word, so 都 is easy to drop. It’s added to today’s extra round.</p></div>
</div>
<div class="dock"><span class="btn">Continue</span></div></div></div>'''


# ---------------------------------------------------------------- standalone SVGs
for N in NAMES:
    d = f"{OUT}/names/{N['slug']}"
    os.makedirs(d, exist_ok=True)
    for D in N["dirs"]:
        t, ic = D["tile"], D["icon"]
        head = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        open(f"{d}/{D['key']}-mark.svg", "w").write(head + D["mark"](t) + "</svg>\n")
        im = D.get("icon_mark", D["mark"])
        open(f"{d}/{D['key']}-app-icon.svg", "w").write(
            head + f'<rect width="100" height="100" rx="22" fill="{ic["bg"]}"/>'
            f'<g transform="translate(18 18) scale(0.64)">{im(ic)}</g></svg>\n')

# ---------------------------------------------------------------- page
FONTS = "family=" + "&family=".join([
    "Instrument+Sans:wght@600", "Literata:opsz,wght@7..72,600", "Cormorant+Garamond:wght@600", "Spectral:wght@500",
    "Fraunces:opsz,wght,SOFT@9..144,600,50", "Gloock", "Archivo:wdth,wght@112,700", "Bitter:wght@600",
    "Bodoni+Moda:opsz,wght@6..96,600", "Hanken+Grotesk:wght@600", "Inter:wght@400;500;600",
    "Noto+Serif+SC:wght@600", "IBM+Plex+Sans:wght@400;500;600", "IBM+Plex+Mono:wght@400"])

sections = []
for N in NAMES:
    dirs = []
    for D in N["dirs"]:
        t, ic = D["tile"], D["icon"]
        im = D.get("icon_mark", D["mark"])
        sw = "".join(f'<li><span class="chip" style="background:{h}"></span>{nm}<code>{h}</code></li>' for nm, h in D["sw"])
        screen = today_screen(N, D) if D["key"] == "a" else exercise_screen(N, D)
        dirs.append(f'''
<article class="dir">
  <div class="spec">
    <div class="tile" style="background:{t['bg']};color:{t['ink']}">
      <div class="lockup">{svg(D['mark'](t), 'lk-mark')}<span class="word" style="font-family:{D['fam']};{D['wstyle']}">{D['word']}</span></div>
    </div>
    <div class="spec-row">
      <div class="app" style="background:{ic['bg']}">{svg(im(ic))}</div>
      <div class="fav" style="background:{t['bg']}">{svg(im(t), size=24)}</div>
      <div class="spec-txt"><h3>{D['title']}</h3><p class="tags"><span>{D['palette']}</span><span>{D['font']}</span></p></div>
    </div>
    <p class="why">{D['why']}</p>
    <ul class="swatches">{sw}</ul>
  </div>
  <figure class="mock">{screen}<figcaption>{"Today screen · light" if D['key'] == 'a' else "Exercise feedback · dark"}</figcaption></figure>
</article>''')
    sections.append(f'''
<section class="name" id="{N['slug']}">
  <header class="name-head">
    <div><p class="eyebrow">{N['origin']}</p><h2 style="font-family:{N['dirs'][0]['fam']}">{N['name']}</h2><p class="say">{N['say']}</p></div>
    <dl class="facts"><div><dt>Meaning</dt><dd>{N['means']}</dd></div><div><dt>Tagline</dt><dd>{N['tagline']}</dd></div><div><dt>Domains</dt><dd>{N['domains']}</dd></div></dl>
  </header>
  <div class="dirs">{"".join(dirs)}</div>
</section>''')

nav = "".join(f'<a href="#{N["slug"]}">{N["name"]}</a>' for N in NAMES)

PAGE = f'''<title>LinguaDojo Name Studies</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{FONTS}&display=swap">
<style>
/* Layout: one band per name; each band holds two directions, each a specimen column beside a phone mockup. Phones carry their own palettes as content. */
:root {{
  --bg: #F3F2EE; --surface: #FFFFFF; --fg: #1E1F1C; --muted: #66675F; --line: #DCDAD2; --frame: #1A1B19;
  --f-ui: 'IBM Plex Sans', system-ui, sans-serif; --f-mono: 'IBM Plex Mono', ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #151614; --surface: #1D1E1B; --fg: #ECEAE3; --muted: #A3A399; --line: #33342F; --frame: #000000; color-scheme: dark; }} }}
:root[data-theme="dark"] {{ --bg: #151614; --surface: #1D1E1B; --fg: #ECEAE3; --muted: #A3A399; --line: #33342F; --frame: #000000; color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-ui); font-size: 15px; line-height: 1.55; }}
.wrap {{ max-width: 1240px; margin: 0 auto; padding-block: 48px 72px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
.intro {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 24px 56px; align-items: end; padding-bottom: 24px; }}
.eyebrow {{ font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin: 0 0 8px; }}
h1 {{ font-size: clamp(30px, 4.6vw, 52px); line-height: 1.05; letter-spacing: -.025em; margin: 0; font-weight: 600; text-wrap: balance; }}
.brief {{ margin: 0; color: var(--muted); max-width: 60ch; }}
.jump {{ display: flex; flex-wrap: wrap; gap: 8px; padding: 16px 0 8px; border-bottom: 1px solid var(--line); }}
.jump a {{ color: var(--fg); text-decoration: none; font-size: 13px; padding: 4px 12px; border: 1px solid var(--line); border-radius: 999px; }}
.jump a:hover, .jump a:focus-visible {{ border-color: var(--fg); outline: none; }}
.name {{ padding-block: 48px 8px; border-bottom: 1px solid var(--line); }}
.name-head {{ display: grid; grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.4fr); gap: 16px 48px; align-items: start; margin-bottom: 28px; }}
.name-head h2 {{ font-size: clamp(36px, 5vw, 56px); line-height: 1; margin: 0; font-weight: 600; letter-spacing: -.01em; }}
.say {{ margin: 8px 0 0; font: 400 13px var(--f-mono); color: var(--muted); }}
.facts {{ margin: 0; display: grid; gap: 10px; }}
.facts div {{ display: grid; grid-template-columns: 84px minmax(0, 1fr); gap: 12px; }}
.facts dt {{ font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); padding-top: 2px; }}
.facts dd {{ margin: 0; }}
.dirs {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 28px; }}
.dir {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; padding: 18px; display: grid; grid-template-columns: minmax(0, 1fr) 248px; gap: 20px; align-items: start; margin-bottom: 40px; }}
.spec {{ display: grid; gap: 14px; min-width: 0; }}
.tile {{ border-radius: 4px; min-height: 150px; display: grid; place-items: center; padding: 20px 14px; }}
.lockup {{ display: flex; align-items: center; gap: 12px; max-width: 100%; }}
.lk-mark {{ width: 56px; height: 56px; flex: none; }}
.word {{ font-size: clamp(24px, 2.6vw, 32px); line-height: 1; white-space: nowrap; }}
.spec-row {{ display: flex; align-items: center; gap: 14px; }}
.app {{ width: 52px; height: 52px; border-radius: 12px; display: grid; place-items: center; flex: none; }}
.app svg {{ width: 34px; height: 34px; }}
.fav {{ padding: 5px; border-radius: 4px; outline: 1px solid var(--line); display: grid; place-items: center; flex: none; }}
.spec-txt h3 {{ margin: 0 0 4px; font-size: 17px; font-weight: 600; }}
.tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0; }}
.tags span {{ font-size: 12px; padding: 1px 8px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); }}
.why {{ margin: 0; font-size: 14px; }}
.swatches {{ list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px 14px; font-size: 13px; }}
.swatches li {{ display: flex; align-items: center; gap: 6px; }}
.chip {{ width: 16px; height: 16px; border-radius: 3px; outline: 1px solid color-mix(in srgb, var(--fg) 18%, transparent); outline-offset: -1px; }}
.swatches code {{ font: 400 11px var(--f-mono); color: var(--muted); }}
.mock {{ margin: 0; display: grid; justify-items: center; gap: 10px; }}
.mock figcaption {{ font: 400 11px var(--f-mono); color: var(--muted); }}
.foot {{ margin-top: 32px; color: var(--muted); font-size: 13px; max-width: 75ch; }}

/* ---- phone mockup: tokens come from inline style on .phone ---- */
.phone {{ width: 248px; aspect-ratio: 248 / 520; background: var(--frame); border-radius: 36px; padding: 8px; box-shadow: 0 18px 40px -22px rgba(0,0,0,.45); max-width: 100%; }}
.screen {{ position: relative; height: 100%; background: var(--bg); color: var(--ink); border-radius: 29px; overflow: hidden; display: flex; flex-direction: column; font: 400 11px/1.4 'Inter', system-ui, sans-serif; }}
.status {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 20px 4px; font-weight: 600; font-size: 11px; }}
.sb {{ display: flex; gap: 5px; align-items: center; }}
.appbar {{ display: flex; align-items: center; gap: 7px; padding: 6px 14px 8px; border-bottom: 1px solid var(--ln); }}
.ab-mark svg {{ width: 22px; height: 22px; display: block; }}
.ab-word {{ font-size: 15px; line-height: 1; flex: 1; white-space: nowrap; }}
.avatar {{ width: 22px; height: 22px; border-radius: 50%; background: var(--sf); border: 1px solid var(--ln); display: grid; place-items: center; font-size: 10px; font-weight: 600; color: var(--mu); }}
.body {{ flex: 1; padding: 12px 14px; display: flex; flex-direction: column; gap: 8px; overflow: hidden; }}
.screen .eyebrow {{ margin: 0; font-size: 9px; letter-spacing: .1em; color: var(--mu); }}
.screen .eyebrow.hi {{ color: var(--hi); font-weight: 600; }}
.h {{ margin: 0; font: 600 20px/1.1 var(--hf); letter-spacing: -.01em; }}
.hero {{ background: var(--sf); border: 1px solid var(--ln); border-radius: 10px; padding: 10px; display: grid; gap: 8px; }}
.hero-top {{ display: flex; justify-content: space-between; color: var(--mu); font-size: 10px; }}
.hero-top b {{ color: var(--ink); font-size: 13px; }}
.bar {{ height: 5px; border-radius: 3px; background: var(--ln); overflow: hidden; display: block; }}
.bar i {{ display: block; height: 100%; background: var(--ac); border-radius: 3px; }}
.btn {{ display: block; text-align: center; background: var(--ac); color: var(--aci); border-radius: 8px; padding: 8px; font-weight: 600; font-size: 11.5px; }}
.sect {{ margin: 4px 0 0; font-size: 9px; letter-spacing: .1em; text-transform: uppercase; color: var(--mu); }}
.rows {{ list-style: none; margin: 0; padding: 0; display: grid; }}
.rows li {{ display: flex; align-items: center; gap: 9px; padding: 7px 0; border-bottom: 1px solid var(--ln); }}
.rows li:last-child {{ border-bottom: 0; }}
.rows .rt {{ flex: 1; display: grid; min-width: 0; }}
.rows b {{ font-weight: 600; font-size: 11.5px; }}
.rows small {{ color: var(--mu); font-size: 9.5px; }}
.rows em {{ font-style: normal; color: var(--mu); font-size: 10px; font-variant-numeric: tabular-nums; }}
.rows li.done b {{ color: var(--mu); }}
.rows li.cur b {{ color: var(--ink); }}
.st svg {{ display: block; }}
.motto {{ margin: auto 0 0; text-align: center; color: var(--mu); font-size: 11px; font-style: italic; }}
.tabs {{ display: flex; justify-content: space-around; padding: 6px 6px 14px; border-top: 1px solid var(--ln); background: var(--sf); }}
.tab {{ display: grid; justify-items: center; gap: 2px; font-size: 9px; color: var(--mu); }}
.tab.on {{ color: var(--ac); font-weight: 600; }}
.exbar {{ display: flex; align-items: center; gap: 10px; padding: 8px 14px; }}
.exbar .x {{ color: var(--mu); font-size: 12px; }}
.exbar .bar {{ flex: 1; }}
.exbar .count {{ color: var(--mu); font-size: 10px; font-variant-numeric: tabular-nums; }}
.prompt {{ margin: 0; font: 600 14px/1.25 var(--hf); }}
.sent {{ background: var(--sf); border: 1px solid var(--ln); border-radius: 10px; padding: 12px 10px; text-align: center; }}
.zh {{ margin: 0; font: 600 17px/1.4 'Noto Serif SC', 'Songti SC', serif; letter-spacing: .02em; }}
.blank {{ display: inline-block; min-width: 1.3em; border-bottom: 2px solid var(--ok); color: var(--ok); }}
.gl {{ margin: 4px 0 0; color: var(--mu); font-size: 10px; }}
.opts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; }}
.opt {{ position: relative; display: grid; justify-items: center; padding: 6px 4px; border-radius: 8px; border: 1px solid var(--ln); background: var(--sf); }}
.opt b {{ font: 600 17px/1.2 'Noto Serif SC', serif; }}
.opt small {{ color: var(--mu); font-size: 9px; }}
.opt i {{ font-style: normal; font-size: 8.5px; font-weight: 600; }}
.opt.ok {{ border-color: var(--ok); background: color-mix(in srgb, var(--ok) 14%, var(--sf)); }}
.opt.ok i {{ color: var(--ok); }}
.opt.no {{ border-color: var(--no); background: color-mix(in srgb, var(--no) 12%, var(--sf)); }}
.opt.no i {{ color: var(--no); }}
.fb {{ border-radius: 10px; padding: 9px 10px; background: color-mix(in srgb, var(--hi) 12%, var(--sf)); border: 1px solid color-mix(in srgb, var(--hi) 40%, var(--ln)); }}
.fb p {{ margin: 0; font-size: 10px; }}
.fb .fb-h {{ font-weight: 600; font-size: 11px; margin-bottom: 3px; }}
.fb .fb-h span {{ color: var(--no); }}
.dock {{ padding: 8px 14px 18px; border-top: 1px solid var(--ln); background: var(--sf); }}

@media (max-width: 1100px) {{ .dirs {{ grid-template-columns: minmax(0, 1fr); }} }}
@media (max-width: 760px) {{ .intro, .name-head {{ grid-template-columns: minmax(0, 1fr); }} }}
@media (max-width: 600px) {{ .dir {{ grid-template-columns: minmax(0, 1fr); }} .facts div {{ grid-template-columns: minmax(0, 1fr); gap: 0; }} }}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
</style>
<div class="wrap">
  <section class="intro">
    <div><p class="eyebrow">Brand identity · round two</p><h1>Five names, ten marks</h1></div>
    <p class="brief">The names recommended from the Latin and non-Latin rounds. Each gets two marks, two colour schemes and a phone mockup of the redesigned app. The first mockup shows the Today screen in light mode; the second shows exercise feedback after a wrong answer in dark mode.</p>
  </section>
  <nav class="jump" aria-label="Names">{nav}</nav>
  {"".join(sections)}
  <p class="foot">Mockups use the redesigned app's real structure (Today · Practice · Tests · Me) and sample Chinese content. Wordmarks are set in live web fonts and are sketches, not final artwork. Domain status is from registry lookups on 17 November 2026; no trademark search has been done. Standalone mark and app-icon SVGs are in <code>wiki/design/brand/names/</code>.</p>
</div>
'''
open(f"{OUT}/name-studies.html", "w").write(PAGE)
print("ok")
