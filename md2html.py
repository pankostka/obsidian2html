# -*- coding: utf-8 -*-
r"""
================================================================================
 WHAT THIS IS
   Turns Markdown into a SELF-CONTAINED HTML file - images inlined as data
   URIs, styles inside, no relative links. Such a file survives email,
   SharePoint, a network share, Teams, or a button in a Power BI report.

   It understands Obsidian syntax, because the source is a vault:
     frontmatter        stripped (it would otherwise render as text)
     ![[image.png]]     embeds the image, resolved the way Obsidian does
     ![[image.png|300]] the same, 300 px wide
     ![[Note]]          inlines that note's content (transclusion)
     [[Note]]           a link when the note is in the batch, otherwise text
     [[Note|label]]     the same, with its own label

   A DEAD LINK IS NEVER PRODUCED. When a link target is not part of the
   batch, the link degrades to plain text and the script reports how many
   did. The document goes to a person, and a link that leads nowhere is
   worse than no link at all.

   NO PDF IS PRODUCED HERE. The script used to do it and was called
   md2pdf.py, but printing is a separate job for a separate tool.

 USAGE
   python md2html.py <file.md>                one file -> <slug>.html
   python md2html.py <directory>              a batch, plus index.html
   python md2html.py <input> -o <where>       where to put the result
   python md2html.py <input> --vault <path>   where to look for ![[images]]
   python md2html.py <file.md> --title "Text" a title without touching the source
   python md2html.py <input> --published-only only articles carrying the marker
   python md2html.py <vault> --site -o <where>  site: shared styl.css, img/,
                                              output into the given directory

   Dependency: pip install markdown.

   Exit code 0 = done, 1 = conversion error, 2 = bad arguments.

 FACETED TAG FILTER
   Tags COMBINE WITH AND, they do not replace one another. `Obsidian` plus
   `Video` yields articles about Obsidian that have a video. A tag that would
   yield nothing in combination with those already picked is DIMMED and
   cannot be clicked, so there is no way to click into an empty result. It is
   dimmed rather than hidden: were it to disappear, the bar would jump on
   every click.

   This lives in two places that complement each other:

   hledani.html   the live version. Tags, the text query and the counts are
                  recomputed together - the query also narrows which tags
                  still light up. State lives in the address
                  (`?tag=a&tag=b&q=...`), so it can be sent and restored with
                  the back button. The tag bar is left out there; two rows of
                  tags on one page only confuse.
   tag-*.html     the static version, WITHOUT JavaScript. A tag in the bar
                  leads to hledani.html carrying BOTH tags, so it adds rather
                  than replaces; an unreachable one is already dimmed in the
                  HTML, because the build knows what co-occurs with what.

   Pre-generating the combinations is not an option - twenty tags make a
   million subsets. Hence combining happens in the browser, while individual
   tag pages stay static for the sake of inbound links and search engines.

   NOTE: the filter is only as good as the tagging. When an article carries a
   single tag there is nothing to combine. It pays off with several
   independent axes, say topic plus form (`Video`, `Howto`) plus level.

 THE PUBLISH FLAG
   It is carried by a MARKER IN THE FILENAME - a globe at the end, so
   'Article name X.md'. A missing marker means not public. The frontmatter
   key publish no longer means anything; when the script meets it on an
   article without the marker it says so, because the author most likely
   believes the article is being published.

   The reason is visibility: the file tree shows what is public, whereas
   frontmatter does not. The marker never reaches the address, slug() drops it.

 FRONTMATTER
   title    overrides the document title, otherwise the filename is used
   date     publication date. When missing, the file's date is used and the
            build says so. On equal dates the article name decides
   excerpt  overrides the excerpt, otherwise the first paragraph is used
   slug     overrides the output filename. Normally NOT USED: the address is
            the cleaned-up filename and no slug is maintained. It is an
            escape hatch for the one address that must survive a rename

   The keys are ENGLISH, as are the flags. Article content is Czech, the
   tool's interface is not - it is the only thing a foreign user has to type.
   The old Czech keys datum, titul and perex are not read; the build reports
   them.

 OUTPUTS
   <name>.html    self-contained HTML, images as data URIs
   index.html     in a batch only, an index of the pages

   With --site it works differently: the style sits in a single styl.css next
   to the pages and images go into img/ as files, because in self-contained
   mode a single page with five screenshots weighs 598 kB and the browser
   caches nothing. Plus two checks - an address clash is an error, and the
   letter case of links is verified against the actual files (on Linux
   Foo.png and foo.png are different).

   THE INPUT DIRECTORY IS ONLY EVER READ. The vault is a source, not a
   workspace: the generator creates, changes and deletes nothing in it. It
   used to write two things - a record of published addresses, and a date
   into the frontmatter of an article that lacked one. The record is gone and
   the date now comes from the file's own timestamp.

   -o gives the base of the path and the extension is appended, so
   -o out/help produces help.html.
================================================================================
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
from html import escape, unescape
from urllib.parse import quote, unquote

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

MAX_TRANSCLUSION = 3
ATTACHMENT_DIRS = ('Attachments', 'img', 'assets')

# The directory holding the site inputs: menu.md, index.md, styl.css, logo.
# The leading dot hides it in Obsidian, which is the point - these are not
# articles and they are edited outside Obsidian. The name says which tool owns
# it, so nothing is ambiguous next to .obsidian. collect() skips it thanks to
# that dot anyway.
CONFIG_DIR = '.obsidian2html'

# The publish flag is a MARKER IN THE FILENAME, not a frontmatter key. The
# reason is visibility: the file tree shows which article is public, whereas
# frontmatter does not. A missing marker means not public.
#
# The marker never reaches the address - slug() drops everything that is
# neither \w nor \s. resolve_wikilinks() strips it from link text as well,
# which would otherwise put a globe in the middle of a sentence.
PUBLISH_MARKER = '🌐'

# A marker file inside the output directory. The script may only wipe a
# directory that carries it, or one that is empty. A directory that belongs to
# somebody else survives even a typo in the path.
OUTPUT_MARKER = '.vygenerovano'

# The pseudo-tag for articles without tags. In the bar it is a '#' button, its
# page is called tag-bez-tagu.html and the heading reads 'Bez tagu' - a bare
# hash is useless as a page title, and useless to a screen reader too.
NO_TAG_SLUG = 'bez-tagu'
NO_TAG_LABEL = '#'
NO_TAG_HEADING = 'Bez tagu'


# ==============================================================================
# Vzhled
# ==============================================================================

CSS_CONTENT = """
:root {
  --text: #1a1a1a; --tlum: #5a5a5a; --nadpis: #1f3864;
  --pozadi: #fff; --blok: #f5f5f5; --kod: #f0f0f0;
  --linka: #b8c4d9; --th: #dce6f2; --zebra: #f5f8fc;
  --odkaz: #2b579a; --ram: #c8c8c8;
}
* { box-sizing: border-box; }
body { font-family: "Segoe UI", -apple-system, "Helvetica Neue", Arial, sans-serif;
       font-size: 16px; line-height: 1.6; color: var(--text);
       background: var(--pozadi); max-width: 46rem; margin: 0 auto;
       padding: 2.5rem 1.25rem 4rem; }
h1 { font-size: 1.9rem; line-height: 1.25; margin: 0 0 1.2rem;
     padding-bottom: .4rem; color: var(--nadpis);
     border-bottom: 2px solid var(--odkaz); }
h2 { font-size: 1.35rem; margin: 2.2rem 0 .7rem; color: var(--nadpis); }
h3 { font-size: 1.1rem; margin: 1.6rem 0 .5rem; color: var(--nadpis); }
h4 { font-size: 1rem; margin: 1.3rem 0 .4rem; color: var(--nadpis); }
p, ul, ol { margin: 0 0 .9rem; }
ul, ol { padding-left: 1.4rem; }
li { margin-bottom: .3rem; }
li > ul, li > ol { margin-top: .3rem; }
table { border-collapse: collapse; width: 100%; margin: .6rem 0 1.4rem;
        font-size: .92rem; }
th, td { border: 1px solid var(--linka); padding: .45rem .6rem;
         text-align: left; vertical-align: top; }
th { background: var(--th); font-weight: 600; }
tr:nth-child(even) td { background: var(--zebra); }
.tabulka { overflow-x: auto; }
img { max-width: 100%; height: auto; border: 1px solid var(--ram);
      margin: .4rem 0 1.2rem; }
code { background: var(--kod); padding: .1em .3em; border-radius: 2px;
       font-family: Consolas, "Cascadia Code", "Courier New", monospace;
       font-size: .9em; }
pre { background: var(--blok); border: 1px solid var(--linka); border-radius: 3px;
      padding: .7rem .9rem; overflow-x: auto; }
pre code { background: none; padding: 0; font-size: .85rem; }
blockquote { margin: 0 0 1rem; padding: .1rem 0 .1rem .9rem;
             border-left: 3px solid var(--linka); color: var(--tlum); }
a { color: var(--odkaz); }
strong { color: var(--text); }
hr { border: 0; border-top: 1px solid var(--linka); margin: 2rem 0; }
.rozcestnik { list-style: none; padding: 0; }
.rozcestnik li { margin-bottom: .6rem; }
.rozcestnik a { font-weight: 600; text-decoration: none; }
.paticka { margin-top: 3rem; padding-top: .8rem; border-top: 1px solid var(--linka);
           font-size: .82rem; color: var(--tlum); }
"""

# Chrom webu: hlavicka s logem a listou, paticka, tmavy rezim. Do samostatneho
# souboru pro mail to nepatri - tam neni kam navigovat.
CSS_CHROME = """
/* Text width. A narrow ribbon down the middle of the screen is exactly why
   Obsidian users are told to turn Readable line length off - it is unusable
   for tables and code. Hence 64rem on the site, while the self-contained
   file keeps 46rem.
   Override it in .obsidian2html/styl.css. */
body { max-width: 64rem; padding-top: 1.25rem; }
/* Article masthead: heading, tags below it, the rule below both. In the
   self-contained file the rule stays on the h1, there being no tags. */
.zahlavi { border-bottom: 2px solid var(--odkaz); padding-bottom: .5rem;
           margin-bottom: 1.4rem; }
.zahlavi h1 { border-bottom: 0; padding-bottom: 0; margin-bottom: .35rem; }
.zahlavi .tagy { display: flex; flex-wrap: wrap; gap: .5rem;
                 font-size: .85rem; }
.zahlavi .tagy a { text-decoration: none; color: var(--tlum); }
.zahlavi .tagy a:hover { color: var(--odkaz); }
.jen-ctecka { position: absolute; width: 1px; height: 1px; overflow: hidden;
              clip-path: inset(50%); white-space: nowrap; }

/* The header has two rows: the logo on the left and search on the right,
   with tags underneath. Search in the header is a form - the index lives
   only in hledani.html, so other pages send the query there via ?q=. */
.hlavicka { padding-bottom: .9rem; margin-bottom: 2rem;
            border-bottom: 1px solid var(--linka); }
.pas { display: flex; align-items: center; gap: 1rem 1.5rem; flex-wrap: wrap; }
.pas .logo { display: flex; align-items: center; gap: .6rem;
             text-decoration: none; color: var(--nadpis);
             font-weight: 700; font-size: 1.15rem; letter-spacing: -.01em; }
.pas .logo img { height: 40px; width: auto; border: 0; margin: 0; }
.hledani { display: flex; align-items: center; gap: .6rem; margin-left: auto; }
.hledani input { font: inherit; font-size: .95rem; width: 15rem; max-width: 100%;
                 padding: .4rem .7rem; border: 1px solid var(--linka);
                 border-radius: 999px; background: var(--pozadi);
                 color: var(--text); }
.hledani input:focus { outline: 2px solid var(--odkaz); outline-offset: 1px; }
.hledani button { font: inherit; font-size: .88rem; padding: .4rem .8rem;
                  border: 1px solid var(--odkaz); border-radius: 999px;
                  background: var(--odkaz); color: #fff; cursor: pointer; }
.hledani button:hover { filter: brightness(1.1); }
.hledani .pocet { font-size: .82rem; color: var(--tlum); white-space: nowrap; }
.hlavicka nav { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .8rem; }
.hlavicka nav a { text-decoration: none; font-size: .88rem; color: var(--odkaz);
                  padding: .25rem .6rem; border: 1px solid var(--linka);
                  border-radius: 999px; white-space: nowrap; }
.hlavicka nav a:hover { background: var(--th); }
.hlavicka nav a[aria-current="page"] { background: var(--odkaz); color: #fff;
                                       border-color: var(--odkaz); }
/* An unreachable tag is DIMMED, not hidden. Were it hidden, the bar would
   reflow on every click and the reader would lose track of what sat where. */
.hlavicka nav .zhasnuty { font-size: .88rem; padding: .25rem .6rem;
                          border: 1px solid var(--linka); border-radius: 999px;
                          white-space: nowrap; color: var(--tlum);
                          opacity: .45; cursor: default; }
.hlavicka nav .pocet-tagu { opacity: .6; font-size: .8em; margin-left: .3em; }

/* The faceted filter on the search page. Tags combine with AND. */
.fasety { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1.5rem; }
.stitek { font: inherit; font-size: .88rem; padding: .25rem .6rem;
          border: 1px solid var(--linka); border-radius: 999px;
          background: none; color: var(--odkaz); cursor: pointer;
          white-space: nowrap; }
.stitek:hover { background: var(--th); }
.stitek.vybrany { background: var(--odkaz); color: #fff; border-color: var(--odkaz); }
/* An unreachable tag is DIMMED, not hidden - otherwise the bar jumps on
   every click and one loses track of what sat where. */
.stitek.zhasnuty { color: var(--tlum); opacity: .45; cursor: default; }
.stitek.zrusit { border-style: dashed; }
.stitek .pocet-tagu { opacity: .6; font-size: .8em; margin-left: .35em; }

.paticka { margin-top: 3.5rem; padding-top: 1rem;
           border-top: 1px solid var(--linka);
           font-size: .85rem; color: var(--tlum);
           display: flex; flex-wrap: wrap; gap: .4rem 1.2rem; }
.paticka a { color: var(--tlum); }
.paticka .tagy a { text-decoration: none; }
.paticka .odkazy { margin-left: auto; display: flex; gap: 1rem; }
.paticka .kopie { font: inherit; font-size: .85rem; padding: 0;
                  border: 0; background: none; color: var(--tlum);
                  text-decoration: underline; cursor: pointer; }
.paticka .kopie:hover { color: var(--odkaz); }

/* The excerpt listing is a grid, not a list. auto-fill instead of three
   fixed columns: at 64rem three fit, on a phone one, and no breakpoints
   are needed. */
.vypis { display: grid; gap: 1.2rem; margin-top: 1.4rem;
         grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); }
.karta { padding: 1rem 1.1rem; border: 1px solid var(--linka);
         border-radius: 8px; background: var(--pozadi); }
/* The thumbnail has a fixed height and is cropped, so cards keep their row
   in the grid. Cropping happens from the bottom (object-position: top) - on
   a screenshot the top is the interesting part. The image decorates the
   title sitting right below it, hence the empty alt, so a screen reader
   does not read the same thing twice. */
.karta .nahled { display: block; margin: -1rem -1.1rem .7rem; }
.karta .nahled img { display: block; width: 100%; height: 9rem;
                     object-fit: cover; object-position: top;
                     border: 0; border-radius: 8px 8px 0 0; margin: 0; }
.karta h2 { margin: 0 0 .35rem; font-size: 1.12rem; line-height: 1.3; }
.karta h2 a { text-decoration: none; }
.karta .meta { font-size: .78rem; color: var(--tlum); margin-bottom: .5rem;
               display: flex; flex-wrap: wrap; gap: .6rem; }
.karta p { margin: 0; font-size: .93rem; }
.perex { color: var(--tlum); }
.intro { margin: 0 0 1.6rem; }
.intro > :last-child { margin-bottom: 0; }
.strankovani { display: flex; gap: 1.5rem; margin-top: 2rem;
               font-size: .9rem; align-items: center; }
.strankovani span { color: var(--tlum); }
mark { background: #ffe58a; color: #1a1a1a; padding: 0 .1em; border-radius: 2px; }
html { scroll-behavior: smooth; }

@media (prefers-color-scheme: dark) {
  :root {
    --text: #e6e6e6; --tlum: #a8a8a8; --nadpis: #9db8e8;
    --pozadi: #16181c; --blok: #21242a; --kod: #262a31;
    --linka: #363b45; --th: #22262e; --zebra: #1b1e23;
    --odkaz: #7aa7e8; --ram: #3a3f4a;
  }
  img { opacity: .92; }
  .hlavicka nav a[aria-current="page"] { color: #16181c; }
  mark { background: #6b5a1e; color: #f2e8c8; }
}

@media (max-width: 34rem) {
  body { padding: 1rem .9rem 3rem; }
  .hledani { margin-left: 0; width: 100%; }
  .hledani input { flex: 1; width: auto; }
  .paticka .odkazy { margin-left: 0; }
}
"""

CSS = CSS_CONTENT
CSS_WEB = CSS_CONTENT + CSS_CHROME


HTML = ('<!doctype html><html lang="cs"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>{title}</title><style>{css}</style></head><body>{body}{footer}'
        '</body></html>')

# Web mode: styl je v jednom souboru vedle stranek, ne v kazde z nich. Duvod
# je velikost - v samostatnem rezimu ma jedna stranka se pati screenshoty
# 598 kB, protoze obrazky jsou v base64 a CSS se opakuje.
HTML_WEB = ('<!doctype html><html lang="cs"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>{title}</title>'
            '<link rel="stylesheet" href="styl.css">{head_extra}</head><body>'
            '{header}<main>{body}</main>{footer}'
            '</body></html>')

# Stranka hledani. Index je ZAPECENY uvnitr, protoze pod file:// nepada
# JavaScript, ale fetch() - prohlizec zakaze cteni lokalniho JSON kvuli CORS.
# Zapecenim ta prekazka mizi a tentyz soubor funguje z hostingu i z disku.
SEARCH_PAGE = r"""<h1 class="jen-ctecka">Hledání</h1>
<div id="fasety" class="fasety"></div>
<div id="vysledky"></div>
<noscript>
  <p>Hledání potřebuje JavaScript. Bez něj zbývá seznam všech článků:</p>
  @LIST@
</noscript>
<script>
// The index is BAKED INTO this page, not fetched. Under file:// it is not
// JavaScript that fails but fetch() - the browser refuses to read local JSON
// because of CORS. Baking it in removes that obstacle, and the very same file
// then works from a host and from a disk alike.
//
// The query field lives in the HEADER, so on every page. The index is only
// here, though, so other pages send the query over via ?q=. When a page is
// filtered to a tag it adds ?tag= as well, and only that tag's articles are
// searched.
const ARTICLES = @DATA@;
const NO_TAG = '@NO_TAG@';
// Tag order is taken from the bar, so the eye looks for a tag in the same
// place as everywhere else.
const ALL_TAGS = @TAGS@;

const fold = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// Czech plurals: 1 clanek, 2-4 clanky, 5+ clanku.
const countLabel = n => n + (n === 1 ? ' článek' : (n < 5 ? ' články' : ' článků'));

ARTICLES.forEach(c => {
  c.nTitle = fold(c.title);
  c.nText = fold(c.text);
  c.nTags = fold(c.tags.map(t => t.name).join(' '));
});

const params = new URLSearchParams(location.search);
// Filter state is MUTABLE: a tag is added, not substituted. The tag from the
// address is merely the starting point, it can be worked with afterwards.
let filters = params.getAll('tag').filter(Boolean);
let scope = [];

function matchesTags(c, combo) {
  return combo.every(f => f === NO_TAG ? c.tags.length === 0
                                       : c.tags.some(t => t.name === f));
}

function scopeLabel() {
  if (!filters.length) return '';
  return ' v ' + filters.map(f => f === NO_TAG ? 'článcích bez tagu'
                                               : '#' + f).join(' a ');
}

function score(c, words) {
  let s = 0;
  for (const w of words) {
    if (c.nTitle.includes(w)) s += 5;
    else if (c.nTags.includes(w)) s += 3;
    else if (c.nText.includes(w)) s += 1;
    else return 0;            // every word has to be found
  }
  return s;
}

function snippet(c, word) {
  const i = c.nText.indexOf(word);
  if (i < 0) return esc(c.text.slice(0, 180)) + (c.text.length > 180 ? '…' : '');
  const start = Math.max(0, i - 70);
  const chunk = c.text.slice(start, i + word.length + 110);
  const rel = i - start;
  return (start > 0 ? '…' : '')
    + esc(chunk.slice(0, rel))
    + '<mark>' + esc(chunk.slice(rel, rel + word.length)) + '</mark>'
    + esc(chunk.slice(rel + word.length))
    + (start + chunk.length < c.text.length ? '…' : '');
}

function card(c, label) {
  const tags = c.tags.map(t => '<a href="tag-' + t.slug + '.html">#' + esc(t.name)
                               + '</a>').join(' ');
  const meta = [c.date, tags].filter(Boolean).join(' ');
  const thumb = c.image
    ? '<a class="nahled" href="' + c.url + '"><img src="' + c.image
      + '" alt=""></a>'
    : '';
  return '<article class="karta">' + thumb
       + '<h2><a href="' + c.url + '">' + esc(c.title)
       + '</a></h2>' + (meta ? '<div class="meta">' + meta + '</div>' : '')
       + '<p class="perex">' + label + '</p></article>';
}

function search(query) {
  const words = fold(query).split(/\s+/).filter(Boolean);
  const counter = document.getElementById('pocet');
  const target = document.getElementById('vysledky');
  const grid = items => '<div class="vypis">' + items.join('') + '</div>';

  if (!words.length) {
    counter.textContent = countLabel(scope.length) + scopeLabel();
    target.innerHTML = grid(scope.map(c => card(c, esc(c.excerpt))));
    return;
  }
  const found = scope.map(c => ({ c: c, s: score(c, words) }))
                     .filter(x => x.s > 0)
                     .sort((a, b) => b.s - a.s);
  if (!found.length) {
    counter.textContent = 'nic nenalezeno' + scopeLabel();
    target.innerHTML = '';
    return;
  }
  counter.textContent = (found.length === 1 ? '1 nalezený'
                                            : found.length + ' nalezených')
                        + scopeLabel();
  target.innerHTML = grid(found.map(x => card(x.c, snippet(x.c, words[0]))));
}

// ---------------------------------------------------------------------------
// Faceted filter
//
// Tags COMBINE WITH AND. Adding a tag therefore never grows the set, and once
// the tags that would yield nothing are dimmed, THERE IS NO WAY to click into
// an empty result. That property is what makes the thing usable - it is not
// an accident.
//
// A dimmed tag STAYS where it is. Were it hidden, the bar would reflow on
// every click and one would lose all bearings.
//
// The counts are recomputed on every redraw, the text query included.
// Otherwise they would lie - and a count that lies is worse than no count.
// ---------------------------------------------------------------------------

function countFor(combo, words) {
  return ARTICLES.filter(c => matchesTags(c, combo)
                              && (!words.length || score(c, words) > 0)).length;
}

function renderFacets(words) {
  const target = document.getElementById('fasety');
  const parts = [];
  for (const tag of ALL_TAGS) {
    const selected = filters.includes(tag.name);
    const combo = selected ? filters.filter(f => f !== tag.name)
                           : filters.concat([tag.name]);
    const count = countFor(combo, words);
    if (selected) {
      // No count here, deliberately: on a selected tag the number would mean
      // 'if I remove it', so more than is on screen, and it would read as
      // that tag's article count. How many results there are right now is
      // what the header says.
      parts.push('<button type="button" class="stitek vybrany" data-tag="'
                 + esc(tag.name) + '" aria-pressed="true" title="odebrat filtr">#'
                 + esc(tag.label) + '</button>');
    } else if (count === 0) {
      parts.push('<span class="stitek zhasnuty" aria-disabled="true">#'
                 + esc(tag.label) + '<span class="pocet-tagu">0</span></span>');
    } else {
      parts.push('<button type="button" class="stitek" data-tag="'
                 + esc(tag.name) + '" aria-pressed="false">#' + esc(tag.label)
                 + '<span class="pocet-tagu">' + count + '</span></button>');
    }
  }
  if (filters.length) {
    parts.push('<button type="button" class="stitek zrusit" id="zrusit">'
               + 'zrušit filtr</button>');
  }
  target.innerHTML = parts.join('');
}

function writeUrl(query) {
  // State belongs in the address, so it can be sent and restored with the
  // back button.
  const p = new URLSearchParams();
  filters.forEach(f => p.append('tag', f));
  if (query) { p.set('q', query); }
  const queryString = p.toString();
  history.replaceState(null, '',
                       location.pathname + (queryString ? '?' + queryString : ''));
}

function render() {
  const query = field.value;
  const words = fold(query).split(/\s+/).filter(Boolean);
  scope = ARTICLES.filter(c => matchesTags(c, filters));
  search(query);
  renderFacets(words);
  writeUrl(query);
}

const field = document.getElementById('dotaz');
// On this page nothing is submitted anywhere, searching happens in place.
// The filter has to stay in the form, though, so the next query keeps it.
field.form.addEventListener('submit', e => e.preventDefault());
field.addEventListener('input', render);

document.getElementById('fasety').addEventListener('click', e => {
  if (e.target.id === 'zrusit') { filters = []; render(); return; }
  const chip = e.target.closest('button[data-tag]');
  if (!chip) { return; }
  const tag = chip.getAttribute('data-tag');
  filters = filters.includes(tag) ? filters.filter(f => f !== tag)
                                  : filters.concat([tag]);
  render();
});

const fromUrl = params.get('q');
if (fromUrl) { field.value = fromUrl; }
field.focus();
render();
</script>"""


# A button that copies the article name to the clipboard. A file:// link
# would give away the layout of the disk, and a browser would refuse it from a
# page served over https anyway; the name is harmless, being on screen as the
# title already.
COPY_SCRIPT = r"""<script>
// Copies the article NAME, not the path to the file. The path would give away
// the layout of the disk, and a browser refuses a file:// link from a page
// served over https anyway. The name is enough: in Obsidian CTRL+O takes it,
// and fuzzy matching finds it despite the marker at the end.
(function () {
  var tlacitko = document.getElementById('kopirovat');
  if (!tlacitko) { return; }
  var nazev = tlacitko.getAttribute('data-nazev');
  var puvodni = tlacitko.textContent;

  function hotovo() {
    tlacitko.textContent = 'Zkopírováno';
    setTimeout(function () { tlacitko.textContent = puvodni; }, 1500);
  }

  tlacitko.addEventListener('click', function () {
    // The Clipboard API wants a secure context. file:// counts as one,
    // unencrypted http does not - hence the fallback through a temporary
    // textarea.
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(nazev).then(hotovo, zaloha);
    } else {
      zaloha();
    }
  });

  function zaloha() {
    var pole = document.createElement('textarea');
    pole.value = nazev;
    pole.setAttribute('readonly', '');
    pole.style.position = 'absolute';
    pole.style.left = '-9999px';
    document.body.appendChild(pole);
    pole.select();
    try { document.execCommand('copy'); hotovo(); } catch (e) { /* nic */ }
    document.body.removeChild(pole);
  }
})();
</script>"""


class Error(Exception):
    pass


# ==============================================================================
# Cteni a frontmatter
# ==============================================================================

def read_text(path):
    """Read a .md file. UTF-8 with or without a BOM, falling back to cp1250."""
    with open(path, 'rb') as f:
        data = f.read()
    for encoding in ('utf-8-sig', 'cp1250'):
        try:
            return data.decode(encoding).replace('\r\n', '\n')
        except UnicodeDecodeError:
            continue
    raise Error('Soubor %s neni v UTF-8 ani v cp1250.' % path)


def split_frontmatter(text):
    """Return (meta, body). Without this the frontmatter would render as text.

    Only what is needed gets parsed - flat YAML key: value. No YAML parser, so
    that no dependency is added.
    """
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---', 3)
    if end < 0:
        return {}, text
    head_text = text[4:end]
    body_text = text[end + 4:].lstrip('\n')
    meta = {}
    last_key = None
    for line in head_text.split(chr(10)):
        indented = line[:1] in (' ', chr(9))
        bare = line.strip()
        # The block form of a list, which Obsidian writes on its own:
        #   tags:
        #     - obsidian
        # Without this such a key would stay empty and the article would lose
        # its tags.
        if indented and bare.startswith('- ') and last_key:
            value = bare[2:].strip().strip(chr(34) + chr(39))
            previous = meta.get(last_key) or ''
            meta[last_key] = (previous + ', ' + value).strip(', ')
            continue
        if ':' not in line or indented or bare.startswith('-'):
            continue
        key, _, value = line.partition(':')
        last_key = key.strip().lower()
        meta[last_key] = value.strip().strip(chr(34) + chr(39))
    return meta, body_text


def strip_marker(text):
    """Strip the publish marker off the end of a name, space included."""
    return text.rstrip().rstrip(PUBLISH_MARKER).rstrip()


def is_published(path):
    """Publishing is decided by the MARKER IN THE FILENAME, not by frontmatter.

    This is the only safeguard against publishing something by accident, so
    there has to be exactly one mechanism. If a publish key worked alongside
    the marker, 'a missing marker means not public' would stop holding - and
    that is the one rule worth relying on here.
    """
    stem = os.path.splitext(os.path.basename(path))[0]
    return stem.rstrip().endswith(PUBLISH_MARKER)


# ==============================================================================
# Slug and title
# ==============================================================================

RE_H1 = re.compile(r'^#\s+(.+)$', re.M)


def title_of(meta, path):
    """The title is the FILENAME, or the frontmatter title when given.

    An H1 is not used, because the two cannot be told apart reliably. Tried on
    real data: docs/nsp20DimManazVysl_AX.md has a single H1 and it genuinely is
    the document title, but PKVault/.../Hadicky.md has a single H1 too and it
    reads 'Popis', a section out of a task template. Same structure, different
    meaning.

    The filename is Obsidian's own model (there, a note's name is its title),
    it is unambiguous within a folder and it can be predicted. When the name is
    technical, as with a loading procedure, the frontmatter title overrides it.
    """
    if meta.get('title'):
        return meta['title']
    return strip_marker(os.path.splitext(os.path.basename(path))[0])


def slug(text):
    """The output filename: lower case, no diacritics, hyphens.

    A note's name may carry diacritics, spaces and emoji; a URL may not. The
    slug is therefore computed, never taken over as is.
    """
    plain = unicodedata.normalize('NFKD', text)
    plain = ''.join(c for c in plain if not unicodedata.combining(c))
    plain = re.sub(r'[^\w\s-]', '', plain, flags=re.U).strip().lower()
    plain = re.sub(r'[\s_]+', '-', plain)
    plain = re.sub(r'-{2,}', '-', plain).strip('-')
    return plain or 'nota'


# ==============================================================================
# Obsidian syntax
# ==============================================================================

RE_EMBED = re.compile(r'!\[\[([^\]|#]+?)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]')
RE_WIKILINK = re.compile(r'(?<!!)\[\[([^\]|#]+?)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]')
IMAGE_EXTS = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')

# A fenced code block and inline code. Nothing is substituted inside.
RE_CODE = re.compile(
    r'^(?P<f>```+|~~~+)[^\n]*\n.*?^(?P=f)[ \t]*$'   # ```...```
    r'|(?P<t>`+)[^\n]*?(?P=t)',                     # `...`
    re.M | re.S)


def outside_code(text, substitute):
    """Run the substitution only on the parts of the text OUTSIDE code.

    Without this the converter rewrites its own syntax examples: a note that
    teaches how to write wikilinks has `[[Name]]` as ordinary code, but
    RE_WIKILINK sees a link there, fails to find the target and flattens it to
    plain text. The reader then learns everything about brackets from an
    article on brackets, except the brackets. Verified on Obsidian Markdown.
    """
    parts, pos = [], 0
    for m in RE_CODE.finditer(text):
        parts.append(substitute(text[pos:m.start()]))
        parts.append(m.group(0))
        pos = m.end()
    parts.append(substitute(text[pos:]))
    return ''.join(parts)


def find_file(name, base, vault):
    """Find a file the way Obsidian does: next to the note, in its attachment
    folder, then anywhere in the vault. Returns None when nothing matches."""
    candidates = [os.path.join(base, name)]
    for p in ATTACHMENT_DIRS:
        candidates.append(os.path.join(base, p, name))
    for c in candidates:
        if os.path.isfile(c):
            return c
    wanted = os.path.basename(name).lower()
    for root, dirs, files in os.walk(vault):
        dirs[:] = [a for a in dirs if not a.startswith('.')]
        for s in files:
            if s.lower() == wanted:
                return os.path.join(root, s)
    return None


class Conversion(object):
    """Holds the context of one conversion - where to look and what is in the batch."""

    def __init__(self, vault, batch=None, site=False):
        self.vault = vault
        self.batch = batch or {}      # {slug of a note name: output file}
        self.site = site
        self.flattened = []           # links that degraded to plain text

    # -- transclusion -----------------------------------------------------

    def expand_embeds(self, text, base, depth=0, seen=None):
        seen = set(seen or ())

        def replace(m):
            target, param = m.group(1).strip(), (m.group(2) or '').strip()
            if target.lower().endswith(IMAGE_EXTS):
                width = param if param.isdigit() else None
                return self._image(target, param, width)
            return self._note(target, base, depth, seen, m.group(0))

        return outside_code(text, lambda t: RE_EMBED.sub(replace, t))

    def _image(self, target, param, width):
        """An Obsidian embed carries no alt text, so it is made from the file
        name - a screen reader needs one."""
        # The publish marker is stripped here as well. A screen reader reads alt
        # text out loud, and a globe at the end of a filename means nothing to it.
        alt = param if (param and not param.isdigit()) else \
            strip_marker(os.path.splitext(os.path.basename(target))[0])
        if width:
            return '<img src="%s" alt="%s" width="%s">' % (target, alt, width)
        return '![%s](%s)' % (alt, target)

    def _note(self, target, base, depth, seen, original):
        # The vault's own navigation does not belong on the site - the site has
        # its own header, and links from menu.md point at internal areas, so
        # they would flatten to text. Inside Obsidian ![[menu]] in an article
        # does make sense, so it is merely skipped.
        if self.site and slug(os.path.splitext(target)[0]) == 'menu':
            return ''
        if depth >= MAX_TRANSCLUSION:
            self.flattened.append('%s (prilis hluboka transkluze)' % target)
            return ''
        name = target if target.lower().endswith('.md') else target + '.md'
        path = find_file(name, base, self.vault)
        if not path or os.path.abspath(path) in seen:
            self.flattened.append(target)
            return ''
        _, body_text = split_frontmatter(read_text(path))
        # Drop the embedded note's H1 - the target document already has one
        body_text = RE_H1.sub('', body_text, count=1).strip()
        return self.expand_embeds(body_text, os.path.dirname(path), depth + 1,
                                  seen | {os.path.abspath(path)})

    # -- wikilinks --------------------------------------------------------

    def resolve_wikilinks(self, text):
        def replace(m):
            target, anchor, label = m.group(1).strip(), m.group(2), m.group(3)
            # Without stripping the marker, a sentence like 'carry on to
            # [[Obsidian Controls X]]' would plant a globe in the middle of the
            # prose. Writing an alias on every link would be more work than the
            # frontmatter key the marker replaced.
            link_text = (label or '').strip() or strip_marker(target)
            key = slug(os.path.splitext(os.path.basename(target))[0])
            if key in self.batch:
                href = self.batch[key]
                if anchor:
                    href += '#' + slug(anchor)
                return '[%s](%s)' % (link_text, href)
            self.flattened.append(target)
            return link_text
        return outside_code(text, lambda t: RE_WIKILINK.sub(replace, t))


# ==============================================================================
# Markdown -> HTML
# ==============================================================================

def inline_images(html, base, vault):
    """Replace src="path" with a data URI, so the HTML stands on its own.

    A missing image is an error, not a warning. Quietly, a document with a
    blank space in it would be produced and sent to a person.
    """
    missing = []

    def replace(m):
        link = m.group(1)
        if link.startswith(('http:', 'https:', 'data:', '//')):
            return m.group(0)
        path = find_file(unquote(link), base, vault)
        if not path:
            missing.append(link)
            return m.group(0)
        mime = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        with open(path, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        return 'src="data:%s;base64,%s"' % (mime, data)

    html = re.sub(r'src="([^"]+)"', replace, html)
    if missing:
        raise Error('Chybi obrazky: %s' % ', '.join(sorted(set(missing))))
    return html


def copy_attachment(source, out_dir, renamed):
    """Copy one file into img/ and return its relative address.

    The name goes through slug(), so it is always lower case and ASCII. On
    Linux Foo.png and foo.png differ, which means a mistyped link works on
    Windows and returns 404 on the server. `renamed` guards against two
    different files ending up under one address.
    """
    directory = os.path.join(out_dir, 'img')
    stem, ext = os.path.splitext(os.path.basename(source))
    name = slug(stem) + ext.lower()
    drive = renamed.get(name)
    source = os.path.abspath(source)
    if drive and drive != source:
        raise Error('Dva obrazky maji stejnou adresu %s: %s a %s'
                    % (name, drive, source))
    if not drive:
        if not os.path.isdir(directory):
            os.makedirs(directory)
        shutil.copy2(source, os.path.join(directory, name))
        renamed[name] = source
    return 'img/' + name


def copy_images(html, base, vault, out_dir, renamed):
    """Site mode: src="path" -> src="img/name.ext", and the file is copied.

    A data URI is right for a single self-contained file going out by email,
    but not for a site - every page would carry its own copy of the images and
    of the CSS, and the browser would cache nothing. A shared img/ directory is
    downloaded once.

    The name goes through slug(), so it is always lower case and ASCII. On
    Linux Foo.png and foo.png differ, which means a mistyped link works on
    Windows and returns 404 on the server - a fault found only after deploying.
    """
    missing = []

    def replace(m):
        link = m.group(1)
        if link.startswith(('http:', 'https:', 'data:', '//')):
            return m.group(0)
        path = find_file(unquote(link), base, vault)
        if not path:
            missing.append(link)
            return m.group(0)
        return 'src="%s"' % copy_attachment(path, out_dir, renamed)

    html = re.sub(r'src="([^"]+)"', replace, html)
    if missing:
        raise Error('Chybi obrazky: %s' % ', '.join(sorted(set(missing))))
    return html


def to_html(path, conv, meta=None, title=None,
            out_dir=None, renamed=None, site=None, date=None):
    """Return (title, complete HTML). With out_dir= it typesets site mode.

    `date` is the fallback for an article that has none in its frontmatter. It
    comes from outside because it is already worked out while assembling the
    batch, and the ordering on the front page derives from it - the article's
    own footer has to show the same thing. While the date was written back into
    the source this could not diverge: the frontmatter was read again and the
    date was already in it.
    """
    try:
        import markdown
    except ImportError:
        raise Error('Chybi balicek markdown. Doinstaluj: pip install markdown')

    base = os.path.dirname(os.path.abspath(path))
    own_meta, body_text = split_frontmatter(read_text(path))
    if date and not own_meta.get('date'):
        own_meta['date'] = date
    if meta is not None:
        meta.update(own_meta)
    heading = title or title_of(own_meta, path)

    body_text = conv.expand_embeds(body_text, base)
    body_text = conv.resolve_wikilinks(body_text)
    if out_dir is not None:
        body_text = demote_headings(body_text)

    body = markdown.markdown(body_text, extensions=[
        'tables', 'fenced_code', 'attr_list', 'sane_lists',
    ])
    body = re.sub(r'(<table>.*?</table>)', r'<div class="tabulka">\1</div>',
                  body, flags=re.S)
    if out_dir is None:
        body = inline_images(body, base, conv.vault)
    else:
        body = copy_images(body, base, conv.vault, out_dir, renamed)

    footer = ''
    if own_meta.get('date'):
        footer = '<div class="paticka">%s</div>' % own_meta['date']

    if out_dir is not None:
        # The article title is the only h1 on the page. Sections coming from
        # the markdown sit one level lower, see demote_headings.
        # Heading and tags live in one block, so the rule falls below both. It
        # is therefore on that block rather than on the h1 - in the
        # self-contained file it stays on the h1, see CSS_CONTENT.
        tags = tags_from_meta(own_meta)
        masthead = ['<div class="zahlavi"><h1>%s</h1>' % heading]
        if tags:
            masthead.append('<div class="tagy">%s</div>' % ' '.join(
                '<a href="tag-%s.html">#%s</a>' % (slug(x), x) for x in tags))
        masthead.append('</div>')
        return heading, HTML_WEB.format(
            title='%s - %s' % (heading, site['name']),
            head_extra=site.get('head_extra', ''),
            header=header_html(site),
            body=''.join(masthead) + body,
            footer=footer_html(site, own_meta.get('date'), tags, heading))
    return heading, HTML.format(title=heading, css=CSS, body=body, footer=footer)


# ==============================================================================
# Davka
# ==============================================================================

def tags_from_meta(meta):
    """Tags out of the frontmatter. Handles [a, b] and the block list form."""
    raw = (meta.get('tags') or '').strip().strip('[]')
    return [x.strip().strip('"\'') for x in raw.split(',') if x.strip()]


def demote_headings(text):
    """Push markdown sections one level down, because the h1 is the title.

    Articles use # for their own sections, so without this a page ends up with
    several h1 elements and none of them the title. To a screen reader and to a
    search engine that is a broken structure. A tag in the text (#dwh) is left
    alone - the pattern requires a space after the hash.
    """
    return outside_code(text, lambda t: re.sub(r'^(#{1,5})(\s)', r'#\1\2', t,
                                           flags=re.M))


def menu_items(text, tags, no_tag=False):
    """Bar items as [(label, address, tag)]. Tag is None for a fixed link.

    Without .obsidian2html/menu.md these are all tags in alphabetical order. A
    curated list is needed because there may be twenty tags and the bar would
    fall apart - and alphabetical order need not match what matters.

    A line may be:
      `#obsidian`             a tag, linking to its page
      [Search](hledani.html)  an ordinary link
      [[Article name]]        a link to an article, address derived from the name
    A leading bullet is ignored, so that it can be a list inside Obsidian.
    """
    pseudo = (NO_TAG_LABEL, 'tag-%s.html' % NO_TAG_SLUG, None)
    if not text:
        done = [(t, 'tag-%s.html' % slug(t), t) for t in tags]
        return done + ([pseudo] if no_tag else [])

    items = []
    for line in text.split('\n'):
        r = line.strip().lstrip('-*').strip()
        if not r or r.startswith('>'):
            continue
        # A tag is written in backticks: `#PowerBI`. Without them Obsidian
        # would treat it as a real vault tag and the bar would show up in tag
        # search, where it does not belong - it is site configuration, not
        # content. The backticks are only a wrapper; a bare #tag is still read,
        # so older files keep working.
        if len(r) > 2 and r.startswith('`') and r.endswith('`'):
            r = r[1:-1].strip()
        m = re.match(r'^\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]$', r)
        if m:
            target = m.group(1).strip()
            label = (m.group(2) or strip_marker(target)).strip()
            items.append((label, slug(target) + '.html', None))
            continue
        m = re.match(r'^\[([^\]]+)\]\(([^)]+)\)$', r)
        if m:
            items.append((m.group(1).strip(), m.group(2).strip(), None))
            continue
        if r == NO_TAG_LABEL:
            # A lone hash on a line is the 'articles without tags' pseudo-tag.
            if no_tag:
                items.append(pseudo)
            continue
        if r.startswith('#') and len(r) > 1 and not r[1].isspace():
            tag = r[1:].strip()
            items.append((tag, 'tag-%s.html' % slug(tag), tag))
    # When menu.md never mentions the pseudo-tag, it appends itself - articles
    # without tags would otherwise be reachable from nowhere but the front page.
    if no_tag and pseudo not in items:
        items.append(pseudo)
    return items


def wikilinks_in_intro(text, batch):
    """In the front-page intro, turn [[Note]] and [[Note|label]] into links.

    The intro in `.obsidian2html/index.md` is the only hand-written text on the
    front page, so a set of pointers belongs there - and those point at
    articles. Without this, ADDRESSES would have to be typed into the file
    (`kostkaaxmain.html`), which is exactly what a wikilink avoids: renaming an
    article would quietly break the link.

    A target that is not in the batch stays plain text. No dead link is
    produced, just as in the articles.
    """
    if not batch:
        return text

    def replace(m):
        target, label = m.group(1).strip(), (m.group(2) or '')[1:].strip()
        fpath = batch.get(slug(strip_marker(target)))
        link_text = label or strip_marker(target)
        return '[%s](%s)' % (link_text, fpath) if fpath else link_text

    return outside_code(text, lambda t: re.sub(r'\[\[([^\]|]+?)(\|[^\]]*)?\]\]',
                                          replace, t))


def site_inputs(vault, batch=None):
    """Read menu.md, index.md and styl.css from CONFIG_DIR. All optional.

    The directory slips past collect() thanks to its leading dot, so none of
    those files ever becomes a page - they are inputs for the site, not
    articles.

    The bar may simply be called menu.md. The vault does have its own menu.md
    as a navigation bar, but that one lives elsewhere and nothing can clash
    with it here.
    """
    out_dir = os.path.join(vault, CONFIG_DIR)
    menu = None
    path = os.path.join(out_dir, 'menu.md')
    if os.path.isfile(path):
        _, menu = split_frontmatter(read_text(path))

    intro, home_title = '', None
    path = os.path.join(out_dir, 'index.md')
    if os.path.isfile(path):
        meta, body_text = split_frontmatter(read_text(path))
        home_title = meta.get('title')
        body_text = wikilinks_in_intro(body_text, batch)
        if body_text.strip():
            try:
                import markdown
            except ImportError:
                raise Error('Chybi balicek markdown. Doinstaluj: pip install markdown')
            intro = '<div class="intro">%s</div>' % markdown.markdown(
                body_text, extensions=['tables', 'fenced_code', 'attr_list', 'sane_lists'])
    # Custom styles are APPENDED after the generated ones, so anything can be
    # overridden - width, colours, typeface. The colours are tokens in :root, so
    # a change is a single line. Without this one would have to edit the
    # generator itself.
    custom_css = ''
    path = os.path.join(out_dir, 'styl.css')
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            custom_css = f.read()
    return menu, intro, home_title, custom_css


def combination_url(tags):
    """Adresa stranky hledani s predvybranymi tagy."""
    return 'hledani.html?' + '&'.join('tag=%s' % quote(t) for t in tags)


def header_html(site, active=None, active_tag=None, reachable=None,
                  fixed_only=False):
    """Logo vlevo, lista z tagu vpravo. Na kazde strance.

    Logo NENI h1. Ten patri titulku clanku a dve prvni urovne nadpisu na jedne
    strance jsou problem pro ctecky pro nevidome i pro vyhledavace.

    `jen_pevne` vynecha z listy stitky tagu a nechá jen pevne polozky. Je to
    pro stranku hledani, kde tagy obsluhuje fasetovy filtr - dve rady stitku,
    jedna ziva a jedna odkazova, jsou na jedne strance zmatek.

    LISTA TAGY PRIDAVA, NENAHRAZUJE. Na nezafiltrovane strance vede stitek na
    svou stranku tagu, jako drive. Na strance tagu ale vede na hledani s OBEMA
    tagy, takze druhy klik zuzuje misto toho, aby prvni filtr zahodil. Tag,
    ktery se s tim aktivnim v zadnem clanku nepotkava, se ztlumi - `dosazitelne`
    je mnozina tagu, ktere s aktivnim filtrem neco vrati. Diky tomu se nedá
    proklikat do prazdna, a to i bez JavaScriptu.

    Ztlumi se i tag, ktery v liste je, ale zadny publikovany clanek ho nema -
    jeho stranka nevznikne, takze odkaz by nikam nevedl.
    """
    name = site['name']
    if site.get('logo'):
        mark = '<img src="%s" alt="%s">' % (site['logo'], name)
    else:
        mark = name
    # Radek 1: logo vlevo, hledani vpravo. Radek 2: tagy odleva.
    # Pole hledani je na KAZDE strance, ale index lezi jen ve hledani.html -
    # odtud tedy formular odesila dotaz tam pres ?q=. Kdyby index nesla kazda
    # stranka, platila by se jeho velikost pri kazdem nacteni.
    parts = ['<header class="hlavicka">', '<div class="pas">',
            '<a class="logo" href="index.html">%s</a>' % mark,
            '<form class="hledani" action="hledani.html" method="get">',
            '<input type="search" name="q" id="dotaz" placeholder="Hledat…"',
            ' autocomplete="off" aria-label="Hledaný výraz">',
            # Tlacitko je tu zamerne, i kdyz Enter v jedinem poli formular
            # odesle sam: explicitni submit je jednoznacny ve vsech prohlizecich
            # a na mobilu se da klepnout. Na strance hledani ho skript zneskodni.
            '<button type="submit">Hledat</button>',
            # Kdyz je stranka zafiltrovana na tag, formular ten tag prilozi a
            # hledani probehne jen v jeho clancich. Bez toho by dotaz ze stranky
            # tagu prohledal cely web a kontext by se ztratil.
            ('<input type="hidden" name="tag" value="%s">' % active_tag)
            if active_tag else '',
            '<span class="pocet" id="pocet"></span>',
            '</form>', '</div>', '<nav>']
    for label, url, tag in site['menu']:
        if fixed_only and (tag or url == 'tag-%s.html' % NO_TAG_SLUG):
            continue
        # aktivni je bud nazev tagu, nebo nazev souboru - aby se dala zvyraznit
        # i pevna polozka, treba Hledani.
        is_current = (tag and tag == active) or url == active
        if tag and tag not in site['tags']:
            # Kuratorovana polozka pro tag, ktery zadny publikovany clanek
            # nema, takze jeho stranka nevznikne. ZTLUMI SE, nezplosti:
            # zkontroluj_odkazy by z odkazu udelal holy text a v liste by mezi
            # stylovanymi pilulkami sedelo neostylovane slovo. Ztlumena pilulka
            # rekne totez a nerozbije radek. Build to navic ohlasi.
            parts.append('<span class="zhasnuty" aria-disabled="true"'
                        ' title="zatím nemá publikovaný článek">%s</span>'
                        % label)
        elif is_current:
            # Aktivni stitek odbira filtr, tedy vraci na titulku.
            parts.append('<a href="index.html" aria-current="page">%s</a>' % label)
        elif tag and active_tag:
            if reachable is not None and tag not in reachable:
                parts.append('<span class="zhasnuty" aria-disabled="true"'
                            ' title="s #%s se nepotkává v žádném článku">%s</span>'
                            % (active_tag, label))
            else:
                parts.append('<a href="%s">%s</a>'
                            % (combination_url([active_tag, tag]), label))
        else:
            parts.append('<a href="%s">%s</a>' % (url, label))
    parts.append('</nav></header>')
    if not site['menu']:
        # Zadny tag - prazdny <nav> by nechal ve strance zbytecny radek.
        parts = [k for k in parts if k not in ('<nav>', '</nav></header>')]
        parts.append('</header>')
    return ''.join(parts)


def footer_html(site, date=None, tags=(), name=None):
    """Datum, tagy clanku a odkazy. U clanku k tomu tlacitko na kopii nazvu."""
    casti = []
    if date:
        casti.append('<span>%s</span>' % date)
    if tags:
        casti.append('<span class="tagy">%s</span>' % ' '.join(
            '<a href="tag-%s.html">#%s</a>' % (slug(t), t) for t in tags))
    links = []
    if name:
        links.append('<button type="button" id="kopirovat" class="kopie"'
                      ' data-nazev="%s">Zkopírovat název</button>'
                      % name.replace('"', '&quot;'))
    links.append('<a href="index.html">Titulka</a>')
    if site.get('search'):
        links.append('<a href="hledani.html">Hledání</a>')
    if site.get('rss'):
        links.append('<a href="rss.xml">RSS</a>')
    links.append('<a href="#">Nahoru</a>')
    casti.append('<span class="odkazy">%s</span>' % ''.join(links))
    skript = COPY_SCRIPT if name else ''
    return '<footer class="paticka">%s</footer>%s' % (''.join(casti), skript)


def site_page(titulek_stranky, content, site, active=None, active_tag=None,
                reachable=None, fixed_only=False):
    """Obali obsah hlavickou a patickou. Pro titulku a stranky tagu."""
    return HTML_WEB.format(title='%s - %s' % (titulek_stranky, site['name']),
                           head_extra=site.get('head_extra', ''),
                           header=header_html(site, active, active_tag,
                                                  reachable, fixed_only),
                           body=content,
                           footer=footer_html(site))


PER_PAGE = 12          # kolik perexu se vypise na jednu stranku
                         # Dvanact proto, ze vypis je mrizka po trech - deset by
                         # nechalo posledni radek s jednou kartou.


EXCERPT_IMAGE_LIMIT = 300 * 1024   # nad tuhle velikost se ozve build


def excerpt_image(cesta_clanku):
    """Najde obrazek k perexu: v Attachments vedle clanku, stejneho nazvu.

    Porovnava se pres slug(), takze sedne kterykoli zapis - "Obsidian Co je",
    "obsidian-co-je" i "obsidian_co_je". Standard chce prilohy malymi pismeny s
    podtrzitkem, kdezto clanek ma mezery a diakritiku; tolerance obe konvence
    smiruje, misto aby nutila jednu z nich porusit.

    Marker publikace se z nazvu clanku strhava - v nazvu prilohy nema co delat.
    """
    directory = os.path.join(os.path.dirname(cesta_clanku), 'Attachments')
    if not os.path.isdir(directory):
        return None
    wanted = slug(strip_marker(os.path.splitext(os.path.basename(cesta_clanku))[0]))
    for fname in sorted(os.listdir(directory)):
        stem, ext = os.path.splitext(fname)
        if ext.lower() in IMAGE_EXTS and slug(stem) == wanted:
            return os.path.join(directory, fname)
    return None


def strip_images(text):
    """Vyhodi z textu obrazky, oba zapisy: ![[embed]] i ![alt](cesta).

    Perex se transkluzi zamerne neprohani, takze bez tohohle by v nem zustala
    hola syntaxe ![[...]] jako text.
    """
    text = RE_EMBED.sub('', text)
    return re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)


def excerpt(body_text, meta, conv):
    """Perex je PRVNI ODSTAVEC clanku, frontmatter klic perex ho prebije.

    Prvni odstavec se bere proto, ze uz je napsany - clanky tak zacinaji a
    delky vychazi na 70 az 230 znaku, tedy presne perexove. Rucni klic je pro
    pripad, kdy se uvod na vypis nehodi.

    Nadpis ukoncuje hledani: kdyz clanek zacina hned sekci, perex nema byt
    prvni veta te sekce, ale zadny.

    Obrazek perex neukoncuje, jen z nej vypadne - je to textova upoutavka a
    nahled ma karta vlastni. Odstavec, ktery obrazkem zacina a pokracuje
    textem, tedy perex DA; teprve kdyz po vyhozeni obrazku nezbyde nic, byl
    to samostatny uvodni obrazek a hleda se dal.
    """
    try:
        import markdown
    except ImportError:
        raise Error('Chybi balicek markdown. Doinstaluj: pip install markdown')

    source = (meta.get('excerpt') or '').strip()
    if not source:
        for block in body_text.strip().split('\n\n'):
            b = block.strip()
            if b.startswith('#'):
                break
            # Citace, tabulka, seznam a kod perexem nejsou ani po ocisteni.
            # Obrazek v tomhle vyctu NENI: ten se z odstavce vyhodi a rozhodne
            # az to, jestli po nem zbyl text.
            if not b or b.startswith(('>', '|', '- ', '* ', '1. ', '```')):
                continue
            b = strip_images(b).strip()
            if not b:
                continue
            # Nadpis muze nasledovat hned na dalsim radku bez prazdneho radku
            # mezi tim - pak je v temze bloku a musi se uriznout, jinak by se
            # do perexu vlil nadpis i zacatek prvni sekce.
            source = re.split(r'^#+\s', b, maxsplit=1, flags=re.M)[0].strip()
            if not source:
                break
            break
    if not source:
        return ''
    # Rucne psany perex z frontmatteru obrazkem taky projde. Automaticky uz
    # ocisteny je, druhy pruchod na nem nic nezmeni.
    source = strip_images(source)
    # Wikilinky i v perexu, aby odkaz z titulky vedl nekam. Marker se strhava
    # stejne jako v tele clanku.
    # Po vyhozeni obrazku zbyde dvojita mezera, proto se bily znaky srazi.
    source = re.sub(r'\s+', ' ', source).strip()
    source = conv.resolve_wikilinks(source)
    html = markdown.markdown(source).strip()
    m = re.match(r'^<p>(.*)</p>$', html, re.S)
    return m.group(1) if m else html


def card(c):
    """Jeden clanek na vypisu: titulek, datum s tagy, perex."""
    parts = ['<article class="karta">']
    if c.get('image'):
        parts.append('<a class="nahled" href="%s"><img src="%s" alt=""></a>'
                    % (c['file'], c['image']))
    parts.append('<h2><a href="%s">%s</a></h2>' % (c['file'], c['heading']))
    popisky = []
    if c['date']:
        popisky.append(c['date'])
    if c['tags']:
        popisky.append(' '.join('<a href="tag-%s.html">#%s</a>' % (slug(t), t)
                                for t in c['tags']))
    if popisky:
        parts.append('<div class="meta">%s</div>' % ' '.join(popisky))
    if c['excerpt']:
        parts.append('<p class="perex">%s</p>' % c['excerpt'])
    parts.append('</article>')
    return ''.join(parts)


def page_name(base, number):
    """Prvni stranka je bez cisla, aby adresa titulky byla index.html."""
    return base + ('.html' if number == 1 else '-%d.html' % number)


def pagination(base, number, total):
    """Odkazy vpred a vzad. Staticke, zadny skript."""
    if total < 2:
        return ''
    parts = []
    if number > 1:
        parts.append('<a href="%s">&larr; Novější</a>'
                    % page_name(base, number - 1))
    parts.append('<span>Stránka %d z %d</span>' % (number, total))
    if number < total:
        parts.append('<a href="%s">Starší &rarr;</a>'
                    % page_name(base, number + 1))
    return '<nav class="strankovani">%s</nav>' % ''.join(parts)


def card_grid(clanky, base, heading, site, active=None, intro='',
                 skryty_nadpis=False, active_tag=None, reachable=None):
    """Vrati [(nazev_souboru, html)] - strankovany vypis perexu po NA_STRANKU.

    Prazdny seznam da jednu prazdnou stranku, aby lista neodkazovala nikam.
    """
    stranky = [clanky[i:i + PER_PAGE]
               for i in range(0, len(clanky), PER_PAGE)] or [[]]
    result = []
    for number, chunk in enumerate(stranky, start=1):
        # Na titulce je nadpis SKRYTY, ne odstraneny: stranka bez h1 je rozbita
        # struktura pro ctecky pro nevidome i pro vyhledavace. Na strankach tagu
        # zustava videt, protoze rika, podle ceho je vyfiltrovano.
        trida = ' class="jen-ctecka"' if skryty_nadpis else ''
        content = ['<h1%s>%s</h1>' % (trida, heading)]
        # Uvod jen na prvni strance - na index-2 uz by se opakoval.
        if number == 1 and intro:
            content.append(intro)
        content.append('<div class="vypis">')
        content.extend(card(c) for c in chunk)
        content.append('</div>')
        content.append(pagination(base, number, len(stranky)))
        titulek_stranky = heading if number == 1 else '%s, strana %d' % (heading, number)
        result.append((page_name(base, number),
                         site_page(titulek_stranky, ''.join(content), site,
                                     active, active_tag, reachable)))
    return result




def text_from_html(html):
    """Cisty text pro index hledani: znacky pryc, entity zpatky.

    Bere jen obsah <main>, tedy telo clanku. Hlavicka a paticka jsou na kazde
    strance stejne, takze by dotaz na kterykoli tag z listy nasel VSECHNY
    clanky - overeno, slovo PowerBI bylo v textu sedmi clanku ze sedmi.
    """
    body_text = re.search(r'(?s)<main>(.*?)</main>', html)
    if body_text:
        html = body_text.group(1)
    bez_kodu = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', html)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', bez_kodu))).strip()


def search_page(articles, site):
    """Vrati HTML stranky hledani s indexem zapecenym uvnitr.

    Rozsah, na ktery je to stavene: pet clanku PKVault ma 24 kB textu, cely
    vault 91 kB. Dokud se index vejde do jednotek MB, zustava zapeceny; pri
    radove vetsim webu by se musel nacitat zvlast - a tim by padl beh z lokalu,
    takze to bude rozhodnuti, ne technicky detail.
    """
    data = []
    for c in articles:
        data.append({'title': c['heading'], 'url': c['file'],
                     'date': c['date'], 'excerpt': text_from_html(c['excerpt']),
                     'text': c['text'], 'image': c.get('image'),
                     'tags': [{'name': x, 'label': x, 'slug': slug(x)}
                              for x in c['tags']]})
    # Sekvence </ se v datech rozdeli, aby retezec ve clanku nemohl uzavrit
    # element script driv, nez ma.
    cards = json.dumps(data, ensure_ascii=False).replace('</', '<' + chr(92) + '/')

    plain = ['<ul class="rozcestnik">']
    for c in articles:
        plain.append('<li><a href="%s">%s</a></li>' % (c['file'], c['heading']))
    plain.append('</ul>')

    # Poradi prebira lista, aby oko hledalo tag na temze miste jako jinde.
    # Tagy, ktere v liste nejsou, se pripoji za ni abecedne.
    #
    # LISTA JE KURATOROVANA, FILTR JE UPLNY. Duvod, proc `.obsidian2html/menu.md`
    # vybira, je sirka hlavicky - dvacet stitku v ni prestane fungovat. Filtr
    # ale ma vlastni misto na vlastni strance, takze stitky unese vsechny, a
    # tag, ktery ma stranku, musi byt filtrovatelny. Jinak by kuratorovani listy
    # tise vyradilo tag z filtru a nikdo by nevedel proc.
    chips = []
    in_menu = set()
    for label, url, tag in site['menu']:
        if tag:
            chips.append({'name': tag, 'label': label})
            in_menu.add(tag)
        elif url == 'tag-%s.html' % NO_TAG_SLUG:
            chips.append({'name': NO_TAG_SLUG, 'label': NO_TAG_LABEL})
            in_menu.add(NO_TAG_SLUG)
    for tag in site['tags']:
        if tag not in in_menu:
            chips.append({'name': tag, 'label': tag})
    if NO_TAG_SLUG not in in_menu and any(not c['tags'] for c in articles):
        chips.append({'name': NO_TAG_SLUG, 'label': NO_TAG_LABEL})

    content = (SEARCH_PAGE.replace('@DATA@', cards)
                    .replace('@TAGS@', json.dumps(chips, ensure_ascii=False))
                    .replace('@LIST@', ''.join(plain))
                    .replace('@NO_TAG@', NO_TAG_SLUG))
    return site_page('Hledání', content, site, 'hledani.html', fixed_only=True)


RSS_ITEMS = 20         # kolik nejnovejsich clanku jde do feedu

# Nazvy dnu a mesicu ANGLICKY a natvrdo. RFC 822 jine nepripousti a locale by
# na ceskych Windows vyrobilo "So, 28 srp", tedy nevalidni feed.
RSS_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
RSS_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def rfc822(date):
    """2026-08-28 -> Fri, 28 Aug 2026 00:00:00 +0000. Vraci None pri nesmyslu."""
    try:
        d = time.strptime(date, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None
    return '%s, %02d %s %d 00:00:00 +0000' % (RSS_DAYS[d.tm_wday], d.tm_mday,
                                              RSS_MONTHS[d.tm_mon - 1], d.tm_year)


def xml_text(s):
    """Escapovani pro textovy uzel. Perex smi obsahovat odkazy a tucny text,
    takze bez tohohle by vznikl nevalidni feed."""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def rss(clanky, site, url):
    """Feed z nejnovejsich clanku. Do feedu jde PEREX, ne cely clanek.

    Cely text by s sebou vzal i obrazky, jejichz relativni cesty by ve ctecce
    nevedly nikam. Perex a odkaz je slusne a soubor zustane maly.

    Odkazy musi byt ABSOLUTNI - proto se adresa zadava prepinacem. Zbytek webu
    je zamerne relativni, aby sel otevrit z disku, ale to ve feedu neplati:
    ten cte ctecka nekde jinde.

    lastBuildDate zamerne chybi. S nim by se soubor menil pri kazdem buildu i
    beze zmeny obsahu a pri rucnim nahravani by se zbytecne prenasel.
    """
    base = url.rstrip('/')
    label = site.get('description') or site['name']
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
             '<channel>',
             '<title>%s</title>' % xml_text(site['name']),
             '<link>%s/</link>' % base,
             '<description>%s</description>' % xml_text(label),
             '<language>cs</language>',
             '<atom:link href="%s/rss.xml" rel="self" type="application/rss+xml"/>'
             % base]

    for c in clanky[:RSS_ITEMS]:
        url = '%s/%s' % (base, c['file'])
        lines.append('<item>')
        lines.append('<title>%s</title>' % xml_text(c['heading']))
        lines.append('<link>%s</link>' % url)
        lines.append('<guid isPermaLink="true">%s</guid>' % url)
        kdy = rfc822(c['date'])
        if kdy:
            lines.append('<pubDate>%s</pubDate>' % kdy)
        for tag in c['tags']:
            lines.append('<category>%s</category>' % xml_text(tag))
        if c['excerpt']:
            lines.append('<description>%s</description>'
                         % xml_text(text_from_html(c['excerpt'])))
        lines.append('</item>')

    lines.extend(['</channel>', '</rss>', ''])
    return '\n'.join(lines)


def find_logo(vault, out_dir):
    """Logo je vstup pro web, tedy .obsidian2html/logo.svg nebo .png.

    Kdyz neni, hlavicka vysadi nazev webu jako text. Placeholder si skript
    nevymysli - logo je vec autora.
    """
    for ext in ('.svg', '.png'):
        source = os.path.join(vault, CONFIG_DIR, 'logo' + ext)
        if os.path.isfile(source):
            directory = os.path.join(out_dir, 'img')
            if not os.path.isdir(directory):
                os.makedirs(directory)
            name = 'logo' + ext
            shutil.copy2(source, os.path.join(directory, name))
            return 'img/' + name
    return None


def file_date(path):
    """Vrati datum posledni zmeny souboru jako YYYY-MM-DD. NEZAPISUJE.

    Zaloha pro clanek, ktery datum ve frontmatteru nema. Rozhodnuti publikovat
    nese marker v nazvu, takze chybejici datum nema byt duvod, aby build spadl.

    Je to vratke: datum souboru se meni pri kopirovani vaultu i pri
    synchronizaci, takze poradi na titulce se muze preskladat. Alternativou by
    byl git, ten ale ve vstupnim adresari fungovat nemusi. Pri shode dat
    rozhoduje nazev clanku, takze build je aspon opakovatelny.

    Drive se datum ZAPISOVALO do frontmatteru zdroje. Uz ne - do vstupniho
    adresare se jen cte.
    """
    return time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(path)))

def clean_output(out_dir):
    """Zabali predchozi vystup do archivu a vyprazdni adresar.

    Smaze se vsechno a postavi znovu, protoze chirurgicky uklid podle seznamu
    vyrobenych souboru je zbytecna masinerie. Puvodni obava z plosneho mazani
    se resi tim archivem - predchozi stav zustava po ruce.

    MAZE SE JEN ADRESAR SE ZNACKOU, nebo prazdny, nebo neexistujici. Cizi
    adresar se tim nesmaze ani pri preklepu v ceste; z 'nepravdepodobne' se
    tak stava 'nemozne'.

    Maze se OBSAH, ne adresar sam - kdyz ho ma neco otevrene (prohlizec, FTP
    klient), smazani adresare selze na Device or resource busy.
    """
    if not os.path.isdir(out_dir):
        return None
    content = os.listdir(out_dir)
    if not content:
        return None
    if not os.path.isfile(os.path.join(out_dir, OUTPUT_MARKER)):
        raise Error('Adresar %s neni od tohoto skriptu (chybi %s) a nebude se '
                    'mazat. Zkontroluj cestu.' % (out_dir, OUTPUT_MARKER))

    archiv = os.path.join(os.path.dirname(os.path.abspath(out_dir)), '_archiv')
    if not os.path.isdir(archiv):
        os.makedirs(archiv)
    # Archiv lezi O UROVEN VYS, ne uvnitr baleneho adresare - jinak by se kazda
    # zaloha zabalila do te pristi a rostly by geometricky.
    # Sekundy v nazvu jsou nutne: dva behy v tez minute by si archiv PREPSALY
    # a starsi verze by tise zmizela. Overeno - stalo se pri testovani.
    base = os.path.join(archiv, '%s-%s' % (os.path.basename(os.path.abspath(out_dir)),
                                             time.strftime('%Y-%m-%d-%H%M%S')))
    # A jeste pojistka na sekundu: kdyz uz archiv toho jmena existuje, prida
    # se cislo. Zaloha se nesmi prepsat nikdy, ani pri dvou behech v tez
    # sekunde - overeno, stane se to pri skriptovanem pusteni za sebou.
    if os.path.exists(base + '.zip'):
        n = 2
        while os.path.exists('%s-%d.zip' % (base, n)):
            n += 1
        base = '%s-%d' % (base, n)
    fpath = shutil.make_archive(base, 'zip', root_dir=out_dir)

    for fname in content:
        path = os.path.join(out_dir, fname)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    return fpath


def check_links(out_dir):
    """Overi relativni odkazy ve vystupu a mrtve zplosti na text.

    Rozlisuji se tri pripady, protoze kazdy znamena neco jineho:

    - CIL EXISTUJE V JINE VELIKOSTI PISMEN je chyba. Windows velikost
      nerozlisuje, Linux ano, takze takovy odkaz funguje lokalne a na serveru
      vrati 404 - a je to preklep, ktery se ma opravit, ne schovat.
    - CHYBEJICI OBRAZEK (src) je chyba. V tichosti by vznikla stranka s
      prazdnym mistem.
    - CHYBEJICI CIL ODKAZU (href) se ZPLOSTI na text a nahlasi. Dokumentace
      projektu bezne odkazuje na soubory v repu - ../20_fact/nsp20Fact.sql:179
      - coz je uvnitr repa spravne a na webu nesmysl. Zplostenim zustane
      ctenari informace, ktery soubor to je, a build projde. Je to totez, co
      uz delaji wikilinky mimo davku.

    Vraci seznam zplostenych odkazu.
    """
    files, uppercase = set(), []
    for root, _, jmena in os.walk(out_dir):
        for s in jmena:
            rel = os.path.relpath(os.path.join(root, s), out_dir).replace(os.sep, '/')
            files.add(rel)
            if s != s.lower() and not s.startswith('.'):
                uppercase.append(rel)
    male = dict((s.lower(), s) for s in files)

    bad, flattened = [], []
    for rel in sorted(files):
        if not rel.endswith('.html'):
            continue
        path = os.path.join(out_dir, rel)
        with open(path, encoding='utf-8') as f:
            html = f.read()
        # Skript pryc: retezce ve JS, ktere se skladaji do adresy
        # ('tag-' + t.slug + '.html'), nejsou odkazy a kontrola by na nich
        # spadla. Stranka hledani je toho plna.
        bez_skriptu = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', html)

        dead = []
        for atribut, link in re.findall(r'(href|src|action)="([^"]+)"', bez_skriptu):
            # file: je v clanku o odkazech zamerna ukazka, ne rozbity odkaz.
            if link.startswith(('http:', 'https:', 'mailto:', 'data:', 'file:',
                                 '#', '//')):
                continue
            target = unquote(link.split('#')[0].split('?')[0])
            if not target or target in files:
                continue
            if target.lower() in male:
                bad.append('%s: %s -> na Linuxu 404, soubor se jmenuje %s'
                              % (rel, link, male[target.lower()]))
            elif atribut == 'src':
                bad.append('%s: %s -> obrazek ve vystupu neni' % (rel, link))
            elif link not in dead:
                dead.append(link)

        for link in dead:
            updated, how_many = re.subn(
                r'<a\b[^>]*href="%s"[^>]*>(.*?)</a>' % re.escape(link),
                r'\1', html, flags=re.S)
            if how_many:
                html = updated
                flattened.append('%s: %s (%dx)' % (rel, link, how_many))
        if dead:
            with open(path, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)

    if uppercase:
        bad.append('velka pismena v nazvu vystupu: %s' % ', '.join(sorted(uppercase)))
    if bad:
        raise Error('Vadne odkazy ve vystupu (%d):\n  %s'
                    % (len(bad), '\n  '.join(bad)))
    return flattened


# Klice frontmatteru, ktere se prejmenovaly do anglictiny. Kdyz na stary
# narazime, clanek by tise prisel o datum nebo titulek, takze se to ohlasi.
STARE_KLICE = {'datum': 'date', 'titul': 'title', 'perex': 'excerpt'}


def collect(src, published_only):
    """Vrati ([(path, meta, body)], forgotten, legacy) pro soubor nebo adresar.

    forgotten jsou clanky s frontmatter klicem publish, ktere marker nemaji.
    Klic uz nic neznamena, takze takovy clanek na web nejde - a autor si
    nejspis mysli opak. Mlcet o tom by znamenalo, ze mu clanek tise nevyjde.

    legacy jsou clanky se starym ceskym klicem. Stejny duvod: klic se necte,
    takze by clanek tise prisel o datum nebo titulek.
    """
    if os.path.isfile(src):
        paths = [src]
    else:
        paths = []
        for root, dirs, files in os.walk(src):
            dirs[:] = [a for a in dirs
                           if not a.startswith(('.', '_')) and a not in ATTACHMENT_DIRS]
            paths.extend(os.path.join(root, s) for s in sorted(files)
                         if s.lower().endswith('.md'))
    result, forgotten, legacy = [], [], []
    for c in paths:
        meta, body_text = split_frontmatter(read_text(c))
        if published_only and not is_published(c):
            if 'publish' in meta:
                forgotten.append(c)
            continue
        for old, new in sorted(STARE_KLICE.items()):
            if old in meta and new not in meta:
                legacy.append((c, old, new))
        result.append((c, meta, body_text))
    return result, forgotten, legacy


def index_page(items):
    lines = ['<h1>Obsah</h1>', '<ul class="rozcestnik">']
    for c in sorted(items, key=lambda x: x['heading'].lower()):
        lines.append('<li><a href="%s">%s</a></li>'
                     % (c['file'], c['heading']))
    lines.append('</ul>')
    css = CSS.replace('@SIZE@', 'A4')
    return HTML.format(title='Obsah', css=css, body='\n'.join(lines), footer='')


# ==============================================================================
# Hlavni program
# ==============================================================================

def main():
    p = argparse.ArgumentParser(
        description='Turn an Obsidian vault into HTML.')
    p.add_argument('input', help='.md file or a directory')
    p.add_argument('-o', '--out', help='output file or directory')
    p.add_argument('--vault', help='where to look for ![[images]]'
                                   ' (default: the input directory)')
    p.add_argument('--title', help='title for a single file, when editing the'
                                   ' source is not wanted (otherwise the'
                                   ' frontmatter title, otherwise the filename)')
    p.add_argument('--published-only', action='store_true',
                   help='only articles carrying the publish marker in the name')
    p.add_argument('--site', action='store_true',
                   help='site mode: shared styl.css, images into img/.'
                        ' Requires -o and implies --published-only')
    p.add_argument('--base-url', help='absolute address of the site, e.g.'
                                      ' https://pankostka.cz. Without it no'
                                      ' rss.xml is written, because a feed'
                                      ' cannot carry relative links')
    p.add_argument('--check', action='store_true',
                   help='only verify that the site builds: writes to a temporary'
                        ' directory and touches nothing else. For a git hook')
    p.add_argument('--clean', action='store_true',
                   help='before building, archive the previous output into'
                        ' _archiv and empty the output directory (site mode only)')
    p.add_argument('--site-name', help='name of the site, used in the header and'
                                       ' in page titles (default: the vault'
                                       ' directory name)')
    args = p.parse_args()

    if not os.path.exists(args.input):
        print('CHYBA: vstup neexistuje: %s' % args.input)
        return 2

    # Web mode bez filtru by vysypal na internet cely vault. Neni to
    # pohodli, je to pojistka.
    # Kontrolni rezim je web mode, ktery stavi do docasneho adresare a vysledek
    # zahodi. Je pro git hook, ktery chce vedet, jestli se web vubec postavi.
    # Do vaultu uz nezapisuje zadny rezim, viz zaruka Z45.
    if args.check:
        args.site = True
    if args.site:
        args.published_only = True
    # Kam se zapisuje, urcuje parametr - zadna vychozi cesta v kodu. Vystup
    # patri mimo repo i mimo vault a jen autor vi kam, viz zaruka Z50.
    if args.site and not args.out and not args.check:
        print('CHYBA: --web potrebuje -o, tedy kam se ma web postavit.')
        return 2

    if args.clean and not args.site:
        print('CHYBA: --uklid ma smysl jen s --web.')
        return 2

    batch_mode = os.path.isdir(args.input)
    vault = os.path.abspath(args.vault or
                            (args.input if batch_mode
                             else os.path.dirname(os.path.abspath(args.input))))

    try:
        items, forgotten, legacy = collect(args.input, args.published_only)
        if not items:
            print('Nic ke prevodu.')
            return 1

        # Mapa noty -> vystupni soubor. Musi byt hotova pred prevodem, aby
        # wikilinky mezi notami v davce vedly nekam.
        #
        # Slug se pocita z NAZVU SOUBORU, ne z titulku. Titulky se opakuji -
        # v PKVault ma pet not z sablony tasku H1 Popis - a slug z titulku by
        # je tise prepsal jeden druhym. Nazev souboru je v ramci slozky
        # jednoznacny. Kdyz i tak nastane kolize (stejny nazev ve dvou
        # slozkach), prida se cislo a nahlasi se to.
        #
        # Frontmatter klic slug prebije jen NAZEV VYSTUPNIHO SOUBORU. Je to kvuli
        # stabilite adresy: publikovany clanek si slug drzi i po prejmenovani
        # noty, protoze odkazy zvenci nikdo neopravi. Prebity slug se stejne
        # prozene funkci slug(), aby preklep v YAML nevyrobil nazev s mezerou.
        #
        # KLIC v mape zustava odvozeny z nazvu souboru, protoze wikilink zna jen
        # nazev cilove noty a dohledava se pres slug(stem) - viz Prevod.odkaz.
        # Kdyby klicem byl prebity slug, odkazy na takovou notu by prestaly vest.
        plan, batch, used, clashes, guessed_dates = [], {}, set(), [], []
        oversized = []
        for path, meta, body_text in items:
            stem = os.path.splitext(os.path.basename(path))[0]
            key = slug(stem)
            base = slug(meta['slug']) if meta.get('slug') else key
            name, n = base, 2
            while name in used:
                name, n = '%s-%d' % (base, n), n + 1
            if name != base:
                # Na webu je adresa zavazek a nesmi se menit podle toho, co se
                # zrovna publikuje spolu s clankem. Tiche prejmenovani na -2 je
                # prijatelne u davky do mailu, na web ne.
                if args.site:
                    raise Error('Kolize adresy %s.html - dva clanky se stejnym '
                                'nazvem. Prejmenuj jeden z nich: %s'
                                % (base, path))
                clashes.append('%s -> %s.html' % (path, name))
            if args.site and not meta.get('date'):
                # Rozhodnuti publikovat nese marker, takze chybejici datum
                # build neshodi - vezme se datum souboru. Do zdroje se
                # nezapisuje, viz zaruka Z45.
                meta['date'] = file_date(path)
                guessed_dates.append((path, meta['date']))
            used.add(name)
            batch.setdefault(key, name + '.html')
            plan.append((path, meta, body_text, name))

        tmp_dir = None
        if args.check:
            tmp_dir = tempfile.mkdtemp(prefix='md2html-kontrola-')
            out_dir = tmp_dir
        elif args.site:
            out_dir = args.out
        elif batch_mode:
            out_dir = args.out or 'html'
        else:
            out_dir = None
        if args.clean:
            archiv = clean_output(out_dir)
            if archiv:
                print('  %s  (%.0f kB, predchozi vystup)'
                      % (archiv, os.path.getsize(archiv) / 1024.0))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)

        renamed = {}
        site = None
        if args.site:
            # Lista je z TAGU, ne z adresaru. Adresare by do verejne navigace
            # propsaly strukturu vaultu - v menu by pristal i interni zapis.
            all_tags = set()
            for _, meta, _ in items:
                all_tags.update(tags_from_meta(meta))
            # Stara slozka _web se uz necte. Mlcet o ni nejde: web by se
            # postavil bez loga, listy i vlastnich stylu a vypadalo by to
            # jako chyba generatoru, ne jako neprejmenovana slozka.
            if (os.path.isdir(os.path.join(vault, '_web'))
                    and not os.path.isdir(os.path.join(vault, CONFIG_DIR))):
                print('\nPOZOR: vault ma slozku _web, ktera se uz necte.'
                      ' Prejmenuj ji na %s.' % CONFIG_DIR)
                print('Uvnitr prejmenuj menu_webu.md na menu.md.')

            menu_source, intro, home_title, custom_css = site_inputs(vault, batch)
            no_tag = any(not tags_from_meta(m) for _, m, _ in items)
            site = {'name': args.site_name or os.path.basename(vault),
                   'tags': sorted(all_tags),
                   'menu': menu_items(menu_source, sorted(all_tags), no_tag),
                   'logo': None,
                   'search': True,
                   'rss': bool(args.base_url),
                   'description': text_from_html(intro) if intro else None,
                   'head_extra': ('<link rel="alternate" type="application/rss+xml"'
                             ' title="%s" href="rss.xml">'
                             % (args.site_name or os.path.basename(vault)))
                            if args.base_url else ''}
            # Znacka rika, ze adresar patri generatoru. Uklid pred buildem smi
            # mazat jen adresar, ktery ji ma - cizi ani pri preklepu v ceste.
            open(os.path.join(out_dir, OUTPUT_MARKER), 'w').close()
            cesta_css = os.path.join(out_dir, 'styl.css')
            with open(cesta_css, 'w', encoding='utf-8', newline='\n') as f:
                f.write(CSS_WEB)
                if custom_css:
                    f.write('\n/* --- ' + CONFIG_DIR + '/styl.css --- */\n')
                    f.write(custom_css)
            print('  %s' % cesta_css)
            site['logo'] = find_logo(vault, out_dir)
            if not site['logo']:
                print('  (logo neni: cekam %s/logo.svg nebo .png,'
                      ' hlavicka zatim vysadi nazev)' % CONFIG_DIR)

        conv = Conversion(vault, batch, site=args.site)
        produced = []
        for path, meta, body_text, name in plan:
            heading, html = to_html(
                path, conv,
                title=None if batch_mode else args.title,
                out_dir=out_dir if args.site else None, renamed=renamed,
                site=site, date=meta.get('date'))
            # -o je zaklad cesty, priponu doplnujeme.
            if out_dir:
                base_path = os.path.join(out_dir, name)
            else:
                base_path = os.path.splitext(args.out or name)[0]
            html_soubor = base_path + '.html'
            with open(html_soubor, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)
            print('  %s  (%.0f kB)' % (html_soubor,
                                       os.path.getsize(html_soubor) / 1024.0))
            produced.append({'heading': heading, 'date': meta.get('date', ''),
                             'tags': tags_from_meta(meta),
                             'file': os.path.basename(html_soubor),
                             'excerpt': excerpt(body_text, meta, conv) if args.site else '',
                             'text': text_from_html(html) if args.site else '',
                             'image': None})
            if args.site:
                zdroj_obr = excerpt_image(path)
                if zdroj_obr:
                    produced[-1]['image'] = copy_attachment(
                        zdroj_obr, out_dir, renamed)
                    if os.path.getsize(zdroj_obr) > EXCERPT_IMAGE_LIMIT:
                        oversized.append(
                            (zdroj_obr, os.path.getsize(zdroj_obr) / 1024.0))

        def zapis(nazev_souboru, html):
            cesta_s = os.path.join(out_dir, nazev_souboru)
            with open(cesta_s, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)
            return cesta_s

        if args.site:
            # Razeni: datum klesajici, pri shode nazev. Bez druhotneho klice by
            # bylo poradi uvnitr serie se stejnym datem libovolne.
            ordered = sorted(produced, key=lambda c: c['heading'].lower())
            ordered.sort(key=lambda c: c['date'], reverse=True)

            for nazev_s, html_s in card_grid(
                    ordered, 'index', home_title or 'Články', site,
                    intro=intro, skryty_nadpis=True):
                print('  %s' % zapis(nazev_s, html_s))

            # Stranky tagu maji tentyz vypis. Vznikaji tady, protoze na ne
            # odkazuje lista na kazde strance a kontrola odkazu by jinak
            # spadla na neexistujici cil.
            # Nadpis je i tady skryty - podle ktereho tagu je vyfiltrovano rekne
            # zvyraznene tlacitko v liste, takze v textu je zbytecny.
            for tag in site['tags']:
                sem = [c for c in ordered if tag in c['tags']]
                # Dosazitelne = tagy, ktere se s timhle nekde potkavaji. Ostatni
                # lista ztlumi, takze kombinace do prazdna nejde ani kliknout.
                reachable = {t for c in sem for t in c['tags']}
                for nazev_s, html_s in card_grid(sem, 'tag-' + slug(tag),
                                                    tag, site, tag,
                                                    skryty_nadpis=True,
                                                    active_tag=tag,
                                                    reachable=reachable):
                    print('  %s  (%d clanku, kombinovatelnych tagu %d)'
                          % (zapis(nazev_s, html_s), len(sem),
                             len(reachable - {tag})))

            sem = [c for c in ordered if not c['tags']]
            if sem:
                for nazev_s, html_s in card_grid(
                        sem, 'tag-' + NO_TAG_SLUG, NO_TAG_HEADING, site,
                        'tag-%s.html' % NO_TAG_SLUG, skryty_nadpis=True,
                        active_tag=NO_TAG_SLUG):
                    print('  %s  (%d clanku bez tagu)'
                          % (zapis(nazev_s, html_s), len(sem)))

            print('  %s' % zapis('hledani.html',
                                 search_page(ordered, site)))

            if args.base_url:
                print('  %s  (%d polozek)'
                      % (zapis('rss.xml', rss(ordered, site, args.base_url)),
                         min(len(ordered), RSS_ITEMS)))
        elif batch_mode:
            cesta_s = zapis('index.html', index_page(produced))
            print('  %s  (rozcestnik na %d stranek)' % (cesta_s, len(produced)))

        if args.site:
            flattened_links = check_links(out_dir)
            if flattened_links:
                print('\nZplostene odkazy na soubory (%d): cil ve vystupu neni,'
                      ' zustal jen text.' % len(flattened_links))
                for x in flattened_links[:10]:
                    print('  %s' % x)
                if len(flattened_links) > 10:
                    print('  ... a dalsich %d' % (len(flattened_links) - 10))

        if args.site:
            # Kuratorovany seznam v KONFIG/menu.md rozhoduje, co je v liste. Novy
            # tag se tam neprida sam, protoze smysl te kurace je drzet listu
            # kratkou - ale mlcet o tom by znamenalo, ze si autor doplni tag a
            # diva se, proc v liste neni.
            in_menu = set(x for _, _, x in site['menu'] if x)
            missing = [x for x in site['tags'] if x not in in_menu]
            if missing:
                print('\nTagy mimo listu (%d): stranka se generuje a vede na ni'
                      ' odkaz z paticky clanku, ale v liste neni.' % len(missing))
                print('Pridej radek do %s/menu.md, kdyz tam patri:' % CONFIG_DIR)
                for x in missing:
                    print('  `#%s`  ->  tag-%s.html' % (x, slug(x)))

            # Opacny pripad: lista jmenuje tag, ktery zadny publikovany
            # clanek nema. Jeho stranka nevznikne, takze se v liste ztlumi
            # - ale autor by mel vedet proc, jinak vypada lista rozbite.
            empty_tags = [x for x in in_menu if x not in site['tags']]
            if empty_tags:
                print('\nStitky v liste bez clanku (%d): stranka nevznika,'
                      ' v liste jsou ztlumene a nejdou kliknout.'
                      % len(empty_tags))
                print('Publikuj clanek s timhle tagem, nebo radek z %s/menu.md'
                      ' odeber:' % CONFIG_DIR)
                for x in sorted(empty_tags):
                    print('  `#%s`' % x)

        if oversized:
            print('\nVelke nahledy (%d): na titulce se zobrazuji ve vysce'
                  ' 9rem, takze staci mensi soubor.' % len(oversized))
            for c, kb in oversized:
                print('  %.0f kB  %s' % (kb, c))

        if guessed_dates:
            print('\nDatum chybi ve frontmatteru, vzato ze souboru (%d).'
                  ' Datum souboru se meni pri kopirovani i synchronizaci,'
                  ' takze poradi na titulce nemusi vydrzet:'
                  % len(guessed_dates))
            for c, d in guessed_dates:
                print('  %s  %s' % (d, c))

        if legacy:
            print('\nPOZOR: stare ceske klice frontmatteru (%d). Uz se nectou,'
                  ' takze clanek prijde o datum nebo titulek:' % len(legacy))
            for c, old, new in legacy:
                print('  %s -> %s  %s' % (old, new, c))

        if forgotten:
            print('\nPOZOR: klic publish bez markeru v nazvu (%d) - na web NEJDOU.'
                  % len(forgotten))
            for c in forgotten:
                print('  %s' % c)

        if clashes:
            print('\nKolize nazvu (%d): stejny nazev souboru ve dvou slozkach, '
                  'prejmenovano.' % len(clashes))
            for k in clashes:
                print('  %s' % k)

        if conv.flattened:
            unique = sorted(set(conv.flattened))
            print('\nZplostene odkazy (%d): cil neni v davce, zustal jen text.'
                  % len(unique))
            for u in unique[:10]:
                print('  %s' % u)
            if len(unique) > 10:
                print('  ... a dalsich %d' % (len(unique) - 10))

        return 0

    except Error as e:
        print('CHYBA: %s' % e)
        return 1
    except (OSError, IOError) as e:
        print('CHYBA: %s' % e)
        return 1
    finally:
        # Kontrolni rezim po sobe nesmi nechat adresar - hook bezi pri kazdem
        # commitu a za mesic by jich v temp byly stovky.
        if 'docasny' in dir() and tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
