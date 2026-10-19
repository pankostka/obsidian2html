# obsidian2html - specifikace: Přílohy

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

**K50. Přílohy leží ve složce článku nebo v `Attachments/`.**  
Složka článku leží vedle něj a jmenuje se jako on: `Obsidian Co je 🌐.md` má přílohy v `Obsidian Co je/`.  
Je pro autora, který pracuje v průzkumníku - u jedné společné `Attachments/` se špatně dohledává, co ke kterému článku patří.  
Porovnává se přes slug bez markeru, takže sedne složka s globusem i bez něj a při zveřejnění ji přejmenovat jde, ale nemusí se.  
Obě naráz jsou chyba, protože vybrat jednu by tu druhou tiše schovalo.  
Hledá se v pořadí: vedle článku, ve složce článku, v jeho složce příloh (`Attachments`), pak v celém vaultu - stejně jako to dělá Obsidian, jen se složkou článku navíc.  
Složka článku jde před `Attachments/`, protože patří jen jednomu článku.

**K60. Náhledový obrázek se jmenuje jako článek** a leží ve složce článku nebo v `Attachments/` vedle něj, složka článku má přednost.  
Porovnává se přes slug, takže sedne `Obsidian Co je.png` i `obsidian-co-je.png`.  
Pojmenovat ho pevně nejde: jedna složka `Attachments/` obsluhuje všechny články své složky, takže by mezi nimi kolidoval.  
Doporučený rozměr je 630x290.  
Jiný rozměr se nepředělává - ořez a vycentrování obstará CSS v prohlížeči (`object-fit: cover`, horní část zůstane), takže generátor nepotřebuje knihovnu na obrázky.

**Z30. Chybějící obrázek je chyba, ne varování.** V tichosti by vznikl dokument s prázdným místem a odešel uživateli.

**Z60. Přílohy se na webu ukládají malými písmeny v ASCII.**  
Na Linuxu je `Foo.png` a `foo.png` rozdíl, takže špatně napsaný odkaz funguje na Windows a na serveru vrátí 404.  
Velikost písmen v odkazech se navíc ověřuje proti skutečným souborům a kolize adres je chyba.  
Přílohy leží v jedné složce `img/`, protože web je plochý: články jsou v kořeni a složky vaultu se do adres nepropisují, takže přeskupení vaultu žádnou adresu nezmění.  
Přílohy ze složky článku (K50) dostanou podsložku `img/<slug článku>/`, takže dva články smějí mít každý svou `schema.png`.
