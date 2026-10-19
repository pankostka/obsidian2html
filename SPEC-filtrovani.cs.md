# obsidian2html - specifikace: Filtrování

> Součást specifikace, rozcestník a pravidla čtení jsou v [SPEC.cs.md](SPEC.cs.md).  
> Platí totéž: když si kód a tenhle dokument odporují, chyba je v kódu.

## Pravidla

**Z70. Filtr přežije kliknutí do článku.**  
Lišta v hlavičce článku je tentýž fasetový filtr jako na titulce, ne řádek odkazů, a stav si čte z adresy - odkaz z výpisu ho s sebou nese.  
Kdo si zafiltroval na `#Obsidian` a otevřel článek, má `#Obsidian` v hlavičce dál a další kliknutí ho vrátí do výpisu s tím filtrem, ne do celého webu.  
Do článku se přitom zapékají jen **tagy** článků, ne index hledání: čísla na štítcích jsou jediné, co ta stránka počítá, a index by se platil na každém načtení článku.  
Textový dotaz s sebou nejede, jede jen filtr - článek nemá výpis, ve kterém by se hledalo, a čísla na štítcích by pak odpovídala na jinou otázku než ta na titulce. Dotaz napsaný v hlavičce článku ale filtr zachová, protože ho formulář pošle na titulku s sebou.  
Bez JavaScriptu zůstává v `<noscript>` původní statická lišta s odkazy na stránky tagů, takže Z10 platí dál.  
Stránky tagů zůstávají statické: jejich výpis se v prohlížeči nepřekresluje, takže živý filtr nad ním by lhal.

**Z75. S `date_filter = true` má titulka pod štítky posuvník na období s histogramem.**  
Je to třetí osa filtru vedle tagů a textu a spojuje se s nimi přes AND.  
Osa jde od prvního článku po poslední a má **všechny dny, měsíce nebo roky** mezi nimi, i ty, ve kterých žádný článek není.  
Díra v psaní je informace a histogram ji má ukázat, ne zavřít.  
**Jednotku vybere build sám**: nejjemnější, se kterou vyjde nejvýš 60 sloupců, takže po dnech je osa zhruba do dvou měsíců, po měsících do pěti let, výš po rocích.  
Víc sloupců by se na telefonu nedalo trefit.  
Jak web roste, jednotka se sama zhrubne.  
U osy po dnech jsou víkendy a dnešek odlišené (token `--vikend`, Z40).  
Histogram počítá celý web a nemění se při výběru, čísla na štítcích období ale započítávají - štítek, který slíbí pět, zatímco výpis drží dva, by lhal.  
Období jde do adresy v jednotce osy (`?from=2023-01&to=2024-06`) a přežije kliknutí do článku stejně jako tagy (Z70).  
Článek posuvník nekreslí, ale čísla v jeho liště počítají se stejným obdobím.  
Bez `date_filter` se `?from=` a `?to=` ignorují, protože filtr, který nejde vidět ani zrušit, by tiše ubíral články.  
Hodnota mimo osu nebo z doby s jinou jednotkou se ignoruje, výpis se neztratí.  
Článek s datem, které datem není (K80), na osu nepatří.  
Když mají všechny články stejné datum, posuvník se nekreslí a build to ohlásí.  
Bez JavaScriptu zbyde statický výpis.

**Z80. Když klik na štítek nechá jedinou stránku, otevře ji.**  
Je to kliknutí na kartu udělané za čtenáře, takže vede na tutéž adresu, jakou nese karta, i s filtrem.  
Stav je v adrese dřív, než se odejde, takže tlačítko zpět vrací tam, odkud se kliklo.  
Skok patří **kliku, ne stavu**: adresa `index.html?tag=a&tag=b` zůstává výpisem, i když vrací jediný článek, aby odkaz poslaný ven přistál tam, co vždycky.  
Skáče jen **jméno** štítku, a jen když se zapíná. Čtvereček zužuje osu, nevybírá článek, a zhasnutí jména výsledek naopak rozšiřuje.  
Textový dotaz do toho mluví jen tím, že zužuje množinu, ve které se počítá.  
Skáče titulka i lišta v hlavičce článku.  
Článek k tomu nese vedle sad štítků i adresy článků, jinak by věděl, že výsledek je jeden, ale ne který.  
Číslo `1` na štítku to říká dopředu, takže se k němu nic dalšího nekreslí.
