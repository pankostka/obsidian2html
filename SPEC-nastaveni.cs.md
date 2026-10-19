# obsidian2html - specifikace: Nastavení webu

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

**K70. Konfigurace webu leží ve složce `.obsidian2html/` nebo `_obsidian2html/`** v kořeni vaultu. Obsahuje (abecedně):
- `config.toml` - název, jazyk a adresa webu, filtr na období a hlavní tagy, viz níže.
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
date_filter = true                  # posuvník s histogramem na titulce (Z75)
lead_tags = "folders"               # hlavní tag i z adresáře (K96)
```

- `name` - název webu vlevo nahoře (u loga jako jeho alternativní text), v titulku každé stránky a v RSS. Výchozí je jméno složky vaultu.
- `lang` - jazyk ovládání webu podle K100. Výchozí je `cs`.
- `base_url` - absolutní adresa, na které web poběží. Potřebuje ji jen RSS, protože čtečka kanál čte jinde a relativní odkaz by tam nikam nevedl. Bez ní `rss.xml` nevznikne.
- `date_filter` - filtr na období podle Z75, `true` nebo `false` bez uvozovek. Výchozí je `false`.  
	Text `"false"` v uvozovkách je chyba, jinak by se jako neprázdný text četl jako zapnuto.
- `lead_tags` - co dělá tag hlavním: `"underscore"` jen podtržítko podle K97, `"folders"` navíc adresář první úrovně podle K96. Výchozí je `"underscore"`.

Každý klíč smí chybět a pak platí výchozí hodnota, chybět smí i celý soubor.  
**Neznámý klíč nebo neplatná hodnota je chyba** a build se zastaví - překlep v `nmae` by jinak tiše vyrobil web se jménem složky.  
Údaje o webu patří do vaultu, ne do přepínačů: jsou to vlastnosti webu jako logo nebo menu, nemění se build od buildu a dávka pak řeší jen odkud, kam a co.

**K90. Klíče frontmatteru, konfigurace a přepínače jsou anglicky.** Tedy `date`, `title`, `excerpt`, `slug`, `tags`, v `config.toml` `name`, `lang`, `base_url`, `date_filter`, `lead_tags`, a přepínače `--source`, `--dest`, `--publish`, `--check`, `--keep-archives`, `--if-changed`, `--edit-links`. Obsah článků je česky, rozhraní nástroje ne - nástroj je veřejný a jeho příkazová řádka i klíče jsou to jediné, co cizí uživatel musí napsat sám. České klíče `datum`, `titul` a `perex` se už nečtou; když na ně build narazí, ohlásí to, protože jinak by článek tiše přišel o datum nebo titulek.

**K100. Jazyk webu určuje klíč `lang` v `config.toml`, výchozí je `cs`.** Lokalizuje se jen to, co vidí **návštěvník** - hlášky při buildu čte ten, kdo build spouští, a ty jsou anglicky vždycky.  
Součástí jazyka jsou i **názvy v adrese**: prázdná pilulka z K98 je na českém webu `?tag=bez-bezneho-tagu`, na anglickém `?tag=no-plain-tag`.  
Adresa, která je jednou venku, je závazek, a odvození od jazyka ho drží na obou stranách.  
Skloňování řeší v prohlížeči `Intl.PluralRules`, takže v kódu nejsou žádná pravidla na počítání - tabulka nese jen tvary. Čeština jich potřebuje tři, angličtina dvě.  
Neznámý jazyk build zastaví. Tiše spadnout na češtinu by znamenalo vyrobit jiný web, než si člověk vyžádal.

**Z40. Vlastní styly se připojují, nenahrazují.** `.obsidian2html/styl.css` jde za vygenerované CSS, takže přepsat jde cokoli. Barvy jsou tokeny v `:root`, takže změna je jedna řádka a nesahá se do generátoru.
