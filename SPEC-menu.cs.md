# obsidian2html - specifikace: Menu a tagy

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

**K95. Hierarchický tag `Obsidian/Video` se rozpadne na dva samostatné tagy.**  
Vzniknou z něj `Obsidian` a `Video`, každý se svou stránkou, takže `Video` sbírá videa z celého vaultu, ne jen ta u Obsidianu - a přesně podle toho chce člověk filtrovat.  
O tom, který tag je hlavní, hierarchie nerozhoduje, to říká značka podle K97, případně adresář podle K96.

**K96. S `lead_tags = "folders"` je hlavním tagem i adresář první úrovně**, ve kterém článek leží.  
Vault bývá rozdělený do adresářů podle stejných témat jako web, a psát totéž ještě tagem s podtržítkem je práce navíc, na kterou se zapomíná.  
Podtržítko podle K97 platí dál a přidá hlavní tag, který jde napříč adresáři, třeba `_Todo` nebo `_Organizační`.  
Výchozí je `"underscore"`, tedy jen podtržítko, takže vault, který nic neřekne, se nezmění.

Z názvu adresáře se tag udělá takhle:
- mezery na začátku a na konci zmizí a víc mezer uvnitř se slije do jedné,
- číslo na začátku, jedno až tři místa, za ním tečka, mezera, pomlčka nebo podtržítko, určuje pořadí a do jména nepatří: `02.Předměty` je tag `Předměty`,
- od pomlčky obklopené mezerami dál je poznámka pro autora: `Ma - Matematika` je tag `Ma`, `E-shop` zůstane celý.

Doporučený oddělovač je tečka, protože cesta bez mezery nepotřebuje ve Windows uvozovky.  
Čtyři číslice nejsou pořadí, ale jméno (`2026`), a číslice přilepená k písmenu patří ke slovu (`3D tisk`).  
Tag dává jen **první úroveň**: hlubší bývá technická (`Materiály`, `Attachments`), nebo ji líp řekne běžný tag.  
Článek v kořeni tag z adresáře nemá a najde ho prázdná pilulka podle K98.  
Adresář začínající tečkou nebo podtržítkem tag nedá, protože se podle K20 přeskakuje celý.

V první řadě jdou očíslované adresáře podle čísla, za nimi ostatní hlavní tagy abecedně; druhá řada zůstává abecední.  
Tag z frontmatteru se stejnou adresou jako tag z adresáře je tentýž tag a jméno má z adresáře: `skola` v článku je `Škola`.  
Dva adresáře se stejným tagem (`01.Škola`, `05.Škola`) dají jeden tag s nižším číslem a adresář, ze kterého nic nezbude (`01`), nedá žádný - obojí build ohlásí, protože ve vaultu to vidět není.  
Tagy, které se liší jen mezerou nebo pomlčkou (`Power BI` a `PowerBI`), build ohlásí, ale nesloučí: mají různé adresy a které jméno platí, ví autor.  
Na tag z adresáře, který jiný článek píše bez podtržítka, build neupozorňuje: vede podle toho, kde článek leží, ne podle značky.

**K97. Tag s podtržítkem na začátku je hlavní**, tedy `_Obsidian` proti běžnému `Obsidian`.  
Ve filtru na titulce vede první řadu, všechno ostatní jde do druhé; obě řady jsou abecedně, jen očíslované adresáře podle K96 jdou napřed.  
Podtržítko je jen značka, ne část jména: tag se pořád jmenuje `Obsidian`, má stránku `tag-obsidian.html` a v článku se vypíše bez něj.  
Který tag je důležitý, tedy říká vault na místě, kde se článek taguje, ne konfigurace webu - povýšit tag znamená napsat jeden znak, ne editovat soubor navíc.  
Podtržítko se navíc řadí před písmena, takže hlavní tagy drží pohromadě i v seznamu tagů uvnitř Obsidianu.  
U hierarchie se posuzuje **každá část zvlášť**: `_Obsidian/Video` povýší `Obsidian`, `Obsidian/_Video` povýší `Video`.  
Protože `_Obsidian` a `Obsidian` je jeden tag, stačí značka u jednoho výskytu a tag vede - build ale vypíše články, které ji nemají, protože ze zápisu se nedůslednost nepozná.  
Kurátorovaný `menu.md` řídí lištu v hlavičce, do filtru nemluví; značku v něm psát netřeba, a když se tam zkopíruje, přeskočí se.

**K98. Každou řadu filtru uzavírá prázdná pilulka pro články, které v ní žádný tag nemají.**  
Bez ní by se k článku bez hlavního tagu nedalo dostat přes první řadu a k článku bez běžného tagu přes druhou.  
Hlavní je tag podle celého webu, ne podle zápisu v článku (K97).  
Obě pilulky naráz dávají články bez jediného tagu, takže třetí pilulka není potřeba.  
Pilulka nemá jméno, nese počet a čtečce obrazovky říká, co znamená, vlastním popiskem.  
Kreslí se, jen když zužuje: sedí na ni aspoň jeden článek a ne všechny.  
Stránku nemá, v adrese je `?tag=bez-hlavniho-tagu` a `?tag=bez-bezneho-tagu` (anglicky `no-lead-tag`, `no-plain-tag`).
