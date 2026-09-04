# obsidian2html

Generátor statického webu z Obsidian vaultu. Jeden skript, jedna závislost.

## Kde co je

- **[README.cs.md](README.cs.md)** - zdrojový text: k čemu nástroj je a všechny konvence. **Autorita.** Když si kód a tenhle dokument odporují, chyba je v kódu.
- **[PROJECT.md](PROJECT.md)** - pracovní dokument: co se dělá teď, co zbývá, co se už zkusilo a zahodilo. Přečti si ho na začátku práce.
- **[README.md](README.md)** - anglický překlad `README.cs.md` pro veřejnost. **Needituj ho přímo**, změna se dělá v českém zdroji a překlad se vyrobí znovu.

## Pravidla

Česky včetně diakritiky, v kódu i v commit zprávách. Anglicky je jen `README.md`.

**Piš jen znaky z běžné klávesnice.** Žádná dlouhá pomlčka, typografické uvozovky ani výpustka; místo nich spojovník, rovné uvozovky, tři tečky. Šipka se píše `->`.

**V `README.cs.md` je jedna věta na řádek** a řádek uvnitř odstavce končí dvěma mezerami, aby zlom prošel do HTML. Doplňuj je při každé úpravě, autor je nepíše ručně.

**V commit zprávě nepoužívej dvojité uvozovky.** Zprávu předávej souborem přes `git commit -F`, ne rourou - PowerShell 5.1 přidá do roury BOM. Git volej po jednom příkazu, zvlášť `add`, zvlášť `commit`.

**Změnu ověřuj buildem.** Postav PKVault před zásahem i po něm a porovnej výstup; skript nemá testy, tohle je zatím jediná pojistka.

Pravidla pocházejí z `_JDStandards` (`dokumentace_JD.md`, `git_JD.md`). Tenhle repozitář není jejich cílem, takže se sem nekopírují a jsou tu opsaná jen ta, která se ho týkají.
