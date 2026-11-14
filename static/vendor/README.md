# Vendored front-end libraries

Self-hosted copies of the libraries `templates/base.html` used to load from
jsdelivr / cdnjs (latency 2026-11, ADR-042 / TASK-933). Same origin means no
extra DNS + TCP + TLS before first paint, and the files get the app's
compression and one-year caching (`services/static_assets.py`: every
`static/vendor/` path is versioned by its directory name, so it is immutable).

| Directory | Library | License | Source |
|---|---|---|---|
| `bootstrap-5.3.2/` | Bootstrap 5.3.2 (CSS + bundle JS) | MIT (`LICENSE`) | npm `bootstrap@5.3.2`, byte-identical to the jsdelivr files (SRI hashes match) |
| `fontawesome-6.5.1/` | Font Awesome Free 6.5.1 (`all.min.css` + solid/regular woff2 webfonts) | Icons CC BY 4.0, fonts SIL OFL 1.1, code MIT (`LICENSE.txt`) | npm `@fortawesome/fontawesome-free@6.5.1`; `all.min.css` is the cdnjs file minus the four `@font-face` rules for the Brands and v4-compatibility fonts |
| `bootstrap-icons-1.11.2/` | Bootstrap Icons 1.11.2 (CSS + woff2) | MIT (`LICENSE`) | npm `bootstrap-icons@1.11.2` |

All three are free for commercial use. The attribution their licenses require
is the license header kept inside each CSS/JS file plus the license files here:
**do not strip those comments or delete the LICENSE files.** Nothing needs to
be shown to users.

Only `.woff2` font files are shipped (every supported browser reads woff2; the
`.ttf`/`.woff` fallbacks in the CSS are never requested). Font Awesome's Brands
and v4-compatibility fonts are not shipped: no page uses a brand icon (`fab`,
`fa-brands`) or a v4 icon name. Using one means restoring the font file and its
`@font-face` rule from the npm package.

To upgrade: add a new versioned directory, point `base.html` at it, delete the
old one. Do not edit files in place: a `static/vendor/` URL requested without
`?v=` (a font referenced from vendored CSS) is cached for a year.
