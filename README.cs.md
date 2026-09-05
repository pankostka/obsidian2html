# obsidian2html - zdrojový text

> **Toto je zdroj, `README.md` je z něj odvozený překlad.** Změna se dělá tady a teprve pak se propíše do README. README se vymaže a pak vytvoří překladem z tohoto.


## Co to je

V Obsidianu mám svoje know-how. Obecné články, postupy, návody apod.  
Některé z těch článků jsou obecné a tak je chci zveřejnit.

Toto je **generátor html**. Z vaultu Obsidianu udělá do samostatného adresáře sadu html souborů.  
Ty se pak mohou nahrát třeba na hosting. Nebo poslat zabalené mailem.

Aby to fungovalo, musím v Obsidianu dodržovat některé konvence.  
*Například když chci článek publikovat, tak do názvu dám na konec znak 🌐. Jednoduché, funkční.*

Nástroj je obecný, sedí v jednom adresáři a zavolám ho se vstupním adresářem (vaultem) a výstupním (webem).  
Prakticky mám dávku v kořeni vaultu.

Co neumí?  
-  Generovat PDF - původně bylo součástí, ale podle mě to má být samostatný nástroj.
- Publikovat na FTP - toto by měl taky řešit jiný nástroj.

Proč Obsidian?
- Umí skvěle editovat MD.
- Je zdarma.


## Instalace a spuštění

```
pip install markdown
```

Jediná závislost. Python 3.8 a novější, samotný nástroj je jeden soubor.

```
python md2html.py <vault> --site -o <kam>
```

Postaví web z vaultu do zadaného adresáře. Bez `--site` se z jednoho `.md` udělá samostatný HTML soubor s obrázky uvnitř, který jde poslat mailem.

| Přepínač | K čemu |
| --- | --- |
| `--site` | režim webu: sdílený `styl.css`, obrázky do `img/`. Vyžaduje `-o` |
| `-o <kam>` | kam se má web postavit. Povinné s `--site` |
| `--lang cs\|en` | jazyk webu, výchozí `cs` |
| `--marker` | znak publikace na konci názvu, výchozí globus |
| `--all` | převede všechny články, i neoznačené |
| `--site-name` | název webu do hlavičky, výchozí je jméno složky vaultu |
| `--base-url` | absolutní adresa webu. Bez ní se negeneruje `rss.xml` |
| `--published-only` | jen články s markerem. `--site` to zapíná samo |
| `--check` | jen ověří, že se web postaví. Pro git hook |
| `--clean` | před buildem zabalí předchozí výstup do archivu |
| `--title` | titulek jednoho souboru, když se nemá sahat do zdroje |
| `--vault` | kde hledat obrázky, výchozí je adresář vstupu |

Návratový kód: `0` hotovo, `1` chyba při převodu, `2` špatné parametry.

Testy se pouštějí `python test_md2html.py`, je jich 71 a běží pod sekundu.


## Konvence

Konvence jsou dvojího druhu:  
**Vaultové** říkají, co musí splnit autor, aby generátor věci našel/zohlednil.  
**Záruky** říkají, co za to nástroj slibuje. 

### Vaultové konvence

**K10. Publikují se jen články, jejichž název končí globusem 🌐.** Článek `Název článku 🌐.md` jde ven, článek `Název článku.md` ne. Chybějící marker tedy znamená neveřejné, takže se zveřejňuje vědomým úkonem, nikdy opomenutím. Je to vidět hned ve stromu souborů, což je příjemné a jasné.  
Znak určuje `--marker`, výchozí je globus. Vault si smí zvolit jiný, ale **znak z běžné klávesnice je špatný marker**: strhává se i z titulku, takže s `--marker '!'` půjde ven článek `Pozor!.md` s titulkem `Pozor`. Build na to upozorní. Prázdný marker je chyba, na "všechno" je jiný přepínač.  
Tím přepínačem je **`--all`**, který filtr vypne úplně. Není to druhá cesta, jak článek publikovat omylem - je to jeden vědomý příkaz a build nahlas řekne, kolik neoznačených článků vzal s sebou. Vzniká tím adresář s HTML; nahrát ho někam je samostatný úkon, který tenhle nástroj neumí.

**K15. Šablony se ignorují a která složka to je, se čte z konfigurace Obsidianu.** Šablona není článek: je to kostra se zástupnými symboly, takže publikovat ji znamená vystavit na web `{{date:YYYY-MM-DD}}`. Čte se `.obsidian/templates.json` i nastavení Templateru, protože vault to už ví a nikdo to nemusí opisovat podruhé. Když je složka označená markerem, přeskočí se stejně - build ale řekne, který článek to byl, protože složka a marker si v tu chvíli odporují.

**K20. Složka začínající tečkou nebo podtržítkem se přeskakuje.** Spolu s K70 to dává jednoduché pravidlo: co má být mimo web, dostane podtržítko.

**K25. Titulek článku je název souboru z Obsidianu, jen bez markeru.** Nadpis `# H1` se nepoužívá - nejde spolehlivě poznat, jestli je to titulek dokumentu, nebo první sekce ze šablony. Název souboru je Obsidianův vlastní model, takže cesta tam i zpět je zřejmá: od titulku na webu se dá dohledat článek ve vaultu a naopak. Frontmatter klíč `title` ho přebije tam, kde je název technický.

**K30. Název článku se převede na slug.** Z `Obsidian Nastavení 🌐.md` vznikne `obsidian-nastaveni.html`: bez diakritiky, malými písmeny, mezery na pomlčky, marker pryč. Je to kvůli publikování na web, kde diakritika ani mezery v adrese nepatří. Oddělovač je **pomlčka, ne podtržítko** - vyhledávače berou pomlčku jako hranici slov, podtržítko ne.

**K40. Perex je první odstavec.** Od začátku až po nadpis. Když článek začíná rovnou nadpisem, pak je perex prázdný. Pokud je v perexu obrázek, pak se vyhodí.

**K50. Přílohy leží v `Attachments/`.** Hledá se v pořadí: vedle článku, v jeho složce příloh (`Attachments`), pak v celém vaultu - stejně jako to dělá Obsidian.

**K60. Náhledový obrázek se jmenuje jako článek** a leží v `Attachments/` vedle něj. Porovnává se přes slug, takže sedne `Obsidian Co je.png` i `obsidian-co-je.png`. Pojmenovat ho pevně nejde: jedna složka `Attachments/` obsluhuje všechny články své složky, takže by mezi nimi kolidoval. Doporučený rozměr je 630x290. Jiný rozměr se nepředělává - ořez a vycentrování obstará CSS v prohlížeči (`object-fit: cover`, horní část zůstane), takže generátor nepotřebuje knihovnu na obrázky.

**K70. Konfigurace webu leží ve složce `.obsidian2html/`** v kořeni vaultu. Drží `menu.md` (kurátorovaná lišta), `index.md` (ruční úvod na titulce), `styl.css` (vlastní styly) a `logo.svg`. Tečka na začátku složku v Obsidianu skryje, což je záměr: jsou to vstupy pro generátor, ne články, a editují se mimo Obsidian. Název říká, ke kterému nástroji ta složka patří, takže vedle `.obsidian/` nevzniká nejasnost. Když složka ve vaultu není, generátor si poradí bez ní.

**K80. Publikovaný článek by měl mít ve frontmatteru `date`.** Když ho nemá, použije se datum souboru. Je to vratké, protože datum souboru se mění při kopírování i při synchronizaci, ale je to jednoduché a nepotřebuje to git - ten ve vstupním adresáři fungovat nemusí. Při shodě dat rozhoduje název článku, aby bylo pořadí jednoznačné.  Tvar `RRRR-MM-DD` se kontroluje a build na cokoli jiného upozorní (třeba datum šablony `{{date:YYYY-MM-DD}}`)

**K90. Klíče frontmatteru a přepínače jsou anglicky.** Tedy `date`, `title`, `excerpt`, `slug`, `tags`, a přepínače `--site`, `--published-only`, `--base-url`, `--check`, `--clean`, `--site-name`. Obsah článků je česky, rozhraní nástroje ne - nástroj je veřejný a jeho příkazová řádka i klíče jsou to jediné, co cizí uživatel musí napsat sám. České klíče `datum`, `titul` a `perex` se už nečtou; když na ně build narazí, ohlásí to, protože jinak by článek tiše přišel o datum nebo titulek.

**K100. Jazyk webu určuje přepínač `--lang`, výchozí je `cs`.** Lokalizuje se jen to, co vidí **návštěvník** - hlášky při buildu čte ten, kdo build spouští, a ty jsou anglicky vždycky.  
Součástí jazyka jsou i **názvy stránek**: český web má `tag-bez-tagu.html`, anglický `tag-no-tag.html`.  
Adresa, která je jednou venku, je závazek, a odvození od jazyka ho drží na obou stranách.  
Skloňování řeší v prohlížeči `Intl.PluralRules`, takže v kódu nejsou žádná pravidla na počítání - tabulka nese jen tvary. Čeština jich potřebuje tři, angličtina dvě.  
Neznámý jazyk build zastaví. Tiše spadnout na češtinu by znamenalo vyrobit jiný web, než si člověk vyžádal.



### Záruky

**Z10. Mrtvý odkaz nikdy nevznikne.** Když cíl odkazu není v dávce, zbyde z něj holý text a skript ohlásí kolik. Dokument jde uživateli, a odkaz, který nikam nevede, je horší než žádný.

**Z20. Uvnitř bloku kódu se nenahrazuje nic.** Bez toho si převodník přepíše vlastní ukázky syntaxe: článek, který učí psát wikilinky, má `[[Název]]` jako kód, ale generátor by v něm viděl odkaz, cíl nenašel a zploštil ho na text. Čtenář by se z článku o závorkách dozvěděl všechno kromě těch závorek.

**Z30. Chybějící obrázek je chyba, ne varování.** V tichosti by vznikl dokument s prázdným místem a odešel uživateli.

**Z40. Vlastní styly se připojují, nenahrazují.** `.obsidian2html/styl.css` jde za vygenerované CSS, takže přepsat jde cokoli. Barvy jsou tokeny v `:root`, takže změna je jedna řádka a nesahá se do generátoru.

**Z45. Do vstupního adresáře se jen čte, nikdy nezapisuje.** Vault je zdroj, ne pracovní plocha. Generátor v něm nesmí nic vytvořit, změnit ani smazat, a to ani konfiguraci, ani evidenci, ani dočasný soubor. Kdo pustí build, nemá mít důvod zjišťovat, co to udělalo s jeho poznámkami.

**Z50. Výstup patří mimo repo.** Aby commit vygenerovaného HTML nebyl možný, ne jen zakázaný, a aby generátor neskenoval adresář, do kterého zapisuje. Kam se zapisuje, **určuje parametr skriptu** - žádná výchozí cesta zadrátovaná v kódu. Smazat smí skript jen adresář se značkou `.vygenerovano`, takže překlep v cestě cizí složku nesmaže.

**Z60. Přílohy se na webu ukládají malými písmeny v ASCII.** Na Linuxu je `Foo.png` a `foo.png` rozdíl, takže špatně napsaný odkaz funguje na Windows a na serveru vrátí 404. Velikost písmen v odkazech se navíc ověřuje proti skutečným souborům a kolize adres je chyba.

## Licence

MIT - viz [LICENSE](LICENSE).
