# obsidian2html - zdrojový text

> **Toto je zdroj, `README.md` je z něj odvozený překlad.** Změna se dělá tady a teprve pak se propíše do README. README se vymaže a pak vytvoří překladem z tohoto.  
> Přesná pravidla a jejich zdůvodnění jsou v [SPEC.cs.md](SPEC.cs.md), kódy K a Z v závorkách odkazují tam.

## Co to je

Toto je **generátor html**.  
Je to python script, který se zavolá na **vstupní adresář s md soubory** (typicky vault Obsidian, ale není to podmínkou) a on vytvoří do **výstupního adresáře html soubory** webu.  
Výstupní web běží samostatně, nepotřebuje databázi.  
Jsou to **statické stránky s Javascriptem**.  
Mohou se nahrát na hosting, poslat zabalené mailem apod.

Používám ho dvěma způsoby:
* **VŠE S VÝJIMKOU** - publikuje se všechno kromě toho, co nechci.  
	To pojmenuji tak, aby adresář nebo soubor začínal podtržítkem.  
	Cokoli s podtržítkem nebo v adresáři s podtržítkem se ignoruje.  
	Neboli ze všech `*.md` mimo `_*.md` udělej `*.html`.
* **JEN S MARKEREM** - publikuje se jen to, co chci publikovat.  
	Takový soubor pojmenuji tak, že mu dám na konec znak 🌐.  
	Ze všech `*🌐.md` udělej `*.html`, všechny ostatní `*.md` ignoruj.

Vše s výjimkou používám pro dokumentaci a lepší zobrazení md souborů.  
Marker používám u svého soukromého webu.  
Mám v Obsidianu svoje know-how: obecné články, postupy, návody apod.  
Některé z těch článků jsou obecné, a tak je chci zveřejnit.  
Tak jim prostě na konec dám 🌐.

## Instalace a spuštění

Vyžaduje nainstalovaný python 3.11 nebo novější a v něm doinstalovaný markdown (`pip install markdown`).  
Volání (na pořadí přepínačů nezáleží):

```
python md2html.py --source C:\vault --dest C:\web --publish "*🌐.md"
python md2html.py --source C:\docs --dest C:\web-docs --publish "*.md"
```

Ze zdrojového adresáře vznikne web: sdílený `styl.css`, obrázky ve složce `img/`, titulka s kartami a filtrem podle tagů, stránky tagů, hledání, lišta, logo, RSS.  
`--source`, `--dest` a `--publish` jsou povinné, jen s `--check` se `--dest` nezadává.  
`--publish` říká, které články jdou ven, a volí tím jeden ze dvou režimů z úvodu (K10).  
Údaje o webu samotném - název, jazyk a adresa - nejsou přepínače, ale leží ve vaultu v `config.toml` (K70).

| Přepínač            | K čemu                                                                |
| ------------------- | --------------------------------------------------------------------- |
| `--source`          | zdrojový adresář s `.md` soubory                                      |
| `--dest`            | cílový adresář, kam se web postaví (Z50, Z55)                         |
| `--keep-archives N` | kolik posledních archivů předchozího výstupu nechat, výchozí 10 (Z55) |
| `--publish "vzor"`  | co se publikuje: `"*🌐.md"` jen s markerem, `"*.md"` všechno (K10)    |
| `--check`           | jen ověří, že se web postaví, nikam nezapisuje. Pro git hook          |

`--check` postaví celý web do dočasného adresáře, výsledek zahodí a dočasný adresář smaže.  
Vrátí `0`, když build prošel, a `1`, když ne, a vypíše stejná upozornění jako normální build.  
Je určený pro git hook ve vaultu, který před commitem ověří, že web jde postavit, a když ne, commit zastaví.  
Cílového adresáře se nedotkne, takže nic nemaže ani nearchivuje (Z55).  
**`--check` spolu s `--dest` nebo `--keep-archives` je chyba** - člověk by si jinak mohl myslet, že se do cíle něco zapsalo.

Návratový kód: `0` hotovo, `1` chyba při převodu, `2` špatné parametry.

## Jak připravit vault

- **Co jde ven** určuje `--publish`: buď jen články s markerem na konci názvu, nebo všechny (K10).
- **Podtržítko nebo tečka** na začátku názvu vyřadí složku i soubor, v obou režimech (K20).
- **Šablony** se přeskočí samy, složka se zjistí z nastavení Obsidianu (K15).
- **Titulek** článku je název souboru bez markeru, přebije ho klíč `title` ve frontmatteru (K25).
- **Adresa** článku je název souboru bez diakritiky, malými písmeny a s pomlčkami, třeba `obsidian-nastaveni.html` (K30).
- **Perex** na kartě je první odstavec článku (K40).
- **Přílohy** se hledají vedle článku, v jeho složce `Attachments/` a nakonec v celém vaultu (K50).
- **Náhledový obrázek** karty leží v `Attachments/` a jmenuje se jako článek, doporučený rozměr je 630x290 (K60).
- **Datum** patří do frontmatteru jako `date: RRRR-MM-DD`, jinak se vezme datum souboru (K80).
- **Tag** `Obsidian/Video` jsou dva tagy, `Obsidian` a `Video` (K95).
- **Hlavní tag** se označí podtržítkem, `_Obsidian`, a ve filtru na titulce pak vede (K97).

Klíče frontmatteru jsou anglicky: `date`, `title`, `excerpt`, `slug`, `tags` (K90).

## Nastavení webu

Nastavení webu leží ve vaultu ve složce `_obsidian2html/`, nebo `.obsidian2html/`, když má být v Obsidianu skrytá (K70).  
Obě naráz jsou chyba.  
Všechno v ní je nepovinné:

- `config.toml` - název, jazyk a adresa webu.
- `index.md` - ruční úvod na titulce.
- `logo.svg` - logo vlevo nahoře, odkaz na titulku.
- `menu.md` - lišta v hlavičce, určuje pořadí tagů. Bez ní je abecední.
- `styl.css` - vlastní styly, připojí se za vygenerované (Z40).

`config.toml` je textový soubor ve formátu [TOML](https://toml.io): na každém řádku `klíč = hodnota`, text v uvozovkách, komentář za `#`.

```toml
name = "Pan Kostka"                 # název webu
lang = "cs"                         # jazyk webu, cs nebo en
base_url = "https://pankostka.cz"   # adresa webu, bez ní nevznikne rss.xml
```

- `name` - název webu vlevo nahoře, v titulku každé stránky a v RSS. Výchozí je jméno složky vaultu.
- `lang` - jazyk tlačítek a popisků webu, ne článků (K100). Výchozí je `cs`.
- `base_url` - adresa, na které web poběží. Bez ní nevznikne `rss.xml`.

Chybějící klíč má výchozí hodnotu, neznámý klíč nebo neplatná hodnota build zastaví.

## Co nástroj slibuje

- Mrtvý odkaz nevznikne: když cíl na webu není, zbyde z odkazu text a build řekne kolik (Z10).
- Ukázky v blocích kódu zůstanou, jak jsou napsané (Z20).
- Chybějící obrázek build zastaví, web s dírou nevznikne (Z30).
- Do vaultu se jen čte, nikdy nezapisuje (Z45).
- Kam se zapisuje, určuje jen `--dest` (Z50).
- Cíl se před buildem vyprázdní, položky s tečkou zůstanou, předchozí obsah jde do archivu a cizí adresář se nesmaže (Z55).
- Přílohy mají adresu malými písmeny v ASCII, takže odkaz funguje i na linuxovém serveru (Z60).
- Filtr podle tagů přežije kliknutí do článku (Z70) a když zbude jediný článek, otevře se (Z80).

## Pro vývoj

Pravidla, jejich zdůvodnění a hraniční případy jsou v [SPEC.cs.md](SPEC.cs.md), ten je autoritou pro kód i testy.  
Testy se pouštějí `python test_md2html.py`, je jich 96 a běží pod sekundu.

## Licence

MIT - viz [LICENSE](LICENSE).
