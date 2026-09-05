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
   Tags COMBINE WITH AND. `Obsidian` plus `Video` yields articles about
   Obsidian that have a video. A tag that would yield nothing in combination
   with those already picked is DIMMED and cannot be clicked, so there is no
   way to click into an empty result. It is dimmed rather than hidden: were it
   to disappear, the bar would jump on every click.

   A tag in the live bar is a PAIR OF CONTROLS in one pill: a checkbox that
   HOLDS the tag in the filter, and the name, which BROWSES - it sets one tag
   more and the next name clicked exchanges it. So one holds `Obsidian` and
   clicks through `Howto`, `Video`, `Backups` to see its subsets without
   renewing `Obsidian` every time. Neither control ever changes the other's
   state; a checkbox that unticked itself because a neighbour was clicked
   would promise an independence it does not keep.

   This lives in two places that complement each other:

   hledani.html   the live version, in TWO ROWS: the tags the curated bar
                  carries lead, the rest follow underneath, and a row with
                  nothing in it is not drawn. Curating the bar is therefore
                  the one place that says which tag matters, and no article
                  has to be renamed to say it. Tags, the text query and the
                  counts are recomputed together - the query also narrows
                  which tags still light up. State lives in the address
                  (`?tag=a&tag=b&pick=c&q=...`, `tag` held and `pick`
                  browsed), so it can be sent and restored with the back
                  button. The header's own tag bar is left out of this page -
                  next to the filter it would be one more row of tags saying
                  something else.
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


def set_marker(mark):
    """Change the publish marker. A vault may use whatever it likes.

    The marker is stripped off the title, the slug and the alt text, so a
    character that also occurs in ordinary names takes a piece of them with it:
    with '!' the article 'Careful!.md' goes out titled 'Careful'. A symbol that
    nobody writes by accident is therefore the safer choice, and the build warns
    about the rest.
    """
    global PUBLISH_MARKER
    if not mark:
        raise Error('The publish marker cannot be empty.'
                    ' Use --all when everything should be converted.')
    PUBLISH_MARKER = mark

# A marker file inside the output directory. The script may only wipe a
# directory that carries it, or one that is empty. A directory that belongs to
# somebody else survives even a typo in the path.
OUTPUT_MARKER = '.vygenerovano'

# The pseudo-tag for articles without tags. In the bar it is a '#' button - a
# bare hash is useless as a page title, and useless to a screen reader too, so
# its page carries a real heading. Both the slug and the heading come from the
# language table; only the button label is the same everywhere.
NO_TAG_LABEL = '#'


# ==============================================================================
# Localisation
# ==============================================================================
#
# Only what a VISITOR of the generated site sees is localised. Messages printed
# while building are for whoever runs the script, and those are English
# unconditionally - the same audience that reads --help.
#
# The default is Czech, so a vault built without --lang comes out exactly as it
# did before this table existed.
#
# Page names are part of the table on purpose. A Czech site therefore keeps
# hledani.html and its published addresses do not move, while an English one
# gets search.html. An address once published is a commitment; deriving it from
# the language keeps that promise on both sides.

TEXTS = {
    'cs': {
        'lang': 'cs',
        'search': 'Hledání',
        'search_file': 'hledani.html',
        'search_button': 'Hledat',
        'search_placeholder': 'Hledat…',
        'search_aria': 'Hledaný výraz',
        'needs_js': 'Hledání potřebuje JavaScript.'
                    ' Bez něj zbývá seznam všech článků:',
        'home': 'Titulka',
        'top': 'Nahoru',
        'articles': 'Články',
        'copy_name': 'Zkopírovat název',
        'copied': 'Zkopírováno',
        'tag_prefix': 'tag-',
        'no_tag_slug': 'bez-tagu',
        'no_tag_heading': 'Bez tagu',
        'no_tag_scope': 'článcích bez tagu',
        'newer': 'Novější',
        'older': 'Starší',
        'page_of': 'Stránka %d z %d',
        'page_suffix': '%s, strana %d',
        'no_article_yet': 'zatím nemá publikovaný článek',
        'no_overlap': 's #%s se nepotkává v žádném článku',
        'clear_filter': 'zrušit filtr',
        'remove_filter': 'odebrat filtr',
        'hold_tag': 'držet #%s ve filtru',
        'release_tag': 'přestat držet #%s',
        'filter_tag': 'filtrovat na #%s',
        'nothing_found': 'nic nenalezeno',
        'in_scope': ' v ',
        'and': ' a ',
        # Plural forms keyed by the categories of Intl.PluralRules. Czech has
        # three that matter, English two; the browser picks, so no counting
        # rules are written here.
        'n_articles': {'one': '%d článek', 'few': '%d články',
                       'many': '%d článků', 'other': '%d článků'},
        'n_found': {'one': '%d nalezený', 'few': '%d nalezené',
                    'many': '%d nalezených', 'other': '%d nalezených'},
    },
    'en': {
        'lang': 'en',
        'search': 'Search',
        'search_file': 'search.html',
        'search_button': 'Search',
        'search_placeholder': 'Search…',
        'search_aria': 'Search query',
        'needs_js': 'Search needs JavaScript.'
                    ' Without it, here is a list of every article:',
        'home': 'Home',
        'top': 'Top',
        'articles': 'Articles',
        'copy_name': 'Copy the name',
        'copied': 'Copied',
        'tag_prefix': 'tag-',
        'no_tag_slug': 'no-tag',
        'no_tag_heading': 'Without a tag',
        'no_tag_scope': 'articles without a tag',
        'newer': 'Newer',
        'older': 'Older',
        'page_of': 'Page %d of %d',
        'page_suffix': '%s, page %d',
        'no_article_yet': 'no published article yet',
        'no_overlap': 'never occurs together with #%s',
        'clear_filter': 'clear the filter',
        'remove_filter': 'remove the filter',
        'hold_tag': 'keep #%s in the filter',
        'release_tag': 'stop keeping #%s',
        'filter_tag': 'filter to #%s',
        'nothing_found': 'nothing found',
        'in_scope': ' in ',
        'and': ' and ',
        'n_articles': {'one': '%d article', 'other': '%d articles'},
        'n_found': {'one': '%d found', 'other': '%d found'},
    },
}

# The texts of the language in use. A module-level name rather than an argument
# threaded through thirty functions: the script converts one vault in one run,
# so the language is set once in main() and never changes underneath anybody.
T = TEXTS['cs']


def set_language(code):
    """Pick the language of the generated site. Unknown code is an error."""
    global T
    if code not in TEXTS:
        raise Error('Unknown language %s. Available: %s'
                    % (code, ', '.join(sorted(TEXTS))))
    T = TEXTS[code]


# ==============================================================================
# Appearance
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

# Site chrome: header with the logo and the bar, footer, dark mode. It has no
# place in a self-contained file going out by email - there is nowhere to
# navigate to there.
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

/* The faceted filter on the search page. A tag is a pair: a checkbox that
   HOLDS it in the filter and a name that browses. The two are one pill to the
   eye and two controls to the hand. */
.fasety { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: .45rem;
          align-items: center; }
/* Two rows: the curated tags lead, the rest follow. A row with nothing in it
   carries the `hidden` attribute - and `display: flex` above would otherwise
   beat the browser's own rule for it and draw an empty line. */
.fasety[hidden] { display: none; }
.fasety.posledni { margin-bottom: 1.5rem; }
.fasety.dalsi { font-size: .94em; }
.stitek { font: inherit; font-size: .88rem; padding: .25rem .6rem;
          border: 1px solid var(--linka); border-radius: 999px;
          background: none; color: var(--odkaz); cursor: pointer;
          white-space: nowrap; }
.stitek:hover { background: var(--th); }
.stitek.zrusit { border-style: dashed; }
.parstitek { display: inline-flex; align-items: center;
             border: 1px solid var(--linka); border-radius: 999px;
             overflow: hidden; }
.parstitek > label { display: flex; align-items: center;
                     padding: .25rem .1rem .25rem .45rem; cursor: pointer; }
.parstitek > label input { margin: 0; cursor: pointer; }
.parstitek > button { font: inherit; font-size: .88rem;
                      padding: .25rem .6rem .25rem .4rem;
                      border: 0; background: none; color: var(--odkaz);
                      cursor: pointer; white-space: nowrap; }
.parstitek > button:hover { background: var(--th); }
/* Held is a PALE fill, the browsed one a FULL fill. The held tag stays put
   while the browsed one is exchanged, so the quieter mark belongs to it. */
.parstitek.drzeny { border-color: var(--odkaz); background: var(--th); }
/* The name of a held tag does nothing - the checkbox beside it is the way
   out - so it must not offer itself to the hand. */
.parstitek.drzeny > button { cursor: default; }
.parstitek.drzeny > button:hover { background: none; }
.parstitek.vybrany { border-color: var(--odkaz); }
.parstitek.vybrany > button { background: var(--odkaz); color: #fff; }
/* An unreachable tag is DIMMED, not hidden - otherwise the bar jumps on
   every click and one loses track of what sat where. */
.parstitek.zhasnuty { opacity: .45; }
.parstitek.zhasnuty > button { color: var(--tlum); cursor: default; }
.parstitek .pocet-tagu { opacity: .6; font-size: .8em; margin-left: .35em; }

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


HTML = ('<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>{title}</title><style>{css}</style></head><body>{body}{footer}'
        '</body></html>')

# Site mode: the style sits in one file next to the pages, not inside each of
# them. The reason is size - in self-contained mode a single page with five
# screenshots weighs 598 kB, because the images are base64 and the CSS repeats.
HTML_WEB = ('<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>{title}</title>'
            '<link rel="stylesheet" href="styl.css">{head_extra}</head><body>'
            '{header}<main>{body}</main>{footer}'
            '</body></html>')

# The search page. The index is BAKED INSIDE, because under file:// it is not
# JavaScript that fails but fetch() - the browser refuses to read local JSON
# because of CORS. Baking it in removes that obstacle and the very same file
# works from a host and from a disk alike.
SEARCH_PAGE = r"""<h1 class="jen-ctecka">@SEARCH@</h1>
<div id="fasety" class="fasety hlavni" hidden></div>
<div id="fasety-dalsi" class="fasety dalsi" hidden></div>
<div id="vysledky"></div>
<noscript>
  <p>@NEEDS_JS@</p>
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
// Every string the visitor reads, in the language of the site. Baked in the
// same way the index is, so the page needs nothing else to work.
const TXT = @TEXTS@;

const fold = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Plurals are picked by Intl.PluralRules, so no counting rules live here.
// Czech needs three forms and English two; the browser knows which category a
// number falls into, and the table supplies the wording.
const plural = new Intl.PluralRules(TXT.lang);
const shape = (forms, n) => {
  const form = forms[plural.select(n)] || forms.other;
  return form.replace('%d', n);
};
const countLabel = n => shape(TXT.n_articles, n);

ARTICLES.forEach(c => {
  c.nTitle = fold(c.title);
  c.nText = fold(c.text);
  c.nTags = fold(c.tags.map(t => t.name).join(' '));
});

const params = new URLSearchParams(location.search);
// The filter has TWO INDEPENDENT PARTS. `held` are the tags pinned with the
// checkbox: they survive every further click. `current` is the one tag whose
// name was clicked, and the next click on a name exchanges it. The filter is
// the intersection of both, so holding #Obsidian and clicking through
// #Howto, #Video, #Backups walks its subsets without renewing #Obsidian.
//
// The point of the split is that NEITHER CONTROL TOUCHES THE OTHER'S STATE.
// A checkbox that unticked itself because a neighbour was clicked would
// promise an independence it does not keep.
//
// A tag in the address is HELD - a link from a tag page carries the tags it
// combined, and those are meant to stay.
let held = params.getAll('tag').filter(Boolean);
let current = params.get('pick') || null;
if (held.includes(current)) { current = null; }
let filters = [];
let scope = [];

function syncFilters() {
  // The guard is for an address typed by hand. Clicking cannot get a tag into
  // both parts at once, but `?tag=a&pick=a` would otherwise say '#a and #a'.
  filters = (current && !held.includes(current)) ? held.concat([current])
                                                 : held.slice();
}

function matchesTags(c, combo) {
  return combo.every(f => f === NO_TAG ? c.tags.length === 0
                                       : c.tags.some(t => t.name === f));
}

function scopeLabel() {
  if (!filters.length) return '';
  return TXT.in_scope + filters.map(f => f === NO_TAG ? TXT.no_tag_scope
                                                      : '#' + f).join(TXT.and);
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
  const tags = c.tags.map(t => '<a href="' + TXT.tag_prefix + t.slug + '.html">#'
                               + esc(t.name) + '</a>').join(' ');
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
    counter.textContent = TXT.nothing_found + scopeLabel();
    target.innerHTML = '';
    return;
  }
  counter.textContent = shape(TXT.n_found, found.length) + scopeLabel();
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
// The number says WHAT A CLICK ON THE NAME WOULD YIELD, so the held tags plus
// this one. On a tag already in the filter there is no number at all: it
// would answer a different question than the number on its neighbour.
// ---------------------------------------------------------------------------

function countFor(combo, words) {
  return ARTICLES.filter(c => matchesTags(c, combo)
                              && (!words.length || score(c, words) > 0)).length;
}

const withTag = (text, tag) => text.replace('%s', tag);

// The bar is drawn in TWO ROWS: the tags the curated menu carries lead, the
// rest follow underneath. A row with nothing in it is not drawn at all - an
// empty line above the results would read as a loading glitch.
function paintRow(id, parts, last) {
  const target = document.getElementById(id);
  target.innerHTML = parts.join('');
  target.hidden = !parts.length;
  // The gap before the results belongs to the LAST row drawn, whichever it
  // turns out to be. CSS cannot see that on its own without :has().
  target.classList.toggle('posledni', last && parts.length > 0);
}

function renderFacets(words) {
  const lead = [];      // tags the curated bar carries
  const rest = [];      // everything else, alphabetically
  for (const tag of ALL_TAGS) {
    const isHeld = held.includes(tag.name);
    const isCurrent = current === tag.name;
    const inFilter = isHeld || isCurrent;
    const count = inFilter ? null : countFor(held.concat([tag.name]), words);
    const dead = count === 0;
    const classes = 'parstitek' + (isHeld ? ' drzeny' : '')
                    + (isCurrent ? ' vybrany' : '') + (dead ? ' zhasnuty' : '');
    const hint = isHeld ? withTag(TXT.release_tag, tag.label)
                        : withTag(TXT.hold_tag, tag.label);
    // The checkbox holds the tag and nothing else. It is a real input, so
    // the keyboard and the screen reader get it for free. On a dimmed tag it
    // is disabled along with the name: holding one yields the same empty
    // result as clicking it.
    //
    // The name is dead on a held tag - it is in the filter already and the
    // checkbox right next to it is how one gets it out, so promising
    // 'filter to this' there would be a lie.
    const pill = '<span class="' + classes + '">'
      + '<label title="' + esc(hint) + '"><input type="checkbox"'
      + ' data-hold="' + esc(tag.name) + '" aria-label="' + esc(hint) + '"'
      + (isHeld ? ' checked' : '') + (dead ? ' disabled' : '') + '></label>'
      + '<button type="button" data-tag="' + esc(tag.name) + '"'
      + (dead || isHeld ? ' disabled' : '')
      + ' aria-pressed="' + (isCurrent ? 'true' : 'false') + '"'
      + (isHeld ? '' : ' title="' + esc(isCurrent ? TXT.remove_filter
                       : withTag(TXT.filter_tag, tag.label)) + '"')
      + '>#' + esc(tag.label)
      + (inFilter ? '' : '<span class="pocet-tagu">' + count + '</span>')
      + '</button></span>';
    (tag.lead ? lead : rest).push(pill);
  }
  if (filters.length) {
    // The clear button closes the LAST row that exists, so it never hangs
    // under a bar on a line of its own.
    (rest.length ? rest : lead).push('<button type="button"'
                 + ' class="stitek zrusit" id="zrusit">' + TXT.clear_filter
                 + '</button>');
  }
  paintRow('fasety', lead, !rest.length);
  paintRow('fasety-dalsi', rest, true);
}

function writeUrl(query) {
  // State belongs in the address, so it can be sent and restored with the
  // back button.
  const p = new URLSearchParams();
  held.forEach(f => p.append('tag', f));
  if (current) { p.set('pick', current); }
  if (query) { p.set('q', query); }
  const queryString = p.toString();
  history.replaceState(null, '',
                       location.pathname + (queryString ? '?' + queryString : ''));
}

function render() {
  const query = field.value;
  const words = fold(query).split(/\s+/).filter(Boolean);
  syncFilters();
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

// The checkbox works on `held` ALONE, the name on `current` alone. The single
// exception is holding the tag one is browsing: it would otherwise sit in the
// filter twice, so it stops being the browsed one and becomes held.
function onHold(e) {
  const box = e.target.closest('input[data-hold]');
  if (!box) { return; }
  const tag = box.getAttribute('data-hold');
  held = box.checked ? held.concat([tag]) : held.filter(f => f !== tag);
  if (box.checked && current === tag) { current = null; }
  render();
}

function onPick(e) {
  if (e.target.id === 'zrusit') { held = []; current = null; render(); return; }
  const chip = e.target.closest('button[data-tag]');
  if (!chip) { return; }
  const tag = chip.getAttribute('data-tag');
  // The name of a held tag is disabled, so this is only a safety net - but it
  // is what keeps `current` from ever being a held tag, and with it the
  // address canonical.
  current = (current === tag || held.includes(tag)) ? null : tag;
  render();
}

// Both rows listen. The clear button lives in whichever of them is the last
// one drawn, so hanging the handler on the leading row alone would leave it
// dead on every site whose bar carries no tags.
for (const id of ['fasety', 'fasety-dalsi']) {
  const bar = document.getElementById(id);
  bar.addEventListener('change', onHold);
  bar.addEventListener('click', onPick);
}

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
    tlacitko.textContent = '@COPIED@';
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
    raise Error('%s is neither UTF-8 nor cp1250.' % path)


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

# THE PIPE MAY BE ESCAPED. Inside a Markdown table a bare | would split the
# cell, so Obsidian writes [[Target\|label]] there - and it does that on its
# own, whenever an alias is added to a link in a table. Without the optional
# backslash the target reads as 'Target\', no such note is found and the link
# degrades to plain text. A whole vault can be full of those and every one of
# them would go quietly, because a flattened link is a warning, not an error.
RE_EMBED = re.compile(r'!\[\[([^\]|#]+?)(?:#[^\]|]*)?(?:\\?\|([^\]]*))?\]\]')
RE_WIKILINK = re.compile(
    r'(?<!!)\[\[([^\]|#]+?)(?:#([^\]|]*))?(?:\\?\|([^\]]*))?\]\]')
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
            self.flattened.append('%s (transclusion nested too deep)' % target)
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
        raise Error('Missing images: %s' % ', '.join(sorted(set(missing))))
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
        raise Error('Two images share the address %s: %s and %s'
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
        raise Error('Missing images: %s' % ', '.join(sorted(set(missing))))
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
        raise Error('The markdown package is missing. Install it: pip install markdown')

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
                '<a href="%s">#%s</a>' % (tag_page(x), x) for x in tags))
        masthead.append('</div>')
        return heading, HTML_WEB.format(
            lang=T['lang'],
            title='%s - %s' % (heading, site['name']),
            head_extra=site.get('head_extra', ''),
            header=header_html(site),
            body=''.join(masthead) + body,
            footer=footer_html(site, own_meta.get('date'), tags, heading))
    return heading, HTML.format(lang=T['lang'], title=heading, css=CSS,
                                body=body, footer=footer)


# ==============================================================================
# Batch
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
    pseudo = (NO_TAG_LABEL, tag_page(T['no_tag_slug']), None)
    if not text:
        done = [(t, tag_page(t), t) for t in tags]
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
        m = re.match(r'^\[\[([^\]|]+?)(?:\\?\|([^\]]+))?\]\]$', r)
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
            items.append((tag, tag_page(tag), tag))
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
        target, label = m.group(1).strip(), (m.group(2) or '').strip()
        fpath = batch.get(slug(strip_marker(target)))
        link_text = label or strip_marker(target)
        return '[%s](%s)' % (link_text, fpath) if fpath else link_text

    return outside_code(text, lambda t: re.sub(
        r'\[\[([^\]|]+?)(?:\\?\|([^\]]*))?\]\]', replace, t))


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
                raise Error('The markdown package is missing. Install it: pip install markdown')
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


def tag_page(name):
    """The filename of a tag page. The prefix comes from the language table, so
    a Czech and an English site do not fight over the same address."""
    return '%s%s.html' % (T['tag_prefix'], slug(name))


def combination_url(tags):
    """The address of the search page with tags pre-selected."""
    return T['search_file'] + '?' + '&'.join('tag=%s' % quote(t) for t in tags)


def header_html(site, active=None, active_tag=None, reachable=None,
                  fixed_only=False):
    """Logo on the left, the tag bar on the right. On every page.

    The logo is NOT an h1. That belongs to the article title, and two top-level
    headings on one page are a problem for screen readers and search engines
    alike.

    `fixed_only` leaves the tag chips out of the bar and keeps only the fixed
    items. It is for the search page, where tags are handled by the faceted
    filter - a row of links above a live filter of the same tags only
    confuses.

    THE BAR ADDS TAGS, IT DOES NOT REPLACE THEM. On an unfiltered page a chip
    leads to its own tag page, as it always did. On a tag page it leads to
    search carrying BOTH tags, so the second click narrows instead of throwing
    the first filter away. A tag that co-occurs with the active one in no
    article is dimmed - `reachable` is the set of tags that return something
    alongside the active filter. Thanks to that there is no clicking into an
    empty result, JavaScript or not.

    A tag that is in the bar but that no published article carries is dimmed
    too - its page is never generated, so the link would lead nowhere.
    """
    name = site['name']
    if site.get('logo'):
        mark = '<img src="%s" alt="%s">' % (site['logo'], name)
    else:
        mark = name
    # Row 1: logo on the left, search on the right. Row 2: tags from the left.
    # The search field is on EVERY page, but the index lives only in
    # hledani.html - the form therefore sends the query there via ?q=. If every
    # page carried the index, its size would be paid on every load.
    parts = ['<header class="hlavicka">', '<div class="pas">',
            '<a class="logo" href="index.html">%s</a>' % mark,
            '<form class="hledani" action="%s" method="get">' % T['search_file'],
            '<input type="search" name="q" id="dotaz" placeholder="%s"'
            % T['search_placeholder'],
            ' autocomplete="off" aria-label="%s">' % T['search_aria'],
            # The button is deliberate, even though Enter in a single field
            # submits the form on its own: an explicit submit is unambiguous in
            # every browser and can be tapped on a phone. On the search page the
            # script disarms it.
            '<button type="submit">%s</button>' % T['search_button'],
            # When a page is filtered to a tag, the form carries that tag along
            # and only its articles are searched. Without it a query from a tag
            # page would search the whole site and the context would be lost.
            ('<input type="hidden" name="tag" value="%s">' % active_tag)
            if active_tag else '',
            '<span class="pocet" id="pocet"></span>',
            '</form>', '</div>', '<nav>']
    for label, url, tag in site['menu']:
        if fixed_only and (tag or url == tag_page(T['no_tag_slug'])):
            continue
        # `active` is either a tag name or a filename - so that a fixed item,
        # Search for instance, can be highlighted too.
        is_current = (tag and tag == active) or url == active
        if tag and tag not in site['tags']:
            # A curated item for a tag that no published article carries, so
            # its page is never generated. It is DIMMED, not flattened:
            # check_links would turn the link into plain text and an unstyled
            # word would sit among styled pills. A dimmed pill says the same
            # thing without breaking the row. The build reports it as well.
            parts.append('<span class="zhasnuty" aria-disabled="true"'
                        ' title="%s">%s</span>'
                        % (T['no_article_yet'], label))
        elif is_current:
            # An active chip removes the filter, so it goes back to the front page.
            parts.append('<a href="index.html" aria-current="page">%s</a>' % label)
        elif tag and active_tag:
            if reachable is not None and tag not in reachable:
                parts.append('<span class="zhasnuty" aria-disabled="true"'
                            ' title="%s">%s</span>'
                            % (T['no_overlap'] % active_tag, label))
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
    """Date, the article's tags and links. On an article, a copy-name button too."""
    parts = []
    if date:
        parts.append('<span>%s</span>' % date)
    if tags:
        parts.append('<span class="tagy">%s</span>' % ' '.join(
            '<a href="%s">#%s</a>' % (tag_page(t), t) for t in tags))
    links = []
    if name:
        links.append('<button type="button" id="kopirovat" class="kopie"'
                      ' data-nazev="%s">%s</button>'
                      % (name.replace('"', '&quot;'), T['copy_name']))
    links.append('<a href="index.html">%s</a>' % T['home'])
    if site.get('search'):
        links.append('<a href="%s">%s</a>' % (T['search_file'], T['search']))
    if site.get('rss'):
        links.append('<a href="rss.xml">RSS</a>')
    links.append('<a href="#">%s</a>' % T['top'])
    parts.append('<span class="odkazy">%s</span>' % ''.join(links))
    script = COPY_SCRIPT.replace('@COPIED@', T['copied']) if name else ''
    return '<footer class="paticka">%s</footer>%s' % (''.join(parts), script)


def site_page(page_title, content, site, active=None, active_tag=None,
                reachable=None, fixed_only=False):
    """Wrap content in the header and footer. For the front page and tag pages."""
    return HTML_WEB.format(lang=T['lang'],
                           title='%s - %s' % (page_title, site['name']),
                           head_extra=site.get('head_extra', ''),
                           header=header_html(site, active, active_tag,
                                                  reachable, fixed_only),
                           body=content,
                           footer=footer_html(site))


PER_PAGE = 12          # how many excerpts go on one page
                         # Twelve because the listing is a grid three across -
                         # ten would leave the last row holding a single card.


EXCERPT_IMAGE_LIMIT = 300 * 1024   # above this size the build speaks up


def excerpt_image(article_path):
    """Find the excerpt image: in Attachments next to the article, same name.

    Matching goes through slug(), so any spelling fits - "Obsidian Co je",
    "obsidian-co-je" and "obsidian_co_je" alike. The standard wants attachments
    in lower case with underscores, whereas an article has spaces and
    diacritics; the tolerance reconciles both conventions instead of forcing
    one of them to be broken.

    The publish marker is stripped off the article name - it has no business
    being in an attachment name.
    """
    directory = os.path.join(os.path.dirname(article_path), 'Attachments')
    if not os.path.isdir(directory):
        return None
    wanted = slug(strip_marker(os.path.splitext(os.path.basename(article_path))[0]))
    for fname in sorted(os.listdir(directory)):
        stem, ext = os.path.splitext(fname)
        if ext.lower() in IMAGE_EXTS and slug(stem) == wanted:
            return os.path.join(directory, fname)
    return None


def strip_images(text):
    """Drop images out of the text, both spellings: ![[embed]] and ![alt](path).

    The excerpt deliberately never goes through transclusion, so without this
    the bare ![[...]] syntax would sit in it as text.
    """
    text = RE_EMBED.sub('', text)
    return re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)


def excerpt(body_text, meta, conv):
    """The excerpt is the FIRST PARAGRAPH; the frontmatter key overrides it.

    The first paragraph is taken because it is already written - articles start
    that way and the lengths come out at 70 to 230 characters, which is exactly
    excerpt-sized. The manual key is for when the opening does not suit a
    listing.

    A heading ends the search: when an article starts with a section straight
    away, the excerpt is not that section's first sentence but nothing at all.

    An image does not end the excerpt, it merely falls out of it - the excerpt
    is a textual teaser and the card has a thumbnail of its own. A paragraph
    that starts with an image and carries on with text therefore DOES yield an
    excerpt; only when nothing is left after the image is dropped was it a
    standalone opening image, and the search goes on.
    """
    try:
        import markdown
    except ImportError:
        raise Error('The markdown package is missing. Install it: pip install markdown')

    source = (meta.get('excerpt') or '').strip()
    if not source:
        for block in body_text.strip().split('\n\n'):
            b = block.strip()
            if b.startswith('#'):
                break
            # A quote, a table, a list and code are no excerpt even once
            # cleaned up. An image is NOT in this list: it gets dropped from the
            # paragraph and what decides is whether text remains after it.
            if not b or b.startswith(('>', '|', '- ', '* ', '1. ', '```')):
                continue
            b = strip_images(b).strip()
            if not b:
                continue
            # A heading may follow on the very next line with no blank line in
            # between - it is then in the same block and has to be cut off, or
            # the heading and the start of the first section would bleed into
            # the excerpt.
            source = re.split(r'^#+\s', b, maxsplit=1, flags=re.M)[0].strip()
            if not source:
                break
            break
    if not source:
        return ''
    # Rucne psany perex z frontmatteru obrazkem taky projde. Automaticky uz
    # already been cleaned, a second pass changes nothing on it.
    source = strip_images(source)
    # Wikilinks work in the excerpt too, so a link from the front page leads
    # somewhere. The marker is stripped just as it is in the article body.
    # Dropping an image leaves a double space, hence the whitespace squeeze.
    source = re.sub(r'\s+', ' ', source).strip()
    source = conv.resolve_wikilinks(source)
    html = markdown.markdown(source).strip()
    m = re.match(r'^<p>(.*)</p>$', html, re.S)
    return m.group(1) if m else html


def card(c):
    """One article in a listing: title, date with tags, excerpt."""
    parts = ['<article class="karta">']
    if c.get('image'):
        parts.append('<a class="nahled" href="%s"><img src="%s" alt=""></a>'
                    % (c['file'], c['image']))
    parts.append('<h2><a href="%s">%s</a></h2>' % (c['file'], c['heading']))
    labels = []
    if c['date']:
        labels.append(c['date'])
    if c['tags']:
        labels.append(' '.join('<a href="%s">#%s</a>' % (tag_page(t), t)
                               for t in c['tags']))
    if labels:
        parts.append('<div class="meta">%s</div>' % ' '.join(labels))
    if c['excerpt']:
        parts.append('<p class="perex">%s</p>' % c['excerpt'])
    parts.append('</article>')
    return ''.join(parts)


def page_name(base, number):
    """The first page carries no number, so the front page is index.html."""
    return base + ('.html' if number == 1 else '-%d.html' % number)


def pagination(base, number, total):
    """Links forward and back. Static, no script."""
    if total < 2:
        return ''
    parts = []
    if number > 1:
        parts.append('<a href="%s">&larr; %s</a>'
                    % (page_name(base, number - 1), T['newer']))
    parts.append('<span>%s</span>' % (T['page_of'] % (number, total)))
    if number < total:
        parts.append('<a href="%s">%s &rarr;</a>'
                    % (page_name(base, number + 1), T['older']))
    return '<nav class="strankovani">%s</nav>' % ''.join(parts)


def card_grid(articles, base, heading, site, active=None, intro='',
                 hidden_heading=False, active_tag=None, reachable=None):
    """Return [(filename, html)] - excerpts paginated PER_PAGE at a time.

    An empty list yields one empty page, so the bar does not link nowhere.
    """
    pages = [articles[i:i + PER_PAGE]
             for i in range(0, len(articles), PER_PAGE)] or [[]]
    result = []
    for number, chunk in enumerate(pages, start=1):
        # On the front page the heading is HIDDEN, not removed: a page without
        # an h1 is a broken structure for screen readers and search engines
        # alike. On tag pages it stays visible, because it says what the filter
        # is.
        css_class = ' class="jen-ctecka"' if hidden_heading else ''
        content = ['<h1%s>%s</h1>' % (css_class, heading)]
        # The intro goes on the first page only - on index-2 it would repeat.
        if number == 1 and intro:
            content.append(intro)
        content.append('<div class="vypis">')
        content.extend(card(c) for c in chunk)
        content.append('</div>')
        content.append(pagination(base, number, len(pages)))
        page_title = (heading if number == 1
                      else T['page_suffix'] % (heading, number))
        result.append((page_name(base, number),
                         site_page(page_title, ''.join(content), site,
                                     active, active_tag, reachable)))
    return result




def text_from_html(html):
    """Plain text for the search index: markup out, entities back.

    Only the contents of <main> are taken, that is the article body. The header
    and the footer are the same on every page, so a query for any tag from the
    bar would find EVERY article - verified, the word PowerBI was in the text of
    seven articles out of seven.
    """
    body_text = re.search(r'(?s)<main>(.*?)</main>', html)
    if body_text:
        html = body_text.group(1)
    without_code = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', html)
    return re.sub(r'\s+', ' ',
                  unescape(re.sub(r'<[^>]+>', ' ', without_code))).strip()


def search_page(articles, site):
    """Return the HTML of the search page with the index baked inside.

    The scale this is built for: five PKVault articles hold 24 kB of text, the
    whole vault 91 kB. As long as the index fits in single-digit megabytes it
    stays baked in; on a site an order of magnitude larger it would have to be
    fetched separately - and running from a local disk would fall with it, so
    that will be a decision, not a technical detail.
    """
    data = []
    for c in articles:
        data.append({'title': c['heading'], 'url': c['file'],
                     'date': c['date'], 'excerpt': text_from_html(c['excerpt']),
                     'text': c['text'], 'image': c.get('image'),
                     'tags': [{'name': x, 'label': x, 'slug': slug(x)}
                              for x in c['tags']]})
    # The sequence </ is split inside the data, so that a string in an article
    # cannot close the script element sooner than it should.
    cards = json.dumps(data, ensure_ascii=False).replace('</', '<' + chr(92) + '/')

    plain = ['<ul class="rozcestnik">']
    for c in articles:
        plain.append('<li><a href="%s">%s</a></li>' % (c['file'], c['heading']))
    plain.append('</ul>')

    # Order is taken from the bar, so the eye looks for a tag in the same place
    # as everywhere else. Tags that are not in the bar are appended after it
    # alphabetically.
    #
    # `lead` also SPLITS THE FILTER INTO TWO ROWS: what the bar carries leads,
    # the rest follows underneath. Curating the bar is thus the one place where
    # a tag is called important, and no article has to be touched to say so.
    #
    # THE BAR IS CURATED, THE FILTER IS COMPLETE. The reason
    # `.obsidian2html/menu.md` selects is the width of the header - twenty chips
    # stop working there. The filter, though, has a page of its own and room of
    # its own, so it carries them all, and a tag that has a page must be
    # filterable. Otherwise curating the bar would quietly drop a tag out of the
    # filter and nobody would know why.
    chips = []
    in_menu = set()
    pseudo = False
    for label, url, tag in site['menu']:
        if tag:
            chips.append({'name': tag, 'label': label, 'lead': True})
            in_menu.add(tag)
        elif url == tag_page(T['no_tag_slug']):
            pseudo = True
            in_menu.add(T['no_tag_slug'])
    for tag in site['tags']:
        if tag not in in_menu:
            chips.append({'name': tag, 'label': tag, 'lead': False})
    if pseudo or any(not c['tags'] for c in articles):
        # The pseudo-tag closes the second row wherever the bar puts it. It
        # names no topic, it collects what fell through, and the leading row
        # is for the axes one filters by on purpose.
        chips.append({'name': T['no_tag_slug'], 'label': NO_TAG_LABEL,
                      'lead': False})

    content = (SEARCH_PAGE.replace('@DATA@', cards)
                    .replace('@TAGS@', json.dumps(chips, ensure_ascii=False))
                    .replace('@TEXTS@', json.dumps(T, ensure_ascii=False))
                    .replace('@LIST@', ''.join(plain))
                    .replace('@NO_TAG@', T['no_tag_slug'])
                    .replace('@NEEDS_JS@', escape(T['needs_js']))
                    .replace('@SEARCH@', escape(T['search'])))
    return site_page(T['search'], content, site, T['search_file'],
                     fixed_only=True)


RSS_ITEMS = 20         # kolik nejnovejsich clanku jde do feedu

# Nazvy dnu a mesicu ANGLICKY a natvrdo. RFC 822 jine nepripousti a locale by
# na ceskych Windows vyrobilo "So, 28 srp", tedy nevalidni feed.
RSS_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
RSS_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def is_date(value):
    """Is this YYYY-MM-DD? Anything else cannot order the front page.

    A date is not decoration - the ordering of the front page rests on it, and
    a string sort puts an unrecognised one wherever it happens to fall. A
    template placeholder like {{date:YYYY-MM-DD}} left in an article therefore
    lands it at the very top, ahead of everything real, and nothing says why.
    """
    try:
        time.strptime(value, '%Y-%m-%d')
    except (ValueError, TypeError):
        return False
    return True


def rfc822(date):
    """2026-08-28 -> Fri, 28 Aug 2026 00:00:00 +0000. Vraci None pri nesmyslu."""
    try:
        d = time.strptime(date, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None
    return '%s, %02d %s %d 00:00:00 +0000' % (RSS_DAYS[d.tm_wday], d.tm_mday,
                                              RSS_MONTHS[d.tm_mon - 1], d.tm_year)


def xml_text(s):
    """Escaping for a text node. An excerpt may contain links and bold text,
    so without this an invalid feed would be produced."""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def rss(articles, site, url):
    """A feed of the newest articles. The EXCERPT goes in, not the whole text.

    The full text would drag the images along, and their relative paths would
    lead nowhere in a reader. An excerpt plus a link is decent and keeps the
    file small.

    Links have to be ABSOLUTE - which is why the address comes from a flag. The
    rest of the site is deliberately relative so it can be opened off a disk,
    but that does not hold in a feed: a reader consumes it somewhere else.

    lastBuildDate is deliberately absent. With it the file would change on every
    build even with no change in content, and it would be uploaded again for
    nothing.
    """
    base = url.rstrip('/')
    label = site.get('description') or site['name']
    lines = ['<?xml version="1.0" encoding="utf-8"?>',
             '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
             '<channel>',
             '<title>%s</title>' % xml_text(site['name']),
             '<link>%s/</link>' % base,
             '<description>%s</description>' % xml_text(label),
             '<language>%s</language>' % T['lang'],
             '<atom:link href="%s/rss.xml" rel="self" type="application/rss+xml"/>'
             % base]

    for c in articles[:RSS_ITEMS]:
        url = '%s/%s' % (base, c['file'])
        lines.append('<item>')
        lines.append('<title>%s</title>' % xml_text(c['heading']))
        lines.append('<link>%s</link>' % url)
        lines.append('<guid isPermaLink="true">%s</guid>' % url)
        when = rfc822(c['date'])
        if when:
            lines.append('<pubDate>%s</pubDate>' % when)
        for tag in c['tags']:
            lines.append('<category>%s</category>' % xml_text(tag))
        if c['excerpt']:
            lines.append('<description>%s</description>'
                         % xml_text(text_from_html(c['excerpt'])))
        lines.append('</item>')

    lines.extend(['</channel>', '</rss>', ''])
    return '\n'.join(lines)


def find_logo(vault, out_dir):
    """The logo is a site input, so .obsidian2html/logo.svg or .png.

    When there is none, the header sets the site name as text. The script does
    not invent a placeholder - a logo is the author's business.
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
    """Return the file's last-modified date as YYYY-MM-DD. WRITES NOTHING.

    The fallback for an article with no date in its frontmatter. The decision to
    publish is carried by the marker in the name, so a missing date should not
    be a reason for the build to fail.

    It is shaky: a file's date changes when the vault is copied and when it is
    synchronised, so the order on the front page can be reshuffled. git would be
    the alternative, but git need not work in the input directory at all. On
    equal dates the article name decides, so the build is at least repeatable.

    The date used to be WRITTEN into the frontmatter of the source. No longer -
    the input directory is only ever read.
    """
    return time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(path)))


def clean_output(out_dir):
    """Archive the previous output and empty the directory.

    Everything is deleted and built again, because a surgical clean-up driven by
    a list of produced files is needless machinery. The original worry about
    wholesale deletion is answered by the archive - the previous state stays at
    hand.

    ONLY A DIRECTORY CARRYING THE MARKER IS WIPED, or an empty one, or one that
    does not exist. A directory belonging to somebody else survives even a typo
    in the path; 'unlikely' thereby becomes 'impossible'.

    The CONTENTS are deleted, not the directory itself - when something holds it
    open (a browser, an FTP client), removing the directory fails with Device or
    resource busy.
    """
    if not os.path.isdir(out_dir):
        return None
    content = os.listdir(out_dir)
    if not content:
        return None
    if not os.path.isfile(os.path.join(out_dir, OUTPUT_MARKER)):
        raise Error('%s does not come from this script (%s is missing) and will'
                    ' not be wiped. Check the path.' % (out_dir, OUTPUT_MARKER))

    archiv = os.path.join(os.path.dirname(os.path.abspath(out_dir)), '_archiv')
    if not os.path.isdir(archiv):
        os.makedirs(archiv)
    # The archive sits ONE LEVEL UP, not inside the directory being packed -
    # otherwise every backup would be packed into the next one and they would
    # grow geometrically.
    # Seconds in the name are necessary: two runs within the same minute would
    # OVERWRITE each other's archive and the older version would quietly
    # vanish. Verified - it happened during testing.
    base = os.path.join(archiv, '%s-%s' % (os.path.basename(os.path.abspath(out_dir)),
                                             time.strftime('%Y-%m-%d-%H%M%S')))
    # And one more guard on the second: when an archive of that name already
    # exists, a number is appended. A backup must never be overwritten, not even
    # by two runs within the same
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
    """Verify relative links in the output and flatten the dead ones to text.

    Three cases are told apart, because each means something different:

    - THE TARGET EXISTS IN A DIFFERENT LETTER CASE is an error. Windows does not
      distinguish case, Linux does, so such a link works locally and returns 404
      on the server - and it is a typo, to be fixed rather than hidden.
    - A MISSING IMAGE (src) is an error. Quietly, a page with a blank space in
      it would be produced.
    - A MISSING LINK TARGET (href) is FLATTENED to text and reported. Project
      documentation routinely links to files in the repository -
      ../20_fact/nsp20Fact.sql:179 - which is right inside the repository and
      nonsense on a website. Flattening keeps the information about which file
      it is, and the build passes. It is the same thing wikilinks outside the
      batch already do.

    Returns the list of flattened links.
    """
    files, uppercase = set(), []
    for root, _, names in os.walk(out_dir):
        for s in names:
            rel = os.path.relpath(os.path.join(root, s), out_dir).replace(os.sep, '/')
            files.add(rel)
            if s != s.lower() and not s.startswith('.'):
                uppercase.append(rel)
    lowered = dict((s.lower(), s) for s in files)

    bad, flattened = [], []
    for rel in sorted(files):
        if not rel.endswith('.html'):
            continue
        path = os.path.join(out_dir, rel)
        with open(path, encoding='utf-8') as f:
            html = f.read()
        # Scripts out: strings in the JS that are assembled into an address
        # ('tag-' + t.slug + '.html') are not links, and the check would trip
        # over them. The search page is full of those.
        without_script = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', html)

        dead = []
        for attr, link in re.findall(r'(href|src|action)="([^"]+)"', without_script):
            # file: in an article about links is a deliberate example, not a
            # broken link.
            if link.startswith(('http:', 'https:', 'mailto:', 'data:', 'file:',
                                 '#', '//')):
                continue
            target = unquote(link.split('#')[0].split('?')[0])
            if not target or target in files:
                continue
            if target.lower() in lowered:
                bad.append('%s: %s -> 404 on Linux, the file is called %s'
                              % (rel, link, lowered[target.lower()]))
            elif attr == 'src':
                bad.append('%s: %s -> no such image in the output' % (rel, link))
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
        bad.append('upper case in an output name: %s' % ', '.join(sorted(uppercase)))
    if bad:
        raise Error('Broken links in the output (%d):\n  %s'
                    % (len(bad), '\n  '.join(bad)))
    return flattened


# Frontmatter keys that were renamed into English. When an old one turns up,
# the article would quietly lose its date or its title, so it gets reported.
LEGACY_KEYS = {'datum': 'date', 'titul': 'title', 'perex': 'excerpt'}


def template_dirs(vault):
    """Folders that Obsidian itself calls templates, as relative paths.

    A template is not an article: it is a skeleton with placeholders in it, and
    publishing one puts {{date:YYYY-MM-DD}} on the web. Reading the setting
    beats asking the author to rename the folder - the vault already says which
    one it is, and every Obsidian user has it configured without knowing.

    The core Templates plugin keeps it in .obsidian/templates.json, Templater in
    its own data.json. Both are read; a vault may well have both.

    A broken or missing file is not an error. The setting is a convenience, and
    a vault without it simply has no templates to skip.
    """
    found = set()
    kde = (('templates.json', 'folder'),
           (os.path.join('plugins', 'templater-obsidian', 'data.json'),
            'templates_folder'))
    for rel, key in kde:
        path = os.path.join(vault, '.obsidian', rel)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, encoding='utf-8') as f:
                folder = (json.load(f) or {}).get(key)
        except (ValueError, OSError, AttributeError):
            continue
        if folder:
            found.add(os.path.normpath(folder).replace(os.sep, '/').strip('/'))
    return found


def collect(src, published_only, skip_dirs=()):
    """Return ([(path, meta, body)], forgotten, legacy) for a file or directory.

    `forgotten` are articles carrying the frontmatter key publish but no marker.
    The key means nothing any more, so such an article does not go out - and its
    author most likely believes the opposite. Staying silent would mean the
    article quietly fails to appear.

    `legacy` are articles with an old Czech key. Same reason: the key is not
    read, so the article would quietly lose its date or its title.

    `templates` are marked articles inside a template folder. They are skipped
    the same way the rest of that folder is, but a marker on one of them is a
    contradiction the author should hear about rather than discover on the site
    that is missing them.
    """
    templates = []
    if os.path.isfile(src):
        paths = [src]
    else:
        paths = []
        for root, dirs, files in os.walk(src):
            rel = os.path.relpath(root, src).replace(os.sep, '/').strip('./')
            ponechat = []
            for a in dirs:
                if a.startswith(('.', '_')) or a in ATTACHMENT_DIRS:
                    continue
                if ('%s/%s' % (rel, a) if rel else a) in skip_dirs:
                    # A marked article in here is a contradiction: the folder
                    # says template, the marker says publish. It stays skipped
                    # and the build says which one it was.
                    templates.extend(
                        os.path.join(root, a, x)
                        for x in sorted(os.listdir(os.path.join(root, a)))
                        if x.lower().endswith('.md')
                        and is_published(os.path.join(root, a, x)))
                    continue
                ponechat.append(a)
            dirs[:] = ponechat
            paths.extend(os.path.join(root, s) for s in sorted(files)
                         if s.lower().endswith('.md'))
    result, forgotten, legacy = [], [], []
    for c in paths:
        meta, body_text = split_frontmatter(read_text(c))
        if published_only and not is_published(c):
            if 'publish' in meta:
                forgotten.append(c)
            continue
        for old, new in sorted(LEGACY_KEYS.items()):
            if old in meta and new not in meta:
                legacy.append((c, old, new))
        result.append((c, meta, body_text))
    return result, forgotten, legacy, templates


def index_page(items):
    lines = ['<h1>Obsah</h1>', '<ul class="rozcestnik">']
    for c in sorted(items, key=lambda x: x['heading'].lower()):
        lines.append('<li><a href="%s">%s</a></li>'
                     % (c['file'], c['heading']))
    lines.append('</ul>')
    css = CSS.replace('@SIZE@', 'A4')
    return HTML.format(lang=T['lang'], title='Obsah', css=css,
                       body='\n'.join(lines), footer='')


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
    p.add_argument('--marker', default='🌐',
                   help='the publish marker at the end of a filename'
                        ' (default: a globe). A character that also turns up in'
                        ' ordinary names is a poor marker - it is stripped off'
                        ' the title as well')
    p.add_argument('--all', action='store_true',
                   help='convert every article, marker or not. The output is'
                        ' still only a directory of HTML - uploading it'
                        ' anywhere is a separate act. The build says how many'
                        ' unmarked articles came along')
    p.add_argument('--lang', default='cs',
                   help='language of the generated site: cs or en (default: cs).'
                        ' It also decides the page names, so a Czech site keeps'
                        ' hledani.html and its published addresses')
    args = p.parse_args()

    try:
        set_language(args.lang)
        set_marker(args.marker)
    except Error as e:
        print('ERROR: %s' % e)
        return 2

    # A marker made of ordinary characters cannot be told apart from a name
    # that simply ends that way. It still works, but the author should hear it
    # once rather than wonder later why an article went out.
    if not any(ord(z) > 0x2000 for z in args.marker):
        print('NOTE: the marker %r is made of ordinary characters, so an'
              ' article whose name merely ends that way goes out too.'
              % args.marker)

    if not os.path.exists(args.input):
        print('ERROR: input does not exist: %s' % args.input)
        return 2

    # Site mode without the filter would dump the whole vault onto the
    # internet. That is not a convenience, it is a safeguard.
    # Check mode is site mode that builds into a temporary directory and throws
    # the result away. It is for a git hook that wants to know whether the site
    # builds at all. No mode writes into the vault any more, see guarantee Z45.
    if args.check:
        args.site = True
    if args.site:
        args.published_only = True
    # --all wins over everything, site mode included. It is not a second way for
    # an article to be published by accident - it is one explicit instruction,
    # and the build repeats out loud what it did.
    if args.all:
        args.published_only = False
    # Where output goes is decided by a flag - no default path in the code. The
    # output belongs outside the repository and outside the vault, and only the
    # author knows where, see guarantee Z50.
    if args.site and not args.out and not args.check:
        print('ERROR: --site needs -o, that is where to build the site.')
        return 2

    if args.clean and not args.site:
        print('ERROR: --clean only makes sense together with --site.')
        return 2

    batch_mode = os.path.isdir(args.input)
    vault = os.path.abspath(args.vault or
                            (args.input if batch_mode
                             else os.path.dirname(os.path.abspath(args.input))))

    try:
        items, forgotten, legacy, templates = collect(
            args.input, args.published_only, template_dirs(vault))
        # --all is loud on purpose. The safeguard is that publishing is a
        # deliberate act; a flag that switches it off has to say so, or the
        # next person to read the log will not know what went out.
        if args.all:
            unmarked = [c for c, _, _ in items if not is_published(c)]
            print('\nNOTE: --all, so %d of the %d articles carry no marker.'
                  % (len(unmarked), len(items)))
            print('A directory of HTML is what comes out; uploading it anywhere'
                  ' is a separate act.')
        if not items:
            print('Nothing to convert.')
            return 1

        # A map of note -> output file. It has to be complete before conversion
        # starts, so that wikilinks between notes in the batch lead somewhere.
        #
        # The slug is computed from the FILENAME, not from the title. Titles
        # repeat - in PKVault five notes out of the task template have the H1
        # 'Popis' - and a slug taken from the title would quietly overwrite one
        # with another. A filename is unambiguous within its folder. Should a
        # clash happen anyway (the same name in two folders), a number is
        # appended and it is reported.
        #
        # The frontmatter key slug overrides only the OUTPUT FILENAME. It exists
        # for the sake of address stability: a published article keeps its slug
        # even after the note is renamed, because nobody will fix inbound links.
        # An overriding slug still goes through slug(), so that a typo in the
        # YAML cannot produce a name with a space in it.
        #
        # The KEY in the map stays derived from the filename, because a wikilink
        # knows only the target note's name and is resolved through slug(stem) -
        # see Conversion.resolve_wikilinks. Were the key the overriding slug,
        # links to such a note would stop leading anywhere.
        plan, batch, used, clashes, guessed_dates = [], {}, set(), [], []
        bad_dates = []
        oversized = []
        for path, meta, body_text in items:
            stem = os.path.splitext(os.path.basename(path))[0]
            key = slug(stem)
            base = slug(meta['slug']) if meta.get('slug') else key
            name, n = base, 2
            while name in used:
                name, n = '%s-%d' % (base, n), n + 1
            if name != base:
                # On a website an address is a commitment and must not change
                # with whatever happens to be published alongside the article.
                # A quiet rename to -2 is acceptable for a batch going out by
                # email, not for a site.
                if args.site:
                    raise Error('Address clash on %s.html - two articles share a'
                                ' name. Rename one of them: %s'
                                % (base, path))
                clashes.append('%s -> %s.html' % (path, name))
            if args.site and not meta.get('date'):
                # The decision to publish is carried by the marker, so a
                # missing date does not fail the build - the file's date is
                # used. Nothing is written into the source, see guarantee Z45.
                meta['date'] = file_date(path)
                guessed_dates.append((path, meta['date']))
            elif meta.get('date') and not is_date(meta['date']):
                # Reported rather than refused: what a date should look like is
                # the author's business, and a build that stops over one article
                # is worse than one that says which article it is.
                bad_dates.append((path, meta['date']))
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
                print('  %s  (%.0f kB, the previous output)'
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
            # built without a logo, without the bar and without the custom
            # styles, and it would look like a fault in the generator rather
            # than a directory nobody renamed.
            if (os.path.isdir(os.path.join(vault, '_web'))
                    and not os.path.isdir(os.path.join(vault, CONFIG_DIR))):
                print('\nNOTE: the vault has a _web directory, which is no longer'
                      ' read. Rename it to %s.' % CONFIG_DIR)
                print('Inside it, rename menu_webu.md to menu.md.')

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
            # wipe only a directory that carries it - never somebody else's,
            # not even after a typo in the path.
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
                print('  (no logo: %s/logo.svg or .png is expected,'
                      ' the header sets the name instead)' % CONFIG_DIR)

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
            # Ordering: date descending, the name on a tie. Without the
            # secondary key
            # bylo poradi uvnitr serie se stejnym datem libovolne.
            ordered = sorted(produced, key=lambda c: c['heading'].lower())
            ordered.sort(key=lambda c: c['date'], reverse=True)

            for nazev_s, html_s in card_grid(
                    ordered, 'index', home_title or T['articles'], site,
                    intro=intro, hidden_heading=True):
                print('  %s' % zapis(nazev_s, html_s))

            # Tag pages use the same listing. They are produced here because
            # the bar on every page links to them, and the link check would
            # otherwise trip over a target that does not exist.
            # The heading is hidden here as well - which tag the filter is on is
            # said by the highlighted button in the bar, so it is redundant in
            # the text.
            for tag in site['tags']:
                sem = [c for c in ordered if tag in c['tags']]
                # Reachable = tags that co-occur with this one somewhere. The
                # bar dims the rest, so a combination yielding nothing cannot
                # even be clicked.
                reachable = {t for c in sem for t in c['tags']}
                for nazev_s, html_s in card_grid(sem, T['tag_prefix'] + slug(tag),
                                                    tag, site, tag,
                                                    hidden_heading=True,
                                                    active_tag=tag,
                                                    reachable=reachable):
                    print('  %s  (%d articles, %d combinable tags)'
                          % (zapis(nazev_s, html_s), len(sem),
                             len(reachable - {tag})))

            sem = [c for c in ordered if not c['tags']]
            if sem:
                for nazev_s, html_s in card_grid(
                        sem, T['tag_prefix'] + T['no_tag_slug'], T['no_tag_heading'], site,
                        tag_page(T['no_tag_slug']), hidden_heading=True,
                        active_tag=T['no_tag_slug']):
                    print('  %s  (%d articles without tags)'
                          % (zapis(nazev_s, html_s), len(sem)))

            print('  %s' % zapis(T['search_file'],
                                 search_page(ordered, site)))

            if args.base_url:
                print('  %s  (%d items)'
                      % (zapis('rss.xml', rss(ordered, site, args.base_url)),
                         min(len(ordered), RSS_ITEMS)))
        elif batch_mode:
            cesta_s = zapis('index.html', index_page(produced))
            print('  %s  (an index of %d pages)' % (cesta_s, len(produced)))

        if args.site:
            flattened_links = check_links(out_dir)
            if flattened_links:
                print('\nFlattened file links (%d): no such target in the'
                      ' output, only the text is left.' % len(flattened_links))
                for x in flattened_links[:10]:
                    print('  %s' % x)
                if len(flattened_links) > 10:
                    print('  ... and %d more' % (len(flattened_links) - 10))

        if args.site:
            # Kuratorovany seznam v KONFIG/menu.md rozhoduje, co je v liste. Novy
            # a new tag does not add itself there, because the point of curating
            # is to keep the bar
            # kratkou - ale mlcet o tom by znamenalo, ze si autor doplni tag a
            # and wonders why it is not in the bar.
            in_menu = set(x for _, _, x in site['menu'] if x)
            missing = [x for x in site['tags'] if x not in in_menu]
            if missing:
                print('\nTags outside the bar (%d): the page is generated and an'
                      ' article footer links to it, but it is not in the bar.'
                      % len(missing))
                print('Add a line to %s/menu.md when it belongs there:' % CONFIG_DIR)
                for x in missing:
                    print('  `#%s`  ->  %s' % (x, tag_page(x)))

            # The opposite case: the bar names a tag that no published article
            # carries. Its page is never generated, so it is dimmed in the bar
            # - but the author should know why, or the bar just looks broken.
            empty_tags = [x for x in in_menu if x not in site['tags']]
            if empty_tags:
                print('\nTags in the bar with no articles (%d): no page is'
                      ' generated, they are dimmed in the bar and cannot be'
                      ' clicked.' % len(empty_tags))
                print('Publish an article with that tag, or drop the line from'
                      ' %s/menu.md:' % CONFIG_DIR)
                for x in sorted(empty_tags):
                    print('  `#%s`' % x)

        if oversized:
            print('\nOversized thumbnails (%d): on the front page they are shown'
                  ' 9rem high, so a smaller file is enough.' % len(oversized))
            for c, kb in oversized:
                print('  %.0f kB  %s' % (kb, c))

        if bad_dates:
            print('\nNOTE: a date that is not a date (%d). The front page is'
                  ' ordered by it, so an unrecognised one lands wherever the'
                  ' string sort puts it - usually at the top:' % len(bad_dates))
            for c, d in bad_dates:
                print('  %r  %s' % (d, c))

        if guessed_dates:
            print('\nNo date in the frontmatter, taken from the file (%d).'
                  ' A file date changes when copying and when syncing, so the'
                  ' order on the front page need not survive:'
                  % len(guessed_dates))
            for c, d in guessed_dates:
                print('  %s  %s' % (d, c))

        if legacy:
            print('\nNOTE: old Czech frontmatter keys (%d). They are no longer'
                  ' read, so the article loses its date or its title:' % len(legacy))
            for c, old, new in legacy:
                print('  %s -> %s  %s' % (old, new, c))

        if templates:
            # Skipping is right, staying silent is not: the author marked the
            # article on purpose and would otherwise look for it on the site.
            print('\nNOTE: a marked article inside the template folder (%d).'
                  ' Templates never go out, so it was skipped:' % len(templates))
            for c in templates:
                print('  %s' % c)

        if forgotten:
            print('\nNOTE: a publish key without the marker in the name (%d) -'
                  ' these do NOT go out.' % len(forgotten))
            for c in forgotten:
                print('  %s' % c)

        if clashes:
            print('\nName clashes (%d): the same filename in two folders, '
                  'prejmenovano.' % len(clashes))
            for k in clashes:
                print('  %s' % k)

        if conv.flattened:
            unique = sorted(set(conv.flattened))
            print('\nFlattened links (%d): the target is not in the batch, only'
                  ' the text is left.' % len(unique))
            for u in unique[:10]:
                print('  %s' % u)
            if len(unique) > 10:
                print('  ... and %d more' % (len(unique) - 10))

        return 0

    except Error as e:
        print('ERROR: %s' % e)
        return 1
    except (OSError, IOError) as e:
        print('ERROR: %s' % e)
        return 1
    finally:
        # Kontrolni rezim po sobe nesmi nechat adresar - hook bezi pri kazdem
        # commitu a za mesic by jich v temp byly stovky.
        if 'docasny' in dir() and tmp_dir and os.path.isdir(tmp_dir):
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
