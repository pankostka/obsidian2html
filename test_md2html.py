# -*- coding: utf-8 -*-
r"""
================================================================================
 POPIS
   Testy k md2html.py. Spousti se `python test_md2html.py`, zavislost zadna
   nad ramec toho, co potrebuje sam generator.

   ZADANIM JSOU KONVENCE ZE SPEC.cs.md, ne implementace. Kazdy test je jedna
   veta odtud, prevedena na otazku, kterou lze zodpovedet ano/ne. Kdyz se test
   a SPEC rozejdou, autoritou je SPEC - test se opravi podle nej.

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
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import md2html


MARKER = '\U0001F310'


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
            hlavicka += 'date: %s\n' % datum
        if tagy:
            hlavicka += 'tags: [%s]\n' % tagy
        hlavicka += '---\n'
        jmeno = nazev + (' ' + MARKER if publikovany else '') + '.md'
        return self.soubor(os.path.join(slozka, jmeno) if slozka else jmeno,
                           hlavicka + telo)

    # -- spusteni -----------------------------------------------------------

    def build(self, *prepinace, **kw):
        """Pusti main() a vrati (navratovy kod, vypis na stdout i stderr).

        Vstup je vault, vystup self.vystup a publikuje se jen s globusem,
        pokud se nerekne jinak. publikovat=None --publish vynecha uplne.
        Chybu v argumentech hlasi argparse pres SystemExit, tady se z ni
        stane navratovy kod jako z kterekoli jine.
        """
        publikovat = kw.pop('publikovat', '*' + MARKER + '.md')
        argv = ['md2html.py', '--source', kw.pop('vstup', self.vault)]
        if publikovat is not None:
            argv += ['--publish', publikovat]
        if kw.pop('s_vystupem', True):
            argv += ['--dest', self.vystup]
        argv += list(prepinace)
        puvodni = sys.argv
        zachyt = io.StringIO()
        try:
            sys.argv = argv
            with contextlib.redirect_stdout(zachyt), \
                    contextlib.redirect_stderr(zachyt):
                try:
                    kod = md2html.main()
                except SystemExit as e:
                    kod = e.code
        finally:
            sys.argv = puvodni
        return kod, zachyt.getvalue()

    # Dnes je jen jeden druh buildu, web. Jmeno zustava, testy ho pouzivaji.
    web = build

    def konfigurace(self, text):
        """Zalozi config.toml v konfiguracni slozce vaultu."""
        return self.soubor('.obsidian2html/config.toml', text)

    def archivy(self):
        """Zipy predchoziho vystupu v _archiv vedle cile, serazene."""
        adresar = os.path.join(self.docasny, '_archiv')
        if not os.path.isdir(adresar):
            return []
        return sorted(os.listdir(adresar))

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
        self.assertIn('Flattened links', vypis)

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

        # Lista s tagy je na kazde strance krome titulky - tam ji nahradil
        # filtr, ktery takovy tag ztlumi taky, jen skriptem a s nulou.
        html = self.vystupni('prvni.html')
        self.assertIn('class="zhasnuty"', html)
        self.assertNotIn('href="tag-prazdny.html"', html)
        # Ve filtru na titulce takovy tag neni vubec: filtr zna tagy clanku a
        # stitek s nulou stejne nekresli.
        self.assertNotIn('"name": "prazdny"', self.vystupni('index.html'))
        self.assertIn('Tags in the bar with no articles', vypis)

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
        kod, vypis = self.web()
        self.assertEqual(kod, 1, 'build mel skoncit chybou, vypis:\n' + vypis)
        self.assertIn('ERROR', vypis)

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
        kod, vypis = self.build(s_vystupem=False)
        self.assertEqual(kod, 2, vypis)
        self.assertIn('--dest', vypis)

    def test_Z50_kontrola_s_cilem_je_chyba(self):
        """--check nikam nezapisuje, cil vedle nej by jen mate."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.build('--check')
        self.assertEqual(kod, 2, vypis)
        self.assertFalse(os.path.exists(self.vystup), 'kontrola zapsala do cile')

        kod, vypis = self.build('--check', '--keep-archives', '3',
                                s_vystupem=False)
        self.assertEqual(kod, 2, vypis)

    def test_Z55_uklid_nesmaze_cizi_adresar(self):
        """Mazat smi jen adresar se znackou, aby preklep v ceste neublizil."""
        self.clanek('Prvni', 'Text.')
        os.makedirs(self.vystup)
        cizi = os.path.join(self.vystup, 'cizi-data.txt')
        with open(cizi, 'w', encoding='utf-8') as f:
            f.write('data, ktera nejsou generovana')

        kod, vypis = self.web()
        self.assertNotEqual(kod, 0,
                            'build mel odmitnout uklidit adresar bez znacky')
        self.assertTrue(os.path.isfile(cizi), 'cizi soubor byl smazan')

    def test_Z55_co_uz_na_web_nepatri_zmizi(self):
        """Clanek, kteremu se odebral marker, nesmi zustat na webu z minula."""
        self.clanek('Prvni', 'Text.')
        cesta = self.clanek('Druha', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('druha.html', self.stranky())

        os.remove(cesta)
        self.clanek('Druha', 'Text.', publikovany=False)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('druha.html', self.stranky())
        self.assertIn('prvni.html', self.stranky())

    def test_Z55_polozky_s_teckou_zustanou(self):
        """.git a rucne pridane soubory pro server build neprezije jen tak."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        os.makedirs(os.path.join(self.vystup, '.git'))
        for rel in ('.git/HEAD', '.htaccess'):
            with open(os.path.join(self.vystup, rel), 'w') as f:
                f.write('x')

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertTrue(os.path.isfile(os.path.join(self.vystup, '.git', 'HEAD')))
        self.assertTrue(os.path.isfile(os.path.join(self.vystup, '.htaccess')))

    def test_Z55_cil_jen_s_teckou_se_postavi(self):
        """Cerstvy klon repozitare nema znacku, ale cizi to neni."""
        self.clanek('Prvni', 'Text.')
        os.makedirs(os.path.join(self.vystup, '.git'))
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('prvni.html', self.stranky())

    def test_Z55_predchozi_obsah_jde_do_archivu_o_uroven_vys(self):
        """Archiv mimo cil se s webem nenahraje a nezabali sam do sebe."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertEqual(self.archivy(), [], 'prvni build nema co archivovat')
        with open(os.path.join(self.vystup, '.htaccess'), 'w') as f:
            f.write('x')

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        archivy = self.archivy()
        self.assertEqual(len(archivy), 1, archivy)
        self.assertTrue(archivy[0].startswith('web-'), archivy)
        with zipfile.ZipFile(os.path.join(self.docasny, '_archiv',
                                          archivy[0])) as z:
            jmena = z.namelist()
        self.assertIn('prvni.html', jmena)
        self.assertNotIn('.htaccess', jmena)
        self.assertNotIn('.vygenerovano', jmena)

    def test_Z55_archivu_zustane_jen_zadany_pocet(self):
        self.clanek('Prvni', 'Text.')
        for _ in range(4):
            kod, vypis = self.web('--keep-archives', '2')
            self.assertEqual(kod, 0, vypis)
        self.assertEqual(len(self.archivy()), 2, self.archivy())

    def test_Z55_vychozi_pocet_archivu_je_deset(self):
        self.clanek('Prvni', 'Text.')
        for _ in range(12):
            kod, vypis = self.web()
            self.assertEqual(kod, 0, vypis)
        self.assertEqual(len(self.archivy()), 10, self.archivy())

    def test_Z55_nula_archivu_zadny_zip(self):
        self.clanek('Prvni', 'Text.')
        for _ in range(2):
            kod, vypis = self.web('--keep-archives', '0')
            self.assertEqual(kod, 0, vypis)
        self.assertEqual(self.archivy(), [])

    def test_Z57_bez_zmeny_se_web_nestavi(self):
        """Planovac pousti build co pet minut, web se nema porad prepisovat."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)
        pred = self.otisk(self.vystup)

        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)
        self.assertIn('No change', vypis)
        self.assertEqual(pred, self.otisk(self.vystup), 'build sahl do cile')
        self.assertEqual(self.archivy(), [])

    def test_Z57_zmena_ve_zdroji_build_vyvola(self):
        cesta = self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)

        with open(cesta, 'a', encoding='utf-8') as f:
            f.write('Dalsi veta.\n')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('No change', vypis)
        self.assertIn('Dalsi veta.', self.vystupni('prvni.html'))

    def test_Z57_zmena_workspace_obsidianu_build_nevyvola(self):
        """workspace.json se meni porad a na web vliv nema."""
        self.clanek('Prvni', 'Text.')
        self.soubor('.obsidian/workspace.json', '{}')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)

        self.soubor('.obsidian/workspace.json', '{"zmena": 1}')
        kod, vypis = self.web('--if-changed')
        self.assertIn('No change', vypis)

    def test_Z57_zmena_konfigurace_build_vyvola(self):
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)

        self.konfigurace('name = "Novy nazev"\n')
        kod, vypis = self.web('--if-changed')
        self.assertNotIn('No change', vypis)
        self.assertIn('Novy nazev', self.vystupni('index.html'))

    def test_Z57_spadly_build_se_zkusi_znovu(self):
        """Otisk se uklada az po uspesnem buildu."""
        self.clanek('Prvni', 'Obrazek: ![[chybi.png]]\n')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 1, vypis)
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 1, vypis)
        self.assertNotIn('No change', vypis)

    def test_Z57_bez_prepinace_se_stavi_vzdy(self):
        """Rucni build ma udelat, co se po nem chce."""
        self.clanek('Prvni', 'Text.')
        for _ in range(2):
            kod, vypis = self.web()
            self.assertEqual(kod, 0, vypis)
            self.assertNotIn('No change', vypis)
        self.assertEqual(len(self.archivy()), 1)

    def test_Z57_s_kontrolou_je_chyba(self):
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.build('--check', '--if-changed', s_vystupem=False)
        self.assertEqual(kod, 2, vypis)

    def test_Z55_cizi_soubor_v_archivu_zustane(self):
        """Uklid archivu maze jen zipy tohoto cile ve tvaru, jaky sam dela."""
        self.clanek('Prvni', 'Text.')
        adresar = os.path.join(self.docasny, '_archiv')
        os.makedirs(adresar)
        cizi = [os.path.join(adresar, x) for x in
                ('jiny-web-2020-01-01-120000.zip', 'web-poznamka.zip')]
        for c in cizi:
            with open(c, 'w') as f:
                f.write('x')
        for _ in range(2):
            kod, vypis = self.web('--keep-archives', '0')
            self.assertEqual(kod, 0, vypis)
        for c in cizi:
            self.assertTrue(os.path.isfile(c), c)

    def test_Z50_kontrola_po_sobe_nenecha_adresar(self):
        """--check nikam nezapisuje, ani do tempu. Hook bezi pri kazdem commitu."""
        self.clanek('Prvni', 'Text.')
        temp = os.path.join(self.docasny, 'temp')
        os.makedirs(temp)
        puvodni, tempfile.tempdir = tempfile.tempdir, temp
        try:
            kod, vypis = self.build('--check', s_vystupem=False)
        finally:
            tempfile.tempdir = puvodni
        self.assertEqual(kod, 0, vypis)
        self.assertEqual(os.listdir(temp), [],
                         'kontrola nechala v tempu adresar')

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

    def test_K10_marker_se_da_zmenit(self):
        """Vault smi pouzivat jiny znak nez globus."""
        self.soubor('Verejny ★.md', '---\ndate: 2026-01-01\n---\nText.\n')
        self.soubor('Soukromy.md', '---\ndate: 2026-01-01\n---\nText.\n')
        kod, vypis = self.web(publikovat='*★.md')
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('verejny.html', stranky)
        self.assertNotIn('soukromy.html', stranky)
        self.assertNotIn('★', self.vystupni('verejny.html'))

    def test_K10_publish_je_povinny(self):
        """Vychozi hodnota by rozhodovala potichu, co jde ven."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web(publikovat=None)
        self.assertEqual(kod, 2, vypis)
        self.assertIn('--publish', vypis)

    def test_K10_marker_z_bezneho_znaku_se_ohlasi(self):
        """Vykricnik se neda odlisit od nazvu, ktery tak proste konci."""
        self.soubor('Pozor!.md', '---\ndate: 2026-01-01\n---\nText.\n')
        kod, vypis = self.web(publikovat='*!.md')
        self.assertEqual(kod, 0, vypis)
        self.assertIn('ordinary characters', vypis)

    def test_K10_prazdny_vzor_je_chyba(self):
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web(publikovat='')
        self.assertEqual(kod, 2, vypis)
        self.assertIn('--publish', vypis)

    def test_K10_jiny_vzor_je_chyba(self):
        """Z libovolne masky nejde poznat, co strhnout z titulku a adresy."""
        self.clanek('Prvni', 'Text.')
        for vzor in ('Navod*.md', '*.txt', '**.md', 'prvni.md'):
            kod, vypis = self.web(publikovat=vzor)
            self.assertEqual(kod, 2, '%s: %s' % (vzor, vypis))

    def test_K10_vzor_rozbaleny_shellem_se_pozna(self):
        """Bash z *.md udela seznam souboru. Build to musi rict, ne tise bezet."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('b.md', 'c.md', publikovat='a.md')
        self.assertEqual(kod, 2, vypis)
        self.assertIn('quotes', vypis)

    def test_K10_hvezdicka_vezme_i_neoznacene(self):
        """--publish "*.md" je rezim VSE S VYJIMKOU."""
        self.clanek('Verejny', 'Text.', publikovany=True)
        self.clanek('Soukromy', 'Text.', publikovany=False)
        kod, vypis = self.web(publikovat='*.md')
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('verejny.html', stranky)
        self.assertIn('soukromy.html', stranky)

    def test_K10_klic_publish_marker_nenahradi(self):
        """Klic publish uz nic neznamena, ale build na nej upozorni."""
        self.soubor('Soukromy.md', '---\npublish: true\ndate: 2026-01-01\n---\nText.\n')
        self.clanek('Verejny', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertNotIn('soukromy.html', self.stranky())
        self.assertIn('publish', vypis)

    def test_K15_slozka_sablon_se_preskoci(self):
        """Sablona neni clanek. Ktera slozka to je, rekne Obsidian sam."""
        self.soubor('.obsidian/templates.json', '{"folder": "Sablony"}')
        self.clanek('Clanek', 'Text.')
        self.clanek('Vzor', 'Text.', slozka='Sablony', publikovany=False)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('clanek.html', stranky)
        self.assertNotIn('vzor.html', stranky)

    def test_K15_bez_konfigurace_se_nepreskakuje_nic(self):
        """Protejsek: slozka jmenem Sablony sama o sobe nic neznamena."""
        self.clanek('Clanek', 'Text.')
        self.clanek('Vzor', 'Text.', slozka='Sablony')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('vzor.html', self.stranky())

    def test_K15_oznacena_sablona_se_preskoci_ale_ohlasi(self):
        """Slozka rika sablona, marker rika publikuj - to si autor ma slyset."""
        self.soubor('.obsidian/templates.json', '{"folder": "Sablony"}')
        self.clanek('Clanek', 'Text.')
        self.clanek('Vzor', 'Text.', slozka='Sablony', publikovany=True)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertNotIn('vzor.html', self.stranky())
        self.assertIn('template folder', vypis)

    def test_K15_s_hvezdickou_se_sablona_neohlasi(self):
        """Bez markeru neni rozpor mezi slozkou a markerem, neni co hlasit."""
        self.soubor('.obsidian/templates.json', '{"folder": "Sablony"}')
        self.clanek('Sablona', 'Text.', slozka='Sablony')
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web(publikovat='*.md')
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('template folder', vypis)

    def test_K15_cte_se_i_nastaveni_Templateru(self):
        self.soubor('.obsidian/plugins/templater-obsidian/data.json',
                    '{"templates_folder": "Meta/Vzory"}')
        self.clanek('Clanek', 'Text.')
        self.clanek('Vzor', 'Text.', slozka='Meta/Vzory')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('vzor.html', self.stranky())

    def test_K15_rozbita_konfigurace_build_neshodi(self):
        """Nastaveni je pohodli, ne podminka - vault bez nej proste sablony nema."""
        self.soubor('.obsidian/templates.json', 'tohle neni JSON {{{')
        self.clanek('Clanek', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('clanek.html', self.stranky())

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

    def test_K20_soubor_s_podtrzitkem_se_preskoci_v_obou_rezimech(self):
        """Podtrzitko znamena mimo web vzdycky, i s markerem."""
        self.clanek('Verejny', 'Text.')
        self.clanek('_Poznamka', 'Text.')
        self.soubor('_Koncept.md', '---\ndate: 2026-01-01\n---\nText.\n')
        self.soubor('.Skryty.md', '---\ndate: 2026-01-01\n---\nText.\n')
        for vzor in ('*' + MARKER + '.md', '*.md'):
            kod, vypis = self.web(publikovat=vzor)
            self.assertEqual(kod, 0, vypis)
            self.assertEqual(self.stranky(),
                             ['index.html', 'tag-obsidian.html', 'verejny.html'],
                             vzor)

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
                    '---\ndate: 2026-01-01\ntitle: Dimenze zakaznika\n---\nText.\n')
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

        # Titulka nese zapeceny index s celym textem clanku, takze se perex
        # overuje tam, kde ho ctenar vidi: na karte a v poli indexu.
        index = self.vystupni('index.html')
        self.assertIn('<p class="perex">Prvni odstavec je perex.</p>', index)
        self.assertIn('"excerpt": "Prvni odstavec je perex."', index)
        self.assertNotIn('Druhy uz ne.</p>', index)

    def test_K40_nadpis_ukoncuje_hledani(self):
        """Kdyz clanek zacina rovnou sekci, perex neni prvni veta te sekce."""
        self.clanek('Prvni', '## Sekce\n\nText sekce, ktery perexem neni.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        # Ne na '<p class="perex">' - ten retezec je i ve skriptu titulky.
        # Rozhoduje pole indexu, ze ktereho se karta kresli.
        self.assertIn('"excerpt": ""', self.vystupni('index.html'))

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
        self.assertIn('"image": "img/obsidian-co-je.png"',
                      self.vystupni('index.html'))

    def test_K60_cizi_obrazek_nahledem_neni(self):
        """Protejsek: priloha s jinym nazvem se nahledem stat nesmi."""
        self.clanek('Obsidian Co je', 'Text s ![[jine.png]] uvnitr.\n')
        self.obrazek('Attachments/jine.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        # Ne 'class="nahled"' - ten retezec je i ve skriptu titulky, ktery
        # kartu s nahledem umi vykreslit. Rozhoduje pole indexu.
        self.assertNotIn('"image": "img/', self.vystupni('index.html'))

    def test_K70_konfigurace_se_cte_z_obsidian2html(self):
        self.clanek('Prvni', 'Text.', tagy='obsidian')
        self.soubor('.obsidian2html/menu.md', '- `#obsidian`\n')
        self.soubor('.obsidian2html/index.md', 'Rucne psany uvod titulky.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Rucne psany uvod titulky.', index)
        self.assertIn('tag-obsidian.html', index)

    def test_K70_konfigurace_se_cte_i_z_podtrzitka(self):
        """_obsidian2html je v Obsidianu videt, jinak plati totez co s teckou.

        Na web se nedostane nic z ni - K20 slozku s podtrzitkem preskakuje.
        """
        self.clanek('Prvni', 'Text.', tagy='obsidian')
        self.soubor('_obsidian2html/menu.md', '- `#obsidian`\n')
        self.soubor('_obsidian2html/index.md', 'Uvod z podtrzitka.\n')
        self.soubor('_obsidian2html/styl.css', 'body { color: hotpink; }\n')
        self.clanek('Skryty', 'Text.', slozka='_obsidian2html')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Uvod z podtrzitka.', index)
        self.assertIn('tag-obsidian.html', index)
        self.assertIn('hotpink', self.vystupni('styl.css'))
        self.assertIn('_obsidian2html/styl.css', self.vystupni('styl.css'))
        self.assertNotIn('skryty.html', self.stranky())

    def test_K70_dve_slozky_konfigurace_zastavi_build(self):
        """Obe slozky naraz jsou chyba, ne prednost.

        Ta, ktera by prohrala, by se tise ignorovala a uprava v ni by nikam
        nevedla. Build spadne jeste pred vyprazdnenim cile, predchozi vystup
        zustane.
        """
        self.clanek('Prvni', 'Text.')
        self.soubor('.obsidian2html/index.md', 'S teckou.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        pred = sorted(os.listdir(self.vystup))

        self.soubor('_obsidian2html/index.md', 'S podtrzitkem.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 1, vypis)
        self.assertIn('both .obsidian2html and _obsidian2html', vypis)
        self.assertEqual(sorted(os.listdir(self.vystup)), pred)

    def test_K70_config_toml_urci_nazev_jazyk_a_adresu(self):
        self.clanek('Prvni', 'Text.')
        self.konfigurace('# komentar\nname = "Pan Kostka"\nlang = "en"\n'
                         'base_url = "https://example.com"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Pan Kostka', index)
        self.assertIn('<html lang="en">', index)
        self.assertIn('<title>Prvni - Pan Kostka</title>',
                      self.vystupni('prvni.html'))
        self.assertIn('https://example.com', self.vystupni('rss.xml'))

    def test_K70_bez_konfigurace_plati_vychozi_hodnoty(self):
        """Nazev je jmeno slozky vaultu, jazyk cestina, RSS nevznikne."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertIn('<title>Prvni - vault</title>', self.vystupni('prvni.html'))
        self.assertNotIn('rss.xml', os.listdir(self.vystup))

    def test_K70_neznamy_klic_v_konfiguraci_je_chyba(self):
        """Preklep v nmae by jinak tise vyrobil web se jmenem slozky."""
        self.clanek('Prvni', 'Text.')
        self.konfigurace('nmae = "Pan Kostka"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 1, vypis)
        self.assertIn('unknown key nmae', vypis)

    def test_K70_neplatna_hodnota_v_konfiguraci_je_chyba(self):
        self.clanek('Prvni', 'Text.')
        for text in ('name = 42\n', 'base_url = "pankostka.cz"\n',
                     'name = "neuzavrena\n'):
            self.konfigurace(text)
            kod, vypis = self.web()
            self.assertEqual(kod, 1, '%s: %s' % (text, vypis))

    def test_K70_index_md_urcuje_titulek_titulky(self):
        """Frontmatter title v index.md prebije nazev vaultu na titulce."""
        self.clanek('Prvni', 'Text.')
        self.soubor('.obsidian2html/index.md',
                    '---\ntitle: Moje znalostni baze\n---\nUvodni text.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('Uvodni text.', index)
        self.assertIn('Moje znalostni baze', index)

    def test_K70_stara_slozka_se_necte_ale_ohlasi(self):
        """Mlcet nejde: web by se postavil bez loga, listy i stylu."""
        self.clanek('Prvni', 'Text.')
        self.soubor('_web/styl.css', 'body { color: hotpink; }\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertNotIn('hotpink', self.vystupni('styl.css'))
        self.assertIn('_web', vypis)
        self.assertIn('.obsidian2html', vypis)

    def test_K80_stary_cesky_klic_se_necte_ale_ohlasi(self):
        """Klice frontmatteru jsou anglicky. Mlcet o starych nejde: clanek by
        tise prisel o datum i o titulek."""
        self.soubor('Stary %s.md' % MARKER,
                    '---\ndatum: 2020-05-05\ntitul: Jiny titulek\n---\nText.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('stary.html')
        self.assertNotIn('Jiny titulek', html)
        self.assertNotIn('2020-05-05', html)
        self.assertIn('old Czech frontmatter keys', vypis)
        self.assertIn('datum -> date', vypis)
        self.assertIn('titul -> title', vypis)

    def test_K80_chybejici_datum_se_vezme_ze_souboru(self):
        cesta = self.clanek('Bez data', 'Text.', datum=None)
        kdy = time.mktime(time.strptime('2019-03-07', '%Y-%m-%d'))
        os.utime(cesta, (kdy, kdy))

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('2019-03-07', self.vystupni('bez-data.html'))
        self.assertIn('taken from the file', vypis)

    def test_K80_datum_z_frontmatteru_ma_prednost(self):
        cesta = self.clanek('S datem', 'Text.', datum='2020-05-05')
        kdy = time.mktime(time.strptime('2019-03-07', '%Y-%m-%d'))
        os.utime(cesta, (kdy, kdy))

        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        html = self.vystupni('s-datem.html')
        # Datum clanku v paticce. Datum souboru se na strance objevi taky,
        # ale v radku Aktualizovano podle Z85 - to je jina vec.
        self.assertIn('<span>2020-05-05</span>', html)
        self.assertNotIn('<span>2019-03-07</span>', html)

    def test_Z85_pod_patickou_je_posledni_zmena_obsahu(self):
        """Nejnovejsi cas zmeny souboru, ze ktereho web vznikl."""
        stary = self.clanek('Stary', 'Text.')
        novy = self.clanek('Novy', 'Text.')
        os.utime(stary, (time.mktime((2024, 1, 2, 3, 4, 0, 0, 0, -1)),) * 2)
        os.utime(novy, (time.mktime((2025, 6, 7, 8, 9, 0, 0, 0, -1)),) * 2)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        radek = '<p class="aktualizace">Aktualizováno 2025-06-07 08:09</p>'
        for stranka in ('index.html', 'stary.html', 'tag-obsidian.html'):
            self.assertIn(radek, self.vystupni(stranka), stranka)

    def test_Z85_neverejny_clanek_cas_nezmeni(self):
        """Uprava soukrome poznamky se na verejnem webu nesmi projevit."""
        verejny = self.clanek('Verejny', 'Text.')
        soukromy = self.clanek('Soukromy', 'Text.', publikovany=False)
        os.utime(verejny, (time.mktime((2024, 1, 2, 3, 4, 0, 0, 0, -1)),) * 2)
        os.utime(soukromy, (time.mktime((2025, 6, 7, 8, 9, 0, 0, 0, -1)),) * 2)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('Aktualizováno 2024-01-02 03:04', self.vystupni('index.html'))

    def test_Z85_obrazek_se_pocita(self):
        clanek = self.clanek('Prvni', 'Obrazek: ![[schema.png]]\n')
        obrazek = self.obrazek('Attachments/schema.png')
        os.utime(clanek, (time.mktime((2024, 1, 2, 3, 4, 0, 0, 0, -1)),) * 2)
        os.utime(obrazek, (time.mktime((2025, 6, 7, 8, 9, 0, 0, 0, -1)),) * 2)
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('Aktualizováno 2025-06-07 08:09', self.vystupni('prvni.html'))

    def test_Z85_anglicky_web_pise_updated(self):
        self.clanek('Prvni', 'Text.')
        self.konfigurace('lang = "en"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('<p class="aktualizace">Updated ', self.vystupni('index.html'))

    def test_Z90_bez_prepinace_odkaz_do_obsidianu_neni(self):
        """Verejny web nesmi prozradit nazev vaultu ani jeho slozky."""
        self.soubor('.obsidian/app.json', '{}')
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('obsidian://', self.vystupni('prvni.html'))

    def test_Z90_odkaz_otevre_clanek_ve_vaultu(self):
        """Vault podle jmena slozky, cesta uvnitr vaultu bez .md."""
        self.soubor('.obsidian/app.json', '{}')
        self.clanek('Předmět', 'Text.', slozka='Fy - Fyzika')
        kod, vypis = self.web('--edit-links')
        self.assertEqual(kod, 0, vypis)
        html = self.vystupni('predmet.html')
        self.assertIn('<a href="obsidian://open?vault=vault&amp;file='
                      'Fy%20-%20Fyzika%2FP%C5%99edm%C4%9Bt%20%F0%9F%8C%90"'
                      ' class="upravit" title="Upravit v Obsidianu"', html)
        # Odkaz stoji vpravo u nadpisu, v paticce uz neni.
        self.assertIn('<div class="titulek"><h1>', html)
        self.assertNotIn('class="upravit"',
                         html[html.index('<footer'):])
        # Kontrola odkazu ho nesmi vzit za soubor a zplostit.
        self.assertNotIn('Flattened', vypis)

    def test_Z90_odkaz_ma_i_karta_v_prehledu(self):
        """Na titulce i na strance tagu, aby se nemuselo rozklikavat."""
        self.soubor('.obsidian/app.json', '{}')
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('--edit-links')
        self.assertEqual(kod, 0, vypis)
        odkaz = 'obsidian://open?vault=vault&amp;file=Prvni%20'
        self.assertIn(odkaz, self.vystupni('tag-obsidian.html'))
        index = self.vystupni('index.html')
        # Karta kreslena skriptem i ta bez skriptu.
        self.assertIn('"edit": "<a href=\\"' + odkaz, index)
        self.assertIn('<div class="titulek"><h2><a href="prvni.html">', index)

    def test_Z90_zdroj_uvnitr_vaultu_se_pocita_od_korene(self):
        self.soubor('.obsidian/app.json', '{}')
        self.clanek('Prvni', 'Text.', slozka='Sekce')
        kod, vypis = self.web('--edit-links',
                              vstup=os.path.join(self.vault, 'Sekce'))
        self.assertEqual(kod, 0, vypis)
        self.assertIn('obsidian://open?vault=vault&amp;file=Sekce%2FPrvni%20',
                      self.vystupni('prvni.html'))

    def test_Z90_bez_vaultu_build_skonci_a_cile_se_nedotkne(self):
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('--edit-links')
        self.assertEqual(kod, 2, vypis)
        self.assertIn('--edit-links needs an Obsidian vault', vypis)
        self.assertFalse(os.path.exists(self.vystup))

    def test_Z90_prepinac_se_pocita_do_otisku(self):
        """Zapnout odkazy je zmena webu, takze --if-changed musi stavet."""
        self.soubor('.obsidian/app.json', '{}')
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web('--if-changed')
        self.assertEqual(kod, 0, vypis)
        kod, vypis = self.web('--if-changed', '--edit-links')
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('No change', vypis)
        self.assertIn('obsidian://', self.vystupni('prvni.html'))

    def test_K80_datum_ktere_datem_neni_se_ohlasi(self):
        """Zbyly zastupny symbol sablony by tise rozhodil poradi na titulce."""
        self.soubor('Prvni %s.md' % MARKER,
                    '---\ndate: {{date:YYYY-MM-DD}}\n---\nText.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('not a date', vypis)
        self.assertIn('{{date:YYYY-MM-DD}}', vypis)

    def test_K80_spravne_datum_se_neohlasi(self):
        """Protejsek: bez tohohle by testu vyhovela i kontrola, ktera hlasi vzdy."""
        self.clanek('Prvni', 'Text.', datum='2026-01-01')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('not a date', vypis)

    def test_K80_nesmyslne_datum_build_neshodi(self):
        """Jak ma datum vypadat, je vec autora - build to rekne a jede dal."""
        self.soubor('Prvni %s.md' % MARKER,
                    '---\ndate: vcera\n---\nText.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('prvni.html', self.stranky())

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
# Lokalizace vystupu
# ==============================================================================

class Lokalizace(Zaklad):

    def test_K100_vychozi_je_cestina(self):
        """Vault bez lang v config.toml se postavi cesky, vcetne nazvu stranek."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('<html lang="cs">', index)
        self.assertIn('Titulka', index)
        self.assertIn('Nahoru', index)

    def test_K100_anglicky_web_ma_anglicke_texty(self):
        self.clanek('Prvni', 'Text.')
        self.konfigurace('lang = "en"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('<html lang="en">', index)
        self.assertIn('Home', index)
        self.assertIn('Top', index)
        self.assertNotIn('Titulka', index)


    def test_K100_prazdna_pilulka_ma_jmeno_podle_jazyka(self):
        """Jmeno jde do adresy, `?tag=no-plain-tag`, tak jako jmena stranek."""
        self.clanek('Prvni', 'Text.', tagy='')
        self.clanek('Druha', 'Text.', tagy='obsidian')
        self.konfigurace('lang = "en"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('"name": "no-plain-tag"', index)
        self.assertNotIn('"name": "bez-bezneho-tagu"', index)

    def test_K100_prazdna_pilulka_ma_ceske_jmeno_na_ceskem_webu(self):
        """Protejsek predchoziho, aby test neprosel generatoru s jednim jazykem."""
        self.clanek('Prvni', 'Text.', tagy='')
        self.clanek('Druha', 'Text.', tagy='obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        index = self.vystupni('index.html')
        self.assertIn('"name": "bez-bezneho-tagu"', index)
        self.assertNotIn('"name": "no-plain-tag"', index)

    def test_K100_tabulka_textu_je_zapecena_v_titulce(self):
        """Skloňování resi prohlizec pres Intl.PluralRules, tvary nese tabulka."""
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertIn('const TXT =', html)
        self.assertIn('Intl.PluralRules', html)
        self.assertIn('článek', html)
        self.assertIn('článků', html)

    def test_stitek_ma_ctverecek_i_jmeno_a_kazdy_svuj_stav(self):
        """Ctverecek tag drzi, jmeno prohlizi. Zadny z nich nesahne na druhy.

        Listu kresli az prohlizec, takze se testuje skript, ktery stranka nese:
        obe casti stitku a obe casti stavu, ktere jim odpovidaji.
        """
        self.clanek('Prvni', 'Text.', tagy='obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertIn('data-hold=', html)          # checkbox: drzi
        self.assertIn('data-tag=', html)           # jmeno: prohlizi
        self.assertIn("params.getAll('tag')", html)
        self.assertIn("params.get('pick')", html)
        self.assertIn("'parstitek'", html)

    def test_filtr_je_i_v_hlavicce_clanku(self):
        """Stejny filtr jako na titulce, jen v liste clanku.

        Drive tam byly staticke odkazy na stranky tagu, tedy jina vec na
        jinem miste. Ctenar prijde z odfiltrovaneho vypisu a lista ma dal
        rikat, kde je.
        """
        self.clanek('Prvni', 'Text.', tagy='Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        self.assertIn('<nav class="zivy">', html)
        self.assertIn('id="fasety"', html)
        self.assertIn("'parstitek'", html)      # stitek se ctvereckem
        self.assertIn('data-hold=', html)
        # Bez skriptu zbyde lista, jakou stranka mela vzdycky.
        self.assertIn('<noscript><a href="tag-obsidian.html">', html)

    def test_filtr_v_clanku_pocita_z_tagu_ne_z_textu(self):
        """Do clanku se zapeci tagy a adresy clanku, ne cely index hledani.

        Cisla na stitcich a skok na jediny vysledek jsou jedine, co ta
        stranka pocita; index by se platil kilobajty na kazdem nacteni
        clanku.
        """
        self.clanek('Prvni', 'Slovo ktere je jen tady.', tagy='Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        skript = html.split('</header>')[1].split('<main>')[0]
        self.assertIn('[{"url": "prvni.html", "tags": ["Obsidian"]}]', skript)
        self.assertNotIn('Slovo ktere je jen tady', skript)

    def test_klik_do_clanku_si_nese_zafiltrovani(self):
        """Otevrit clanek nesmi zahodit to, na co si ctenar zafiltroval.

        Odkaz z vypisu nese stav filtru, protoze lista v hlavicce clanku ho
        z adresy zase precte.
        """
        self.clanek('Prvni', 'Text.', tagy='Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        # Staticka stranka tagu: tag te stranky se drzi dal.
        self.assertIn('href="prvni.html?tag=Obsidian"',
                      self.vystupni('tag-obsidian.html'))
        # Zivy vypis na titulce sklada tutez adresu skriptem.
        self.assertIn('c.url + stateQuery()', self.vystupni('index.html'))

    def test_Z80_jedina_karta_se_otevre_rovnou(self):
        """Klik na jmeno stitku, po kterem zbyde jedna karta, ji otevre.

        Skok patri KLIKU, ne stavu: adresa s jednim vysledkem zustava
        vypisem, aby odkaz poslany ven pristal tam co vzdycky. Skace jen
        jmeno, ne ctverecek, a jen kdyz se jmeno zapina.

        Skript spousti az prohlizec, takze se testuje kod, ktery stranka
        nese. Skace titulka i clanek; clanek k tomu nese vedle sad stitku
        i adresy clanku, jinak by vedel, ze vysledek je jeden, ale ne ktery.
        """
        self.clanek('Prvni', 'Text.', tagy='Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        titulka = self.vystupni('index.html')
        # Otevre se tataz adresa, jakou nese karta, tedy i s filtrem.
        self.assertIn('shown.length === 1', titulka)
        self.assertIn("location.href = shown[0].url + stateQuery()", titulka)
        # Skace jmeno, kdyz se zapina; ctverecek ma render bez pick.
        self.assertIn('render({ pick: current === tag })', titulka)
        self.assertIn('held.filter(f => f !== tag);', titulka)
        # Clanek skace stejne, z adres zapecenych u sad stitku. Kdyz klik
        # necha vic nez jeden clanek, vraci na titulku.
        clanek = self.vystupni('prvni.html')
        self.assertIn('{"url": "prvni.html", "tags": ["Obsidian"]}', clanek)
        self.assertIn('opts && opts.pick && shown.length === 1', clanek)
        self.assertIn("location.href = shown[0].url + stateQuery()", clanek)
        self.assertIn("location.href = 'index.html' + stateQuery()", clanek)

    def test_Z75_bez_nastaveni_filtr_na_obdobi_neni(self):
        """Filtr na obdobi je volitelny a vychozi je vypnuty.

        Web, ktery si ho nevyzadal, nedostane ani ovladac, ani jeho styly,
        ani mesice u clanku.
        """
        self.clanek('Prvni', 'Text.', datum='2025-01-01')
        self.clanek('Druhy', 'Text.', datum='2026-01-01')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        titulka = self.vystupni('index.html')
        self.assertNotIn('id="obdobi"', titulka)
        self.assertIn('const BINS = [];', titulka)
        self.assertNotIn('.histogram', self.vystupni('styl.css'))
        self.assertNotIn('"date": "2025-01-01"', self.vystupni('prvni.html'))

    def test_Z75_osa_jsou_souvisle_mesice(self):
        """Osa jde od prvniho clanku po posledni a nevynecha prazdny mesic.

        Dira v psani je informace a histogram ji ma ukazat, ne zavrit.
        Clanky jsou od sebe pres dva mesice, takze osa je po mesicich.
        """
        self.clanek('Prvni', 'Text.', datum='2025-11-20')
        self.clanek('Druhy', 'Text.', datum='2026-02-03')
        self.konfigurace('date_filter = true\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        titulka = self.vystupni('index.html')
        self.assertIn('id="obdobi"', titulka)
        self.assertIn('const BINS = ["2025-11", "2025-12", "2026-01", "2026-02"];',
                      titulka)
        self.assertIn('.histogram', self.vystupni('styl.css'))

    def test_Z75_obdobi_jde_do_adresy_a_do_clanku(self):
        """Obdobi je treti osa filtru a preziji kliknuti do clanku jako tagy.

        Clanek posuvnik nekresli, ale nese datum kazdeho clanku, aby cisla
        na stitcich v jeho hlavicce pocitala se stejnym obdobim.
        """
        self.clanek('Prvni', 'Text.', datum='2025-11-20', tagy='Obsidian')
        self.clanek('Druhy', 'Text.', datum='2026-02-03', tagy='Obsidian')
        self.konfigurace('date_filter = true\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        titulka = self.vystupni('index.html')
        self.assertIn("p.set('from', since)", titulka)
        self.assertIn("p.set('to', until)", titulka)
        self.assertIn('matchesTags(c, combo) && inPeriod(c)', titulka)
        clanek = self.vystupni('prvni.html')
        self.assertIn('"date": "2025-11-20"', clanek)
        self.assertIn('matchesTags(c, combo) && inPeriod(c)', clanek)

    def test_Z75_osa_po_dnech_zna_vikend_a_dnesek(self):
        """Vikend ma vlastni barvu jako token, dnesek pocita prohlizec.

        Build by dnesek znal jen v den buildu; web s --if-changed ale stoji
        beze zmeny tak dlouho, dokud se nic nezmeni.
        """
        self.clanek('Prvni', 'Text.', datum='2026-09-01')
        self.clanek('Druhy', 'Text.', datum='2026-09-20')
        self.konfigurace('date_filter = true\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        styl = self.vystupni('styl.css')
        self.assertIn('--vikend:', styl)
        self.assertIn('.osa .vikend { color: var(--vikend); }', styl)
        titulka = self.vystupni('index.html')
        self.assertIn('const now = new Date();', titulka)
        self.assertIn("' class=\"dnes\"'", titulka)

    def test_Z75_jediny_den_posuvnik_nekresli(self):
        """Posuvnik, se kterym neni kam jet, se nekresli, a build to rekne."""
        self.clanek('Prvni', 'Text.', datum='2026-01-20')
        self.clanek('Druhy', 'Text.', datum='2026-01-20')
        self.konfigurace('date_filter = true\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertNotIn('id="obdobi"', self.vystupni('index.html'))
        self.assertIn('date_filter is on', vypis)

    def test_Z75_datum_ktere_datem_neni_na_osu_nepatri(self):
        """Sablonovy zastupce by jinak osu natahl na nesmyslny den."""
        self.assertEqual(md2html.period_axis(
            ['2026-01-02', '{{date:YYYY-MM-DD}}', '2025-12-31']),
            ['2025-12-31', '2026-01-01', '2026-01-02'])

    def test_Z75_jednotka_je_nejjemnejsi_ktera_se_vejde(self):
        """Dny, mesice, nebo roky - podle toho, co da nejvys PERIOD_BARS sloupcu.

        Sloupcu je nejvys sedesat, aby na telefonu zbylo na kazdy par pixelu
        a palec se na nej trefil.
        """
        dny = md2html.period_axis(['2026-09-01', '2026-10-30'])
        self.assertEqual(len(dny), 60)
        self.assertEqual(dny[0], '2026-09-01')
        mesice = md2html.period_axis(['2026-09-01', '2026-10-31'])
        self.assertEqual(mesice, ['2026-09', '2026-10'])
        self.assertEqual(len(md2html.period_axis(['2021-01-01', '2025-12-31'])), 60)
        self.assertEqual(md2html.period_axis(['2021-01-01', '2026-01-01']),
                         ['2021', '2022', '2023', '2024', '2025', '2026'])

    def test_K70_date_filter_je_vypinac(self):
        """true nebo false bez uvozovek. "false" v uvozovkach by jinak zapnulo."""
        self.clanek('Prvni', 'Text.')
        for text in ('date_filter = "true"\n', 'date_filter = "false"\n',
                     'date_filter = 1\n'):
            self.konfigurace(text)
            kod, vypis = self.web()
            self.assertEqual(kod, 1, '%s: %s' % (text, vypis))
            self.assertIn('true or false', vypis)

    def test_hierarchicky_tag_se_rozpadne_na_dva_samostatne(self):
        """`Obsidian/Video` jsou dva tagy, kazdy se svou strankou.

        Kdyby zustal jeden, `Video` by sbiralo jen videa u Obsidianu - a to je
        prave to, podle ceho chce clovek filtrovat napric vaultem.
        """
        self.clanek('Prvni', 'Text.', tagy='Obsidian/Video')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('tag-obsidian.html', stranky)
        self.assertIn('tag-video.html', stranky)
        self.assertNotIn('tag-obsidian-video.html', stranky)
        self.assertIn('#Video', self.vystupni('prvni.html'))

    def test_filtr_ma_dve_rady_a_delitkem_je_znacka_na_tagu(self):
        """Podtrzitko pred jmenem vede prvni radu, zbytek jde pod ni.

        Dulezitost tedy rika vault tam, kde se clanek taguje, a obe rady jdou
        abecedne - jiny poradek uz neni podle ceho urcit.
        """
        self.clanek('Prvni', 'Text.', tagy='_Obsidian, Video')
        self.clanek('Druha', 'Text.', tagy='Alfa')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertIn('"name": "Obsidian", "label": "Obsidian", "lead": true', html)
        self.assertIn('"name": "Video", "label": "Video", "lead": false', html)
        self.assertIn('"name": "Alfa", "label": "Alfa", "lead": false', html)
        self.assertIn('id="fasety-dalsi"', html)
        # Abecedne v ramci celku, ze ktereho si rady vybiraji: Alfa pred Video.
        self.assertLess(html.index('"name": "Alfa"'), html.index('"name": "Video"'))

    def test_K97_kazdou_radu_uzavira_prazdna_pilulka(self):
        """Clanek bez tagu v jedne rade se k ni dostane pres jeji prazdnou pilulku.

        Pilulka nema jmeno, jen cislo, takze ctecce obrazovky rika, co je,
        vlastni aria-label.
        """
        self.clanek('Prvni', 'Text.', tagy='_Obsidian, Video')
        self.clanek('Druha', 'Text.', tagy='Alfa')
        self.clanek('Treti', 'Text.', tagy='_Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        for html in (self.vystupni('index.html'), self.vystupni('prvni.html')):
            self.assertIn('"name": "bez-hlavniho-tagu", "label": "", "lead": true,'
                          ' "pseudo": "lead"', html)
            self.assertIn('"name": "bez-bezneho-tagu", "label": "", "lead": false,'
                          ' "pseudo": "plain"', html)
            self.assertIn('"aria": "bez hlavního tagu"', html)
        # Na konci sve rady: za vsemi tagy.
        html = self.vystupni('index.html')
        self.assertLess(html.index('"name": "Video"'),
                        html.index('"name": "bez-hlavniho-tagu"'))

    def test_K97_prazdna_pilulka_jen_kdyz_zuzuje(self):
        """Pilulka, na kterou nesedi zadny clanek nebo sedi vsechny, se nekresli.

        Na webu bez hlavniho tagu by pilulka prvni rady nesla vsechno, a klik,
        ktery nic nezmeni, na listu nepatri.
        """
        self.clanek('Prvni', 'Text.', tagy='Obsidian')
        self.clanek('Druha', 'Text.', tagy='')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertNotIn('"name": "bez-hlavniho-tagu"', html)
        # Druha nema bezny tag, Prvni ano - tady pilulka zuzuje.
        self.assertIn('"name": "bez-bezneho-tagu"', html)

    def test_K97_bez_clanku_mimo_radu_neni_prazdna_pilulka(self):
        self.clanek('Prvni', 'Text.', tagy='Obsidian')
        self.clanek('Druha', 'Text.', tagy='Video')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertNotIn('"pseudo"', html)

    def test_K97_stranka_clanku_bez_tagu_uz_neni(self):
        """Clanky bez tagu najde prazdna pilulka, samostatna stranka zmizela.

        Osamely `#` v menu.md tak nic nedela a build to rekne.
        """
        self.clanek('Prvni', 'Text.', tagy='')
        self.clanek('Druha', 'Text.', tagy='obsidian')
        self.soubor('.obsidian2html/menu.md', '- `#obsidian`\n- `#`\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertNotIn('tag-bez-tagu.html', stranky)
        self.assertNotIn('tag-bez-tagu.html', self.vystupni('druha.html'))
        self.assertIn('lone `#`', vypis)

    def test_znacka_neni_soucasti_jmena_tagu(self):
        """`_Obsidian` a `Obsidian` je jeden tag, jedna stranka, jedna adresa.

        Kdyby znacka prosla do jmena, vznikly by dva tagy s toutez temou a
        adresa by nesla znak, ktery patri autorovi, ne ctenari.
        """
        self.clanek('Prvni', 'Text.', tagy='_Obsidian')
        self.clanek('Druha', 'Text.', tagy='Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        stranky = self.stranky()
        self.assertIn('tag-obsidian.html', stranky)
        self.assertNotIn('tag-_obsidian.html', stranky)
        self.assertIn('#Obsidian', self.vystupni('prvni.html'))
        self.assertNotIn('#_Obsidian', self.vystupni('prvni.html'))
        # Jeden tag, tedy oba clanky na jeho strance.
        stranka = self.vystupni('tag-obsidian.html')
        self.assertIn('prvni.html', stranka)
        self.assertIn('druha.html', stranka)

    def test_znacka_se_posuzuje_na_kazde_casti_hierarchie_zvlast(self):
        """`Obsidian/_Video` povysi Video, ne Obsidian.

        Hierarchie uz o vedeni rady nerozhoduje, rozhoduje znacka - a ta plati
        pro tag, u ktereho je napsana.
        """
        self.clanek('Prvni', 'Text.', tagy='Obsidian/_Video')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('index.html')
        self.assertIn('"name": "Video", "label": "Video", "lead": true', html)
        self.assertIn('"name": "Obsidian", "label": "Obsidian", "lead": false', html)

    def test_znacka_jen_v_jednom_clanku_vede_a_build_to_ohlasi(self):
        """Jeden vyskyt se znackou staci, ostatni build vyjmenuje.

        Slucovat je spravne, tag je jeden. Mlcet ne: autor napsal znacku
        jednou a desetkrat na ni zapomnel, a ze zapisu to nepozna.
        """
        self.clanek('Prvni', 'Text.', tagy='_Obsidian')
        self.clanek('Druha', 'Text.', tagy='Obsidian')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        self.assertIn('"name": "Obsidian", "label": "Obsidian", "lead": true',
                      self.vystupni('index.html'))
        self.assertIn('without the mark', vypis)
        self.assertIn('Druha', vypis)
        self.assertNotIn('Prvni', vypis.split('without the mark')[1])

    def test_K100_neznamy_jazyk_skonci_chybou(self):
        """Mlcky spadnout na cestinu by znamenalo tise vyrobit jiny web."""
        self.clanek('Prvni', 'Text.')
        self.konfigurace('lang = "de"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 1, vypis)
        self.assertIn('unknown language', vypis.lower())

    def test_K100_feed_hlasi_jazyk(self):
        self.clanek('Prvni', 'Text.')
        self.konfigurace('lang = "en"\nbase_url = "https://example.com"\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('<language>en</language>', self.vystupni('rss.xml'))


# ==============================================================================
# Obsidian syntaxe
# ==============================================================================

class Syntaxe(Zaklad):

    def test_frontmatter_se_nevykresli(self):
        self.clanek('Prvni', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertNotIn('date:', self.vystupni('prvni.html'))

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

    def test_wikilink_s_escapovanou_rourou(self):
        """V tabulce Obsidian rouru escapuje, jinak by rozdelila bunku."""
        self.clanek('Prvni',
                    '| Kdo | Kde |\n| --- | --- |\n'
                    '| [[Druha\\|zkratka]] | trida |\n')
        self.clanek('Druha', 'Text.')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        self.assertIn('<a href="druha.html">zkratka</a>', html)
        self.assertNotIn('Flattened links', vypis)

    def test_wikilink_s_escapovanou_rourou_a_kotvou(self):
        self.clanek('Prvni', 'Viz [[Druha#Sekce\\|jinam]].')
        self.clanek('Druha', '## Sekce\n\nText.\n')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)
        self.assertIn('>jinam</a>', self.vystupni('prvni.html'))

    def test_embed_obrazku_s_escapovanou_sirkou(self):
        """Totez u obrazku: ![[obr.png\\|300]] uvnitr tabulky."""
        self.clanek('Prvni', 'Obrazek: ![[schema.png\\|300]]\n')
        self.obrazek('Attachments/schema.png')
        kod, vypis = self.web()
        self.assertEqual(kod, 0, vypis)

        html = self.vystupni('prvni.html')
        self.assertIn('width="300"', html)
        self.assertIn('src="img/schema.png"', html)

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


if __name__ == '__main__':
    unittest.main(verbosity=2)
