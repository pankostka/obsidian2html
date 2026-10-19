# obsidian2html - specifikace: Publikování

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

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
