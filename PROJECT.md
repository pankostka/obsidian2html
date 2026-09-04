# PROJECT

Pracovní dokument. Co se dělá, co zbývá, co se už zkusilo. Důležité nahoře, slepé cesty dole.

**Konvence nástroje nejsou tady, jsou v [README.cs.md](README.cs.md).** Ten je autoritou; když si kód a konvence odporují, chyba je v kódu. Tady je jen práce kolem.

## Stav

Repozitář žije zatím **jen lokálně**, na GitHubu není nic. Až se publikuje, půjde na `pankostka/obsidian2html` jako veřejný, licence MIT, držitel práv `pankostka.cz`.

Skript přišel z `_JDStandards`, kde nepatřil - to repo drží pravidla, tohle je nástroj. Do cílových rep se nekopíroval, takže přesunem se nic nerozbilo. **V `_JDStandards` zatím pořád leží** a smaže se, až tenhle repozitář poběží.

Historie se nepřenášela, začalo se od aktuálního stavu.

## Úkoly

Pořadí je záměrné: nejdřív to, co mění tvar nástroje, pak rozpory mezi konvencemi a kódem, pak jazyk, nakonec publikace.

### 1. Vyříznout PDF - HOTOVO

Odešlo `na_pdf`, `najdi_prohlizec`, `pockej_na_soubor`, `PROHLIZECE`, `CSS_TISK`, přepínače `--pdf`, `--vedle`, `--footer`, `--landscape` a `--browser`, parametr `landscape` funkce `na_html` a `import subprocess`. Skript zhubl o 142 řádků a ztratil závislost na Edge a Chrome.

`CSS_TISK` nedržel jen `@media print`, ale i styl `.paticka`, který používá samostatný HTML - ten se přesunul do `CSS_OBSAH`.

Ověřeno porovnáním: PKVault postaven oběma verzemi ze složek stejného jména, všech 18 stránek bajt za bajtem shodných.

Tisk v prohlížeči teď vytiskne stránku i s hlavičkou a lištou. Vědomě přijato.

### 2. Srovnat kód s konvencemi

Čtyři místa, kde `README.cs.md` slibuje něco jiného, než kód dělá:

| Konvence | Dnešní kód | Co udělat |
|---|---|---|
| **Z45** ze vstupu se jen čte | zapisuje `_web/vydano.md` do vaultu | zrušit evidenci vydaných adres úplně |
| **K70** složka `.obsidian2html/` | čte z `_web/` | přejmenovat, starý název nepodporovat |
| **K80** datum souboru jako záloha | bez `datum` build spadne | doplnit zálohu, při shodě řadit podle názvu |
| **Z50** kořen výstupu | napevno `c:\_web` | **udělat z něj parametr skriptu** |

### 3. Testy

Musí vzniknout **před** přejmenováváním v krocích 4 a 5. Skript má 2233 řádků a ani jeden test; hromadné přejmenování bez nich je místo, kde se něco tiše rozbije a zjistí se to za měsíc.

Zadáním jsou **záruky Z10 až Z60** z `README.cs.md`. Každá je věta, kterou test buď potvrdí, nebo shodí.

### 4. Vnitřek do angličtiny

51 funkcí s českými názvy, komentáře, docstringy. Mechanické, ale bez testů riskantní.

### 5. Rozhraní do angličtiny

Přepínače (`--titul`, `--jen-publikovane`, `--vedle`, `--adresa`, `--kontrola`, `--uklid`, `--nazev`) a klíče frontmatteru (`titul`, `datum`, `perex`, `slug`). **Rozbije to PKVault**, takže k tomu patří jeho migrace.

### 6. Lokalizace výstupu

Osmnáct řetězců, které vidí návštěvník webu. Výchozí jazyk `cs`, aby PKVault vypadal stejně jako dnes.

Drobná komplikace je skloňování: čeština má tři tvary, angličtina dvě. V prohlížeči to řeší `Intl.PluralRules`, na straně Pythonu je to pár řádků. Řetězce jsou na dvou místech, v Pythonu i ve vloženém JavaScriptu - mechanismus na propsání do JS už existuje, `@TAGY@` v šabloně hledání.

Vedlejší efekt: když jazyk určí i názvy stránek, zůstane `hledani.html` v češtině `hledani.html` a adresy, které jsou venku, se nezmění.

### 7. Publikace

Vyrobit `README.md` překladem z `README.cs.md`. Založit repozitář na GitHubu, pushnout, smazat `md2html.py` z `_JDStandards`.

`gh` ani `git filter-repo` na stroji nejsou. `gh` se dá doinstalovat, nebo se prázdný repozitář založí ručně přes web.

## Otevřené otázky

- **Přejmenovat `menu_webu.md` na `menu.md`?** Původní důvod pro delší název byl, že `menu.md` je ve vaultu obsazené navigací samotného vaultu. Konfigurace teď ale sedí ve vlastní skryté složce, kde se srazit nemůže.
- **Vynucovat tagy?** `dokumentace_JD.md` chce PascalCase a jednu variantu na tag, protože se porovnávají jako řetězce a dvě varianty tiše rozpůlí stránku tagu. Skript to nekontroluje ani nehlásí.

## Slepé cesty

Zapsané proto, aby se nezkoumaly podruhé.

### Quartz

Vyzkoušen v5.0.0 nad kopií PKVaultu, celé prostředí pak smazáno. **Není to cesta**, ale ne proto, že by byl špatný - v lecčems je lepší. Vyhledávání má okamžité a fulltextové, k tomu obsah stránky, zpětné odkazy, graf a strom složek, což tenhle nástroj nemá.

Nesedl na konvence, a to zásadně:

- **Publikoval všechno**, včetně `JirkaTODO` se soukromými poznámkami. Filtr `ExplicitPublish` existuje, ale jede na frontmatter `publish: true`, tedy na konvenci, která byla vědomě opuštěna ve prospěch markeru v názvu.
- **Nevyrobil titulku**, protože vault nemá `index.md`.
- **Nechal v adresách diakritiku i globus** (`obsidian-nastavení-🌐.html`), takže by se rozbila každá už vydaná adresa.
- **Nemá fasetový filtr.** Stránka tagu je prostý seznam, kliknutí na jiný štítek ten první nahradí; kombinování přes AND ani tlumení nedosažitelných tam není.
- **Neznal konvence.** Nezpracoval devět obrázků, mezi nimi náhledy pojmenované podle článku a logo.

Cena migrace by byla několik dní a pak trvalá daň při každém upgradu, protože Quartz se aktualizuje mergem z upstreamu do repozitáře s vlastními úpravami.

### Samostatný HTML jako důvod existence

Původní README tvrdilo, že smyslem nástroje je jeden soubor s obrázky v data URI do mailu a Teams. **Neplatí to** - autor tenhle režim skoro nepoužívá, jede `--web`.

Odlišení není ani jednosouborový režim, ani fasetový filtr sám o sobě, ale **vyslovené a zdůvodněné konvence**. Proto jsou jádrem `README.cs.md`.

### nl2br

Rozšíření knihovny `markdown`, které dělá zlom z každého nového řádku - odpadly by koncové mezery. Vyzkoušeno na PKVaultu: přidalo 48 zlomů v 7 článcích, počet stránek i obsah titulky a stránek tagů zůstal shodný, tedy **bezpečné**. Obsidian se ve výchozím nastavení chová stejně.

Nepřijato, autor si vystačí s Enterem. Zapsáno pro případ, že by se ty koncové mezery ukázaly jako příliš křehké.

### Zpětné lomítko jako zlom řádku

Nefunguje. Je to CommonMark, kdežto knihovna `markdown` CommonMark není - `Věta.\` se vykreslí i s tím lomítkem. Fungují jen **dvě koncové mezery**.

### Pevný název náhledového obrázku

Zvažoval se `perex.png` místo pojmenování podle článku. **Nejde to**: jedna složka `Attachments/` obsluhuje všechny články své složky, takže by náhled mohl mít jen jeden z nich.

### Přenos historie

`git filter-repo` uměl vyříznout 23 commitů `md2html.py` z `_JDStandards`. Nakonec se nepřenášely, staré commity nejsou potřeba.
