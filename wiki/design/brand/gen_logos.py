"""Generate 10 LinguaDojo logo studies: standalone SVGs + an HTML specimen page."""
import math, os, html, itertools  # noqa: E401

OUT = os.path.dirname(os.path.abspath(__file__))
os.makedirs(f"{OUT}/logos", exist_ok=True)
_uid = itertools.count()


def arc_pts(cx, cy, r, a0, a1):
    p = lambda a: (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
    (x0, y0), (x1, y1) = p(a0), p(a1)
    large = 1 if (a1 - a0) % 360 > 180 else 0
    return f"M{x0:.2f} {y0:.2f} A{r} {r} 0 {large} 1 {x1:.2f} {y1:.2f}"


# Each mark: f(c) -> svg inner markup, viewBox 0 0 100 100. c has ink, acc, bg, (mix).
def m_delft(c):
    return (f'<path d="M25 8.5 V86 H47 A36 36 0 0 0 47 14" fill="none" stroke="{c["ink"]}" '
            f'stroke-width="11" stroke-linejoin="miter"/>')


def m_persimmon(c):
    pts = []
    for k in range(73):
        a = math.radians(200 + k * 5.4)          # ~390 degrees: overshoots its own start
        grow = 1 + 0.12 * k / 72
        rx, ry, tilt = 26 * grow, 16 * grow, math.radians(-7)
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((47 + x * math.cos(tilt) - y * math.sin(tilt), 63 + x * math.sin(tilt) + y * math.cos(tilt)))
    ring = "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    faint = f'fill="{c["ink"]}" opacity=".3"'
    return (f'<rect x="4" y="25" width="30" height="9" rx="1" {faint}/>'
            f'<rect x="40" y="25" width="34" height="9" rx="1" {faint}/>'
            f'<rect x="80" y="25" width="16" height="9" rx="1" {faint}/>'
            f'<rect x="4" y="59" width="10" height="9" rx="1" {faint}/>'
            f'<rect x="29" y="58" width="36" height="11" rx="1" fill="{c["ink"]}"/>'
            f'<rect x="80" y="59" width="16" height="9" rx="1" {faint}/>'
            f'<path d="{ring}" fill="none" stroke="{c["acc"]}" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>')


def m_moss(c):
    return (f'<path d="M28 90 V14 H50 A36 36 0 0 1 50 86 H42 V30 H50 A20 20 0 0 1 50 70 H47" fill="none" '
            f'stroke="{c["ink"]}" stroke-width="8" stroke-linejoin="miter"/>'
            f'<circle cx="56" cy="50" r="5" fill="{c["acc"]}"/>')


def m_kingfisher(c):
    tick = "M33 50 L46 64 L80 22"
    return (f'<path d="M20 16 H48 A34 34 0 0 1 48 84 H20 Z" fill="none" stroke="{c["ink"]}" '
            f'stroke-width="8" stroke-linejoin="round"/>'
            f'<path d="{tick}" fill="none" stroke="{c["bg"]}" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="{tick}" fill="none" stroke="{c["acc"]}" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>')


def m_lichen(c):
    i = next(_uid)
    d = "M25 14 H49 A36 36 0 0 1 49 86 H25 Z"
    l = "M13 14 H31 V68 H63 V86 H13 Z"
    return (f'<defs><clipPath id="ld-clip-{i}"><path d="{d}"/></clipPath></defs>'
            f'<path d="{d}" fill="{c["acc"]}"/><path d="{l}" fill="{c["ink"]}"/>'
            f'<path d="{l}" fill="{c["mix"]}" clip-path="url(#ld-clip-{i})"/>')


def m_oxblood(c):
    return (f'<rect x="4" y="44" width="44" height="12" fill="{c["ink"]}"/>'
            f'<rect x="70" y="44" width="26" height="12" fill="{c["ink"]}"/>'
            f'<path d="M45 86 L59 61 L73 86" fill="none" stroke="{c["ink"]}" stroke-width="7" stroke-linejoin="miter"/>'
            f'<rect x="46" y="20" width="28" height="12" fill="{c["acc"]}"/>')


def m_basalt(c):
    rings = [(40, -60), (27, 60), (14, 180)]
    s = "".join(
        f'<path d="{arc_pts(50, 50, r, g + 32, g + 328)}" fill="none" stroke="{c["ink"]}" stroke-width="7"/>'
        for r, g in rings)
    return s + f'<circle cx="50" cy="50" r="5.5" fill="{c["acc"]}"/>'


def m_heather(c):
    over = "M44.21 26.82 A24 24 0 0 1 54.97 33.03"
    return (f'<circle cx="38" cy="50" r="24" fill="none" stroke="{c["ink"]}" stroke-width="9"/>'
            f'<circle cx="62" cy="50" r="24" fill="none" stroke="{c["acc"]}" stroke-width="9"/>'
            f'<path d="{over}" fill="none" stroke="{c["bg"]}" stroke-width="15"/>'
            f'<path d="M42 26 A24 24 0 0 1 57 35" fill="none" stroke="{c["ink"]}" stroke-width="9"/>')


def m_fjord(c):
    return (f'<rect x="10" y="10" width="80" height="80" rx="5" fill="{c["ink"]}"/>'
            f'<path d="M31 16 H57.5 A26.5 26.5 0 0 1 57.5 69 H31 Z" fill="{c["bg"]}"/>'
            f'<rect x="75" y="75" width="9" height="9" fill="{c["acc"]}"/>')


def m_tidepool(c):
    return (f'<path d="M8 68 C 28 68, 40 61, 48 47 C 56 33, 54 13, 44 15 C 33 17, 33 44, 46 60 L 55 71" '
            f'fill="none" stroke="{c["ink"]}" stroke-width="8" stroke-linecap="round" stroke-linejoin="round"/>'
            f'<path d="M55 71 L 90 28" fill="none" stroke="{c["acc"]}" stroke-width="8" stroke-linecap="round"/>')


LOGOS = [
    dict(slug="single-stroke", name="Single Stroke", concept="LD monogram",
         palette="Delft & Dune", font="Fraunces", fam="'Fraunces', Georgia, serif",
         swatches=[("Cobalt", "#2346A0"), ("Bone", "#EFE9DC"), ("Dune sand", "#D2B98A")],
         tile=dict(bg="#EFE9DC", ink="#2346A0", acc="#D2B98A"),
         icon=dict(bg="#2346A0", ink="#EFE9DC", acc="#D2B98A"),
         word='<span style="font-weight:400">Lingua</span><span style="font-weight:700">Dojo</span>',
         wstyle="font-variation-settings:'SOFT' 50,'opsz' 96;letter-spacing:-0.01em",
         mark=m_delft,
         why="One unbroken line draws the L's stem and the D's bowl. The D's top-left corner is left open so the L's stem stands clear. "
             "Cobalt on bone recalls Delft ink on unglazed clay, and the sand rule underneath is the mat the work happens on."),
    dict(slug="the-circled-word", name="The Circled Word", concept="Correction mark",
         palette="Persimmon", font="Gloock", fam="'Gloock', Georgia, serif",
         swatches=[("Vermillion", "#DD3F26"), ("Rice paper", "#F6EFE1"), ("Lamp black", "#1D1A17")],
         tile=dict(bg="#F6EFE1", ink="#1D1A17", acc="#DD3F26"),
         icon=dict(bg="#DD3F26", ink="#F6EFE1", acc="#F6EFE1"),
         word='LinguaDojo', wstyle="letter-spacing:0",
         mark=m_persimmon,
         why="A line of text with one word circled in red by a teacher who was not satisfied with it. The ring overshoots its own start, "
             "the way a real pen does. It is the most direct reading of 'honest feedback' in the set."),
    dict(slug="inward-spiral", name="Inward Spiral", concept="Loop / LD monogram",
         palette="Moss Garden", font="Young Serif", fam="'Young Serif', Georgia, serif",
         swatches=[("Emerald", "#0D6A4A"), ("Cream", "#F2EDDF"), ("Deep moss", "#12291F")],
         tile=dict(bg="#F2EDDF", ink="#0D6A4A", acc="#0D6A4A"),
         icon=dict(bg="#0D6A4A", ink="#F2EDDF", acc="#F2EDDF"),
         word='LinguaDojo', wstyle="letter-spacing:-0.01em",
         mark=m_moss,
         why="A D drawn twice, the second pass inside the first, so the line winds toward a point at the centre. "
             "It nods to LinguaLoop: each loop of practice is tighter than the last. Square corners keep it disciplined rather than playful."),
    dict(slug="breakout-tick", name="Breakout Tick", concept="Correction mark",
         palette="Kingfisher", font="Schibsted Grotesk", fam="'Schibsted Grotesk', 'Helvetica Neue', sans-serif",
         swatches=[("Kingfisher", "#0B6A86"), ("Breast rust", "#E0782F"), ("Riverbank", "#EDF0EA"), ("Deep water", "#0F2A33")],
         tile=dict(bg="#EDF0EA", ink="#0B6A86", acc="#E0782F"),
         icon=dict(bg="#0F2A33", ink="#5FB3CC", acc="#E0782F"),
         word='LinguaDojo', wstyle="font-weight:700;letter-spacing:-0.02em",
         mark=m_kingfisher,
         why="A tick that starts inside the D and breaks out through its edge: the moment you get something right that was beyond you. "
             "The kingfisher's blue back and rust breast give a pair of colours that is bright but not neon."),
    dict(slug="overprint", name="Overprint", concept="LD monogram",
         palette="Lichen on Slate", font="Familjen Grotesk", fam="'Familjen Grotesk', 'Helvetica Neue', sans-serif",
         swatches=[("Slate", "#2D3A41"), ("Lichen", "#B8C46C"), ("Overlap olive", "#6B7646"), ("Field stone", "#E6E4DC")],
         tile=dict(bg="#E6E4DC", ink="#2D3A41", acc="#B8C46C", mix="#6B7646"),
         icon=dict(bg="#2D3A41", ink="#E6E4DC", acc="#B8C46C", mix="#8E9A55"),
         word='<span>lingua</span><span style="color:#6B7646">dojo</span>', wstyle="font-weight:600;letter-spacing:-0.025em",
         mark=m_lichen,
         why="A solid L and a solid D printed over each other like two passes of ink; where they overlap a third colour appears. "
             "It suggests two languages, or what you know plus what you're learning, producing something neither has alone. Heavy and geometric, so it holds up as a 16 px favicon."),
    dict(slug="insertion-caret", name="Insertion Caret", concept="Correction mark",
         palette="Oxblood & Oat", font="Instrument Serif", fam="'Instrument Serif', Georgia, serif",
         swatches=[("Oxblood", "#6A1E2A"), ("Oat", "#EBE0C9"), ("Ripe wheat", "#C79A4B")],
         tile=dict(bg="#EBE0C9", ink="#6A1E2A", acc="#C79A4B"),
         icon=dict(bg="#6A1E2A", ink="#EBE0C9", acc="#C79A4B"),
         word='Lingua<em style="font-style:italic">Dojo</em>', wstyle="font-size:clamp(33px, 5.2vw, 54px);letter-spacing:0",
         mark=m_oxblood,
         why="The proofreader's caret (‸) means 'something belongs here'. It sits under a gap in a line of words, "
             "with the missing word placed above it. The vocabulary is an editor's, not a game's, which suits translators and test-takers."),
    dict(slug="four-rings", name="Dial", concept="Loop",
         palette="Basalt & Ochre", font="Bricolage Grotesque", fam="'Bricolage Grotesque', 'Helvetica Neue', sans-serif",
         swatches=[("Basalt", "#24221F"), ("Ochre", "#C98A2A"), ("Volcanic ash", "#E7E2D8")],
         tile=dict(bg="#E7E2D8", ink="#24221F", acc="#C98A2A"),
         icon=dict(bg="#24221F", ink="#E7E2D8", acc="#C98A2A"),
         word='LinguaDojo', wstyle="font-weight:700;letter-spacing:-0.03em;font-variation-settings:'opsz' 96",
         mark=m_basalt,
         why="Three open rings with their gaps turned like a combination dial, and an ochre core. It echoes Vocab Dojo's rings "
             "and the idea of unlocking each one in turn. It keeps the current display face, so it is the least disruptive change to the live app."),
    dict(slug="linked-pair", name="Linked Pair", concept="Loop",
         palette="Heather & Peat", font="Newsreader", fam="'Newsreader', Georgia, serif",
         swatches=[("Peat", "#3A2D28"), ("Heather", "#7F6AA2"), ("Chalk", "#F1EDE6")],
         tile=dict(bg="#F1EDE6", ink="#3A2D28", acc="#7F6AA2"),
         icon=dict(bg="#3A2D28", ink="#F1EDE6", acc="#B3A1D1"),
         word='LinguaDojo', wstyle="font-weight:500;font-variation-settings:'opsz' 72;letter-spacing:-0.01em",
         mark=m_heather,
         why="Two loops woven through each other: your language and the one you're learning, held together by translation. "
             "It ties directly to dual translation and to practice as a loop. Moorland purple and peat-brown are an unusual, quiet pairing."),
    dict(slug="negative-space", name="Negative Space", concept="LD monogram",
         palette="Fjord & Glacier", font="Syne", fam="'Syne', 'Helvetica Neue', sans-serif",
         swatches=[("Fjord", "#14324A"), ("Glacier", "#D5E4E8"), ("Arctic poppy", "#E6C24A")],
         tile=dict(bg="#D5E4E8", ink="#14324A", acc="#E6C24A"),
         icon=dict(bg="#D5E4E8", ink="#14324A", acc="#E6C24A"),
         word='Lingua<span style="text-decoration:underline;text-decoration-color:#C9A12A;text-decoration-thickness:0.12em;text-underline-offset:0.12em">Dojo</span>',
         wstyle="font-weight:700;letter-spacing:-0.02em",
         mark=m_fjord,
         why="A solid tile with a D cut out of it. The ice-coloured D is the figure, and what remains of the tile is an equal-weight L. "
             "It is built to be an app icon first. A poppy-yellow full stop at the end of the L, echoed in the wordmark's underline, is the one point of warmth."),
    dict(slug="loop-to-tick", name="Loop to Tick", concept="Loop + correction",
         palette="Tidepool", font="Red Hat Display", fam="'Red Hat Display', 'Helvetica Neue', sans-serif",
         swatches=[("Kelp", "#1C3B36"), ("Anemone", "#E46E55"), ("Shell", "#F4ECE3")],
         tile=dict(bg="#F4ECE3", ink="#1C3B36", acc="#E46E55"),
         icon=dict(bg="#1C3B36", ink="#F4ECE3", acc="#E46E55"),
         word='Lingua<span style="color:#C4513A">Dojo</span>', wstyle="font-weight:700;letter-spacing:-0.02em",
         mark=m_tidepool,
         why="One line that loops once, like a handwritten l, then drops into a tick. Practice, then the correct answer, in a single gesture. "
             "It combines both concepts you picked, and the colours come from a rock pool: kelp-green and anemone coral."),
]


def svg(inner, size=None, cls=""):
    sz = f' width="{size}" height="{size}"' if size else ""
    return f'<svg viewBox="0 0 100 100"{sz} class="{cls}" aria-hidden="true">{inner}</svg>'


# ---------- standalone SVG files ----------
for n, L in enumerate(LOGOS, 1):
    d = f"{OUT}/logos/{n:02d}-{L['slug']}"
    os.makedirs(d, exist_ok=True)
    t, ic = L["tile"], L["icon"]
    head = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
    open(f"{d}/mark.svg", "w").write(head + L["mark"](t) + "</svg>\n")
    open(f"{d}/app-icon.svg", "w").write(
        head + f'<rect width="100" height="100" rx="22" fill="{ic["bg"]}"/>'
        f'<g transform="translate(18 18) scale(0.64)">{L["mark"](ic)}</g></svg>\n')
    w = 120 + 10 * 30
    word_txt = html.escape("LinguaDojo" if "lingua" not in L["word"] else "linguadojo")
    open(f"{d}/lockup.svg", "w").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 100">'
        f'<rect width="{w}" height="100" fill="{t["bg"]}"/>'
        f'<g transform="translate(6 10) scale(0.8)">{L["mark"](t)}</g>'
        f'<text x="102" y="64" font-family="{html.escape(L["fam"])}" font-size="46" fill="{t["ink"]}">{word_txt}</text>'
        f'</svg>\n')

# ---------- HTML specimen page ----------
fonts = "family=" + "&family=".join([
    "Fraunces:opsz,wght,SOFT@9..144,400;9..144,700,50", "Gloock", "Young+Serif",
    "Schibsted+Grotesk:wght@700", "Familjen+Grotesk:wght@600", "Instrument+Serif:ital@0;1",
    "Bricolage+Grotesque:opsz,wght@12..96,700", "Newsreader:opsz,wght@6..72,500", "Syne:wght@700",
    "Red+Hat+Display:wght@700", "IBM+Plex+Sans:wght@400;500;600", "IBM+Plex+Mono:wght@400;500"])

cards = []
for n, L in enumerate(LOGOS, 1):
    t, ic = L["tile"], L["icon"]
    sw = "".join(
        f'<li><span class="chip" style="background:{h}"></span><span class="sw-name">{nm}</span>'
        f'<code>{h}</code></li>' for nm, h in L["swatches"])
    cards.append(f'''
<article class="study" id="logo-{n:02d}">
  <div class="tile" style="background:{t['bg']};color:{t['ink']}">
    <span class="tile-no" style="color:{t['ink']}">{n:02d}</span>
    <div class="lockup">
      {svg(L['mark'](t), cls='lockup-mark')}
      <span class="word" style="font-family:{L['fam']};{L['wstyle']}">{L['word']}</span>
    </div>
  </div>
  <div class="sizes">
    <figure><div class="app" style="background:{ic['bg']}">{svg(L['mark'](ic))}</div><figcaption>App icon</figcaption></figure>
    <figure><div class="mono">{svg(L['mark'](t), 56)}</div><figcaption>Mark alone</figcaption></figure>
    <figure><div class="fav" style="background:{t['bg']}">{svg(L['mark'](t), 32)}</div><figcaption>32 px</figcaption></figure>
    <figure><div class="fav" style="background:{t['bg']}">{svg(L['mark'](t), 16)}</div><figcaption>16 px</figcaption></figure>
  </div>
  <div class="meta">
    <header><h2>{L['name']}</h2><p class="tags"><span>{L['concept']}</span><span>{L['palette']}</span><span>{L['font']}</span></p></header>
    <p class="why">{L['why']}</p>
    <ul class="swatches">{sw}</ul>
  </div>
</article>''')

page = f'''<title>LinguaDojo Mark Studies</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{fonts}&display=swap">
<style>
/* Layout: specimen sheet. Quiet gallery chrome, each study a bordered card; the logo tiles carry their own fixed palettes as content. */
:root {{
  --bg: #F3F2EE; --surface: #FFFFFF; --fg: #1E1F1C; --muted: #66675F; --line: #DCDAD2; --accent: #2346A0;
  --f-ui: 'IBM Plex Sans', system-ui, sans-serif; --f-mono: 'IBM Plex Mono', ui-monospace, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #151614; --surface: #1D1E1B; --fg: #ECEAE3; --muted: #A3A399; --line: #33342F; --accent: #8FA8F0; color-scheme: dark; }} }}
:root[data-theme="dark"] {{ --bg: #151614; --surface: #1D1E1B; --fg: #ECEAE3; --muted: #A3A399; --line: #33342F; --accent: #8FA8F0; color-scheme: dark; }}
body {{ background: var(--bg); color: var(--fg); font-family: var(--f-ui); font-size: 15px; line-height: 1.55; }}
.wrap {{ max-width: 1240px; margin: 0 auto; padding-block: 48px 72px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px)); }}
.intro {{ display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 1fr); gap: 32px 56px; align-items: end; padding-bottom: 32px; border-bottom: 1px solid var(--line); }}
.eyebrow {{ font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: var(--muted); margin: 0 0 10px; }}
h1 {{ font-size: clamp(30px, 4.6vw, 52px); line-height: 1.05; letter-spacing: -.025em; margin: 0; font-weight: 600; text-wrap: balance; }}
.brief {{ margin: 0; color: var(--muted); max-width: 60ch; }}
.brief b {{ color: var(--fg); font-weight: 600; }}
.grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 28px; margin-top: 32px; }}
.study {{ background: var(--surface); border: 1px solid var(--line); border-radius: 6px; overflow: hidden; display: flex; flex-direction: column; }}
.tile {{ position: relative; aspect-ratio: 16 / 8; display: grid; place-items: center; padding: 24px; }}
.tile-no {{ position: absolute; top: 14px; left: 16px; font: 500 12px/1 var(--f-mono); opacity: .55; }}
.lockup {{ display: flex; align-items: center; gap: clamp(10px, 2vw, 18px); max-width: 100%; }}
.lockup-mark {{ width: clamp(56px, 9vw, 88px); height: auto; flex: none; }}
.word {{ font-size: clamp(28px, 4.4vw, 46px); line-height: 1; white-space: nowrap; }}
.sizes {{ display: flex; flex-wrap: wrap; align-items: flex-end; gap: 20px 28px; padding: 20px 22px; border-bottom: 1px solid var(--line); }}
.sizes figure {{ margin: 0; display: grid; justify-items: center; gap: 8px; }}
.sizes figcaption {{ font: 400 11px/1 var(--f-mono); color: var(--muted); }}
.app {{ width: 72px; height: 72px; border-radius: 16px; display: grid; place-items: center; }}
.app svg {{ width: 46px; height: 46px; }}
.fav {{ padding: 6px; border-radius: 4px; outline: 1px solid var(--line); display: grid; place-items: center; }}
.meta {{ padding: 20px 22px 24px; display: grid; gap: 14px; }}
.meta h2 {{ font-size: 20px; margin: 0 0 6px; letter-spacing: -.01em; font-weight: 600; }}
.tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0; }}
.tags span {{ font-size: 12px; padding: 2px 8px; border: 1px solid var(--line); border-radius: 999px; color: var(--muted); }}
.why {{ margin: 0; max-width: 62ch; }}
.swatches {{ list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 8px 18px; }}
.swatches li {{ display: flex; align-items: center; gap: 8px; font-size: 13px; }}
.chip {{ width: 18px; height: 18px; border-radius: 3px; outline: 1px solid color-mix(in srgb, var(--fg) 18%, transparent); outline-offset: -1px; }}
.swatches code {{ font: 400 12px var(--f-mono); color: var(--muted); }}
.foot {{ margin-top: 40px; color: var(--muted); font-size: 13px; max-width: 75ch; }}
@media (max-width: 860px) {{ .grid, .intro {{ grid-template-columns: minmax(0, 1fr); }} .tile {{ aspect-ratio: auto; min-height: 200px; }} }}
@media (max-width: 440px) {{ .word {{ font-size: 25px; }} .lockup-mark {{ width: 48px; }} }}
</style>
<div class="wrap">
  <section class="intro">
    <div><p class="eyebrow">Brand identity · round one</p><h1>Ten marks for LinguaDojo</h1></div>
    <p class="brief">Brief from ADR-004 and your answers: <b>rigour over comfort</b>, no mascots or game-app gloss, <b>abstract</b> marks only (no ensō or hanko), built from an <b>LD monogram</b>, a <b>correction mark</b> or a <b>loop</b>. Studies 01–03 use your three palettes; 04–10 take pairings from nature.</p>
  </section>
  <div class="grid">{"".join(cards)}</div>
  <p class="foot">Wordmarks are set in live web fonts, so they are typographic sketches. The chosen direction would be redrawn and outlined before production. Each study is also saved as standalone <code>mark.svg</code>, <code>app-icon.svg</code> and <code>lockup.svg</code> files under <code>wiki/design/brand/logos/</code>.</p>
</div>
'''
open(f"{OUT}/logo-studies.html", "w").write(page)
print("ok")
