# obsidian2html - specifikace: Článek

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

**K25. Titulek článku je název souboru z Obsidianu, jen bez markeru.** Nadpis `# H1` se nepoužívá - nejde spolehlivě poznat, jestli je to titulek dokumentu, nebo první sekce ze šablony. Název souboru je Obsidianův vlastní model, takže cesta tam i zpět je zřejmá: od titulku na webu se dá dohledat článek ve vaultu a naopak. Frontmatter klíč `title` ho přebije tam, kde je název technický.

**K30. Název článku se převede na slug.** Z `Obsidian Nastavení 🌐.md` vznikne `obsidian-nastaveni.html`: bez diakritiky, malými písmeny, mezery na pomlčky, marker pryč. Je to kvůli publikování na web, kde diakritika ani mezery v adrese nepatří. Oddělovač je **pomlčka, ne podtržítko** - vyhledávače berou pomlčku jako hranici slov, podtržítko ne.

**K40. Perex je první odstavec.** Od začátku až po nadpis. Když článek začíná rovnou nadpisem, pak je perex prázdný. Pokud je v perexu obrázek, pak se vyhodí.

**K80. Publikovaný článek by měl mít ve frontmatteru `date`.** Když ho nemá, použije se datum souboru. Je to vratké, protože datum souboru se mění při kopírování i při synchronizaci, ale je to jednoduché a nepotřebuje to git - ten ve vstupním adresáři fungovat nemusí. Při shodě dat rozhoduje název článku, aby bylo pořadí jednoznačné.  Tvar `RRRR-MM-DD` se kontroluje a build na cokoli jiného upozorní (třeba datum šablony `{{date:YYYY-MM-DD}}`)

**Z10. Mrtvý odkaz nikdy nevznikne.** Když cíl odkazu není v dávce, zbyde z něj holý text a skript ohlásí kolik.  
Dokument jde uživateli, a odkaz, který nikam nevede, je horší než žádný.  
Platí to pro wikilink `[[Článek]]` i pro standardní odkaz `[Text](Složka/Článek.md)`, který píše Obsidian s volbou `useMarkdownLinks` a každý jiný editor.  
Standardní odkaz se převede na adresu stránky cílového článku podle jeho názvu, cesta k němu ve vaultu nehraje roli, protože všechny stránky leží na webu vedle sebe.  
Bez převodu by prohlížeč hledal soubor `.md`, který na webu není.

**Z20. Uvnitř bloku kódu se nenahrazuje nic.** Bez toho si převodník přepíše vlastní ukázky syntaxe: článek, který učí psát wikilinky, má `[[Název]]` jako kód, ale generátor by v něm viděl odkaz, cíl nenašel a zploštil ho na text. Čtenář by se z článku o závorkách dozvěděl všechno kromě těch závorek.
