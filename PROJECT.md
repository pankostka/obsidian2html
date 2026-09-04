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

Zadáním jsou konvence z `README.cs.md`, ne implementace. Název testu začíná kódem konvence, takže když spadne, rovnou říká, která věta přestala platit.

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

## Otevřené otázky


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
