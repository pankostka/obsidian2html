# obsidian2html - zdrojový text

> **Toto je zdroj, `README.md` je z něj odvozený překlad.** Změna se dělá tady a teprve pak se propíše do README. README se vymaže a pak vytvoří překladem z tohoto.

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

Řídí konvencemi, které jsou sepsané níže (K10, K15 atd.).
## Instalace a spuštění

Vyžaduje nainstalovaný python a v něm doinstalovaný markdown (`pip install markdown`).  
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

Testy se pouštějí `python test_md2html.py`, je jich 81 a běží pod sekundu.

## Konvence

Konvence jsou dvojího druhu:  
**Vaultové** říkají, co musí splnit autor, aby generátor věci našel/zohlednil.  
**Záruky** říkají, co za to nástroj slibuje. 

### Vaultové konvence

**K10. Co se publikuje, určuje povinný přepínač `--publish`.**  
Hodnota je vzor názvu souboru a má jen dva tvary, jeden pro každý režim z úvodu:
- `--publish "*🌐.md"` - **jen s markerem**. Článek `Název článku 🌐.md` jde ven, článek `Název článku.md` ne.  
	Chybějící marker znamená neveřejné, takže se zveřejňuje vědomým úkonem, nikdy opomenutím.  
	Je to vidět hned ve stromu souborů, což je příjemné a jasné.
- `--publish "*.md"` - **všechno**, kromě toho, co vyřadí K15 a K20.

Přepínač je povinný, takže bez něj build nezačne a v každé dávce je vidět, co jde ven.  
Výchozí hodnota by rozhodovala potichu.  
Marker je znak mezi `*` a `.md` a vault si smí zvolit jiný než globus.  
**Znak z běžné klávesnice je ale špatný marker**: strhává se i z titulku, takže s `--publish "*!.md"` půjde ven článek `Pozor!.md` s titulkem `Pozor`.  
Build na to upozorní.  
Jiný vzor, třeba `"Návod*.md"`, je chyba: marker se strhává z titulku i z adresy (K25, K30) a z libovolné masky nejde poznat, co strhnout.  
Prázdná hodnota je taky chyba.  
**Vzor patří do uvozovek.** Ve Windows by prošel i bez nich, ale bash by `*.md` rozbalil na seznam souborů v aktuálním adresáři.  
Build to pozná podle toho, že místo jednoho vzoru dostal soubory, a zastaví se.  
Vzniká tím adresář s HTML; nahrát ho někam je samostatný úkon, který tenhle nástroj neumí.

**K15. Šablony se ignorují a která složka to je, se čte z konfigurace Obsidianu.** Šablona není článek: je to kostra se zástupnými symboly, takže publikovat ji znamená vystavit na web `{{date:YYYY-MM-DD}}`. Čte se `.obsidian/templates.json` i nastavení Templateru, protože vault to už ví a nikdo to nemusí opisovat podruhé. Když je složka označená markerem, přeskočí se stejně - build ale řekne, který článek to byl, protože složka a marker si v tu chvíli odporují.

**K20. Složka nebo soubor začínající tečkou nebo podtržítkem se přeskakuje.**  
Spolu s K70 to dává jednoduché pravidlo: co má být mimo web, dostane podtržítko.  
Platí to v obou režimech, takže ani `_Poznámka 🌐.md` na web nejde.

**K25. Titulek článku je název souboru z Obsidianu, jen bez markeru.** Nadpis `# H1` se nepoužívá - nejde spolehlivě poznat, jestli je to titulek dokumentu, nebo první sekce ze šablony. Název souboru je Obsidianův vlastní model, takže cesta tam i zpět je zřejmá: od titulku na webu se dá dohledat článek ve vaultu a naopak. Frontmatter klíč `title` ho přebije tam, kde je název technický.

**K30. Název článku se převede na slug.** Z `Obsidian Nastavení 🌐.md` vznikne `obsidian-nastaveni.html`: bez diakritiky, malými písmeny, mezery na pomlčky, marker pryč. Je to kvůli publikování na web, kde diakritika ani mezery v adrese nepatří. Oddělovač je **pomlčka, ne podtržítko** - vyhledávače berou pomlčku jako hranici slov, podtržítko ne.

**K40. Perex je první odstavec.** Od začátku až po nadpis. Když článek začíná rovnou nadpisem, pak je perex prázdný. Pokud je v perexu obrázek, pak se vyhodí.

**K50. Přílohy leží v `Attachments/`.** Hledá se v pořadí: vedle článku, v jeho složce příloh (`Attachments`), pak v celém vaultu - stejně jako to dělá Obsidian.

**K60. Náhledový obrázek se jmenuje jako článek** a leží v `Attachments/` vedle něj. Porovnává se přes slug, takže sedne `Obsidian Co je.png` i `obsidian-co-je.png`. Pojmenovat ho pevně nejde: jedna složka `Attachments/` obsluhuje všechny články své složky, takže by mezi nimi kolidoval. Doporučený rozměr je 630x290. Jiný rozměr se nepředělává - ořez a vycentrování obstará CSS v prohlížeči (`object-fit: cover`, horní část zůstane), takže generátor nepotřebuje knihovnu na obrázky.

**K70. Konfigurace webu leží ve složce `.obsidian2html/` nebo `_obsidian2html/`** v kořeni vaultu. Obsahuje (abecedně):
- `config.toml` - název, jazyk a adresa webu, viz níže.
- `index.md` (ruční úvod na titulce) - vykreslí se na všech stránkách.
- `logo.svg` - logo vlevo nahoře. Klikatelné (home).
- `menu.md` (kurátorovaná lišta) - určuje pořadí tagů. Pokud není tak je abecední.
- `styl.css` (vlastní styly)

Obě jména jsou rovnocenná a liší se jen tím, co s nimi dělá Obsidian.  
Tečka složku v Obsidianu skryje, takže vstupy pro generátor nepletou strom článků a editují se mimo Obsidian.  
Podtržítko ji nechá vidět, takže úvod titulky a lištu jde psát tam, kde se píše všechno ostatní.  
Na web se nedostane ani jedna, obě přeskočí K20.  
Název říká, ke kterému nástroji ta složka patří, takže vedle `.obsidian/` nevzniká nejasnost.  
**Obě složky naráz jsou chyba a build se zastaví**, ještě před vyprázdněním cíle (Z55).  
Přednost by znamenala, že jedna z nich se tiše ignoruje a úprava v ní nikam nevede.  
Když složka ve vaultu není, generátor si poradí bez ní.

`config.toml` je textový soubor ve formátu [TOML](https://toml.io): na každém řádku `klíč = hodnota`, text v uvozovkách, komentář za `#`.  
Python ho čte sám, takže nepřibývá závislost.

```toml
name = "Pan Kostka"                 # název webu
lang = "cs"                         # jazyk webu, cs nebo en (K100)
base_url = "https://pankostka.cz"   # adresa webu, bez ní nevznikne rss.xml
```

- `name` - název webu vlevo nahoře (u loga jako jeho alternativní text), v titulku každé stránky a v RSS. Výchozí je jméno složky vaultu.
- `lang` - jazyk ovládání webu podle K100. Výchozí je `cs`.
- `base_url` - absolutní adresa, na které web poběží. Potřebuje ji jen RSS, protože čtečka kanál čte jinde a relativní odkaz by tam nikam nevedl. Bez ní `rss.xml` nevznikne.

Každý klíč smí chybět a pak platí výchozí hodnota, chybět smí i celý soubor.  
**Neznámý klíč nebo neplatná hodnota je chyba** a build se zastaví - překlep v `nmae` by jinak tiše vyrobil web se jménem složky.  
Údaje o webu patří do vaultu, ne do přepínačů: jsou to vlastnosti webu jako logo nebo menu, nemění se build od buildu a dávka pak řeší jen odkud, kam a co.

**K80. Publikovaný článek by měl mít ve frontmatteru `date`.** Když ho nemá, použije se datum souboru. Je to vratké, protože datum souboru se mění při kopírování i při synchronizaci, ale je to jednoduché a nepotřebuje to git - ten ve vstupním adresáři fungovat nemusí. Při shodě dat rozhoduje název článku, aby bylo pořadí jednoznačné.  Tvar `RRRR-MM-DD` se kontroluje a build na cokoli jiného upozorní (třeba datum šablony `{{date:YYYY-MM-DD}}`)

**K90. Klíče frontmatteru, konfigurace a přepínače jsou anglicky.** Tedy `date`, `title`, `excerpt`, `slug`, `tags`, v `config.toml` `name`, `lang`, `base_url`, a přepínače `--source`, `--dest`, `--publish`, `--check`, `--keep-archives`. Obsah článků je česky, rozhraní nástroje ne - nástroj je veřejný a jeho příkazová řádka i klíče jsou to jediné, co cizí uživatel musí napsat sám. České klíče `datum`, `titul` a `perex` se už nečtou; když na ně build narazí, ohlásí to, protože jinak by článek tiše přišel o datum nebo titulek.

**K95. Hierarchický tag `Obsidian/Video` se rozpadne na dva samostatné tagy.**  
Vzniknou z něj `Obsidian` a `Video`, každý se svou stránkou, takže `Video` sbírá videa z celého vaultu, ne jen ta u Obsidianu - a přesně podle toho chce člověk filtrovat.  
O tom, který tag je hlavní, hierarchie nerozhoduje, to říká značka podle K97.

**K97. Tag s podtržítkem na začátku je hlavní**, tedy `_Obsidian` proti běžnému `Obsidian`.  
Ve filtru na titulce vede první řadu, všechno ostatní jde do druhé; obě řady jsou abecedně.  
Podtržítko je jen značka, ne část jména: tag se pořád jmenuje `Obsidian`, má stránku `tag-obsidian.html` a v článku se vypíše bez něj.  
Který tag je důležitý, tedy říká vault na místě, kde se článek taguje, ne konfigurace webu - povýšit tag znamená napsat jeden znak, ne editovat soubor navíc.  
Podtržítko se navíc řadí před písmena, takže hlavní tagy drží pohromadě i v seznamu tagů uvnitř Obsidianu.  
U hierarchie se posuzuje **každá část zvlášť**: `_Obsidian/Video` povýší `Obsidian`, `Obsidian/_Video` povýší `Video`.  
Protože `_Obsidian` a `Obsidian` je jeden tag, stačí značka u jednoho výskytu a tag vede - build ale vypíše články, které ji nemají, protože ze zápisu se nedůslednost nepozná.  
Kurátorovaný `menu.md` řídí lištu v hlavičce, do filtru nemluví; značku v něm psát netřeba, a když se tam zkopíruje, přeskočí se.

**K100. Jazyk webu určuje klíč `lang` v `config.toml`, výchozí je `cs`.** Lokalizuje se jen to, co vidí **návštěvník** - hlášky při buildu čte ten, kdo build spouští, a ty jsou anglicky vždycky.  
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

**Z60. Přílohy se na webu ukládají malými písmeny v ASCII.** Na Linuxu je `Foo.png` a `foo.png` rozdíl, takže špatně napsaný odkaz funguje na Windows a na serveru vrátí 404. Velikost písmen v odkazech se navíc ověřuje proti skutečným souborům a kolize adres je chyba.

**Z70. Filtr přežije kliknutí do článku.**  
Lišta v hlavičce článku je tentýž fasetový filtr jako na titulce, ne řádek odkazů, a stav si čte z adresy - odkaz z výpisu ho s sebou nese.  
Kdo si zafiltroval na `#Obsidian` a otevřel článek, má `#Obsidian` v hlavičce dál a další kliknutí ho vrátí do výpisu s tím filtrem, ne do celého webu.  
Do článku se přitom zapékají jen **tagy** článků, ne index hledání: čísla na štítcích jsou jediné, co ta stránka počítá, a index by se platil na každém načtení článku.  
Textový dotaz s sebou nejede, jede jen filtr - článek nemá výpis, ve kterém by se hledalo, a čísla na štítcích by pak odpovídala na jinou otázku než ta na titulce. Dotaz napsaný v hlavičce článku ale filtr zachová, protože ho formulář pošle na titulku s sebou.  
Bez JavaScriptu zůstává v `<noscript>` původní statická lišta s odkazy na stránky tagů, takže Z10 platí dál.  
Stránky tagů zůstávají statické: jejich výpis se v prohlížeči nepřekresluje, takže živý filtr nad ním by lhal.

**Z80. Když klik na štítek nechá jedinou stránku, otevře ji.**  
Je to kliknutí na kartu udělané za čtenáře, takže vede na tutéž adresu, jakou nese karta, i s filtrem.  
Stav je v adrese dřív, než se odejde, takže tlačítko zpět vrací tam, odkud se kliklo.  
Skok patří **kliku, ne stavu**: adresa `index.html?tag=a&tag=b` zůstává výpisem, i když vrací jediný článek, aby odkaz poslaný ven přistál tam, co vždycky.  
Skáče jen **jméno** štítku, a jen když se zapíná. Čtvereček zužuje osu, nevybírá článek, a zhasnutí jména výsledek naopak rozšiřuje.  
Textový dotaz do toho mluví jen tím, že zužuje množinu, ve které se počítá.  
Skáče titulka i lišta v hlavičce článku.  
Článek k tomu nese vedle sad štítků i adresy článků, jinak by věděl, že výsledek je jeden, ale ne který.  
Číslo `1` na štítku to říká dopředu, takže se k němu nic dalšího nekreslí.

## Licence

MIT - viz [LICENSE](LICENSE).
