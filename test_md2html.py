# -*- coding: utf-8 -*-
r"""
================================================================================
 POPIS
   Testy k md2html.py. Spousti se `python test_md2html.py`, zavislost zadna
   nad ramec toho, co potrebuje sam generator.

   ZADANIM JSOU KONVENCE Z README.cs.md, ne implementace. Kazdy test je jedna
   veta odtud, prevedena na otazku, kterou lze zodpovedet ano/ne. Kdyz se test
   a README rozejdou, autoritou je README - test se opravi podle nej.

   Nazev testu proto zacina kodem konvence: test_Z10_* overuje zaruku Z10,
   test_K40_* konvenci K40. Kdyz test spadne, kod v nazvu rekne, ktera veta
   prestala platit.

   Testy stavi male vaulty v docasnem adresari a poustej na ne main(). Behaji
   tedy pres cely retezec od souboru po HTML, ne jen pres jednotlivou funkci.
   Nekolik testu je presto jednotkovych - u slug() nebo perex() je vstup a
   vystup tak uzky, ze cely build by jen zamlzil, co se vlastne meri.
================================================================================
"""
import contextlib
import io
import os
import shutil
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md2html


MARKER = md2html.MARKER_PUBLIKACE


class Zaklad(unittest.TestCase):
    """Spolecne nastroje: postavit vault, pustit build, precist vystup."""

    def setUp(self):
        self.docasny = tempfile.mkdtemp(prefix='test-md2html-')
        self.vault = os.path.join(self.docasny, 'vault')
        self.vystup = os.path.join(self.docasny, 'web')
        os.makedirs(self.vault)

    def tearDown(self):
        shutil.rmtree(self.docasny, ignore_errors=True)

    # -- stavba vaultu ------------------------------------------------------

    def soubor(self, rel, obsah):
        """Zalozi soubor ve vaultu. rel smi obsahovat podadresare."""
        cesta = os.path.join(self.vault, rel.replace('/', os.sep))
        adresar = os.path.dirname(cesta)
        if adresar and not os.path.isdir(adresar):
            os.makedirs(adresar)
        with open(cesta, 'w', encoding='utf-8', newline='\n') as f:
            f.write(obsah)
        return cesta

    def obrazek(self, rel):
        """Zalozi nejmensi platne PNG. Obsah nehraje roli, jen at je to obrazek."""
        data = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00'
                b'\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDAT'
                b'x\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND'
                b'\xaeB`\x82')
        cesta = os.path.join(self.vault, rel.replace('/', os.sep))
        adresar = os.path.dirname(cesta)
        if adresar and not os.path.isdir(adresar):
            os.makedirs(adresar)
        with open(cesta, 'wb') as f:
            f.write(data)
        return cesta

    def clanek(self, nazev, telo, datum='2026-01-01', tagy='obsidian',
               publikovany=True, slozka=''):
        """Zalozi clanek. Marker publikace se doplni podle `publikovany`."""
        hlavicka = '---\n'
        if datum:
            hlavicka += 'datum: %s\n' % datum
        if tagy:
            hlavicka += 'tags: [%s]\n' % tagy
        hlavicka += '---\n'
        jmeno = nazev + (' ' + MARKER if publikovany else '') + '.md'
        return self.soubor(os.path.join(slozka, jmeno) if slozka else jmeno,
                           hlavicka + telo)

    # -- spusteni -----------------------------------------------------------

    def build(self, *prepinace, **kw):
        """Pusti main() a vrati (navratovy kod, vypis na stdout).

        Vstup je vault a vystup self.vystup, pokud se nerekne jinak.
        """
        vstup = kw.pop('vstup', self.vault)
        argv = ['md2html.py', vstup] + list(prepinace)
        if kw.pop('s_vystupem', True):
            argv += ['-o', self.vystup]
        puvodni = sys.argv
        zachyt = io.StringIO()
        try:
            sys.argv = argv
            with contextlib.redirect_stdout(zachyt):
                kod = md2html.main()
        finally:
            sys.argv = puvodni
        return kod, zachyt.getvalue()

    def web(self, *prepinace, **kw):
        """Build v rezimu --web. Nejcastejsi pripad, at se to nepise porad."""
        return self.build('--web', *prepinace, **kw)

    # -- cteni vystupu ------------------------------------------------------

    def vystupni(self, nazev):
        cesta = os.path.join(self.vystup, nazev)
        self.assertTrue(os.path.isfile(cesta),
                        've vystupu chybi %s; je tam: %s'
                        % (nazev, sorted(os.listdir(self.vystup))))
        with open(cesta, encoding='utf-8') as f:
            return f.read()

    def stranky(self):
        return sorted(x for x in os.listdir(self.vystup) if x.endswith('.html'))

    def otisk(self, koren):
        """Seznam (relativni cesta, velikost, cas zmeny) pro cely strom."""
        polozky = []
        for adresar, _, soubory in os.walk(koren):
            for s in soubory:
                c = os.path.join(adresar, s)
                polozky.append((os.path.relpath(c, koren), os.path.getsize(c),
                                os.path.getmtime(c)))
        return sorted(polozky)


# ==============================================================================
# Zaruky
# ==============================================================================

class Zaruky(Zaklad):

    def test_Z10_mrtvy_odkaz_zustane_textem(self):
        """Cil odkazu neni v davce, takze z odkazu zbyde holy text."""
        self.clanek('Prvni', 'Odkaz na [[Neexistujici notu]] uprostred vety.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        self.assertIn('Neexistujici notu', html)
        self.assertNotIn('<a href="neexistujici-notu.html"', html)
        self.assertIn('Zplostene odkazy', vypis)

    def test_Z10_zivy_odkaz_zustane_odkazem(self):
        """Protejsek predchoziho: kdyz cil v davce JE, odkaz se zachova.

        Bez tohohle by testu vyhovel i generator, ktery zplosti uplne vsechno.
        """
        self.clanek('Prvni', 'Odkaz na [[Druha]] uprostred vety.')
        self.clanek('Druha', 'Text druhe noty.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('<a href="druha.html">Druha</a>', self.vystupni('prvni.html'))

    def test_Z10_stitek_bez_stranky_se_ztlumi(self):
        """Lista smi jmenovat tag, ktery nema clanek. Ztlumi se, nezplosti."""
        self.clanek('Prvni', 'Text.', tagy='obsidian')
        self.soubor('.obsidian2html/menu.md', '- `#obsidian`\n- `#prazdny`\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertIn('class="zhasnuty"', html)
        self.assertNotIn('href="tag-prazdny.html"', html)
        self.assertIn('Stitky v liste bez clanku', vypis)

    def test_Z20_kod_se_neprepisuje(self):
        """Wikilink uvnitr kodu je ukazka syntaxe, ne odkaz."""
        self.clanek('Prvni', 'Vlozit notu jde zapisem `[[Druha]]` v textu.')
        self.clanek('Druha', 'Text druhe noty.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        self.assertIn('<code>[[Druha]]</code>', html)
        self.assertNotIn('<code><a href=', html)

    def test_Z20_kod_v_ohranicenem_bloku(self):
        """Totez pro blok ohraniceny zpetnymi apostrofy."""
        self.clanek('Prvni', '```\n![[obrazek.png]]\n[[Druha]]\n```\n')
        self.clanek('Druha', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        self.assertIn('![[obrazek.png]]', html)
        self.assertIn('[[Druha]]', html)

    def test_Z30_chybejici_obrazek_je_chyba(self):
        """V tichosti by vznikl dokument s prazdnym mistem a odesel uzivateli."""
        self.clanek('Prvni', 'Obrazek: ![[chybi.png]]\n')
        kod, vypis = self.build(s_vystupem=True)
        self.assertEqual(kod, 1, 'build mel skoncit chybou, vypis:\n' + vypis)
        self.assertIn('CHYBA', vypis)

    def test_Z40_vlastni_styly_se_pripojuji(self):
        """Vlastni CSS jde ZA vygenerovane, takze prepsat jde cokoli."""
        self.clanek('Prvni', 'Text.')
        self.soubor('.obsidian2html/styl.css', 'body { color: hotpink; }\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        css = self.vystupni('styl.css')
        self.assertIn('hotpink', css)
        self.assertIn('--odkaz', css, 'vygenerovane CSS zmizelo')
        self.assertLess(css.index('--odkaz'), css.index('hotpink'),
                        'vlastni CSS musi byt AZ ZA vygenerovanym, jinak neprepise')

    def test_Z45_do_vaultu_se_nezapisuje(self):
        """Vault je zdroj, ne pracovni plocha."""
        self.clanek('Prvni', 'Text s [[Mrtvym odkazem]] a tagem.')
        self.clanek('Druha', 'Text.', datum=None)
        self.soubor('.obsidian2html/menu.md', '- `#obsidian`\n')
        self.obrazek('Attachments/prvni.png')

        pred = self.otisk(self.vault)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertEqual(pred, self.otisk(self.vault),
                         'build sahl do vaultu')

    def test_Z45_nezapisuje_ani_datum_do_clanku(self):
        """Drive se chybejici datum dopisovalo do frontmatteru zdroje."""
        cesta = self.clanek('Bez data', 'Text.', datum=None)
        with open(cesta, encoding='utf-8') as f:
            pred = f.read()

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        with open(cesta, encoding='utf-8') as f:
            self.assertEqual(pred, f.read(), 'datum se zapsalo do clanku')

    def test_Z50_web_bez_vystupu_skonci_chybou(self):
        """Kam se zapisuje, urcuje parametr - zadna vychozi cesta v kodu."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.build('--web', s_vystupem=False)
        self.assertEqual(kod, 2, vypis)
        self.assertIn('-o', vypis)

    def test_Z50_uklid_nesmaze_cizi_adresar(self):
        """Mazat smi jen adresar se znackou, aby preklep v ceste neublizil."""
        self.clanek('Prvni', 'Text.')
        os.makedirs(self.vystup)
        cizi = os.path.join(self.vystup, 'cizi-data.txt')
        with open(cizi, 'w', encoding='utf-8') as f:
            f.write('data, ktera nejsou generovana')

        kod, vypis = self.web('--uklid')
        self.assertNotEqual(kod, 0,
                            'build mel odmitnout uklidit adresar bez znacky')
        self.assertTrue(os.path.isfile(cizi), 'cizi soubor byl smazan')

    def test_Z60_prilohy_maji_adresu_malymi_v_ascii(self):
        """Na Linuxu je Foo.png a foo.png rozdil, takze adresa musi byt jista."""
        self.clanek('Prvni', 'Obrazek: ![[Velký Obrázek.PNG]]\n')
        self.obrazek('Attachments/Velký Obrázek.PNG')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        soubory = os.listdir(os.path.join(self.vystup, 'img'))
        self.assertEqual(len(soubory), 1, soubory)
        nazev = soubory[0]
        self.assertEqual(nazev, nazev.lower(), 'v nazvu jsou velka pismena')
        self.assertTrue(all(ord(z) < 128 for z in nazev),
                        'v nazvu je znak mimo ASCII: %s' % nazev)
        self.assertIn(nazev, self.vystupni('prvni.html'))


# ==============================================================================
# Vaultove konvence
# ==============================================================================

class Konvence(Zaklad):

    def test_K10_publikuje_se_jen_s_markerem(self):
        """Chybejici marker znamena neverejne. Jedina pojistka, tedy jedina."""
        self.clanek('Verejny', 'Text.', publikovany=True)
        self.clanek('Soukromy', 'Text.', publikovany=False)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('verejny.html', stranky)
        self.assertNotIn('soukromy.html', stranky)

    def test_K10_klic_publish_marker_nenahradi(self):
        """Klic publish uz nic neznamena, ale build na nej upozorni."""
        self.soubor('Soukromy.md', '---\npublish: true\ndatum: 2026-01-01\n---\nText.\n')
        self.clanek('Verejny', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertNotIn('soukromy.html', self.stranky())
        self.assertIn('publish', vypis)

    def test_K20_slozka_s_teckou_a_podtrzitkem_se_preskoci(self):
        """Co ma byt mimo web, dostane tecku nebo podtrzitko."""
        self.clanek('Verejny', 'Text.')
        self.clanek('Skryty', 'Text.', slozka='_pracovni')
        self.clanek('Taky skryty', 'Text.', slozka='.obsidian2html')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('verejny.html', stranky)
        self.assertNotIn('skryty.html', stranky)
        self.assertNotIn('taky-skryty.html', stranky)

    def test_K25_titulek_je_nazev_souboru(self):
        """Ne H1. Cesta od titulku na webu k clanku ve vaultu ma byt zrejma."""
        self.clanek('Skutecny Nazev', '# Popis\n\nText ze sablony tasku.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('skutecny-nazev.html')
        self.assertIn('<h1>Skutecny Nazev</h1>', html)
        self.assertNotIn('<h1>Popis</h1>', html)

    def test_K25_titulek_bez_markeru(self):
        """Globus je priznak publikace, ne soucast nazvu."""
        self.clanek('Nazev', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn(MARKER, self.vystupni('nazev.html'))

    def test_K25_frontmatter_titul_prebije_nazev(self):
        """Unikovy vychod pro clanek pojmenovany po objektu."""
        self.soubor('nsp20DimZakaznik %s.md' % MARKER,
                    '---\ndatum: 2026-01-01\ntitul: Dimenze zakaznika\n---\nText.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('<h1>Dimenze zakaznika</h1>',
                      self.vystupni('nsp20dimzakaznik.html'))

    def test_K30_slug(self):
        """Adresa se pocita, neprebira: mala pismena, bez diakritiky, pomlcky."""
        self.assertEqual(md2html.slug('Obsidian Nastavení'), 'obsidian-nastaveni')
        self.assertEqual(md2html.slug('Příliš Žluťoučký Kůň'),
                         'prilis-zlutoucky-kun')
        self.assertEqual(md2html.slug('Dva  mezery'), 'dva-mezery')
        self.assertEqual(md2html.slug('S_podtrzitkem'), 's-podtrzitkem')

    def test_K30_slug_oddeluje_pomlckou(self):
        """Vyhledavace berou pomlcku jako hranici slov, podtrzitko ne."""
        self.assertNotIn('_', md2html.slug('Nazev clanku v obsidianu'))
        self.assertIn('-', md2html.slug('Nazev clanku'))

    def test_K30_marker_se_do_adresy_nepropise(self):
        self.clanek('Muj Článek', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('muj-clanek.html', self.stranky())

    def test_K40_perex_je_prvni_odstavec(self):
        self.clanek('Prvni', 'Prvni odstavec je perex.\n\nDruhy uz ne.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Prvni odstavec je perex.', index)
        self.assertNotIn('Druhy uz ne.', index)

    def test_K40_nadpis_ukoncuje_hledani(self):
        """Kdyz clanek zacina rovnou sekci, perex neni prvni veta te sekce."""
        self.clanek('Prvni', '## Sekce\n\nText sekce, ktery perexem neni.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('Text sekce', self.vystupni('index.html'))

    def test_K40_obrazek_uprostred_odstavce_se_vyhodi(self):
        """Perex je textova upoutavka, nahled ma karta vlastni."""
        self.clanek('Prvni', 'Text pred ![[uvodni.png]] a text za.\n')
        self.obrazek('Attachments/uvodni.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Text pred', index)
        self.assertIn('a text za.', index)
        self.assertNotIn('![[', index)
        self.assertNotIn('uvodni.png', index)

    def test_K40_obrazek_na_zacatku_odstavce_text_za_nim_zustane(self):
        """Obrazek perex neukoncuje, jen z nej vypadne."""
        self.clanek('Prvni', '![[uvodni.png]] Text za obrazkem.\n')
        self.obrazek('Attachments/uvodni.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Text za obrazkem.', index)
        self.assertNotIn('![[', index)

    def test_K40_obrazek_zapsany_markdownem_se_taky_vyhodi(self):
        """Oba zapisy obrazku, ne jen Obsidian embed."""
        self.clanek('Prvni', '![popis](Attachments/uvodni.png) Text za nim.\n')
        self.obrazek('Attachments/uvodni.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Text za nim.', index)
        self.assertNotIn('popis', index)

    def test_K40_obrazek_na_vlastnim_radku_perex_neni(self):
        """Odstavec, ktery je jen obrazek, se preskoci a perex je ten dalsi."""
        self.clanek('Prvni', '![[uvodni.png]]\n\nAz tohle je perex.\n')
        self.obrazek('Attachments/uvodni.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('Az tohle je perex.', self.vystupni('index.html'))

    def test_K50_priloha_se_najde_v_Attachments(self):
        self.clanek('Prvni', 'Obrazek: ![[schema.png]]\n')
        self.obrazek('Attachments/schema.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        html = self.vystupni('prvni.html')
        self.assertIn('src="img/schema.png"', html)
        self.assertIn('<img ', html)

    def test_K60_nahled_se_jmenuje_jako_clanek(self):
        """Porovnava se pres slug, takze sedne i priloha malymi s podtrzitkem."""
        self.clanek('Obsidian Co je', 'Text.')
        self.obrazek('Attachments/obsidian_co_je.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('class="nahled"', self.vystupni('index.html'))

    def test_K60_cizi_obrazek_nahledem_neni(self):
        """Protejsek: priloha s jinym nazvem se nahledem stat nesmi."""
        self.clanek('Obsidian Co je', 'Text s ![[jine.png]] uvnitr.\n')
        self.obrazek('Attachments/jine.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('class="nahled"', self.vystupni('index.html'))

    def test_K70_konfigurace_se_cte_z_obsidian2html(self):
        self.clanek('Prvni', 'Text.', tagy='obsidian')
        self.soubor('.obsidian2html/menu.md', '- `#obsidian`\n')
        self.soubor('.obsidian2html/index.md', 'Rucne psany uvod titulky.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Rucne psany uvod titulky.', index)
        self.assertIn('tag-obsidian.html', index)

    def test_K70_stara_slozka_se_necte_ale_ohlasi(self):
        """Mlcet nejde: web by se postavil bez loga, listy i stylu."""
        self.clanek('Prvni', 'Text.')
        self.soubor('_web/styl.css', 'body { color: hotpink; }\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertNotIn('hotpink', self.vystupni('styl.css'))
        self.assertIn('_web', vypis)
        self.assertIn('.obsidian2html', vypis)

    def test_K80_chybejici_datum_se_vezme_ze_souboru(self):
        cesta = self.clanek('Bez data', 'Text.', datum=None)
        kdy = time.mktime(time.strptime('2019-03-07', '%Y-%m-%d'))
        os.utime(cesta, (kdy, kdy))

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('2019-03-07', self.vystupni('bez-data.html'))
        self.assertIn('vzato ze souboru', vypis)

    def test_K80_datum_z_frontmatteru_ma_prednost(self):
        cesta = self.clanek('S datem', 'Text.', datum='2020-05-05')
        kdy = time.mktime(time.strptime('2019-03-07', '%Y-%m-%d'))
        os.utime(cesta, (kdy, kdy))

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        html = self.vystupni('s-datem.html')
        self.assertIn('2020-05-05', html)
        self.assertNotIn('2019-03-07', html)

    def test_K80_pri_shode_dat_rozhoduje_nazev(self):
        """Poradi na titulce musi byt jednoznacne, jinak build neni opakovatelny."""
        for nazev in ('Cecko', 'Acko', 'Becko'):
            self.clanek(nazev, 'Text %s.' % nazev, datum='2026-01-01')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        poradi = [index.index('>%s</a>' % x) for x in ('Acko', 'Becko', 'Cecko')]
        self.assertEqual(poradi, sorted(poradi),
                         'clanky se stejnym datem nejsou serazene podle nazvu')


# ==============================================================================
# Obsidian syntaxe
# ==============================================================================

class Syntaxe(Zaklad):

    def test_frontmatter_se_nevykresli(self):
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('datum:', self.vystupni('prvni.html'))

    def test_transkluze_vlozi_obsah_noty(self):
        self.clanek('Prvni', 'Pred.\n\n![[Vlozena]]\n\nPo.\n')
        self.soubor('Vlozena.md', 'Obsah vlozene noty.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('Obsah vlozene noty.', self.vystupni('prvni.html'))

    def test_transkluze_v_kruhu_neskonci_zacyklenim(self):
        """Nota, ktera vklada sama sebe, nesmi build zastavit."""
        self.clanek('Prvni', 'Zacatek.\n\n![[Prvni]]\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('Zacatek.', self.vystupni('prvni.html'))

    def test_wikilink_s_vlastnim_popisem(self):
        self.clanek('Prvni', 'Jdi na [[Druha|jinou notu]].')
        self.clanek('Druha', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('<a href="druha.html">jinou notu</a>',
                      self.vystupni('prvni.html'))

    def test_embed_obrazku_se_sirkou(self):
        self.clanek('Prvni', 'Obrazek: ![[schema.png|300]]\n')
        self.obrazek('Attachments/schema.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('width="300"', self.vystupni('prvni.html'))

    def test_embed_obrazku_ma_alt_text(self):
        """Alt potrebuje ctecka pro nevidome; Obsidian embed ho nema."""
        self.clanek('Prvni', 'Obrazek: ![[schema.png]]\n')
        self.obrazek('Attachments/schema.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('alt="schema"', self.vystupni('prvni.html'))


# ==============================================================================
# Samostatny HTML
# ==============================================================================

class Samostatny(Zaklad):

    def test_obrazek_je_v_souboru_jako_data_uri(self):
        """Jeden soubor snese mail i sitovy disk, relativni odkaz ne."""
        cesta = self.clanek('Prvni', 'Obrazek: ![[schema.png]]\n')
        self.obrazek('Attachments/schema.png')
        kod, vypis = self.build(vstup=cesta)
        self.assertEqual(kod, 0, vypis)

        with open(self.vystup + '.html', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('src="data:image/png;base64,', html)
        self.assertNotIn('src="img/', html)

    def test_styl_je_uvnitr_dokumentu(self):
        cesta = self.clanek('Prvni', 'Text.')
        kod, vypis = self.build(vstup=cesta)
        self.assertEqual(kod, 0, vypis)

        with open(self.vystup + '.html', encoding='utf-8') as f:
            html = f.read()
        self.assertIn('<style>', html)
        self.assertNotIn('<link rel="stylesheet"', html)


if __name__ == '__main__':
    unittest.main(verbosity=2)
