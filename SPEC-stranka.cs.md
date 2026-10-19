# obsidian2html - specifikace: Stránka

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

**Z85. Pod patičkou každé stránky je vlevo datum a čas poslední změny obsahu webu.**  
Tvar je `Aktualizováno 2026-09-25 12:43`, na anglickém webu `Updated`, v místním čase.  
Je to nejnovější čas změny souboru, ze kterého web opravdu vznikl: publikovaného článku, vložené poznámky, obrázku a souboru v konfigurační složce.  
**Není to čas buildu.** Ten by se měnil s každým ručním buildem, takže stejný zdroj by nedal stejný web a porovnání dvou verzí generátoru by hlásilo rozdíl na každé stránce.  
A `--if-changed` sleduje celý vault, takže web by po úpravě soukromé poznámky ukázal čas, kdy autor pracoval na něčem, co na webu není.  
Soubor, který na web nejde - neoznačený článek, poznámka s podtržítkem - čas nezmění.  
Nová verze `md2html.py` ho nezmění taky: obsah webu je ten samý, jen jinak vysázený.
