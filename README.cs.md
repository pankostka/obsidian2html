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
* Generovat PDF - původně bylo součástí, ale podle mě to má být samostatný nástroj.
* Publikovat na FTP - toto by měl taky řešit jiný nástroj.

Proč Obsidian?
* Umí skvěle editovat MD.
* Je zdarma.


## Konvence

Jádro dokumentu. Každá konvence se popisuje třemi věcmi: co vynucuje, jak se pozná ve vaultu, a proč je právě takhle. Bez toho třetího se první nepohodlnou výjimkou obejde.

Konvence jsou dvojího druhu.  
**Vaultové** říkají, co musí splnit autor, aby generátor věci našel.  
**Záruky** říkají, co za to nástroj slibuje. Rozdíl je podstatný: vaultovou konvenci lze změnit dohodou, záruku ne, protože na ní stojí důvěra ve výstup.

Značka **[?]** označuje konvenci, u které je otevřená otázka do kroku revize.

### Vaultové konvence

**1. Příznak publikace je marker v názvu souboru.** Článek končící globusem (`Název článku 🌐.md`) jde ven, ostatní ne. Chybějící marker znamená neveřejné, takže se zveřejňuje vědomým úkonem, nikdy opomenutím. Důvod je viditelnost: ve stromu souborů je vidět, co je veřejné, kdežto frontmatter vidět není. Mechanismus je záměrně **jediný** - kdyby vedle markeru fungoval i klíč `publish`, přestalo by platit, že chybějící marker znamená neveřejné. Klíč `publish` se proto ignoruje, ale když ho článek bez markeru má, build to ohlásí; autor si nejspíš myslí, že článek publikuje.

**2. Titulek je název souboru.** Ne nadpis `# H1`. Vyzkoušeno a neplatí to: nápověda k datamartu má jediné H1 a je to opravdu titulek, ale článek ze šablony tasku má taky jediné H1 a je to `# Popis`, tedy sekce ze šablony. Stejná struktura, jiný význam, strojově nerozlišitelné. Název souboru je Obsidianův model, je jednoznačný v rámci složky a dá se předpovědět. Klíč `titul` ho přebije tam, kde je název technický.

**3. Perex je první odstavec.** Bere se proto, že už je napsaný - články tak začínají a délky vycházejí na 70 až 230 znaků, tedy přesně perexové. Hledání ukončuje nadpis: když článek začíná rovnou sekcí, perex není první věta té sekce, ale žádný. Klíč `perex` ho přebije.

**4. Náhledový obrázek se jmenuje jako článek.** Leží v `Attachments/` vedle článku. Porovnává se přes slug, takže sedne `Obsidian Co je.png`, `obsidian-co-je.png` i `obsidian_co_je.png` - standard chce přílohy malými písmeny s podtržítkem, kdežto článek má mezery a diakritiku, a tolerance obě konvence smiřuje, místo aby nutila jednu porušit. **[?]** Zvážit variantu s pevným názvem (`perex.png` ve složce článku) a definovanou velikostí. Pojmenování podle článku váže přílohu na název, který se může změnit; pevný název je stabilnější, ale nejde mít dva náhledy vedle sebe.

**5. Přílohy leží v `Attachments/`.** Hledá se v pořadí: vedle článku, v jeho složce příloh (`Attachments`, `img`, `assets`), pak v celém vaultu - stejně jako to dělá Obsidian. **[?]** Tři názvy složky jsou tolerance navíc; `dokumentace_JD.md` připouští jediný. Zvážit zúžení na `Attachments`.

**6. Adresář `_web/` je konfigurace, ne obsah.** Drží `menu_webu.md` (kurátorovaná lišta), `index.md` (ruční úvod na titulce), `styl.css` (vlastní styly), `logo.svg` a `vydano.md` (evidence vydaných adres). Podtržítko na začátku vyřazuje složku ze sběru článků, takže se z těch souborů nikdy nestane stránka. Lišta se jmenuje `menu_webu.md` proto, že `menu.md` je ve vaultu obsazené navigací samotného vaultu a dva soubory téhož jména se v Obsidianu pletou.

**7. Publikovaný článek musí mít `datum`.** Bez něj nejde určit pořadí na titulce a build spadne. Je to jediný povinný klíč frontmatteru.

**8. Složka začínající tečkou nebo podtržítkem se přeskakuje.** Spolu s bodem 6 to dává jednoduché pravidlo: co má být mimo web, dostane podtržítko.

### Záruky

**9. Mrtvý odkaz nikdy nevznikne.** Když cíl odkazu není v dávce, zbyde z něj holý text a skript ohlásí kolik. Dokument jde uživateli, a odkaz, který nikam nevede, je horší než žádný.

**10. Adresa se počítá, nepřebírá.** Slug je název souboru malými písmeny, bez diakritiky, bez emoji, mezery na pomlčky. Název článku smí mít cokoli, URL ne. Marker publikace se do adresy nepropíše. Klíč `slug` je únikový východ pro jedinou adresu, na které záleží i po přejmenování.

**11. Uvnitř bloku kódu se nenahrazuje nic.** Bez toho si převodník přepíše vlastní ukázky syntaxe: článek, který učí psát wikilinky, má `[[Název]]` jako kód, ale generátor by v něm viděl odkaz, cíl nenašel a zploštil ho na text. Čtenář by se z článku o závorkách dozvěděl všechno kromě těch závorek.

**12. Chybějící obrázek je chyba, ne varování.** V tichosti by vznikl dokument s prázdným místem a odešel uživateli.

**13. Vlastní styly se připojují, nenahrazují.** `_web/styl.css` jde za vygenerované CSS, takže přepsat jde cokoli. Barvy jsou tokeny v `:root`, takže změna je jedna řádka a nesahá se do generátoru.

**14. Výstup patří mimo repo.** Aby commit vygenerovaného HTML nebyl možný, ne jen zakázaný, a aby generátor neskenoval adresář, do kterého zapisuje. Smazat smí skript jen adresář se značkou `.vygenerovano`, takže překlep v cestě cizí složku nesmaže. **[?]** Výchozí kořen je dnes napevno `c:\_web`, což je cesta na jeden konkrétní stroj. Musí se zparametrizovat.

**15. Vydané adresy se evidují.** Každá adresa, která šla ven, se zapíše do `_web/vydano.md` s datem. Když se přestane vyrábět, build to ohlásí - je to adresa, kterou už někdo možná má v záložkách.

**16. Přílohy se na webu ukládají malými písmeny v ASCII.** Na Linuxu je `Foo.png` a `foo.png` rozdíl, takže špatně napsaný odkaz funguje na Windows a na serveru vrátí 404. Velikost písmen v odkazech se navíc ověřuje proti skutečným souborům a kolize adres je chyba.

### Otevřené otázky mimo jednotlivé konvence

- **Lokalizace.** Rozhraní i generovaný web jsou dnes česky. Vyřešeno bude v kroku 6: rozhraní anglicky, výstup lokalizovaný s `cs` jako výchozím.
- **Tagy.** `dokumentace_JD.md` chce PascalCase a jednu variantu na tag, protože generátor je porovnává jako řetězce. Není to ale nikde vynucené ani ohlášené.

## Co to záměrně nedělá

## Proč Python
