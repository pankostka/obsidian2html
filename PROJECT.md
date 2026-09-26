# PROJECT

Pracovní dokument. Co se dělá, co zbývá, co se už zkusilo. Důležité nahoře, slepé cesty dole.

**Konvence nástroje nejsou tady, jsou v [SPEC.cs.md](SPEC.cs.md).** Ten je autoritou; když si kód a konvence odporují, chyba je v kódu. Tady je jen práce kolem.

## Stav

Repozitář je **publikovaný** na GitHubu jako veřejný `pankostka/obsidian2html`, licence MIT, držitel práv `pankostka.cz`. Historie je tím veřejná, proto jsou kód i commit zprávy anglicky.

Skript přišel z `_JDStandards`, kde nepatřil - to repo drží pravidla, tohle je nástroj. Do cílových rep se nekopíroval, takže přesunem se nic nerozbilo. **V `_JDStandards` zatím pořád leží** (`md2html.py`) a měl by se odtamtud smazat, když tenhle repozitář už běží.

Historie se nepřenášela, začalo se od aktuálního stavu.

## Úkoly

Pořadí je záměrné: nejdřív to, co mění tvar nástroje, pak rozpory mezi konvencemi a kódem, pak jazyk, nakonec publikace.

### 1. Vyříznout PDF - HOTOVO

Odešlo `na_pdf`, `najdi_prohlizec`, `pockej_na_soubor`, `PROHLIZECE`, `CSS_TISK`, přepínače `--pdf`, `--vedle`, `--footer`, `--landscape` a `--browser`, parametr `landscape` funkce `na_html` a `import subprocess`. Skript zhubl o 142 řádků a ztratil závislost na Edge a Chrome.

`CSS_TISK` nedržel jen `@media print`, ale i styl `.paticka`, který používá samostatný HTML - ten se přesunul do `CSS_OBSAH`.

Ověřeno porovnáním: PKVault postaven oběma verzemi ze složek stejného jména, všech 18 stránek bajt za bajtem shodných.

Tisk v prohlížeči teď vytiskne stránku i s hlavičkou a lištou. Vědomě přijato.

### 2. Srovnat kód s konvencemi - HOTOVO

| Konvence | Stav |
|---|---|
| **Z45** ze vstupu se jen čte | **hotovo** |
| **Z50** kořen výstupu parametrem | **hotovo** |
| **K80** datum souboru jako záloha | **hotovo** |
| **K70** složka `.obsidian2html/` | **hotovo** |

Do vaultu zapisovala **dvě** místa, ne jedno. Vedle evidence vydaných adres to byla `doplnit_datum`, která dopisovala datum přímo do frontmatteru článku; její docstring přitom tvrdil, že jiné takové místo není.

Evidence vydaných adres zrušena celá. `doplnit_datum` nahrazena funkcí `datum_souboru`, která jen čte. Konstanta `KOREN_WEBU` pryč, `--web` bez `-o` končí s kódem 2.

Cesta ke konfiguraci už není roztroušená po kódu, drží ji konstanta `KONFIG`. Lišta se vrátila k názvu `menu.md`, podpora starého názvu odešla. Starou složku `_web` build nečte, ale ohlásí ji - jinak by se web postavil bez loga, lišty i stylů a vypadalo by to jako chyba generátoru.

Ověřeno: výstup PKVaultu shodný bajt za bajtem, otisk vaultu před buildem a po něm totožný.

PKVault je zmigrovaný (`8aef5b9`): `_web` přejmenováno na `.obsidian2html`, `menu_webu.md` na `menu.md`, `vydano.md` smazáno.

Při ověřování se ukázala drobná vada, opravena hned: kurátorovaná lišta smí jmenovat tag, který žádný publikovaný článek nemá, a takový odkaz se zplošťoval na holý neostylovaný text mezi stylovanými pilulkami. Záruka Z10 platila, mrtvý odkaz nevznikl, ale řešilo se to až dodatečně nad hotovým HTML. Teď se štítek ztlumí rovnou při generování lišty a build to ohlásí.

### 3. Testy - HOTOVO

52 testů v `test_md2html.py`, spouští se `python test_md2html.py`, běží pod sekundu a nepotřebují nic nad rámec toho, co potřebuje generátor.

Zadáním jsou konvence ze `SPEC.cs.md`, ne implementace. Název testu začíná kódem konvence, takže když spadne, rovnou říká, která věta přestala platit.

Několik testů je záměrně v párech: vedle mrtvého odkazu se ověřuje i živý, vedle náhledu podle názvu i příloha s názvem jiným. Bez protějšku by testu vyhověl i generátor, který zplošťuje nebo zobrazuje úplně všechno.

**Hned našly regresi**, kterou zavlekl krok 2. Chybějící datum se bralo ze souboru, ale `na_html` si frontmatter četla znovu ze zdroje, takže o dopočítaném datu nevěděla: datum se objevilo na titulce a v řazení, v patičce článku ne. Dokud se datum zapisovalo do zdroje, rozpor nemohl nastat. Nikdo by si toho nevšiml, protože všechny články PKVaultu datum mají.

### 4. Vnitřek do angličtiny - HOTOVO

Hotovo: **1044 identifikátorů** - názvy funkcí, tříd, konstant a proměnných.

Přejmenovával **tokenizér, ne hledání v textu**. Spousta českých slov v tom souboru nejsou jména, ale výstup: `class="perex"`, `class="karta"`, `hledani.html`. Hledání v textu by je přepsalo a rozbilo `styl.css` ve vaultech, tedy Z40. Druhá pojistka je na `args.*` - ta jména vyrobil argparse z přepínačů.

Testy hned našly chybu: `HTML_WEB.format` předával argument `hlavicka`, jenže zástupný symbol `{hlavicka}` uvnitř šablony je řetězec a přejmenování se ho správně netklo.

Hotové jsou i **vnitřní klíče slovníků a vložený JavaScript** (`30f4a5f`). Muselo to jít naráz, index hledání je společné rozhraní obou stran. JS blok jsem přepsal celý místo čtyřiceti záměn: `karta`, `stitek`, `vybrany`, `perex` a `vypis` jsou současně názvy proměnných i CSS tříd, takže záměna po slovech by se dřív nebo později trefila do třídy.

České zůstávají **záměrně** CSS třídy, id prvků a texty pro čtenáře - na ně se váže `styl.css` ve vaultech.

Ověřeno i v prohlížeči, protože testy JavaScript nespouští: fasetový filtr, kombinace s dotazem, zvýrazňování, skládání diakritiky i zápis stavu do adresy.

Přeloženy i **komentáře a docstringy** (`0712dcc`, `312d13d`, `9311c3d`), po sekcích s testy po každé. České jsou už jen řetězce, které čte člověk.

Cestou vypadly dvě chyby, které testy samy nenašly. `site_inputs` inicializovala `titul`, přiřazovala do `home_title` a vracela `titul`, takže **vlastní titulek titulky z `index.md` se zahazoval** - vzniklo to při přejmenování klíčů v kroku 5 a test na to teď je. A hláška při `--site` bez `-o` pořád mluvila o `--web`.

### 5. Rozhraní do angličtiny - HOTOVO

Konvence **K90**. Přepínače `--title`, `--published-only`, `--site`, `--base-url`, `--check`, `--clean`, `--site-name`, poziční `input`. Klíče frontmatteru `date`, `title`, `excerpt`; `slug`, `tags` a `publish` anglické už byly.

Staré české klíče se nečtou, ale build je ohlásí - jinak by článek tiše přišel o datum nebo titulek. Stejný vzor jako u přejmenované složky `_web`.

PKVault zmigrován (`551eea5`, `f520cd2`): deset článků, jen klíč `datum` na `date`. Web je proti stavu před zásahem shodný bajt za bajtem.

### 5b. Hlášky do angličtiny - HOTOVO

38 hlášek (`b2dfa0d`): chyby, varování i výpis průběhu. Čte je týž člověk, který čte `--help`, takže patří ke krokům 5, ne k lokalizaci.

Pětice testů ověřovala české řetězce a správně spadla.

### 6. Lokalizace výstupu - HOTOVO

Konvence **K100**, přepínač `--lang`, výchozí `cs` (`31148a2`).

Součástí jazyka jsou i **názvy stránek**: český web má dál `hledani.html`, anglický dostane `search.html`. Adresa, která je jednou venku, je závazek.

Skloňování řeší `Intl.PluralRules` v prohlížeči, takže v kódu nejsou žádná pravidla na počítání - tabulka nese jen tvary. Vedlejším účinkem se opravila čeština: původní kód měl u nalezených výsledků jen dva tvary a říkal „3 nalezených", teď říká „3 nalezené".

Ověřeno: z osmnácti stránek PKVaultu se s výchozím `cs` liší jediná, `hledani.html`, a to jen o nový mechanismus. Obě jazykové verze proklikány v prohlížeči. 52 testů.

### 7. Publikace

Vyrobit `README.md` překladem z `README.cs.md`. Založit repozitář na GitHubu, pushnout, smazat `md2html.py` z `_JDStandards`.

`gh` ani `git filter-repo` na stroji nejsou. `gh` se dá doinstalovat, nebo se prázdný repozitář založí ručně přes web.

### 8. Štítek se zaškrtávátkem - HOTOVO

Štítek na `hledani.html` je nově dvojice ovladačů v jedné pilulce: **zaškrtávátko tag drží** ve filtru, **jméno prohlíží** - nastaví jeden tag navíc a další kliknuté jméno ho vystřídá. Filtr je průnik obojího, takže se dá držet `#Obsidian` a proklikat se jeho podmnožinami, aniž by se `#Obsidian` pokaždé obnovoval.

Podstatné je, že **žádný z těch dvou ovladačů nesahá na stav toho druhého**. Zaškrtávátko, které by se odškrtlo proto, že se kliklo na souseda, slibuje nezávislost, kterou nedodrží.

Do adresy přibyl parametr `pick` pro prohlížený tag; `tag` zůstal pro držené. Odkaz ze statické stránky tagu nese jen `tag`, takže se to, co přinesl, drží - jinak by první kliknutí smazalo obojí.

Číslo na štítku teď znamená **kolik bude vidět po kliknutí na jméno**, tedy držené plus tenhle. Na tagu, který už ve filtru je, žádné číslo není - odpovídalo by na jinou otázku než číslo na sousedovi. Zhasnutý štítek má zakázané i zaškrtávátko, jinak by se dalo držením spadnout do prázdného výsledku, což je celá pointa tlumení.

Zkoušelo se a zahodilo: **Ctrl+klik** jako přidávání (na Macu koliduje s kontextovým menu a nikdo ho neuhodne), **jedno zaškrtávátko na celou lištu** ve smyslu "kombinovat tagy" (režim, který se nehledá tam, kde je potřeba) a varianta, kde klik na jméno odškrtává cizí čtverečky (viz odstavec o nezávislosti). Rozhodovalo se nad klikací maketou všech variant.

Ověřeno v prohlížeči nad PKVaultem: držení, střídání, čtení stavu z adresy, kombinace s textovým dotazem, zrušení filtru. Porovnání staré a nové verze říká, že se liší jen `hledani.html` a `styl.css`, ostatních 17 stránek je bajt za bajtem shodných.

### 9. Dvě řady štítků - HOTOVO

Filtr kreslí štítky do dvou řad: **co nese kurátorovaná lišta, vede**, zbytek jde pod ni abecedně. Prázdná řada se nekreslí. Rozdělení v kódu už bylo, `search_page` skládala štítky přesně takhle za sebe; přibyl jen příznak `lead` a druhý `div`.

Důležitost se tedy říká **v `menu.md`, ne v názvu tagu**. Zvažovaly se VELKÁ PÍSMENA a zahodily se: jméno tagu se ukazuje i na kartách a v patičce, Obsidian bere jinou velikost písmen jako druhý tag (přesně to riziko, které mají otevřené otázky zapsané), a povýšit nebo degradovat tag by znamenalo přepsat každý článek, který ho nese. V `menu.md` je to přesun řádku.

Pseudotag `#` (bez tagu) uzavírá druhou řadu, i když ho lišta jmenuje. Není to osa, podle které se filtruje záměrně, je to zbytek.

Mezera před výsledky patří **poslední vykreslené řadě**, což se řeší třídou `posledni` z JavaScriptu - `:has()` by to uměl taky, ale tohle je jistota. Obsluha kliknutí visí na obou řadách, protože tlačítko "zrušit filtr" sedí v té poslední, která existuje.

Ověřeno v prohlížeči na kopii PKVaultu s ořezanou lištou: dvě řady, jen důležité, jen ostatní, a zrušení filtru z druhé řady.

### 10. Filtr je titulka, hledání jako stránka zrušeno - HOTOVO

Titulka je nově ta stránka, co bývala `hledani.html`, a `hledani.html` se negeneruje. Důvod je, že tatáž pilulka dělala na dvou stránkách dvě různé věci: v hlavičce vedla na statickou stránku tagu, ve filtru filtrovala živě. Jedno místo, kde se hledá článek, je lepší než dvě, která se chovají jinak.

Pořadí na titulce: hlavička, filtr, **čára**, ruční úvod z `index.md`, výpis. Čáru drží obal `div.filtr`, hlavička ji na téhle stránce nemá (`bez-linky`) - je tedy pod tagy stejně jako na ostatních stránkách, jen jsou nad ní tagy živé místo statických. Když vault nemá ani jeden tag, sedne čára rovnou pod hlavičku, tam kde byla vždycky.

Co odešlo: **stránkování titulky** (`index-2.html` a dál), protože výpis kreslí skript a co stránku zužuje, je filtr, ne číslo stránky. Dál klíče `search` a `search_file` z obou jazyků, odkaz "Hledání" z patičky (vedl by na titulku, kde už jsme) a parametr `intro` funkce `card_grid`, který po odstranění titulky z jejího seznamu nemá kdo naplnit.

Bez JavaScriptu ukazuje titulka **tutéž mřížku karet** s perexy a náhledy, jen celou a nefiltrovanou. Dřív měla `hledani.html` v `noscript` holý seznam názvů, ale na titulce by to byla ztráta.

Stránky tagů zůstávají statické a beze změny. Jsou pro odkazy zvenčí a pro vyhledávače, kde skript spolehnout nejde, a jejich štítky teď vedou do filtru na titulce (`index.html?tag=a&tag=b`).

Stará adresa `hledani.html` se **nezachovala ani jako přesměrování**, vědomé rozhodnutí - repozitář je zatím lokální a web nikde nevisí, takže není co lámat. Kdyby se to publikovalo dřív, chtělo by to přesměrování.

Testy padly na dvě věci, které stojí za zapsání. Titulka nese zapečený index s **celým textem** článků, takže test na perex nesmí říkat "druhý odstavec na titulce není" - je tam, jen ho nikdo nevidí; ověřuje se pole `excerpt` a karta. A skript titulky obsahuje řetězce `class="nahled"` i `<p class="perex">`, takže `assertNotIn` na ně projde vždycky a nic netestuje - i tady rozhoduje pole indexu.

Ověřeno v prohlížeči nad PKVaultem i nad kopií s ořezanou lištou a ručním úvodem: pořadí prvků, čára pod tagy, filtr, stránka tagu i cesta z ní zpátky do filtru.

### 11. Nulový štítek se nekreslí - HOTOVO

Změna záměru, ne oprava. Dosud se štítek, který by nic nevrátil, **ztlumil**, a bylo to tak zapsané i v hlavičce skriptu s odůvodněním, že jinak lišta poskakuje. Nově se **nekreslí vůbec** - zbyde jen to, kam se dá jít, a oko má míň co třídit.

Ta původní obava platí dál, jen se řeší jinde: pod živou lištou leží její **neviditelný duch v plné podobě** (všechny tagy, nic odfiltrované) ve stejné buňce gridu. Výšku bloku určuje ten vyšší z obou, tedy vždycky duch, takže se výpis pod filtrem nehne, ať se lišta zúží jakkoli. Je to čisté CSS, žádné měření - první pokus výšku měřil a ukázalo se, že stačí jedno měření v nesprávnou chvíli (než se stihne uplatnit `styl.css`, nebo při šířce, kterou nikdo nečekal) a v hlavičce zůstane díra napořád.

Tlačítko "zrušit filtr" se kreslí pořád, jen je při prázdném filtru neviditelné. Objevit se až při prvním kliknutí znamenalo posunout lištu o řádek a výpis s ní, což byl mimochodem jediný skok, který zbyl po zavedení ducha.

Duch se kreslí týmž kódem jako lišta (`facetRows`), aby se nemohly rozejít, jen mu `paintGhost` sebere `id` u tlačítka - dvě stejná `id` v jednom dokumentu jsou rozbité HTML.

Stránky tagů zůstávají u **ztlumení**. Nemají skript, který by lištu překreslil, takže nemůžou vědět, co bude další klik; říct, co je dosažitelné, je tam užitečnější než schovat, co není. Záruka Z10 se tím nehnula, jen ji teď test hledá na stránce článku.

Ověřeno v prohlížeči: po zaškrtnutí `#Obsidian` zmizely čtyři nulové štítky a čára, úvod i první karta zůstaly na stejném pixelu.

### 12. Hlavní tag říká hierarchie, ne menu.md - HOTOVO

Konvence **K95**. Hierarchický tag `Obsidian/Video` se rozpadne na dva samostatné tagy, `Obsidian` a `Video`, každý se svou stránkou. Kdyby zůstal jeden, `Video` by sbíralo jen videa u Obsidianu, a to není osa, podle které chce člověk filtrovat napříč vaultem.

Hierarchie tehdy určovala i hlavní tag: **první část je hlavní tag** a vede první řadu filtru. To už neplatí, hlavní tag říká podtržítko podle kroku 14. Vystřídalo to `menu.md`, které tu roli drželo od kroku 9. Rozdíl je v tom, kdo to říká - dřív konfigurace webu, teď vault na místě, kde se článek taguje. Povýšit tag znamená napsat lomítko, ne editovat soubor navíc.

Obě řady jdou **abecedně**. Kurátorované pořadí se sem nemá odkud vzít a mezi dvaceti štítky je abeceda jediný pořádek, který čtenář uhodne. `menu.md` dál řídí lištu v hlavičce, do filtru nemluví.

Rozpad se děje **v `tags_from_meta`**, tedy hned při čtení frontmatteru, takže se projeví všude stejně: stránky tagů, patička článku, karty i zapečený index. Hierarchii si pamatuje `lead_tags`, která z původního zápisu vytáhne první části, a `site['lead_tags']` je nese do filtru.

Vedlejší důsledek, který ukázal test: tag, který jmenuje lišta a nemá článek, **ve filtru na titulce už není vůbec**. Štítky se berou z tagů článků, a štítek s nulou se stejně nekreslí. V liště se dál ztlumí a build to dál hlásí, takže Z10 platí, jen se ověřuje na stránce článku.

**PKVault zatím hierarchii nemá**, takže mu vyjde první řada prázdná a všech šest tagů spadne do druhé. Není to chyba, prázdná řada se nekreslí - ale dvě řady tam budou vidět, až se ve vaultu objeví první `Neco/Neco`.

### 14. Hlavní tag říká podtržítko, ne hierarchie - HOTOVO

Krok 12 nechal hlavní tag určovat hierarchii: první část `Obsidian/Video` vedla první řadu. Fungovalo to, ale říkalo se to vedlejším efektem. Autor psal lomítko, aby vyjádřil vztah, a nástroj z toho četl něco o titulce - a ten vztah pak stejně zahodil. Bylo to i křehké v množství: stačil jeden článek s lomítkem a tag vedl globálně, zatímco dvacet dalších o tom nevědělo a nikdo to neřekl.

Konvence **K97**. Hlavní tag je ten, který má na začátku **podtržítko**, `_Obsidian`. Značka není součástí jména, strhává se v `bare_tag` hned při čtení, takže tag se pořád jmenuje `Obsidian`, má stránku `tag-obsidian.html` a v patičce článku se vypíše bez ní. `lead_tags` vrací tagy se značkou, `site['lead_tags']` je nese do filtru, zbytek zůstal jak byl.

Zvažovaly se **velká písmena** a **číslo na začátku**. Velká písmena padla na zkratkách, `#DWH` a `#SQL` jsou velké přirozeně a staly by se hlavními omylem, a hlavně na tom, že Obsidian tagy porovnává bez ohledu na velikost - značka, kterou nástroj pod tebou nevidí, není značka. Číslo (`#1-Obsidian`) by šlo a škáluje na víc úrovní, ale slibuje škálu, která nebude: řady jsou dvě a uvnitř abecedně, takže `2-` a `3-` by nikdy nic neudělaly. Podtržítko je přesně tak velké jako ta myšlenka, ano/ne, a nekoliduje s tagy jako `#2024` nebo `#3D`.

Značka se posuzuje **na každé části hierarchie zvlášť**, `Obsidian/_Video` povýší `Video`. Hierarchie tím přestala hlavní tag určovat a zbylo jí to, co dělá poctivě: rozpad na osy, podle kterých se filtruje napříč vaultem. Z jednoho spleteného pravidla jsou dvě nezávislá.

Protože `_Obsidian` a `Obsidian` je jeden tag, **stačí značka u jednoho výskytu**. Mlčet o zbytku by ale znamenalo totéž, co vadilo na hierarchii, takže build vypíše, ve kterých článcích značka chybí - stejný vzor jako u ztlumeného odkazu v liště.

`menu.md` značku nepotřebuje a `bare_tag` ji strhne i tam, aby zkopírovaný `#_Obsidian` mířil na tutéž stránku.

**PKVault značku zatím nemá**, takže mu první řada vyjde prázdná a všech šest tagů spadne do druhé. Prázdná řada se nekreslí, takže se do vaultu podtržítko doplní, až se rozhodne které tagy vedou.

### 15. Filtr i v hlavičce článku - HOTOVO

Záruka **Z70**. Lišta v hlavičce článku byla řádek statických odkazů na stránky tagů, zatímco titulka měla fasetový filtr - dvě různé věci na tomtéž místě, a při kliknutí do článku navíc filtr zmizel. Nově je v hlavičce článku **tentýž filtr**, kreslený tímtéž kódem, a **stav si čte z adresy**: odkaz z výpisu nese `?tag=` i `?pick=`, takže co si čtenář zafiltroval, to v hlavičce článku zůstává stát.

Kliknutí na štítku článku nemá co překreslit, tak **odchází na titulku** s novým stavem. Tím je pilulka na obou stránkách stejná i významem: čtvereček drží, jméno prohlíží.

**Zapékají se jen tagy článků, ne index hledání.** Čísla na štítcích jsou jediné, co ta stránka počítá, a index by se platil kilobajty při každém načtení článku. Z toho plyne i to, že **textový dotaz s sebou do článku nejede** - článek nemá výpis, ve kterém by se hledalo, a čísla by pak odpovídala na jinou otázku než ta na titulce. Dotaz *napsaný* v hlavičce článku ale filtr zachová: skript ho vloží do formuláře jako skrytá pole a titulka ho přebere.

Společná část skriptu se vyřízla do `FACET_JS` a obě stránky ji vkládají. Nešlo o úsporu řádků, ale o to, že dvě kopie téhož filtru se dřív nebo později rozejdou - a rozdíl by byl vidět jako poskakující lišta mezi výpisem a článkem. Vedle toho ubyla druhá kopie skládání štítků: `filter_chips` je teď jedna a používá ji titulka i článek.

Lišta v článku stojí **na tomtéž místě, kde má filtr titulka** - stejná mezera nad ní i pod ní. Titulka totiž mezeru nad filtrem platí dvakrát (`.8rem` prázdná lišta v hlavičce, `.9rem` spodní mezera hlavičky), kdežto článek nemá ani jedno, takže si je sečte třídou `s-filtrem`. Bez toho lišta mezi titulkou a článkem viditelně poskočí, a to je přesně ta věc, kterou oko pozná dřív, než ji pojmenuje. Třída na `<nav>` se jmenuje `zivy`, ne `filtr`: `filtr` už patří obalu na titulce a nesl by s sebou druhou čáru pod lištou.

Bez JavaScriptu zbyde v `<noscript>` **původní statická lišta** i se ztlumeným štítkem, takže Z10 platí beze změny.

Stránky tagů zůstaly statické. Jejich výpis se v prohlížeči nepřekresluje, takže živý filtr nad ním by ukazoval jiné štítky, než jaké karty pod ním leží.

Ověřeno v prohlížeči nad PKVaultem: držení a prohlížení na titulce, otevření článku z odfiltrovaného výpisu, stav v jeho hlavičce, návrat kliknutím na štítek, dotaz z článku i cesta ze statické stránky tagu. Testy 78.

### 16. Jediný výsledek se otevře rovnou - HOTOVO

Záruka **Z80**. Když klik na jméno štítku nechá ve výpisu jedinou kartu, titulka ten článek rovnou otevře. Je to **kliknutí na kartu udělané za čtenáře**, tedy tatáž adresa, jakou nese odkaz z karty, i s filtrem - `stateQuery()` je společný, takže se ty dvě cesty nemůžou rozejít.

Podstatné je, na co se to váže. Skok patří **kliku, ne stavu**: `render()` dostal nepovinné `opts` a skáče jen na `{ pick: true }`, které mu pošle `onPick`. Adresa tím zůstává tím, čím byla - `index.html?tag=a&tag=b` vrátí výpis, i když je v něm jeden článek, takže se nerozbil žádný odkaz zvenčí ani ze statické stránky tagu. Stav se navíc zapisuje `writeUrl` ještě před odchodem, takže tlačítko zpět vrátí do toho výpisu a druhý skok se nekoná.

Neskáče **čtvereček**, ten zužuje osu a nevybírá článek; kdyby odskočil, odškrtnout by se dal jen tlačítkem zpět. A neskáče ani **zhasnutí jména** - `render({ pick: current === tag })`, tedy jen zapnutí. Zhasnutí výsledek rozšiřuje a rozšiřování není způsob, jak si někdo říká o článek. Textový dotaz do toho mluví jen tím, že zužuje množinu, ve které se počítá; funkce je stejná, jen na menší množině.

**V hlavičce článku se zprvu neskákalo.** Článek si zapékal jen množiny tagů, takže věděl, že výsledek je jeden, ale ne který, a klik odcházel na titulku. V praxi to vypadalo jako chyba: na webu KostkaAXMain skočil štítek DimUtvar z titulky rovnou na článek, ale DimUcet z hlavičky toho článku jen na `index.html?pick=DimUcet`. Pilulka tak na dvou stránkách dělala dvě různé věci.

**Teď skáče i článek.** K sadě štítků se zapéká adresa článku, `{url, tags}`, takže `render(opts)` v `ARTICLE_FILTER` spočítá výsledek stejně jako titulka a při jediném článku jde rovnou na něj, i s filtrem. Jinak dál odchází na titulku. Stojí to jméno souboru na článek, index hledání v článku dál není. Sady se skládají z `plan`, ne z `items`, protože jméno souboru vzniká až tam.

Zvažovalo se a zahodilo: skok **z adresy** (rozbil by odkazy a po tlačítku zpět by se cyklil), skok i na **čtverečku**, a **příznak v adrese** (`index.html?tag=video&jump=1`), kterým by článek řekl, že jde o klik, a titulka by doskočila za něj. Příznak by chování srovnal za cenu parametru navíc v mezikroku; adresy zapečené v článku to srovnaly bez mezikroku.

Nic se nepřidalo na štítek: **číslo `1` říká dopředu dost**.

`search()` nově vrací to, co vykreslila, aby se nemusela počítat druhá pravda o tom, kolik je vidět. Posluchač na psaní v poli volá `render()` bez argumentu, jinak by mu prohlížeč jako `opts` podstrčil událost.

Ověřeno v prohlížeči nad PKVaultem: klik na štítek s jedničkou, tlačítko zpět, tentýž štítek z hlavičky článku, kombinace s dotazem, čtvereček na jedničce a odkaz `?tag=` s jediným výsledkem. Testy 79.

### 17. Konfigurace i v `_obsidian2html` - HOTOVO

Složka s tečkou se v Obsidianu nezobrazí, takže `menu.md` a `index.md` se psaly jiným editorem. Vault si teď může vybrat i `_obsidian2html/`, kterou Obsidian ukáže. Obě jména jsou rovnocenná a na web se nedostane ani jedna, obě přeskočí K20. Jména drží `CONFIG_DIRS`, složku vybírá `config_name(vault)`. Vault bez konfigurace dostane `CONFIG_DIR`, takže hlášky typu *přidej řádek do .../menu.md* dál jmenují zdokumentovaný tvar.

**Obě složky naráz zastaví build.** Zvažovala se přednost jedné z nich a zahodila se: ta, která by prohrála, by se tiše ignorovala a úprava v ní by nikam nevedla. Je to stejná past, kvůli které build hlásí starou složku `_web`. Kontrola běží ještě před `--clean`, takže předchozí výstup zůstane na místě a nejde do archivu.

Testy 81.

### 13. Štítek ve filtru bez mřížky - HOTOVO

Pilulka sama říká, že jde o tag, takže `#` před názvem nic nepřidávalo. Odešlo jen ve **filtru**; na kartách a v patičce článku mřížka zůstává, tam stojí název tagu vedle data a odlišit je od sebe je potřeba.

Spravilo to mimochodem i pseudotag: jeho popiska sama je `#`, takže se ve filtru kreslil jako `##`. V liště v hlavičce byl vždycky správně, protože ta popisku vypisuje rovnou.

### 18. Nové rozhraní a jen web - HOTOVO

Zadání vzniklo úpravou README a jeho rozdělením na uživatelský `README.cs.md` a `SPEC.cs.md` (`cc24851`, `ee9f179`), kód šel za ním.

- **Přepínače:** `--source`, `--dest`, povinný `--publish` a `--keep-archives`, `--check` zůstal. `--publish` bere jen `"*.md"` (všechno) nebo `"*X.md"` (marker X). Vzor rozbalený bashem se pozná podle souborů navíc a build poradí uvozovky. Staré přepínače nezůstaly ani jako skryté aliasy, dávky se předělávají.
- **Jen web:** režim samostatného souboru s obrázky v data URI a holý `index.html` z dávky odešly i s `--title`, `--vault`, `inline_images`, `index_page` a šablonou `HTML`. Za kořen vaultu se bere `--source`.
- **Cíl (Z55):** vyprazdňuje se při každém buildu, položky s tečkou zůstávají. Co se maže, jde nejdřív do zipu v `_archiv` o úroveň výš a zůstane posledních N zipů tohoto cíle. Pojistka se značkou `.vygenerovano` platí dál, adresář jen s tečkovými položkami se bere jako prázdný.
- **`config.toml`** v konfigurační složce nese `name`, `lang` a `base_url` místo `--site-name`, `--lang` a `--base-url`. Čte ho `tomllib`, takže je potřeba Python 3.11. Neznámý klíč nebo neplatná hodnota build zastaví.
- **K20:** soubor s tečkou nebo podtržítkem na začátku se přeskakuje stejně jako složka.

Testy našly chybu, která by se jinak ukázala až u prvního cíle nasazovaného gitem: kontrola odkazů procházela i `.git` a zakopla o `HEAD` psaný velkými písmeny. Tečkové složky teď přeskakuje.

Ověřeno na kopii PKVaultu s `config.toml`. S markerem se proti staré verzi liší jen `styl.css`, a to komentáři a mrtvým pravidlem `.rozcestnik`. S `"*.md"` se liší 21 stránek a všechny jen tím, že v titulcích zůstal globus - viz otevřené otázky.

Testy 96.

### 19. Build jen při změně - HOTOVO

Pro pravidelný build z plánovače, kde se web nemá každých pět minut přepisovat. `--if-changed` spočítá otisk zdroje (cesta, velikost a čas změny souborů, které na web mají vliv, vzor z `--publish` a samotný `md2html.py`) a uloží ho po úspěšném buildu do značky `.vygenerovano`. Shoda znamená konec bez zásahu do cíle. Popsané jako Z57.

Nápad převzatý z Vikina `web_auto.py`, který totéž dělal zvenku. Uvnitř nástroje stačí, aby dávka pro každý web byla jeden řádek.

Do otisku nejdou tečkové položky kromě konfigurační složky a nastavení šablon, protože `.obsidian/workspace.json` se mění pořád. Složky s podtržítkem jdou, `find_file()` z nich bere přílohy.

Na kopii PKVaultu trvá běh bez změny zhruba 0,3 s.

Testy 103.

### 20. Datum poslední změny pod patičkou - HOTOVO

Pod patičkou každé stránky je vlevo `Aktualizováno 2026-09-25 12:43`, popsané jako Z85. Je to nejnovější čas změny souboru, ze kterého web vznikl: publikované články, vložené poznámky, obrázky zkopírované do `img/` a soubory v konfigurační složce.

Čas buildu se zvažoval a zahodil. Ruční build by změnil každou stránku, takže porovnání dvou verzí generátoru by přestalo fungovat. A `--if-changed` sleduje celý vault, takže veřejný web by ukázal, kdy autor upravil soukromou poznámku.

Obrázky jsou známé až po vysázení všech stránek, proto patička nese zástupný komentář a `stamp_pages()` ho doplní na konci buildu. Transkluze si `Conversion` pamatuje v `included`.

Ověřeno na kopii PKVaultu: ve všech 17 stránkách přibyl jen ten řádek a položka `updated` v tabulce textů, kterou stránky s filtrem nesou celou.

Testy 107.

### 21. Filtr na období - HOTOVO

Varianta *posuvník s histogramem* z `maketa-datum-TMP.html`, zapíná ji `date_filter = true` v `config.toml`. Popsané jako Z75. Výchozí je vypnuto, takže PKVault zůstává, jak byl.

Období je třetí osa filtru vedle tagů a textu, spojená přes AND. Stav drží `since` a `until` jako měsíce `RRRR-MM`, `null` je otevřený konec, takže celé období se do adresy nepíše. Do adresy jde jako `?from=` a `?to=` a jede do článku jako tagy. Článek posuvník nekreslí, ale nese u sad štítků měsíc každého článku, aby čísla v jeho liště počítala se stejným obdobím. Osu měsíců počítá build (`period_months`) a zapéká ji do titulky i do článků; prázdná osa znamená web bez filtru a `?from=` se na něm ignoruje.

Oproti maketě: popisky roků se měří až po odkrytí bloku a při úzké ose se píše jen každý druhý nebo pátý rok. První rok dostane popisek i tehdy, když osa nezačíná lednem. Počítadlo u hledání je s obdobím dlouhé, na telefonu proto dostane vlastní řádek. Překreslení při tažení čeká na snímek a spustí se jen při změně měsíce, kvůli limitu `history.replaceState` v Safari.

Styly jsou v `CSS_PERIOD` a do `styl.css` jdou jen s filtrem. Web bez něj se proti předchozí verzi liší jen vloženými skripty a tabulkou textů, `styl.css` a stránky tagů jsou shodné bajt za bajtem. Ověřeno na PKVaultu, zapnutá varianta v prohlížeči na vymyšleném vaultu s daty z makety, na šířce počítače i telefonu.

Zapnuto v PKVaultu i v ProjektKrizik.

**Jednotka osy podle rozpětí.** Pevné měsíce nedávaly ProjektKrizik nic, všech 88 článků je ze září 2026. Osa teď vezme nejjemnější jednotku, se kterou vyjde nejvýš 60 sloupců (`PERIOD_BARS`, `period_axis`): dny zhruba do dvou měsíců, měsíce do pěti let, nad tím roky. Zvažovala se hranice čtyř měsíců pro dny a zahodila se - na telefonu by vyšly tři pixely na den. Přihrádky jsou začátky data (`RRRR-MM-DD`, `RRRR-MM`, `RRRR`), takže filtr jen porovnává, kolik znaků klíč má. Článek proto místo měsíce nese celé datum.

Zvažovalo se i `date_filter = "day"`, tedy jednotku zamknout, aby uložené odkazy nepřestaly zužovat, když se jednotka s růstem webu zhrubne. Nepotřebné, neudělalo se.

Osa po dnech popisuje měsíce a k nim dny: každý, každý druhý, nebo 1., 8., 15., 22. a 29., co se vejde. Původně jen 8., 15. a 22., a PKVault s pěti dny od 28. 8. do 1. 9. pak pod osou ukázal jen dva měsíce a vypadal jako osa po měsících. Popisek, který se do sloupce vejde, je vycentrovaný pod úchytem. Víkendy mají číslo červeně (`--vikend`, `#b02a37`), dnešek je pilulka v barvě textu a je očíslovaný vždycky. Původně byl dnešek v barvě odkazů, jenže ta je u PKVaultu i ProjektKrizik červená a splývala s víkendem. Prázdný sloupec byl dvoupixelová skoro průhledná čárka a dny bez článku skoro nebyly vidět; teď je každý sloupec podbarvené políčko (`--zebra`) a počet v něm roste odspodu. Dnešek se bere z prohlížeče, ne z buildu - `--if-changed` staví jen při změně, takže build by den za dnem ukazoval den poslední úpravy. Popisky jsou přes `min-width: 0` široké jako svůj sloupec, jinak dlouhý text roztáhl svůj span a osa ujela od sloupců. Dráha posuvníku je zúžená na středy krajních sloupců, jinak při šesti ročních sloupcích stál úchyt na hraně sloupce místo nad ním.

Při zkoušení v prohlížeči se ukázala chyba, kterou testy nevidí: `binOf` jako `const` ve `FACET_JS` titulka i článek volají dřív, než se ten kód vloží, a stránka zůstala prázdná - i na webu bez filtru. Je z něj deklarace funkce.

Testy 115.

### 22. Odkaz do Obsidianu - HOTOVO

Popsané jako Z90. S `--edit-links` má patička článku odkaz *Upravit v Obsidianu*, `obsidian://open?vault=...&file=...`. Podnět: na lokálním webu ProjektKrizik je k `fy-2026-09-22-soustava-si-a-prevody-jednotek.html` pracné dohledat `02 Předměty/Fy - Fyzika/Fy 2026-09-22 Soustava SI a převody jednotek.md`.

Zvažovalo se a zahodilo: `file:///` (z `http(s)` ho prohlížeč zablokuje a `.md` jen zobrazí jako text), `obsidian://open?path=` s absolutní cestou (rozbije se přesunem vaultu a prozradí disk), vlastní protokol v registru pro libovolný editor (instalace navíc) a klíč v `config.toml` (z jednoho vaultu vzniká veřejný web i náhled a odkaz patří jen do náhledu). Protokol `obsidian://` ověřen ručně na ProjektKrizik před implementací.

Vault se hledá nahoru od `--source` podle `.obsidian/` (`find_vault_root`), odkaz skládá `edit_link`. Kontrola odkazů přeskakuje schéma `obsidian:`, jinak by odkaz zploštila. Přepínač jde do otisku.

Testy 120.

### 23. Tužka u nadpisu místo textu v patičce - HOTOVO

Odkaz z Z90 se přestěhoval z patičky vpravo k nadpisu článku a přibyl i na kartách titulky a stránek tagů, aby se kvůli opravě nemusel článek otevírat. Místo textu je ikonka tužky jako vložené SVG (`EDIT_ICON`, `edit_button`, `with_edit`), text zůstal v `title` a `aria-label`.

Zvažovalo se a zahodilo: emoji klíče nebo tužky (vzhled podle písma a systému, v tlumené barvě patičky nejde obarvit), znak tužky U+270E (některá písma ho nemají), logo Obsidianu (ochranná známka a na malé velikosti nečitelné).

Karta na titulce dostane v datech klíč `edit` jen s přepínačem, takže bez něj se PKVault liší jen skriptem a CSS - ověřeno na zmrazené kopii vaultu.

Testy 121.

## Otevřené otázky

- **Globus v titulcích s `"*.md"`.** Bez markeru se nestrhává nic, takže náhled PKVaultALL má u článků s globusem v titulku `Obsidian Co je 🌐`. Staré `--all` globus strhávalo, protože marker měl výchozí hodnotu. Pro vault bez markeru je to jedno.
- **Dva weby z jednoho vaultu.** `PKVault!.cmd` a `PKVaultALL.cmd` staví ze stejného vaultu s jiným názvem webu a náhled bez RSS. S `config.toml` ve vaultu sdílí obě dávky jeden název i `base_url`.


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

Odlišení není ani jednosouborový režim, ani fasetový filtr sám o sobě, ale **vyslovené a zdůvodněné konvence**. Proto jsou jádrem `SPEC.cs.md`.

### nl2br

Rozšíření knihovny `markdown`, které dělá zlom z každého nového řádku - odpadly by koncové mezery. Vyzkoušeno na PKVaultu: přidalo 48 zlomů v 7 článcích, počet stránek i obsah titulky a stránek tagů zůstal shodný, tedy **bezpečné**. Obsidian se ve výchozím nastavení chová stejně.

Nepřijato, autor si vystačí s Enterem. Zapsáno pro případ, že by se ty koncové mezery ukázaly jako příliš křehké.

### Zpětné lomítko jako zlom řádku

Nefunguje. Je to CommonMark, kdežto knihovna `markdown` CommonMark není - `Věta.\` se vykreslí i s tím lomítkem. Fungují jen **dvě koncové mezery**.

### Pevný název náhledového obrázku

Zvažoval se `perex.png` místo pojmenování podle článku. **Nejde to**: jedna složka `Attachments/` obsluhuje všechny články své složky, takže by náhled mohl mít jen jeden z nich.

### Přenos historie

`git filter-repo` uměl vyříznout 23 commitů `md2html.py` z `_JDStandards`. Nakonec se nepřenášely, staré commity nejsou potřeba.
