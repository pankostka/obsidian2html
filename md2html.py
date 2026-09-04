# -*- coding: utf-8 -*-
r"""
================================================================================
 POPIS
   Prevede Markdown na SAMOSTATNY HTML soubor pro uzivatele - obrazky vlozene
   jako data URI, styly uvnitr, zadne relativni odkazy. Snese to mail,
   SharePoint, sitovy disk, Teams i tlacitko v Power BI reportu.

   Rozumi Obsidian syntaxi, protoze zdrojem je vault:
     frontmatter        odstrizne se (jinak by se vykreslil jako text)
     ![[obrazek.png]]   vlozi obrazek, hleda ho jako Obsidian
     ![[obrazek.png|300]] totez, sirka 300 px
     ![[Nota]]          vlozi obsah te noty (transkluze, jako v Obsidianu)
     [[Nota]]           odkaz, kdyz je nota v davce; jinak jen text
     [[Nota|jinak]]     totez se svym textem

   MRTVY ODKAZ SE NIKDY NEVYROBI. Kdyz cil odkazu v davce neni, zustane z
   nej holy text a skript rekne kolik. Dokument jde uzivateli - odkaz, ktery
   nikam nevede, je horsi nez zadny.

   PDF SE TADY NEVYRABI. Drive to skript umel a jmenoval se md2pdf.py, ale
   tisk je samostatna uloha pro samostatny nastroj.

 SPUSTENI
   python md2html.py <soubor.md>              jeden soubor -> <slug>.html
   python md2html.py <adresar>                davka, vcetne index.html
   python md2html.py <vstup> -o <kam>         kam to ulozit
   python md2html.py <vstup> --vault <cesta>  kde hledat ![[obrazky]]
   python md2html.py <soubor.md> --titul "Text"  titulek bez zasahu do zdroje
   python md2html.py <vstup> --jen-publikovane  jen clanky s markerem v nazvu
   python md2html.py <vault> --web -o <kam>   web: sdilene styl.css, img/,
                                              vystup do zadaneho adresare

   Zavislost: pip install markdown.

   Navratovy kod 0 = hotovo, 1 = chyba pri prevodu, 2 = spatne parametry.

 FASETOVY FILTR TAGU
   Stitky se KOMBINUJI A ZAROVEN (AND), nenahrazuji se. `Obsidian` + `Video` da
   clanky o Obsidianu, ktere maji video. Stitek, ktery by v kombinaci s uz
   vybranymi dal nulu, se ZTLUMI a nejde kliknout - proto se neda proklikat do
   prazdna. Ztlumi se, nezmizi: kdyby mizel, lista pri kazdem kliknuti poskoci.

   Zije to na dvou mistech, ktera se doplnuji:

   hledani.html   ziva verze. Stitky, textovy dotaz i pocty se prepocitavaji
                  spolecne - dotaz zuzuje i to, ktere stitky jeste sviti. Stav
                  je v adrese (`?tag=a&tag=b&q=...`), takze se da poslat a
                  vratit tlacitkem zpet. Lista tagu se tam vynechava, dve rady
                  stitku na jedne strance jsou zmatek.
   tag-*.html     staticka verze BEZ JavaScriptu. Stitek v liste vede na
                  hledani.html s OBEMA tagy, tedy pridava; nedosazitelny je
                  ztlumeny uz v HTML, protoze co s cim se potkava, vi build.

   Predgenerovat kombinace nejde - dvacet tagu je milion podmnozin. Proto je
   kombinovani v prohlizeci, zatimco jednotlive stranky tagu zustavaji staticke
   kvuli odkazum zvenci a vyhledavacum.

   POZOR: ten filtr je jen tak dobry, jak dobre je tagovani. Kdyz ma clanek
   jeden tag, neni co kombinovat. Vyplati se az u vic nezavislych osi, tedy
   napriklad tema + forma (`Video`, `Navod`) + uroven.

 PRIZNAK PUBLIKACE
   Nese ho MARKER V NAZVU SOUBORU - globus na konci, tedy 'Nazev clanku X.md'.
   Chybejici marker znamena neverejne. Frontmatter klic publish uz neznamena
   nic; kdyz na nej skript narazi u clanku bez markeru, ohlasi to, protoze
   autor si nejspis mysli, ze clanek publikuje.

   Duvod je viditelnost: ve strome souboru je videt, co je verejne, kdezto
   frontmatter videt neni. Do adresy se marker nepropise, slug() ho zahodi.

 FRONTMATTER
   titul    prebije titulek dokumentu, jinak je jim nazev souboru
   datum    datum vydani. Kdyz chybi, vezme se datum souboru a build to
            ohlasi. Pri shode dat rozhoduje nazev clanku
   slug     prebije nazev vystupniho souboru. Bezne se NEPOUZIVA: adresa je
            ocisteny nazev souboru a slug se neudrzuje. Je to unikovy vychod
            pro jednu adresu, na ktere zalezi i po prejmenovani clanku

 VYSTUPY
   <nazev>.html   samostatny HTML, obrazky jako data URI
   index.html     jen v davce, rozcestnik na HTML

   S --web je to jinak: styl je v jednom styl.css vedle stranek a obrazky v
   img/ jako soubory, protoze v samostatnem rezimu ma jedna stranka s pati
   screenshoty 598 kB a prohlizec nekesuje nic. K tomu tri kontroly - kolize
   adresy je chyba a velikost pismen v odkazech se overuje proti skutecnym
   souborum (na Linuxu je Foo.png a foo.png rozdil).

   DO VSTUPNIHO ADRESARE SE JEN CTE. Vault je zdroj, ne pracovni plocha:
   generator v nem nic nevytvori, nezmeni ani nesmaze. Drive zapisoval dve
   veci - evidenci vydanych adres a datum do frontmatteru clanku, ktery ho
   nemel. Evidence zrusena, datum se bere z data souboru.

   -o urcuje zaklad cesty a pripona se doplni, takze z -o vystup/napoveda
   vznikne napoveda.html.
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

MAX_TRANSKLUZE = 3
PRILOHY = ('Attachments', 'img', 'assets')

# Slozka se vstupy pro web: menu.md, index.md, styl.css, logo. Tecka na
# zacatku ji v Obsidianu skryje, coz je zamer - nejsou to clanky a edituji se
# mimo Obsidian. Nazev rika, ke kteremu nastroji patri, takze vedle .obsidian
# nevznika nejasnost. posbirej() ji preskoci uz kvuli te tecce.
KONFIG = '.obsidian2html'

# Priznak publikace je MARKER V NAZVU SOUBORU, ne frontmatter klic. Duvod je
# viditelnost: ve strome souboru je videt, ktery clanek je verejny, kdezto
# frontmatter videt neni. Chybejici marker znamena neverejne.
#
# Do adresy se marker nepropise - slug() zahodi vsechno, co neni \w ani \s.
# Ze textu odkazu ho strhava preloz_wikilinky, jinak by byl globus uprostred
# prozy.
MARKER_PUBLIKACE = '🌐'

# Znacka ve vystupnim adresari. Mazat smi skript jen adresar, ktery ji ma,
# nebo je prazdny. Cizi adresar se tim nesmaze ani pri preklepu v ceste.
ZNACKA_VYSTUPU = '.vygenerovano'

# Pseudotag pro clanky bez tagu. V liste je z nej tlacitko '#', stranka se
# jmenuje tag-bez-tagu.html a nadpis zni 'Bez tagu' - samotna mrizka je jako
# titulek stranky i pro ctecku pro nevidome k nicemu.
BEZ_TAGU_SLUG = 'bez-tagu'
BEZ_TAGU_POPIS = '#'
BEZ_TAGU_NADPIS = 'Bez tagu'


# ==============================================================================
# Vzhled
# ==============================================================================

CSS_OBSAH = """
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
CSS_CHROM = """
/* Sirka textu. Uzka nudle uprostred obrazovky je presne to, proc je v
   Obsidianu doporuceno vypnout Readable line length - na tabulky a kod je
   to k nepouziti. Na webu proto 64rem misto 46rem, ktere zustava
   samostatnemu souboru.
   Prepsat jde v .obsidian2html/styl.css. */
body { max-width: 64rem; padding-top: 1.25rem; }
/* Zahlavi clanku: nadpis, pod nim tagy, linka az pod obojim. V samostatnem
   souboru zustava linka na h1, protoze tam zadne tagy nejsou. */
.zahlavi { border-bottom: 2px solid var(--odkaz); padding-bottom: .5rem;
           margin-bottom: 1.4rem; }
.zahlavi h1 { border-bottom: 0; padding-bottom: 0; margin-bottom: .35rem; }
.zahlavi .tagy { display: flex; flex-wrap: wrap; gap: .5rem;
                 font-size: .85rem; }
.zahlavi .tagy a { text-decoration: none; color: var(--tlum); }
.zahlavi .tagy a:hover { color: var(--odkaz); }
.jen-ctecka { position: absolute; width: 1px; height: 1px; overflow: hidden;
              clip-path: inset(50%); white-space: nowrap; }

/* Hlavicka ma dva radky: nahore logo vlevo a hledani vpravo, pod tim tagy
   odleva. Hledani v hlavicce je formular - index lezi jen ve hledani.html,
   takze z ostatnich stranek se dotaz posila tam pres ?q=. */
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
/* Nedosazitelny stitek se ZTLUMI, nezmizi. Kdyby zmizel, lista se pri kazdem
   kliknuti prelozi a ctenar ztrati orientaci, kde co bylo. */
.hlavicka nav .zhasnuty { font-size: .88rem; padding: .25rem .6rem;
                          border: 1px solid var(--linka); border-radius: 999px;
                          white-space: nowrap; color: var(--tlum);
                          opacity: .45; cursor: default; }
.hlavicka nav .pocet-tagu { opacity: .6; font-size: .8em; margin-left: .3em; }

/* Fasetovy filtr na strance hledani. Stitky se kombinuji a zaroven. */
.fasety { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: 1.5rem; }
.stitek { font: inherit; font-size: .88rem; padding: .25rem .6rem;
          border: 1px solid var(--linka); border-radius: 999px;
          background: none; color: var(--odkaz); cursor: pointer;
          white-space: nowrap; }
.stitek:hover { background: var(--th); }
.stitek.vybrany { background: var(--odkaz); color: #fff; border-color: var(--odkaz); }
/* Nedosazitelny stitek se ZTLUMI, nezmizi - jinak lista pri kazdem kliknuti
   poskakuje a clovek ztrati orientaci, kde co bylo. */
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

/* Vypis perexu je mrizka, ne seznam. auto-fill misto pevnych tri sloupcu:
   pri 64rem vyjdou tri, na mobilu jeden, a nepotrebuje to breakpointy. */
.vypis { display: grid; gap: 1.2rem; margin-top: 1.4rem;
         grid-template-columns: repeat(auto-fill, minmax(18rem, 1fr)); }
.karta { padding: 1rem 1.1rem; border: 1px solid var(--linka);
         border-radius: 8px; background: var(--pozadi); }
/* Nahled ma pevnou vysku a orizne se, aby karty v mrizce drzely radek.
   Orez je odspodu (object-position: top) - u screenshotu je zajimavy vrsek.
   Obrazek je dekorace k titulku, ktery je hned pod nim - proto prazdny
   alt, aby ho ctecka pro nevidome necetla dvakrat. */
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

CSS = CSS_OBSAH
CSS_WEB = CSS_OBSAH + CSS_CHROM


HTML = ('<!doctype html><html lang="cs"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>{title}</title><style>{css}</style></head><body>{body}{paticka}'
        '</body></html>')

# Web mode: styl je v jednom souboru vedle stranek, ne v kazde z nich. Duvod
# je velikost - v samostatnem rezimu ma jedna stranka se pati screenshoty
# 598 kB, protoze obrazky jsou v base64 a CSS se opakuje.
HTML_WEB = ('<!doctype html><html lang="cs"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<title>{title}</title>'
            '<link rel="stylesheet" href="styl.css">{hlava}</head><body>'
            '{hlavicka}<main>{body}</main>{paticka}'
            '</body></html>')

# Stranka hledani. Index je ZAPECENY uvnitr, protoze pod file:// nepada
# JavaScript, ale fetch() - prohlizec zakaze cteni lokalniho JSON kvuli CORS.
# Zapecenim ta prekazka mizi a tentyz soubor funguje z hostingu i z disku.
HLEDANI = r"""<h1 class="jen-ctecka">Hledání</h1>
<div id="fasety" class="fasety"></div>
<div id="vysledky"></div>
<noscript>
  <p>Hledání potřebuje JavaScript. Bez něj zbývá seznam všech článků:</p>
  @SEZNAM@
</noscript>
<script>
// Index je ZAPECENY v teto strance, nikoli nacitany. Pod file:// nepada
// JavaScript, ale fetch() - prohlizec zakaze cteni lokalniho JSON kvuli CORS.
// Zapecenim ta prekazka mizi a tentyz soubor funguje z hostingu i z disku.
//
// Pole pro dotaz je v HLAVICCE, tedy na kazde strance. Index je ale jen tady,
// takze na ostatnich strankach formular odesle dotaz sem pres ?q=. Kdyz je
// stranka zafiltrovana na tag, prilozi k tomu jeste ?tag= a hleda se jen v
// clancich toho tagu.
const CLANKY = @DATA@;
const BEZ_TAGU = '@BEZ@';
// Poradi stitku prebira lista, aby oko hledalo tag na temze miste jako jinde.
const VSECHNY_TAGY = @TAGY@;

const bez = s => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// Ceske sklonovani: 1 clanek, 2-4 clanky, 5+ clanku.
const clanku = n => n + (n === 1 ? ' článek' : (n < 5 ? ' články' : ' článků'));

CLANKY.forEach(c => {
  c.nTitul = bez(c.titul);
  c.nText = bez(c.text);
  c.nTagy = bez(c.tagy.map(t => t.nazev).join(' '));
});

const parametry = new URLSearchParams(location.search);
// Stav filtru je MENITELNY: stitek se pridava, nenahrazuje. Tag z adresy je
// jen vychozi nastaveni, dal se s nim da pracovat.
let filtry = parametry.getAll('tag').filter(Boolean);
let rozsah = [];

function projdeTagy(c, sada) {
  return sada.every(f => f === BEZ_TAGU ? c.tagy.length === 0
                                        : c.tagy.some(t => t.nazev === f));
}

function popisRozsahu() {
  if (!filtry.length) return '';
  return ' v ' + filtry.map(f => f === BEZ_TAGU ? 'článcích bez tagu'
                                                : '#' + f).join(' a ');
}

function skore(c, slova) {
  let s = 0;
  for (const w of slova) {
    if (c.nTitul.includes(w)) s += 5;
    else if (c.nTagy.includes(w)) s += 3;
    else if (c.nText.includes(w)) s += 1;
    else return 0;            // vsechna slova musi byt nalezena
  }
  return s;
}

function uryvek(c, slovo) {
  const i = c.nText.indexOf(slovo);
  if (i < 0) return esc(c.text.slice(0, 180)) + (c.text.length > 180 ? '…' : '');
  const od = Math.max(0, i - 70);
  const kus = c.text.slice(od, i + slovo.length + 110);
  const rel = i - od;
  return (od > 0 ? '…' : '')
    + esc(kus.slice(0, rel))
    + '<mark>' + esc(kus.slice(rel, rel + slovo.length)) + '</mark>'
    + esc(kus.slice(rel + slovo.length))
    + (od + kus.length < c.text.length ? '…' : '');
}

function karta(c, popis) {
  const tagy = c.tagy.map(t => '<a href="tag-' + t.slug + '.html">#' + esc(t.nazev)
                               + '</a>').join(' ');
  const meta = [c.datum, tagy].filter(Boolean).join(' ');
  const nahled = c.obrazek
    ? '<a class="nahled" href="' + c.adresa + '"><img src="' + c.obrazek
      + '" alt=""></a>'
    : '';
  return '<article class="karta">' + nahled
       + '<h2><a href="' + c.adresa + '">' + esc(c.titul)
       + '</a></h2>' + (meta ? '<div class="meta">' + meta + '</div>' : '')
       + '<p class="perex">' + popis + '</p></article>';
}

function hledej(dotaz) {
  const slova = bez(dotaz).split(/\s+/).filter(Boolean);
  const pocet = document.getElementById('pocet');
  const cil = document.getElementById('vysledky');
  const vypis = seznam => '<div class="vypis">' + seznam.join('') + '</div>';

  if (!slova.length) {
    pocet.textContent = clanku(rozsah.length) + popisRozsahu();
    cil.innerHTML = vypis(rozsah.map(c => karta(c, esc(c.perex))));
    return;
  }
  const nalezene = rozsah.map(c => ({ c: c, s: skore(c, slova) }))
                         .filter(x => x.s > 0)
                         .sort((a, b) => b.s - a.s);
  if (!nalezene.length) {
    pocet.textContent = 'nic nenalezeno' + popisRozsahu();
    cil.innerHTML = '';
    return;
  }
  pocet.textContent = (nalezene.length === 1 ? '1 nalezený'
                                             : nalezene.length + ' nalezených')
                      + popisRozsahu();
  cil.innerHTML = vypis(nalezene.map(x => karta(x.c, uryvek(x.c, slova[0]))));
}

// ---------------------------------------------------------------------------
// Fasetovy filtr
//
// Stitky se KOMBINUJI A ZAROVEN (AND). Diky tomu pridani stitku mnozinu nikdy
// nezvetsi, a kdyz se zhasnou stitky, ktere by daly nulu, NEDA SE proklikat do
// prazdna. Ta vlastnost je duvod, proc to jde pouzivat - neni to nahoda.
//
// Zhasnuty stitek ZUSTAVA na svem miste. Kdyby se skryval, lista by se pri
// kazdem kliknuti prelozila a clovek by ztratil orientaci.
//
// Pocty se prepocitavaji pri kazdem prekresleni, vcetne textoveho dotazu.
// Jinak by lhaly - a pocet, ktery lze, je horsi nez zadny.
// ---------------------------------------------------------------------------

function pocetPro(sada, slova) {
  return CLANKY.filter(c => projdeTagy(c, sada)
                            && (!slova.length || skore(c, slova) > 0)).length;
}

function vykresliFasety(slova) {
  const cil = document.getElementById('fasety');
  const kusy = [];
  for (const tag of VSECHNY_TAGY) {
    const vybrany = filtry.includes(tag.nazev);
    const sada = vybrany ? filtry.filter(f => f !== tag.nazev)
                         : filtry.concat([tag.nazev]);
    const pocet = pocetPro(sada, slova);
    if (vybrany) {
      // Bez poctu zamerne: u vybraneho stitku by cislo znamenalo 'kdyz ho
      // odeberu', tedy vic nez je videt, a cetlo by se jako pocet jeho clanku.
      // Kolik je vysledku ted, rika udaj v hlavicce.
      kusy.push('<button type="button" class="stitek vybrany" data-tag="'
                + esc(tag.nazev) + '" aria-pressed="true" title="odebrat filtr">#'
                + esc(tag.popis) + '</button>');
    } else if (pocet === 0) {
      kusy.push('<span class="stitek zhasnuty" aria-disabled="true">#'
                + esc(tag.popis) + '<span class="pocet-tagu">0</span></span>');
    } else {
      kusy.push('<button type="button" class="stitek" data-tag="'
                + esc(tag.nazev) + '" aria-pressed="false">#' + esc(tag.popis)
                + '<span class="pocet-tagu">' + pocet + '</span></button>');
    }
  }
  if (filtry.length) {
    kusy.push('<button type="button" class="stitek zrusit" id="zrusit">'
              + 'zrušit filtr</button>');
  }
  cil.innerHTML = kusy.join('');
}

function zapisAdresu(dotaz) {
  // Stav patri do adresy, aby se dal poslat a vratit tlacitkem zpet.
  const p = new URLSearchParams();
  filtry.forEach(f => p.append('tag', f));
  if (dotaz) { p.set('q', dotaz); }
  const dotazovaCast = p.toString();
  history.replaceState(null, '',
                       location.pathname + (dotazovaCast ? '?' + dotazovaCast : ''));
}

function prekresli() {
  const dotaz = pole.value;
  const slova = bez(dotaz).split(/\s+/).filter(Boolean);
  rozsah = CLANKY.filter(c => projdeTagy(c, filtry));
  hledej(dotaz);
  vykresliFasety(slova);
  zapisAdresu(dotaz);
}

const pole = document.getElementById('dotaz');
// Na teto strance se nikam neodesila, hleda se na miste. Filtr ale musi ve
// formulari zustat, aby ho dalsi dotaz neztratil.
pole.form.addEventListener('submit', e => e.preventDefault());
pole.addEventListener('input', prekresli);

document.getElementById('fasety').addEventListener('click', e => {
  if (e.target.id === 'zrusit') { filtry = []; prekresli(); return; }
  const stitek = e.target.closest('button[data-tag]');
  if (!stitek) { return; }
  const tag = stitek.getAttribute('data-tag');
  filtry = filtry.includes(tag) ? filtry.filter(f => f !== tag)
                                : filtry.concat([tag]);
  prekresli();
});

const zParametru = parametry.get('q');
if (zParametru) { pole.value = zParametru; }
pole.focus();
prekresli();
</script>"""


# Tlacitko, ktere zkopiruje nazev clanku do schranky. Odkaz file:// by
# prozradil usporadani disku a prohlizec ho ze stranky nactene pres https
# stejne nepusti; nazev je neskodny, protoze uz je videt jako titulek.
KOPIROVAT = r"""<script>
// Zkopiruje NAZEV clanku, ne cestu k souboru. Cesta by prozradila usporadani
// disku a odkaz file:// prohlizec ze stranky nacetene pres https stejne
// nepusti. Nazev staci: v Obsidianu ho vezme CTRL+O a fuzzy hledani si
// dohleda i marker na konci nazvu.
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
    // Clipboard API chce zabezpeceny kontext. file:// se za nej povazuje, ale
    // http bez sifrovani ne - proto zalozni cesta pres docasny textarea.
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


class Chyba(Exception):
    pass


# ==============================================================================
# Cteni a frontmatter
# ==============================================================================

def zdroj_text(cesta):
    """Precte .md. UTF-8 s BOM i bez nej, jinak spadne na cp1250."""
    with open(cesta, 'rb') as f:
        data = f.read()
    for kodovani in ('utf-8-sig', 'cp1250'):
        try:
            return data.decode(kodovani).replace('\r\n', '\n')
        except UnicodeDecodeError:
            continue
    raise Chyba('Soubor %s neni v UTF-8 ani v cp1250.' % cesta)


def oddel_frontmatter(text):
    """Vrati (meta, telo). Bez tohohle by se frontmatter vykreslil jako text.

    Parsuje se jen to, co potrebujeme - plosny YAML klic: hodnota. Zadny
    parser YAMLu, aby nebyla zavislost.
    """
    if not text.startswith('---\n'):
        return {}, text
    konec = text.find('\n---', 3)
    if konec < 0:
        return {}, text
    hlavicka = text[4:konec]
    telo = text[konec + 4:].lstrip('\n')
    meta = {}
    posledni = None
    for radek in hlavicka.split(chr(10)):
        odsazeny = radek[:1] in (' ', chr(9))
        holy = radek.strip()
        # Blokovy zapis seznamu, ktery Obsidian umi vyrobit sam:
        #   tags:
        #     - obsidian
        # Bez tohohle by takovy klic zustal prazdny a clanek prisel o tagy.
        if odsazeny and holy.startswith('- ') and posledni:
            hodnota = holy[2:].strip().strip(chr(34) + chr(39))
            stara = meta.get(posledni) or ''
            meta[posledni] = (stara + ', ' + hodnota).strip(', ')
            continue
        if ':' not in radek or odsazeny or holy.startswith('-'):
            continue
        klic, _, hodnota = radek.partition(':')
        posledni = klic.strip().lower()
        meta[posledni] = hodnota.strip().strip(chr(34) + chr(39))
    return meta, telo


def bez_markeru(text):
    """Odstrizne marker publikace z konce nazvu vcetne mezery pred nim."""
    return text.rstrip().rstrip(MARKER_PUBLIKACE).rstrip()


def je_publikovana(cesta):
    """Publikuje se podle MARKERU V NAZVU SOUBORU, ne podle frontmatteru.

    Jedina pojistka proti nechtenemu zverejneni, takze mechanismus musi byt
    jeden. Kdyby vedle markeru fungoval i klic publish, prestalo by platit
    'chybejici marker znamena neverejne' - a to je to jedine pravidlo, na
    ktere se tady da spolehnout.
    """
    stem = os.path.splitext(os.path.basename(cesta))[0]
    return stem.rstrip().endswith(MARKER_PUBLIKACE)


# ==============================================================================
# Slug a titulek
# ==============================================================================

RE_H1 = re.compile(r'^#\s+(.+)$', re.M)


def titulek(meta, cesta):
    """Titulek je NAZEV SOUBORU, pripadne frontmatter titul.

    H1 se na titulek nepouziva, protoze to nejde spolehlive poznat. Zkouseno na
    skutecnych datech: docs/nsp20DimManazVysl_AX.md ma jedine H1 a je to opravdu
    titulek dokumentu, ale PKVault/…/Hadičky.md ma taky jedine H1 a je to
    Popis - sekce ze sablony tasku. Stejna struktura, jiny vyznam.

    Nazev souboru je Obsidianuv model (v Obsidianu je nazev noty jeji titulek),
    je jednoznacny v ramci slozky a da se predpovedet. Kdyz je nazev technicky,
    jako u plnici procedury, prebije ho frontmatter klic titul.
    """
    if meta.get('titul'):
        return meta['titul']
    return bez_markeru(os.path.splitext(os.path.basename(cesta))[0])


def slug(text):
    """Nazev vystupniho souboru: mala pismena, bez diakritiky, pomlcky.

    Nazev noty smi mit diakritiku, mezery i emoji; URL ne. Slug se proto
    pocita, nikoli prebira.
    """
    bez = unicodedata.normalize('NFKD', text)
    bez = ''.join(c for c in bez if not unicodedata.combining(c))
    bez = re.sub(r'[^\w\s-]', '', bez, flags=re.U).strip().lower()
    bez = re.sub(r'[\s_]+', '-', bez)
    bez = re.sub(r'-{2,}', '-', bez).strip('-')
    return bez or 'nota'


# ==============================================================================
# Obsidian syntaxe
# ==============================================================================

RE_EMBED = re.compile(r'!\[\[([^\]|#]+?)(?:#[^\]|]*)?(?:\|([^\]]*))?\]\]')
RE_WIKILINK = re.compile(r'(?<!!)\[\[([^\]|#]+?)(?:#([^\]|]*))?(?:\|([^\]]*))?\]\]')
OBRAZKY = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')

# Ohraniceny blok kodu a kod v radku. Uvnitr se nic nenahrazuje.
RE_KOD = re.compile(
    r'^(?P<f>```+|~~~+)[^\n]*\n.*?^(?P=f)[ \t]*$'   # ```...```
    r'|(?P<t>`+)[^\n]*?(?P=t)',                     # `...`
    re.M | re.S)


def mimo_kod(text, nahrada):
    """Pusti nahradu jen na casti textu MIMO kod.

    Bez toho si prevodnik prepise vlastni ukazky syntaxe: nota, ktera uci psat
    wikilinky, ma v `[[Nazev]]` obycejny kod, ale RE_WIKILINK ho vidi jako
    odkaz, cil nenajde a zplosti ho na holy text. Ctenar se pak z clanku o
    zavorkach dozvi vsechno krome tech zavorek. Overeno na Obsidian Markdown.
    """
    kusy, pozice = [], 0
    for m in RE_KOD.finditer(text):
        kusy.append(nahrada(text[pozice:m.start()]))
        kusy.append(m.group(0))
        pozice = m.end()
    kusy.append(nahrada(text[pozice:]))
    return ''.join(kusy)


def najdi_soubor(nazev, zaklad, vault):
    """Najde soubor jako Obsidian: u noty, v jeji slozce priloh, pak v celem
    vaultu. Vraci None, kdyz nic."""
    kandidati = [os.path.join(zaklad, nazev)]
    for p in PRILOHY:
        kandidati.append(os.path.join(zaklad, p, nazev))
    for c in kandidati:
        if os.path.isfile(c):
            return c
    hledany = os.path.basename(nazev).lower()
    for koren, adresare, soubory in os.walk(vault):
        adresare[:] = [a for a in adresare if not a.startswith('.')]
        for s in soubory:
            if s.lower() == hledany:
                return os.path.join(koren, s)
    return None


class Prevod(object):
    """Drzi kontext jednoho prevodu - kde hledat soubory a co je v davce."""

    def __init__(self, vault, davka=None, web=False):
        self.vault = vault
        self.davka = davka or {}      # {slug nazvu noty: vystupni soubor}
        self.web = web
        self.zplostene = []           # odkazy, ze kterych zbyl jen text

    # -- transkluze -------------------------------------------------------

    def rozbal_embedy(self, text, zaklad, hloubka=0, videne=None):
        videne = set(videne or ())

        def nahrad(m):
            cil, param = m.group(1).strip(), (m.group(2) or '').strip()
            if cil.lower().endswith(OBRAZKY):
                sirka = param if param.isdigit() else None
                return self._obrazek(cil, param, sirka)
            return self._nota(cil, zaklad, hloubka, videne, m.group(0))

        return mimo_kod(text, lambda t: RE_EMBED.sub(nahrad, t))

    def _obrazek(self, cil, param, sirka):
        """Obsidian embed nema alt text, tak ho udelame z nazvu souboru -
        ctecka pro nevidome ho potrebuje."""
        # Marker publikace se strhava i tady. Alt text cte ctecka pro nevidome
        # nahlas a globus na konci nazvu souboru pro ni neznamena nic.
        alt = param if (param and not param.isdigit()) else \
            bez_markeru(os.path.splitext(os.path.basename(cil))[0])
        if sirka:
            return '<img src="%s" alt="%s" width="%s">' % (cil, alt, sirka)
        return '![%s](%s)' % (alt, cil)

    def _nota(self, cil, zaklad, hloubka, videne, original):
        # Vaultova lista na web nepatri - web ma vlastni hlavicku a odkazy z
        # menu.md miri na interni oblasti, takze by se zplostily na text.
        # V Obsidianu ale ![[menu]] v clanku smysl ma, tak se jen preskoci.
        if self.web and slug(os.path.splitext(cil)[0]) == 'menu':
            return ''
        if hloubka >= MAX_TRANSKLUZE:
            self.zplostene.append('%s (prilis hluboka transkluze)' % cil)
            return ''
        nazev = cil if cil.lower().endswith('.md') else cil + '.md'
        cesta = najdi_soubor(nazev, zaklad, self.vault)
        if not cesta or os.path.abspath(cesta) in videne:
            self.zplostene.append(cil)
            return ''
        _, telo = oddel_frontmatter(zdroj_text(cesta))
        # H1 vlozene noty zahodit - v cilovem dokumentu uz jeden H1 je
        telo = RE_H1.sub('', telo, count=1).strip()
        return self.rozbal_embedy(telo, os.path.dirname(cesta), hloubka + 1,
                                  videne | {os.path.abspath(cesta)})

    # -- wikilinky --------------------------------------------------------

    def preloz_wikilinky(self, text):
        def nahrad(m):
            cil, kotva, popis = m.group(1).strip(), m.group(2), m.group(3)
            # Bez strzeni markeru by veta 'Dal pokracuj na [[Obsidian Ovladani X]]'
            # vysadila globus doprostred prozy. Aliasy u kazdeho odkazu by byly
            # vic prace nez frontmatter, ktery marker nahradil.
            text_odkazu = (popis or '').strip() or bez_markeru(cil)
            klic = slug(os.path.splitext(os.path.basename(cil))[0])
            if klic in self.davka:
                href = self.davka[klic]
                if kotva:
                    href += '#' + slug(kotva)
                return '[%s](%s)' % (text_odkazu, href)
            self.zplostene.append(cil)
            return text_odkazu
        return mimo_kod(text, lambda t: RE_WIKILINK.sub(nahrad, t))


# ==============================================================================
# Markdown -> HTML
# ==============================================================================

def vloz_obrazky(html, zaklad, vault):
    """Nahradi src="cesta" za data URI, aby bylo HTML samostatne.

    Chybejici obrazek je chyba, ne varovani. V tichosti by vznikl dokument s
    prazdnym mistem a odesel uzivateli.
    """
    chybi = []

    def nahrad(m):
        odkaz = m.group(1)
        if odkaz.startswith(('http:', 'https:', 'data:', '//')):
            return m.group(0)
        cesta = najdi_soubor(unquote(odkaz), zaklad, vault)
        if not cesta:
            chybi.append(odkaz)
            return m.group(0)
        typ = mimetypes.guess_type(cesta)[0] or 'application/octet-stream'
        with open(cesta, 'rb') as f:
            data = base64.b64encode(f.read()).decode('ascii')
        return 'src="data:%s;base64,%s"' % (typ, data)

    html = re.sub(r'src="([^"]+)"', nahrad, html)
    if chybi:
        raise Chyba('Chybi obrazky: %s' % ', '.join(sorted(set(chybi))))
    return html


def zkopiruj_prilohu(zdroj, kam, prejmenovane):
    """Zkopiruje jeden soubor do img/ a vrati relativni adresu.

    Nazev se prozene slug(), takze je vzdy malymi pismeny a v ASCII. Na Linuxu
    je Foo.png a foo.png rozdil, takze spatne napsany odkaz funguje na Windows
    a na serveru vrati 404. prejmenovane hlida, aby dva ruzne soubory neskoncily
    pod jednou adresou.
    """
    adresar = os.path.join(kam, 'img')
    stem, pripona = os.path.splitext(os.path.basename(zdroj))
    nazev = slug(stem) + pripona.lower()
    drive = prejmenovane.get(nazev)
    zdroj = os.path.abspath(zdroj)
    if drive and drive != zdroj:
        raise Chyba('Dva obrazky maji stejnou adresu %s: %s a %s'
                    % (nazev, drive, zdroj))
    if not drive:
        if not os.path.isdir(adresar):
            os.makedirs(adresar)
        shutil.copy2(zdroj, os.path.join(adresar, nazev))
        prejmenovane[nazev] = zdroj
    return 'img/' + nazev


def zkopiruj_obrazky(html, zaklad, vault, kam, prejmenovane):
    """Web mode: src="cesta" -> src="img/nazev.ext" a soubor se zkopiruje.

    Data URI je spravne pro jeden samostatny soubor do mailu, ale na web ne -
    kazda stranka by nesla vlastni kopii obrazku i CSS a prohlizec by nekesoval
    nic. Sdileny adresar img/ se stahne jednou.

    Nazev se prozene slug(), takze je vzdy malymi pismeny a v ASCII. Na Linuxu
    je Foo.png a foo.png rozdil, takze spatne napsany odkaz funguje na Windows
    a na serveru vrati 404 - chyba, ktera se najde az po nasazeni.
    """
    chybi = []

    def nahrad(m):
        odkaz = m.group(1)
        if odkaz.startswith(('http:', 'https:', 'data:', '//')):
            return m.group(0)
        cesta = najdi_soubor(unquote(odkaz), zaklad, vault)
        if not cesta:
            chybi.append(odkaz)
            return m.group(0)
        return 'src="%s"' % zkopiruj_prilohu(cesta, kam, prejmenovane)

    html = re.sub(r'src="([^"]+)"', nahrad, html)
    if chybi:
        raise Chyba('Chybi obrazky: %s' % ', '.join(sorted(set(chybi))))
    return html


def na_html(cesta, prevod, meta=None, titul=None,
            kam=None, prejmenovane=None, web=None):
    """Vrati (titulek, kompletni HTML). S kam= sazi web mode."""
    try:
        import markdown
    except ImportError:
        raise Chyba('Chybi balicek markdown. Doinstaluj: pip install markdown')

    zaklad = os.path.dirname(os.path.abspath(cesta))
    vlastni_meta, telo = oddel_frontmatter(zdroj_text(cesta))
    if meta is not None:
        meta.update(vlastni_meta)
    nadpis = titul or titulek(vlastni_meta, cesta)

    telo = prevod.rozbal_embedy(telo, zaklad)
    telo = prevod.preloz_wikilinky(telo)
    if kam is not None:
        telo = snizit_nadpisy(telo)

    body = markdown.markdown(telo, extensions=[
        'tables', 'fenced_code', 'attr_list', 'sane_lists',
    ])
    body = re.sub(r'(<table>.*?</table>)', r'<div class="tabulka">\1</div>',
                  body, flags=re.S)
    if kam is None:
        body = vloz_obrazky(body, zaklad, prevod.vault)
    else:
        body = zkopiruj_obrazky(body, zaklad, prevod.vault, kam, prejmenovane)

    paticka = ''
    if vlastni_meta.get('datum'):
        paticka = '<div class="paticka">%s</div>' % vlastni_meta['datum']

    if kam is not None:
        # Titulek clanku je jediny h1 na strance. Sekce z markdownu jsou o
        # uroven niz, viz snizit_nadpisy.
        # Nadpis a tagy jsou v jednom bloku, aby linka byla az pod tagy. Je
        # proto na tom bloku, ne na h1 - v samostatnem souboru zustava na h1,
        # viz CSS_OBSAH.
        tagy = tagy_z_meta(vlastni_meta)
        zahlavi = ['<div class="zahlavi"><h1>%s</h1>' % nadpis]
        if tagy:
            zahlavi.append('<div class="tagy">%s</div>' % ' '.join(
                '<a href="tag-%s.html">#%s</a>' % (slug(x), x) for x in tagy))
        zahlavi.append('</div>')
        return nadpis, HTML_WEB.format(
            title='%s - %s' % (nadpis, web['nazev']),
            hlava=web.get('hlava', ''),
            hlavicka=hlavicka_html(web),
            body=''.join(zahlavi) + body,
            paticka=paticka_html(web, vlastni_meta.get('datum'), tagy, nadpis))
    return nadpis, HTML.format(title=nadpis, css=CSS, body=body, paticka=paticka)


# ==============================================================================
# Davka
# ==============================================================================

def tagy_z_meta(meta):
    """Tagy z frontmatteru. Zvladne [a, b] i blokovy seznam pod klicem."""
    hrube = (meta.get('tags') or '').strip().strip('[]')
    return [x.strip().strip('"\'') for x in hrube.split(',') if x.strip()]


def snizit_nadpisy(text):
    """Sekce z markdownu o uroven niz, protoze h1 je titulek clanku.

    Clanky pouzivaji # pro svoje sekce, takze bez tohohle ma stranka nekolik h1
    a zadny, ktery by byl titulkem. Pro ctecku pro nevidome i pro vyhledavac je
    to rozbita struktura. Tag v textu (#dwh) zustava - regexp chce za mrizkou
    mezeru.
    """
    return mimo_kod(text, lambda t: re.sub(r'^(#{1,5})(\s)', r'#\1\2', t,
                                           flags=re.M))


def polozky_menu(text, tagy, bez_tagu=False):
    """Polozky listy jako [(popis, adresa, tag)]. Tag je None u pevneho odkazu.

    Bez .obsidian2html/menu.md jsou to vsechny tagy abecedne. Kuratorovany seznam je
    potreba proto, ze tagu muze byt dvacet a lista by se rozsypala - a poradi
    tagu abecedne nemusi odpovidat tomu, co je dulezite.

    Radek smi byt:
      `#obsidian`            tag, odkaz na jeho stranku
      [Hledani](hledani.html) obycejny odkaz
      [[Nazev clanku]]       odkaz na clanek, adresa se odvodi z nazvu
    Odrazka na zacatku se ignoruje, aby to v Obsidianu mohl byt seznam.
    """
    pseudo = (BEZ_TAGU_POPIS, 'tag-%s.html' % BEZ_TAGU_SLUG, None)
    if not text:
        hotovo = [(t, 'tag-%s.html' % slug(t), t) for t in tagy]
        return hotovo + ([pseudo] if bez_tagu else [])

    polozky = []
    for radek in text.split('\n'):
        r = radek.strip().lstrip('-*').strip()
        if not r or r.startswith('>'):
            continue
        # Tag se pise v backticich: `#PowerBI`. Bez nich by ho Obsidian bral
        # jako skutecny tag vaultu a lista by lezla do vyhledavani tagu, kam
        # nepatri - je to konfigurace webu, ne obsah. Backticky jsou jen obal,
        # holy #tag se cte dal, aby starsi soubory fungovaly.
        if len(r) > 2 and r.startswith('`') and r.endswith('`'):
            r = r[1:-1].strip()
        m = re.match(r'^\[\[([^\]|]+?)(?:\|([^\]]+))?\]\]$', r)
        if m:
            cil = m.group(1).strip()
            popis = (m.group(2) or bez_markeru(cil)).strip()
            polozky.append((popis, slug(cil) + '.html', None))
            continue
        m = re.match(r'^\[([^\]]+)\]\(([^)]+)\)$', r)
        if m:
            polozky.append((m.group(1).strip(), m.group(2).strip(), None))
            continue
        if r == BEZ_TAGU_POPIS:
            # Samotna mrizka na radku je pseudotag 'clanky bez tagu'.
            if bez_tagu:
                polozky.append(pseudo)
            continue
        if r.startswith('#') and len(r) > 1 and not r[1].isspace():
            tag = r[1:].strip()
            polozky.append((tag, 'tag-%s.html' % slug(tag), tag))
    # Kdyz se v menu.md o pseudotagu nikdo nezminil, prida se na konec sam -
    # jinak by clanky bez tagu nebyly dosazitelne odnikud nez z titulky.
    if bez_tagu and pseudo not in polozky:
        polozky.append(pseudo)
    return polozky


def wikilinky_v_uvodu(text, davka):
    """V uvodu titulky prevede [[Nota]] a [[Nota|popis]] na markdown odkaz.

    Uvod z `.obsidian2html/index.md` je jediny rucne psany text na titulce, takze do nej
    patri rozcestnik - a ten odkazuje na clanky. Bez tohohle by se do souboru
    musely psat ADRESY (`kostkaaxmain.html`), tedy presne to, cemu se wikilink
    vyhyba: prejmenovani clanku by odkaz tise rozbilo.

    Cil, ktery v davce neni, zustava holym textem. Mrtvy odkaz se nevyrobi,
    stejne jako v clancich.
    """
    if not davka:
        return text

    def nahrad(m):
        cil, popis = m.group(1).strip(), (m.group(2) or '')[1:].strip()
        soubor = davka.get(slug(bez_markeru(cil)))
        text_odkazu = popis or bez_markeru(cil)
        return '[%s](%s)' % (text_odkazu, soubor) if soubor else text_odkazu

    return mimo_kod(text, lambda t: re.sub(r'\[\[([^\]|]+?)(\|[^\]]*)?\]\]',
                                          nahrad, t))


def web_vstupy(vault, davka=None):
    """Precte menu.md, index.md a styl.css ze slozky KONFIG. Vse volitelne.

    Slozka obchazi posbirej() kvuli tecce na zacatku, takze se z tech souboru
    nikdy nestane stranka - jsou to vstupy pro web, ne clanky.

    Lista se smi jmenovat proste menu.md. Vault sice ma vlastni menu.md jako
    navigacni listu, ale ta lezi jinde a tady se s ni nic srazit nemuze.
    """
    kam = os.path.join(vault, KONFIG)
    menu = None
    cesta = os.path.join(kam, 'menu.md')
    if os.path.isfile(cesta):
        _, menu = oddel_frontmatter(zdroj_text(cesta))

    intro, titul = '', None
    cesta = os.path.join(kam, 'index.md')
    if os.path.isfile(cesta):
        meta, telo = oddel_frontmatter(zdroj_text(cesta))
        titul = meta.get('titul')
        telo = wikilinky_v_uvodu(telo, davka)
        if telo.strip():
            try:
                import markdown
            except ImportError:
                raise Chyba('Chybi balicek markdown. Doinstaluj: pip install markdown')
            intro = '<div class="intro">%s</div>' % markdown.markdown(
                telo, extensions=['tables', 'fenced_code', 'attr_list', 'sane_lists'])
    # Vlastni styly se PRIPOJUJI za vygenerovane, takze prepsat jde cokoli -
    # sirka, barvy, pismo. Barvy jsou tokeny v :root, takze zmena je jedna
    # radka. Bez tohohle by se muselo sahat do generatoru.
    vlastni_css = ''
    cesta = os.path.join(kam, 'styl.css')
    if os.path.isfile(cesta):
        with open(cesta, encoding='utf-8') as f:
            vlastni_css = f.read()
    return menu, intro, titul, vlastni_css


def odkaz_kombinace(tagy):
    """Adresa stranky hledani s predvybranymi tagy."""
    return 'hledani.html?' + '&'.join('tag=%s' % quote(t) for t in tagy)


def hlavicka_html(web, aktivni=None, filtr=None, dosazitelne=None,
                  jen_pevne=False):
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
    nazev = web['nazev']
    if web.get('logo'):
        znacka = '<img src="%s" alt="%s">' % (web['logo'], nazev)
    else:
        znacka = nazev
    # Radek 1: logo vlevo, hledani vpravo. Radek 2: tagy odleva.
    # Pole hledani je na KAZDE strance, ale index lezi jen ve hledani.html -
    # odtud tedy formular odesila dotaz tam pres ?q=. Kdyby index nesla kazda
    # stranka, platila by se jeho velikost pri kazdem nacteni.
    kusy = ['<header class="hlavicka">', '<div class="pas">',
            '<a class="logo" href="index.html">%s</a>' % znacka,
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
            ('<input type="hidden" name="tag" value="%s">' % filtr)
            if filtr else '',
            '<span class="pocet" id="pocet"></span>',
            '</form>', '</div>', '<nav>']
    for popis, adresa, tag in web['menu']:
        if jen_pevne and (tag or adresa == 'tag-%s.html' % BEZ_TAGU_SLUG):
            continue
        # aktivni je bud nazev tagu, nebo nazev souboru - aby se dala zvyraznit
        # i pevna polozka, treba Hledani.
        je_tu = (tag and tag == aktivni) or adresa == aktivni
        if tag and tag not in web['tagy']:
            # Kuratorovana polozka pro tag, ktery zadny publikovany clanek
            # nema, takze jeho stranka nevznikne. ZTLUMI SE, nezplosti:
            # zkontroluj_odkazy by z odkazu udelal holy text a v liste by mezi
            # stylovanymi pilulkami sedelo neostylovane slovo. Ztlumena pilulka
            # rekne totez a nerozbije radek. Build to navic ohlasi.
            kusy.append('<span class="zhasnuty" aria-disabled="true"'
                        ' title="zatím nemá publikovaný článek">%s</span>'
                        % popis)
        elif je_tu:
            # Aktivni stitek odbira filtr, tedy vraci na titulku.
            kusy.append('<a href="index.html" aria-current="page">%s</a>' % popis)
        elif tag and filtr:
            if dosazitelne is not None and tag not in dosazitelne:
                kusy.append('<span class="zhasnuty" aria-disabled="true"'
                            ' title="s #%s se nepotkává v žádném článku">%s</span>'
                            % (filtr, popis))
            else:
                kusy.append('<a href="%s">%s</a>'
                            % (odkaz_kombinace([filtr, tag]), popis))
        else:
            kusy.append('<a href="%s">%s</a>' % (adresa, popis))
    kusy.append('</nav></header>')
    if not web['menu']:
        # Zadny tag - prazdny <nav> by nechal ve strance zbytecny radek.
        kusy = [k for k in kusy if k not in ('<nav>', '</nav></header>')]
        kusy.append('</header>')
    return ''.join(kusy)


def paticka_html(web, datum=None, tagy=(), nazev=None):
    """Datum, tagy clanku a odkazy. U clanku k tomu tlacitko na kopii nazvu."""
    casti = []
    if datum:
        casti.append('<span>%s</span>' % datum)
    if tagy:
        casti.append('<span class="tagy">%s</span>' % ' '.join(
            '<a href="tag-%s.html">#%s</a>' % (slug(t), t) for t in tagy))
    odkazy = []
    if nazev:
        odkazy.append('<button type="button" id="kopirovat" class="kopie"'
                      ' data-nazev="%s">Zkopírovat název</button>'
                      % nazev.replace('"', '&quot;'))
    odkazy.append('<a href="index.html">Titulka</a>')
    if web.get('hledani'):
        odkazy.append('<a href="hledani.html">Hledání</a>')
    if web.get('rss'):
        odkazy.append('<a href="rss.xml">RSS</a>')
    odkazy.append('<a href="#">Nahoru</a>')
    casti.append('<span class="odkazy">%s</span>' % ''.join(odkazy))
    skript = KOPIROVAT if nazev else ''
    return '<footer class="paticka">%s</footer>%s' % (''.join(casti), skript)


def stranka_web(titulek_stranky, obsah, web, aktivni=None, filtr=None,
                dosazitelne=None, jen_pevne=False):
    """Obali obsah hlavickou a patickou. Pro titulku a stranky tagu."""
    return HTML_WEB.format(title='%s - %s' % (titulek_stranky, web['nazev']),
                           hlava=web.get('hlava', ''),
                           hlavicka=hlavicka_html(web, aktivni, filtr,
                                                  dosazitelne, jen_pevne),
                           body=obsah,
                           paticka=paticka_html(web))


NA_STRANKU = 12          # kolik perexu se vypise na jednu stranku
                         # Dvanact proto, ze vypis je mrizka po trech - deset by
                         # nechalo posledni radek s jednou kartou.


OBRAZEK_PEREXU_VAROVANI = 300 * 1024   # nad tuhle velikost se ozve build


def obrazek_perexu(cesta_clanku):
    """Najde obrazek k perexu: v Attachments vedle clanku, stejneho nazvu.

    Porovnava se pres slug(), takze sedne kterykoli zapis - "Obsidian Co je",
    "obsidian-co-je" i "obsidian_co_je". Standard chce prilohy malymi pismeny s
    podtrzitkem, kdezto clanek ma mezery a diakritiku; tolerance obe konvence
    smiruje, misto aby nutila jednu z nich porusit.

    Marker publikace se z nazvu clanku strhava - v nazvu prilohy nema co delat.
    """
    adresar = os.path.join(os.path.dirname(cesta_clanku), 'Attachments')
    if not os.path.isdir(adresar):
        return None
    hledany = slug(bez_markeru(os.path.splitext(os.path.basename(cesta_clanku))[0]))
    for jmeno in sorted(os.listdir(adresar)):
        stem, pripona = os.path.splitext(jmeno)
        if pripona.lower() in OBRAZKY and slug(stem) == hledany:
            return os.path.join(adresar, jmeno)
    return None


def perex(telo, meta, prevod):
    """Perex je PRVNI ODSTAVEC clanku, frontmatter klic perex ho prebije.

    Prvni odstavec se bere proto, ze uz je napsany - clanky tak zacinaji a
    delky vychazi na 70 az 230 znaku, tedy presne perexove. Rucni klic je pro
    pripad, kdy se uvod na vypis nehodi.

    Nadpis ukoncuje hledani: kdyz clanek zacina hned sekci, perex nema byt
    prvni veta te sekce, ale zadny.
    """
    try:
        import markdown
    except ImportError:
        raise Chyba('Chybi balicek markdown. Doinstaluj: pip install markdown')

    zdroj = (meta.get('perex') or '').strip()
    if not zdroj:
        for blok in telo.strip().split('\n\n'):
            b = blok.strip()
            if b.startswith('#'):
                break
            if not b or b.startswith(('![', '>', '|', '- ', '* ', '1. ', '```')):
                continue
            # Nadpis muze nasledovat hned na dalsim radku bez prazdneho radku
            # mezi tim - pak je v temze bloku a musi se uriznout, jinak by se
            # do perexu vlil nadpis i zacatek prvni sekce.
            zdroj = re.split(r'^#+\s', b, maxsplit=1, flags=re.M)[0].strip()
            if not zdroj:
                break
            break
    if not zdroj:
        return ''
    # Vlozeny obrazek do perexu nepatri - je to textova upoutavka a nahled
    # ma karta vlastni. Bez tohohle by v nem zustala hola syntaxe ![[...]],
    # protoze perex se transkluzi zamerne neprohani.
    zdroj = RE_EMBED.sub('', zdroj)
    zdroj = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', zdroj)
    # Wikilinky i v perexu, aby odkaz z titulky vedl nekam. Marker se strhava
    # stejne jako v tele clanku.
    # Po vyhozeni obrazku zbyde dvojita mezera, proto se bily znaky srazi.
    zdroj = re.sub(r'\s+', ' ', zdroj).strip()
    zdroj = prevod.preloz_wikilinky(zdroj)
    html = markdown.markdown(zdroj).strip()
    m = re.match(r'^<p>(.*)</p>$', html, re.S)
    return m.group(1) if m else html


def karta(c):
    """Jeden clanek na vypisu: titulek, datum s tagy, perex."""
    kusy = ['<article class="karta">']
    if c.get('obrazek'):
        kusy.append('<a class="nahled" href="%s"><img src="%s" alt=""></a>'
                    % (c['soubor'], c['obrazek']))
    kusy.append('<h2><a href="%s">%s</a></h2>' % (c['soubor'], c['nadpis']))
    popisky = []
    if c['datum']:
        popisky.append(c['datum'])
    if c['tagy']:
        popisky.append(' '.join('<a href="tag-%s.html">#%s</a>' % (slug(t), t)
                                for t in c['tagy']))
    if popisky:
        kusy.append('<div class="meta">%s</div>' % ' '.join(popisky))
    if c['perex']:
        kusy.append('<p class="perex">%s</p>' % c['perex'])
    kusy.append('</article>')
    return ''.join(kusy)


def nazev_stranky(zaklad, cislo):
    """Prvni stranka je bez cisla, aby adresa titulky byla index.html."""
    return zaklad + ('.html' if cislo == 1 else '-%d.html' % cislo)


def strankovani(zaklad, cislo, celkem):
    """Odkazy vpred a vzad. Staticke, zadny skript."""
    if celkem < 2:
        return ''
    kusy = []
    if cislo > 1:
        kusy.append('<a href="%s">&larr; Novější</a>'
                    % nazev_stranky(zaklad, cislo - 1))
    kusy.append('<span>Stránka %d z %d</span>' % (cislo, celkem))
    if cislo < celkem:
        kusy.append('<a href="%s">Starší &rarr;</a>'
                    % nazev_stranky(zaklad, cislo + 1))
    return '<nav class="strankovani">%s</nav>' % ''.join(kusy)


def vypis_perexu(clanky, zaklad, nadpis, web, aktivni=None, intro='',
                 skryty_nadpis=False, filtr=None, dosazitelne=None):
    """Vrati [(nazev_souboru, html)] - strankovany vypis perexu po NA_STRANKU.

    Prazdny seznam da jednu prazdnou stranku, aby lista neodkazovala nikam.
    """
    stranky = [clanky[i:i + NA_STRANKU]
               for i in range(0, len(clanky), NA_STRANKU)] or [[]]
    vysledek = []
    for cislo, kus in enumerate(stranky, start=1):
        # Na titulce je nadpis SKRYTY, ne odstraneny: stranka bez h1 je rozbita
        # struktura pro ctecky pro nevidome i pro vyhledavace. Na strankach tagu
        # zustava videt, protoze rika, podle ceho je vyfiltrovano.
        trida = ' class="jen-ctecka"' if skryty_nadpis else ''
        obsah = ['<h1%s>%s</h1>' % (trida, nadpis)]
        # Uvod jen na prvni strance - na index-2 uz by se opakoval.
        if cislo == 1 and intro:
            obsah.append(intro)
        obsah.append('<div class="vypis">')
        obsah.extend(karta(c) for c in kus)
        obsah.append('</div>')
        obsah.append(strankovani(zaklad, cislo, len(stranky)))
        titulek_stranky = nadpis if cislo == 1 else '%s, strana %d' % (nadpis, cislo)
        vysledek.append((nazev_stranky(zaklad, cislo),
                         stranka_web(titulek_stranky, ''.join(obsah), web,
                                     aktivni, filtr, dosazitelne)))
    return vysledek




def text_z_html(html):
    """Cisty text pro index hledani: znacky pryc, entity zpatky.

    Bere jen obsah <main>, tedy telo clanku. Hlavicka a paticka jsou na kazde
    strance stejne, takze by dotaz na kterykoli tag z listy nasel VSECHNY
    clanky - overeno, slovo PowerBI bylo v textu sedmi clanku ze sedmi.
    """
    telo = re.search(r'(?s)<main>(.*?)</main>', html)
    if telo:
        html = telo.group(1)
    bez_kodu = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', html)
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', bez_kodu))).strip()


def stranka_hledani(clanky, web):
    """Vrati HTML stranky hledani s indexem zapecenym uvnitr.

    Rozsah, na ktery je to stavene: pet clanku PKVault ma 24 kB textu, cely
    vault 91 kB. Dokud se index vejde do jednotek MB, zustava zapeceny; pri
    radove vetsim webu by se musel nacitat zvlast - a tim by padl beh z lokalu,
    takze to bude rozhodnuti, ne technicky detail.
    """
    data = []
    for c in clanky:
        data.append({'titul': c['nadpis'], 'adresa': c['soubor'],
                     'datum': c['datum'], 'perex': text_z_html(c['perex']),
                     'text': c['text'], 'obrazek': c.get('obrazek'),
                     'tagy': [{'nazev': x, 'slug': slug(x)} for x in c['tagy']]})
    # Sekvence </ se v datech rozdeli, aby retezec ve clanku nemohl uzavrit
    # element script driv, nez ma.
    vypis = json.dumps(data, ensure_ascii=False).replace('</', '<' + chr(92) + '/')

    seznam = ['<ul class="rozcestnik">']
    for c in clanky:
        seznam.append('<li><a href="%s">%s</a></li>' % (c['soubor'], c['nadpis']))
    seznam.append('</ul>')

    # Poradi prebira lista, aby oko hledalo tag na temze miste jako jinde.
    # Tagy, ktere v liste nejsou, se pripoji za ni abecedne.
    #
    # LISTA JE KURATOROVANA, FILTR JE UPLNY. Duvod, proc `.obsidian2html/menu.md`
    # vybira, je sirka hlavicky - dvacet stitku v ni prestane fungovat. Filtr
    # ale ma vlastni misto na vlastni strance, takze stitky unese vsechny, a
    # tag, ktery ma stranku, musi byt filtrovatelny. Jinak by kuratorovani listy
    # tise vyradilo tag z filtru a nikdo by nevedel proc.
    stitky = []
    v_liste = set()
    for popis, adresa, tag in web['menu']:
        if tag:
            stitky.append({'nazev': tag, 'popis': popis})
            v_liste.add(tag)
        elif adresa == 'tag-%s.html' % BEZ_TAGU_SLUG:
            stitky.append({'nazev': BEZ_TAGU_SLUG, 'popis': BEZ_TAGU_POPIS})
            v_liste.add(BEZ_TAGU_SLUG)
    for tag in web['tagy']:
        if tag not in v_liste:
            stitky.append({'nazev': tag, 'popis': tag})
    if BEZ_TAGU_SLUG not in v_liste and any(not c['tagy'] for c in clanky):
        stitky.append({'nazev': BEZ_TAGU_SLUG, 'popis': BEZ_TAGU_POPIS})

    obsah = (HLEDANI.replace('@DATA@', vypis)
                    .replace('@TAGY@', json.dumps(stitky, ensure_ascii=False))
                    .replace('@SEZNAM@', ''.join(seznam))
                    .replace('@BEZ@', BEZ_TAGU_SLUG))
    return stranka_web('Hledání', obsah, web, 'hledani.html', jen_pevne=True)


RSS_POLOZEK = 20         # kolik nejnovejsich clanku jde do feedu

# Nazvy dnu a mesicu ANGLICKY a natvrdo. RFC 822 jine nepripousti a locale by
# na ceskych Windows vyrobilo "So, 28 srp", tedy nevalidni feed.
RSS_DNY = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
RSS_MESICE = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def rfc822(datum):
    """2026-08-28 -> Fri, 28 Aug 2026 00:00:00 +0000. Vraci None pri nesmyslu."""
    try:
        d = time.strptime(datum, '%Y-%m-%d')
    except (ValueError, TypeError):
        return None
    return '%s, %02d %s %d 00:00:00 +0000' % (RSS_DNY[d.tm_wday], d.tm_mday,
                                              RSS_MESICE[d.tm_mon - 1], d.tm_year)


def xml_text(s):
    """Escapovani pro textovy uzel. Perex smi obsahovat odkazy a tucny text,
    takze bez tohohle by vznikl nevalidni feed."""
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def rss(clanky, web, adresa):
    """Feed z nejnovejsich clanku. Do feedu jde PEREX, ne cely clanek.

    Cely text by s sebou vzal i obrazky, jejichz relativni cesty by ve ctecce
    nevedly nikam. Perex a odkaz je slusne a soubor zustane maly.

    Odkazy musi byt ABSOLUTNI - proto se adresa zadava prepinacem. Zbytek webu
    je zamerne relativni, aby sel otevrit z disku, ale to ve feedu neplati:
    ten cte ctecka nekde jinde.

    lastBuildDate zamerne chybi. S nim by se soubor menil pri kazdem buildu i
    beze zmeny obsahu a pri rucnim nahravani by se zbytecne prenasel.
    """
    zaklad = adresa.rstrip('/')
    popis = web.get('popis') or web['nazev']
    radky = ['<?xml version="1.0" encoding="utf-8"?>',
             '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
             '<channel>',
             '<title>%s</title>' % xml_text(web['nazev']),
             '<link>%s/</link>' % zaklad,
             '<description>%s</description>' % xml_text(popis),
             '<language>cs</language>',
             '<atom:link href="%s/rss.xml" rel="self" type="application/rss+xml"/>'
             % zaklad]

    for c in clanky[:RSS_POLOZEK]:
        url = '%s/%s' % (zaklad, c['soubor'])
        radky.append('<item>')
        radky.append('<title>%s</title>' % xml_text(c['nadpis']))
        radky.append('<link>%s</link>' % url)
        radky.append('<guid isPermaLink="true">%s</guid>' % url)
        kdy = rfc822(c['datum'])
        if kdy:
            radky.append('<pubDate>%s</pubDate>' % kdy)
        for tag in c['tagy']:
            radky.append('<category>%s</category>' % xml_text(tag))
        if c['perex']:
            radky.append('<description>%s</description>'
                         % xml_text(text_z_html(c['perex'])))
        radky.append('</item>')

    radky.extend(['</channel>', '</rss>', ''])
    return '\n'.join(radky)


def najdi_logo(vault, kam):
    """Logo je vstup pro web, tedy .obsidian2html/logo.svg nebo .png.

    Kdyz neni, hlavicka vysadi nazev webu jako text. Placeholder si skript
    nevymysli - logo je vec autora.
    """
    for pripona in ('.svg', '.png'):
        zdroj = os.path.join(vault, KONFIG, 'logo' + pripona)
        if os.path.isfile(zdroj):
            adresar = os.path.join(kam, 'img')
            if not os.path.isdir(adresar):
                os.makedirs(adresar)
            nazev = 'logo' + pripona
            shutil.copy2(zdroj, os.path.join(adresar, nazev))
            return 'img/' + nazev
    return None


def datum_souboru(cesta):
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
    return time.strftime('%Y-%m-%d', time.localtime(os.path.getmtime(cesta)))

def uklid_vystupu(kam):
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
    if not os.path.isdir(kam):
        return None
    obsah = os.listdir(kam)
    if not obsah:
        return None
    if not os.path.isfile(os.path.join(kam, ZNACKA_VYSTUPU)):
        raise Chyba('Adresar %s neni od tohoto skriptu (chybi %s) a nebude se '
                    'mazat. Zkontroluj cestu.' % (kam, ZNACKA_VYSTUPU))

    archiv = os.path.join(os.path.dirname(os.path.abspath(kam)), '_archiv')
    if not os.path.isdir(archiv):
        os.makedirs(archiv)
    # Archiv lezi O UROVEN VYS, ne uvnitr baleneho adresare - jinak by se kazda
    # zaloha zabalila do te pristi a rostly by geometricky.
    # Sekundy v nazvu jsou nutne: dva behy v tez minute by si archiv PREPSALY
    # a starsi verze by tise zmizela. Overeno - stalo se pri testovani.
    zaklad = os.path.join(archiv, '%s-%s' % (os.path.basename(os.path.abspath(kam)),
                                             time.strftime('%Y-%m-%d-%H%M%S')))
    # A jeste pojistka na sekundu: kdyz uz archiv toho jmena existuje, prida
    # se cislo. Zaloha se nesmi prepsat nikdy, ani pri dvou behech v tez
    # sekunde - overeno, stane se to pri skriptovanem pusteni za sebou.
    if os.path.exists(zaklad + '.zip'):
        n = 2
        while os.path.exists('%s-%d.zip' % (zaklad, n)):
            n += 1
        zaklad = '%s-%d' % (zaklad, n)
    soubor = shutil.make_archive(zaklad, 'zip', root_dir=kam)

    for jmeno in obsah:
        cesta = os.path.join(kam, jmeno)
        if os.path.isdir(cesta):
            shutil.rmtree(cesta)
        else:
            os.remove(cesta)
    return soubor


def zkontroluj_odkazy(kam):
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
    soubory, velka = set(), []
    for koren, _, jmena in os.walk(kam):
        for s in jmena:
            rel = os.path.relpath(os.path.join(koren, s), kam).replace(os.sep, '/')
            soubory.add(rel)
            if s != s.lower() and not s.startswith('.'):
                velka.append(rel)
    male = dict((s.lower(), s) for s in soubory)

    spatne, zplostene = [], []
    for rel in sorted(soubory):
        if not rel.endswith('.html'):
            continue
        cesta = os.path.join(kam, rel)
        with open(cesta, encoding='utf-8') as f:
            html = f.read()
        # Skript pryc: retezce ve JS, ktere se skladaji do adresy
        # ('tag-' + t.slug + '.html'), nejsou odkazy a kontrola by na nich
        # spadla. Stranka hledani je toho plna.
        bez_skriptu = re.sub(r'(?s)<(script|style)\b.*?</\1>', ' ', html)

        mrtve = []
        for atribut, odkaz in re.findall(r'(href|src|action)="([^"]+)"', bez_skriptu):
            # file: je v clanku o odkazech zamerna ukazka, ne rozbity odkaz.
            if odkaz.startswith(('http:', 'https:', 'mailto:', 'data:', 'file:',
                                 '#', '//')):
                continue
            cil = unquote(odkaz.split('#')[0].split('?')[0])
            if not cil or cil in soubory:
                continue
            if cil.lower() in male:
                spatne.append('%s: %s -> na Linuxu 404, soubor se jmenuje %s'
                              % (rel, odkaz, male[cil.lower()]))
            elif atribut == 'src':
                spatne.append('%s: %s -> obrazek ve vystupu neni' % (rel, odkaz))
            elif odkaz not in mrtve:
                mrtve.append(odkaz)

        for odkaz in mrtve:
            novy, kolik = re.subn(
                r'<a\b[^>]*href="%s"[^>]*>(.*?)</a>' % re.escape(odkaz),
                r'\1', html, flags=re.S)
            if kolik:
                html = novy
                zplostene.append('%s: %s (%dx)' % (rel, odkaz, kolik))
        if mrtve:
            with open(cesta, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)

    if velka:
        spatne.append('velka pismena v nazvu vystupu: %s' % ', '.join(sorted(velka)))
    if spatne:
        raise Chyba('Vadne odkazy ve vystupu (%d):\n  %s'
                    % (len(spatne), '\n  '.join(spatne)))
    return zplostene


def posbirej(vstup, jen_publikovane):
    """Vrati ([(cesta, meta, telo)], zapomenute) pro soubor nebo adresar.

    zapomenute jsou clanky s frontmatter klicem publish, ktere marker nemaji.
    Klic uz nic neznamena, takze takovy clanek na web nejde - a autor si
    nejspis mysli opak. Mlcet o tom by znamenalo, ze mu clanek tise nevyjde.
    """
    if os.path.isfile(vstup):
        cesty = [vstup]
    else:
        cesty = []
        for koren, adresare, soubory in os.walk(vstup):
            adresare[:] = [a for a in adresare
                           if not a.startswith(('.', '_')) and a not in PRILOHY]
            cesty.extend(os.path.join(koren, s) for s in sorted(soubory)
                         if s.lower().endswith('.md'))
    vysledek, zapomenute = [], []
    for c in cesty:
        meta, telo = oddel_frontmatter(zdroj_text(c))
        if jen_publikovane and not je_publikovana(c):
            if 'publish' in meta:
                zapomenute.append(c)
            continue
        vysledek.append((c, meta, telo))
    return vysledek, zapomenute


def rozcestnik(polozky):
    radky = ['<h1>Obsah</h1>', '<ul class="rozcestnik">']
    for c in sorted(polozky, key=lambda x: x['nadpis'].lower()):
        radky.append('<li><a href="%s">%s</a></li>'
                     % (c['soubor'], c['nadpis']))
    radky.append('</ul>')
    css = CSS.replace('@SIZE@', 'A4')
    return HTML.format(title='Obsah', css=css, body='\n'.join(radky), paticka='')


# ==============================================================================
# Hlavni program
# ==============================================================================

def main():
    p = argparse.ArgumentParser(
        description='Prevede Markdown na samostatny HTML. '
                    'Rozumi Obsidian syntaxi.')
    p.add_argument('vstup', help='soubor .md nebo adresar')
    p.add_argument('-o', '--out', help='vystupni soubor nebo adresar')
    p.add_argument('--vault', help='kde hledat ![[obrazky]] (vychozi: adresar vstupu)')
    p.add_argument('--titul', help='titulek jednoho souboru, kdyz nechces sahat '
                                   'do zdroje (jinak frontmatter titul, jinak nazev souboru)')
    p.add_argument('--jen-publikovane', action='store_true',
                   help='jen clanky s markerem publikace v nazvu')
    p.add_argument('--web', action='store_true',
                   help='web mode: sdilene styl.css, obrazky do img/. '
                        'Vyzaduje -o a implikuje --jen-publikovane')
    p.add_argument('--adresa', help='absolutni adresa webu, treba '
                                   'https://pankostka.cz. Bez ni se negeneruje '
                                   'rss.xml, protoze feed relativni odkazy nesnese')
    p.add_argument('--kontrola', action='store_true',
                   help='jen overi, ze se web postavi: staví do docasneho adresare '
                        'a NIC nezapisuje do vaultu. Pro git hook')
    p.add_argument('--uklid', action='store_true',
                   help='pred buildem zabalit predchozi vystup do _archiv a '
                        'vyprazdnit vystupni adresar (jen s --web)')
    p.add_argument('--nazev', help='nazev webu do hlavicky a titulku stranek '
                                  '(vychozi: jmeno vaultu)')
    args = p.parse_args()

    if not os.path.exists(args.vstup):
        print('CHYBA: vstup neexistuje: %s' % args.vstup)
        return 2

    # Web mode bez filtru by vysypal na internet cely vault. Neni to
    # pohodli, je to pojistka.
    # Kontrolni rezim je web mode, ktery stavi do docasneho adresare a vysledek
    # zahodi. Je pro git hook, ktery chce vedet, jestli se web vubec postavi.
    # Do vaultu uz nezapisuje zadny rezim, viz zaruka Z45.
    if args.kontrola:
        args.web = True
    if args.web:
        args.jen_publikovane = True
    # Kam se zapisuje, urcuje parametr - zadna vychozi cesta v kodu. Vystup
    # patri mimo repo i mimo vault a jen autor vi kam, viz zaruka Z50.
    if args.web and not args.out and not args.kontrola:
        print('CHYBA: --web potrebuje -o, tedy kam se ma web postavit.')
        return 2

    if args.uklid and not args.web:
        print('CHYBA: --uklid ma smysl jen s --web.')
        return 2

    davka_rezim = os.path.isdir(args.vstup)
    vault = os.path.abspath(args.vault or
                            (args.vstup if davka_rezim
                             else os.path.dirname(os.path.abspath(args.vstup))))

    try:
        polozky, zapomenute = posbirej(args.vstup, args.jen_publikovane)
        if not polozky:
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
        plan, davka, pouzite, kolize, doplnena_data = [], {}, set(), [], []
        velke_nahledy = []
        for cesta, meta, telo in polozky:
            stem = os.path.splitext(os.path.basename(cesta))[0]
            klic = slug(stem)
            zaklad = slug(meta['slug']) if meta.get('slug') else klic
            nazev, n = zaklad, 2
            while nazev in pouzite:
                nazev, n = '%s-%d' % (zaklad, n), n + 1
            if nazev != zaklad:
                # Na webu je adresa zavazek a nesmi se menit podle toho, co se
                # zrovna publikuje spolu s clankem. Tiche prejmenovani na -2 je
                # prijatelne u davky do mailu, na web ne.
                if args.web:
                    raise Chyba('Kolize adresy %s.html - dva clanky se stejnym '
                                'nazvem. Prejmenuj jeden z nich: %s'
                                % (zaklad, cesta))
                kolize.append('%s -> %s.html' % (cesta, nazev))
            if args.web and not meta.get('datum'):
                # Rozhodnuti publikovat nese marker, takze chybejici datum
                # build neshodi - vezme se datum souboru. Do zdroje se
                # nezapisuje, viz zaruka Z45.
                meta['datum'] = datum_souboru(cesta)
                doplnena_data.append((cesta, meta['datum']))
            pouzite.add(nazev)
            davka.setdefault(klic, nazev + '.html')
            plan.append((cesta, meta, telo, nazev))

        docasny = None
        if args.kontrola:
            docasny = tempfile.mkdtemp(prefix='md2html-kontrola-')
            kam = docasny
        elif args.web:
            kam = args.out
        elif davka_rezim:
            kam = args.out or 'html'
        else:
            kam = None
        if args.uklid:
            archiv = uklid_vystupu(kam)
            if archiv:
                print('  %s  (%.0f kB, predchozi vystup)'
                      % (archiv, os.path.getsize(archiv) / 1024.0))
        if kam and not os.path.isdir(kam):
            os.makedirs(kam)

        prejmenovane = {}
        web = None
        if args.web:
            # Lista je z TAGU, ne z adresaru. Adresare by do verejne navigace
            # propsaly strukturu vaultu - v menu by pristal i interni zapis.
            vsechny_tagy = set()
            for _, meta, _ in polozky:
                vsechny_tagy.update(tagy_z_meta(meta))
            # Stara slozka _web se uz necte. Mlcet o ni nejde: web by se
            # postavil bez loga, listy i vlastnich stylu a vypadalo by to
            # jako chyba generatoru, ne jako neprejmenovana slozka.
            if (os.path.isdir(os.path.join(vault, '_web'))
                    and not os.path.isdir(os.path.join(vault, KONFIG))):
                print('\nPOZOR: vault ma slozku _web, ktera se uz necte.'
                      ' Prejmenuj ji na %s.' % KONFIG)
                print('Uvnitr prejmenuj menu_webu.md na menu.md.')

            menu_text, intro, titul_titulky, vlastni_css = web_vstupy(vault, davka)
            bez_tagu = any(not tagy_z_meta(m) for _, m, _ in polozky)
            web = {'nazev': args.nazev or os.path.basename(vault),
                   'tagy': sorted(vsechny_tagy),
                   'menu': polozky_menu(menu_text, sorted(vsechny_tagy), bez_tagu),
                   'logo': None,
                   'hledani': True,
                   'rss': bool(args.adresa),
                   'popis': text_z_html(intro) if intro else None,
                   'hlava': ('<link rel="alternate" type="application/rss+xml"'
                             ' title="%s" href="rss.xml">'
                             % (args.nazev or os.path.basename(vault)))
                            if args.adresa else ''}
            # Znacka rika, ze adresar patri generatoru. Uklid pred buildem smi
            # mazat jen adresar, ktery ji ma - cizi ani pri preklepu v ceste.
            open(os.path.join(kam, ZNACKA_VYSTUPU), 'w').close()
            cesta_css = os.path.join(kam, 'styl.css')
            with open(cesta_css, 'w', encoding='utf-8', newline='\n') as f:
                f.write(CSS_WEB)
                if vlastni_css:
                    f.write('\n/* --- ' + KONFIG + '/styl.css --- */\n')
                    f.write(vlastni_css)
            print('  %s' % cesta_css)
            web['logo'] = najdi_logo(vault, kam)
            if not web['logo']:
                print('  (logo neni: cekam %s/logo.svg nebo .png,'
                      ' hlavicka zatim vysadi nazev)' % KONFIG)

        prevod = Prevod(vault, davka, web=args.web)
        vyrobene = []
        for cesta, meta, telo, nazev in plan:
            nadpis, html = na_html(
                cesta, prevod,
                titul=None if davka_rezim else args.titul,
                kam=kam if args.web else None, prejmenovane=prejmenovane,
                web=web)
            # -o je zaklad cesty, priponu doplnujeme.
            if kam:
                zaklad_cesty = os.path.join(kam, nazev)
            else:
                zaklad_cesty = os.path.splitext(args.out or nazev)[0]
            html_soubor = zaklad_cesty + '.html'
            with open(html_soubor, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)
            print('  %s  (%.0f kB)' % (html_soubor,
                                       os.path.getsize(html_soubor) / 1024.0))
            vyrobene.append({'nadpis': nadpis, 'datum': meta.get('datum', ''),
                             'tagy': tagy_z_meta(meta),
                             'soubor': os.path.basename(html_soubor),
                             'perex': perex(telo, meta, prevod) if args.web else '',
                             'text': text_z_html(html) if args.web else '',
                             'obrazek': None})
            if args.web:
                zdroj_obr = obrazek_perexu(cesta)
                if zdroj_obr:
                    vyrobene[-1]['obrazek'] = zkopiruj_prilohu(
                        zdroj_obr, kam, prejmenovane)
                    if os.path.getsize(zdroj_obr) > OBRAZEK_PEREXU_VAROVANI:
                        velke_nahledy.append(
                            (zdroj_obr, os.path.getsize(zdroj_obr) / 1024.0))

        def zapis(nazev_souboru, html):
            cesta_s = os.path.join(kam, nazev_souboru)
            with open(cesta_s, 'w', encoding='utf-8', newline='\n') as f:
                f.write(html)
            return cesta_s

        if args.web:
            # Razeni: datum klesajici, pri shode nazev. Bez druhotneho klice by
            # bylo poradi uvnitr serie se stejnym datem libovolne.
            poradi = sorted(vyrobene, key=lambda c: c['nadpis'].lower())
            poradi.sort(key=lambda c: c['datum'], reverse=True)

            for nazev_s, html_s in vypis_perexu(
                    poradi, 'index', titul_titulky or 'Články', web,
                    intro=intro, skryty_nadpis=True):
                print('  %s' % zapis(nazev_s, html_s))

            # Stranky tagu maji tentyz vypis. Vznikaji tady, protoze na ne
            # odkazuje lista na kazde strance a kontrola odkazu by jinak
            # spadla na neexistujici cil.
            # Nadpis je i tady skryty - podle ktereho tagu je vyfiltrovano rekne
            # zvyraznene tlacitko v liste, takze v textu je zbytecny.
            for tag in web['tagy']:
                sem = [c for c in poradi if tag in c['tagy']]
                # Dosazitelne = tagy, ktere se s timhle nekde potkavaji. Ostatni
                # lista ztlumi, takze kombinace do prazdna nejde ani kliknout.
                dosazitelne = {t for c in sem for t in c['tagy']}
                for nazev_s, html_s in vypis_perexu(sem, 'tag-' + slug(tag),
                                                    tag, web, tag,
                                                    skryty_nadpis=True,
                                                    filtr=tag,
                                                    dosazitelne=dosazitelne):
                    print('  %s  (%d clanku, kombinovatelnych tagu %d)'
                          % (zapis(nazev_s, html_s), len(sem),
                             len(dosazitelne - {tag})))

            sem = [c for c in poradi if not c['tagy']]
            if sem:
                for nazev_s, html_s in vypis_perexu(
                        sem, 'tag-' + BEZ_TAGU_SLUG, BEZ_TAGU_NADPIS, web,
                        'tag-%s.html' % BEZ_TAGU_SLUG, skryty_nadpis=True,
                        filtr=BEZ_TAGU_SLUG):
                    print('  %s  (%d clanku bez tagu)'
                          % (zapis(nazev_s, html_s), len(sem)))

            print('  %s' % zapis('hledani.html',
                                 stranka_hledani(poradi, web)))

            if args.adresa:
                print('  %s  (%d polozek)'
                      % (zapis('rss.xml', rss(poradi, web, args.adresa)),
                         min(len(poradi), RSS_POLOZEK)))
        elif davka_rezim:
            cesta_s = zapis('index.html', rozcestnik(vyrobene))
            print('  %s  (rozcestnik na %d stranek)' % (cesta_s, len(vyrobene)))

        if args.web:
            zplostene_odkazy = zkontroluj_odkazy(kam)
            if zplostene_odkazy:
                print('\nZplostene odkazy na soubory (%d): cil ve vystupu neni,'
                      ' zustal jen text.' % len(zplostene_odkazy))
                for x in zplostene_odkazy[:10]:
                    print('  %s' % x)
                if len(zplostene_odkazy) > 10:
                    print('  ... a dalsich %d' % (len(zplostene_odkazy) - 10))

        if args.web:
            # Kuratorovany seznam v KONFIG/menu.md rozhoduje, co je v liste. Novy
            # tag se tam neprida sam, protoze smysl te kurace je drzet listu
            # kratkou - ale mlcet o tom by znamenalo, ze si autor doplni tag a
            # diva se, proc v liste neni.
            v_liste = set(x for _, _, x in web['menu'] if x)
            chybi = [x for x in web['tagy'] if x not in v_liste]
            if chybi:
                print('\nTagy mimo listu (%d): stranka se generuje a vede na ni'
                      ' odkaz z paticky clanku, ale v liste neni.' % len(chybi))
                print('Pridej radek do %s/menu.md, kdyz tam patri:' % KONFIG)
                for x in chybi:
                    print('  `#%s`  ->  tag-%s.html' % (x, slug(x)))

            # Opacny pripad: lista jmenuje tag, ktery zadny publikovany
            # clanek nema. Jeho stranka nevznikne, takze se v liste ztlumi
            # - ale autor by mel vedet proc, jinak vypada lista rozbite.
            prazdne = [x for x in v_liste if x not in web['tagy']]
            if prazdne:
                print('\nStitky v liste bez clanku (%d): stranka nevznika,'
                      ' v liste jsou ztlumene a nejdou kliknout.'
                      % len(prazdne))
                print('Publikuj clanek s timhle tagem, nebo radek z %s/menu.md'
                      ' odeber:' % KONFIG)
                for x in sorted(prazdne):
                    print('  `#%s`' % x)

        if velke_nahledy:
            print('\nVelke nahledy (%d): na titulce se zobrazuji ve vysce'
                  ' 9rem, takze staci mensi soubor.' % len(velke_nahledy))
            for c, kb in velke_nahledy:
                print('  %.0f kB  %s' % (kb, c))

        if doplnena_data:
            print('\nDatum chybi ve frontmatteru, vzato ze souboru (%d).'
                  ' Datum souboru se meni pri kopirovani i synchronizaci,'
                  ' takze poradi na titulce nemusi vydrzet:'
                  % len(doplnena_data))
            for c, d in doplnena_data:
                print('  %s  %s' % (d, c))

        if zapomenute:
            print('\nPOZOR: klic publish bez markeru v nazvu (%d) - na web NEJDOU.'
                  % len(zapomenute))
            for c in zapomenute:
                print('  %s' % c)

        if kolize:
            print('\nKolize nazvu (%d): stejny nazev souboru ve dvou slozkach, '
                  'prejmenovano.' % len(kolize))
            for k in kolize:
                print('  %s' % k)

        if prevod.zplostene:
            unikaty = sorted(set(prevod.zplostene))
            print('\nZplostene odkazy (%d): cil neni v davce, zustal jen text.'
                  % len(unikaty))
            for u in unikaty[:10]:
                print('  %s' % u)
            if len(unikaty) > 10:
                print('  ... a dalsich %d' % (len(unikaty) - 10))

        return 0

    except Chyba as e:
        print('CHYBA: %s' % e)
        return 1
    except (OSError, IOError) as e:
        print('CHYBA: %s' % e)
        return 1
    finally:
        # Kontrolni rezim po sobe nesmi nechat adresar - hook bezi pri kazdem
        # commitu a za mesic by jich v temp byly stovky.
        if 'docasny' in dir() and docasny and os.path.isdir(docasny):
            shutil.rmtree(docasny, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
