# obsidian2html - specifikace: Příkazová řádka a build

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Příkazová řádka

| Přepínač            | K čemu                                                                |
| ------------------- | --------------------------------------------------------------------- |
| `--source`          | zdrojový adresář s `.md` soubory                                      |
| `--dest`            | cílový adresář, kam se web postaví (Z50, Z55)                         |
| `--keep-archives N` | kolik posledních archivů předchozího výstupu nechat, výchozí 10 (Z55) |
| `--publish "vzor"`  | co se publikuje: `"*🌐.md"` jen s markerem, `"*.md"` všechno (K10)    |
| `--check`           | jen ověří, že se web postaví, nikam nezapisuje. Pro git hook          |
| `--if-changed`      | postaví web, jen když se od minula něco změnilo. Pro plánovač (Z57)   |
| `--edit-links`      | článek dostane odkaz, který jeho zdroj otevře v Obsidianu (Z90)       |

`--check` postaví celý web do dočasného adresáře, výsledek zahodí a dočasný adresář smaže.  
Vrátí `0`, když build prošel, a `1`, když ne, a vypíše stejná upozornění jako normální build.  
Je určený pro git hook ve vaultu, který před commitem ověří, že web jde postavit, a když ne, commit zastaví.  
Cílového adresáře se nedotkne, takže nic nemaže ani nearchivuje (Z55).  
**`--check` spolu s `--dest` nebo `--keep-archives` je chyba** - člověk by si jinak mohl myslet, že se do cíle něco zapsalo.

`--if-changed` je pro build pouštěný pravidelně, třeba každých pět minut z plánovače.  
Když se ve zdroji od posledního buildu nic nezměnilo, skončí hned a na cíl nesáhne, takže se web zbytečně nepřepisuje.  
Nová verze `md2html.py` se počítá jako změna.

`--edit-links` je pro web, který čte jen jeho autor.  
Vpravo od nadpisu článku i jeho karty v přehledu přibude tužka a klik na ni otevře poznámku, ze které článek vznikl.  
Prohlížeč se napoprvé zeptá, jestli smí Obsidian spustit.  
Na veřejný web nepatří, prozradil by název vaultu a jeho složky.  
`--source` musí ležet ve vaultu Obsidianu, tedy ve složce se `.obsidian/` nebo pod ní, jinak build skončí chybou.

Návratový kód: `0` hotovo, `1` chyba při převodu, `2` špatné parametry.

## Chování buildu

**Z45. Do vstupního adresáře se jen čte, nikdy nezapisuje.** Vault je zdroj, ne pracovní plocha. Generátor v něm nesmí nic vytvořit, změnit ani smazat, a to ani konfiguraci, ani evidenci, ani dočasný soubor. Kdo pustí build, nemá mít důvod zjišťovat, co to udělalo s jeho poznámkami.

**Z50. Výstup patří mimo repo.**  
Aby commit vygenerovaného HTML nebyl možný, ne jen zakázaný, a aby generátor neskenoval adresář, do kterého zapisuje.  
Kam se zapisuje, **určuje parametr skriptu** `--dest` - žádná výchozí cesta zadrátovaná v kódu.

**Z55. Cílový adresář se před každým buildem vyprázdní.**  
Co v něm zůstane z minula, zůstane i na webu, takže článek, kterému se odebral marker nebo který se přejmenoval, by byl dál veřejně k dispozici.  
Smaže se všechno kromě položek, jejichž název začíná tečkou: `.git`, `.htaccess`, `.well-known` i značka `.vygenerovano` přežijí.  
Do výstupu, který se nasazuje gitem, tak jde stavět přímo, a ručně přidané soubory pro server se nemusí po každém buildu vracet.  
Předtím se to, co se bude mazat, zabalí do zipu ve složce `_archiv` o úroveň výš, třeba `C:\_archiv\web-2026-09-25-143000.zip`.  
Archiv leží mimo cíl, aby se s webem nenahrál na hosting a aby se nebalil sám do sebe.  
Nechává se posledních 10 zipů, jiný počet určí `--keep-archives`, `0` znamená žádný zip.  
**Pojistka:** položky s tečkou se nepočítají.  
Cíl, který neexistuje, je prázdný nebo obsahuje jen položky s tečkou (třeba čerstvý klon repozitáře), se postaví.  
Cíl, ve kterém je cokoli dalšího a chybí značka `.vygenerovano`, build zastaví a nic se nesmaže - překlep v cestě tak cizí složku nesmaže.

**Z57. S `--if-changed` se web nestaví znovu, když se od posledního buildu nic nezměnilo.**  
Je to pro build pouštěný pravidelně, třeba každých pět minut z plánovače.  
Naslepo by každý běh vyprázdnil cíl a zapsal celý web znovu: Dropbox by pořád synchronizoval, web by byl na okamžik prázdný a s archivací by pokaždé vznikl zip.  
Generátor proto spočítá otisk zdroje: cestu, velikost a čas změny každého souboru, který na web může mít vliv, k tomu vzor z `--publish` a vlastní verzi.  
Otisk uloží po úspěšném buildu do značky `.vygenerovano` v cíli, kterou vyprázdnění podle Z55 nechává být.  
Když se otisk shoduje, build skončí hned, na cíl nesáhne a vrátí `0`.  
Build, který spadl, otisk neuloží, takže se příště zkusí znovu.  
Do otisku se počítá všechno kromě složek a souborů s tečkou na začátku, s výjimkou konfigurační složky `.obsidian2html/` a nastavení šablon v `.obsidian/`.  
Složky s podtržítkem se počítají, protože přílohy v nich generátor najde (K50).  
Nová verze `md2html.py` znamená nový build, i když se ve vaultu nic nezměnilo.  
Bez `--if-changed` se staví vždycky - ruční build má udělat, co se po něm chce.  
`--if-changed` spolu s `--check` je chyba, `--check` žádný cíl nemá.

**Z90. S `--edit-links` má nadpis každého článku i jeho karta v přehledu odkaz, který zdroj otevře v Obsidianu.**  
Na lokálním webu se článek čte a vzápětí opravuje, a dohledat k `fy-2026-09-22-soustava-si.html` jeho poznámku ve vaultu je zbytečná práce.  
Od adresy k souboru se zpátky nedojde, protože slug zahodí diakritiku, velikost písmen i složku (K30) - odkaz proto musí vložit build, který cestu zná.  
Odkaz má tvar `obsidian://open?vault=ProjektKrizik&file=02%20P%C5%99edm%C4%9Bty%2F...`, tedy vault podle jména složky a poznámka podle cesty uvnitř vaultu, bez `.md`.  
Otevře ho Obsidian, který si protokol `obsidian://` zaregistruje při instalaci; prohlížeč se napoprvé zeptá, jestli ho smí spustit.  
**Absolutní cesta v odkazu není**, takže odkaz funguje dál, i když se vault přesune jinam, a na disku nic neprozradí.  
Vault se hledá od `--source` nahoru podle složky `.obsidian/`, protože `--source` smí být i podsložka vaultu a Obsidian cestu počítá od jeho kořene.  
Když vault nahoře není, build skončí s kódem `2` dřív, než sáhne na cíl - odkaz, který nic neotevře, je mrtvý odkaz (Z10).  
Odkaz dostane jen článek, protože jen ten má jeden zdroj; titulka a stránky tagů ho mají u karet svých článků, ne u sebe.  
Na kartě je proto, aby se kvůli opravě nemusel článek rozklikávat.  
**Je to ikonka tužky vpravo od nadpisu, ne text.**  
Tužka je vložené SVG v barvě textu, protože emoji a znaky Unicode vypadají podle písma čtenáře a některá písma je nemají.  
Slova *Upravit v Obsidianu* jsou v `title` a `aria-label`, takže je ukáže najetí myší a přečte čtečka.  
**Výchozí je vypnuto a je to přepínač, ne klíč v `config.toml`.**  
Název vaultu a jeho složky jsou soukromé, na veřejný web nepatří.  
Z jednoho vaultu přitom může vzniknout veřejný web i lokální náhled a odkaz patří jen do náhledu - rozhoduje tedy, kdo tenhle build čte, ne vlastnost webu (K70).  
Přepínač se počítá do otisku, takže jeho zapnutí `--if-changed` pozná jako změnu (Z57).  
Odkaz má třídu `upravit` a s nadpisem ho drží blok `titulek`, takže ho jde ve `styl.css` přestylovat nebo schovat (Z40).
