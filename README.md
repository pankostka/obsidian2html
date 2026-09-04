# obsidian2html

Turns an Obsidian vault into HTML. Two modes, and the first one is the reason this exists:

- **Single-file HTML** - images inlined as data URIs, styles inside, no relative links. One file that survives email, SharePoint, a network share, Teams, or a button in a Power BI report.
- **Static site** (`--web`) - shared stylesheet, images as files, tag pages, and a faceted search page.

PDF is a bonus, typeset from the very same HTML through headless Edge or Chrome.

## Why not Quartz or Pandoc

Fair question, and worth answering before you read further.

[Quartz](https://github.com/jackyzha0/quartz) is more mature at building a **site** from a vault. If a website is all you need, use Quartz.

What neither Quartz nor Obsidian Publish does is produce **one self-contained file** you can attach to an email. Pandoc does that (`--standalone --embed-resources`) but does not natively understand Obsidian syntax - `![[embeds]]`, transclusion, wikilinks. This tool sits in that gap: vault in, one file out.

One design decision worth naming: **a dead link is never generated.** If a link target is not part of the batch, the link degrades to plain text and the script reports how many did. A document sent to a person is worse with a link that goes nowhere than with no link at all.

## Install

```bash
pip install markdown
```

For PDF output you also need Edge or Chrome installed. Python 3.8+.

## Usage

```bash
python md2html.py notes.md                  # one file -> <slug>.html
python md2html.py vault/                    # batch, plus index.html
python md2html.py vault/ -o out/            # where to put it
python md2html.py notes.md --pdf            # HTML, and a PDF from the same render
python md2html.py vault/ --vault path/      # where to look for ![[images]]
python md2html.py vault/ --web              # static site mode
```

Exit codes: `0` done, `1` conversion error, `2` bad arguments. Run `--help` for the full list.

## Obsidian syntax it understands

| Syntax | Result |
|---|---|
| frontmatter | stripped, not rendered as text |
| `![[image.png]]` | embedded, resolved the way Obsidian resolves it |
| `![[image.png\|300]]` | same, width 300 px |
| `![[Note]]` | transclusion - the note's content is inlined |
| `[[Note]]` | link if the note is in the batch, otherwise plain text |
| `[[Note\|label]]` | same, with its own label |

## Publishing flag

Whether an article goes out is carried by a **marker in the filename** - a globe at the end, so `Article name X.md`. No marker means not public.

The reason is visibility: you can see what is public in the file tree, while frontmatter you cannot. The marker never reaches the URL, the slug drops it.

## Frontmatter

| Key | Meaning |
|---|---|
| `titul` | overrides the document title, otherwise the filename is used |
| `datum` | publication date. Required for published articles - without it the front page cannot be ordered and `--web` fails |
| `slug` | overrides the output filename. Rarely needed - an escape hatch for one URL that must survive a rename |
| `tags` | topics, used by the tag bar and the faceted filter |

## A note on language

The tool was written for a Czech vault, so **command-line flags, frontmatter keys, and the generated interface are in Czech** - `--titul`, `--jen-publikovane`, `datum`, and a search page called `hledani.html`. Comments and docstrings inside the source are Czech too.

Making the interface English and the output localizable is planned. Until then, `--help` explains every flag, and this README covers the keys you need.

## License

MIT - see [LICENSE](LICENSE).
