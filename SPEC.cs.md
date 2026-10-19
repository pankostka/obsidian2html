# obsidian2html - specifikace

> **Tohle je autorita pro kód a testy.** Když si kód a tenhle dokument odporují, chyba je v kódu.  
> Uživatelský popis je v [README.cs.md](README.cs.md) a odkazuje sem kódy K a Z.  
> Kdyby si README a tenhle dokument odporovaly, platí tenhle.  
> Každý test v `test_md2html.py` nese v názvu kód pravidla, které ověřuje.

## Jak se to čte

Specifikace je rozdělená podle toho, co člověk hledá, ne podle druhu pravidla.  
Každé pravidlo má kód: **K** je pravidlo pro autora vaultu, **Z** je to, co za to slibuje nástroj.  
Kód je jen štítek, který najdou testy a kód, a nemění se, ani když se pravidlo přesune do jiného souboru.

## Soubory

| Soubor | O čem je | Pravidla |
| --- | --- | --- |
| [SPEC-publikovani.cs.md](SPEC-publikovani.cs.md) | Co jde na web a co ne: režimy, marker, šablony, podtržítko a tečka. | K10, K15, K20 |
| [SPEC-clanek.cs.md](SPEC-clanek.cs.md) | Z čeho se skládá stránka článku: titulek, adresa, perex, datum, odkazy a bloky kódu. | K25, K30, K40, K80, Z10, Z20 |
| [SPEC-prilohy.cs.md](SPEC-prilohy.cs.md) | Obrázky a přílohy: kde se hledají, náhledový obrázek, adresy na webu. | K50, K60, Z30, Z60 |
| [SPEC-menu.cs.md](SPEC-menu.cs.md) | Jak vzniká menu: hierarchie tagů, tagy z adresářů, hlavní tagy a řady filtru. | K95, K96, K97, K98 |
| [SPEC-filtrovani.cs.md](SPEC-filtrovani.cs.md) | Jak se filtruje: filtr přežije kliknutí do článku, jediný výsledek se otevře, filtr na období. | Z70, Z75, Z80 |
| [SPEC-nastaveni.cs.md](SPEC-nastaveni.cs.md) | Konfigurační složka, `config.toml`, jazyk, vlastní styly a anglické klíče. | K70, K90, K100, Z40 |
| [SPEC-prikazy.cs.md](SPEC-prikazy.cs.md) | Přepínače, návratové kódy, cílový adresář, archivy, `--if-changed` a `--edit-links`. | Z45, Z50, Z55, Z57, Z90 |
| [SPEC-stranka.cs.md](SPEC-stranka.cs.md) | Co je na každé stránce: patička s datem změny. | Z85 |

## Kde je které pravidlo

| Kód | Soubor |
| --- | --- |
| K10 | [SPEC-publikovani.cs.md](SPEC-publikovani.cs.md) |
| K15 | [SPEC-publikovani.cs.md](SPEC-publikovani.cs.md) |
| K20 | [SPEC-publikovani.cs.md](SPEC-publikovani.cs.md) |
| K25 | [SPEC-clanek.cs.md](SPEC-clanek.cs.md) |
| K30 | [SPEC-clanek.cs.md](SPEC-clanek.cs.md) |
| K40 | [SPEC-clanek.cs.md](SPEC-clanek.cs.md) |
| K50 | [SPEC-prilohy.cs.md](SPEC-prilohy.cs.md) |
| K60 | [SPEC-prilohy.cs.md](SPEC-prilohy.cs.md) |
| K70 | [SPEC-nastaveni.cs.md](SPEC-nastaveni.cs.md) |
| K80 | [SPEC-clanek.cs.md](SPEC-clanek.cs.md) |
| K90 | [SPEC-nastaveni.cs.md](SPEC-nastaveni.cs.md) |
| K95 | [SPEC-menu.cs.md](SPEC-menu.cs.md) |
| K96 | [SPEC-menu.cs.md](SPEC-menu.cs.md) |
| K97 | [SPEC-menu.cs.md](SPEC-menu.cs.md) |
| K98 | [SPEC-menu.cs.md](SPEC-menu.cs.md) |
| K100 | [SPEC-nastaveni.cs.md](SPEC-nastaveni.cs.md) |
| Z10 | [SPEC-clanek.cs.md](SPEC-clanek.cs.md) |
| Z20 | [SPEC-clanek.cs.md](SPEC-clanek.cs.md) |
| Z30 | [SPEC-prilohy.cs.md](SPEC-prilohy.cs.md) |
| Z40 | [SPEC-nastaveni.cs.md](SPEC-nastaveni.cs.md) |
| Z45 | [SPEC-prikazy.cs.md](SPEC-prikazy.cs.md) |
| Z50 | [SPEC-prikazy.cs.md](SPEC-prikazy.cs.md) |
| Z55 | [SPEC-prikazy.cs.md](SPEC-prikazy.cs.md) |
| Z57 | [SPEC-prikazy.cs.md](SPEC-prikazy.cs.md) |
| Z60 | [SPEC-prilohy.cs.md](SPEC-prilohy.cs.md) |
| Z70 | [SPEC-filtrovani.cs.md](SPEC-filtrovani.cs.md) |
| Z75 | [SPEC-filtrovani.cs.md](SPEC-filtrovani.cs.md) |
| Z80 | [SPEC-filtrovani.cs.md](SPEC-filtrovani.cs.md) |
| Z85 | [SPEC-stranka.cs.md](SPEC-stranka.cs.md) |
| Z90 | [SPEC-prikazy.cs.md](SPEC-prikazy.cs.md) |
