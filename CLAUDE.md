# obsidian2html

Generátor statického webu z Obsidian vaultu. Jeden skript, jedna závislost.

## Kde co je

- **[SPEC.cs.md](SPEC.cs.md)** - konvence K a záruky Z se zdůvodněním. **Autorita** pro kód i testy. Když si kód a tenhle dokument odporují, chyba je v kódu.
- **[README.cs.md](README.cs.md)** - popis pro uživatele: k čemu nástroj je, jak ho spustit a nastavit. Pravidla jen stručně a s odkazem na kód ve `SPEC.cs.md`; když si odporují, platí SPEC.
- **[PROJECT.md](PROJECT.md)** - pracovní dokument: co se dělá teď, co zbývá, co se už zkusilo a zahodilo. Přečti si ho na začátku práce.
- **[README.md](README.md)** - anglický překlad `README.cs.md` pro veřejnost. **Needituj ho přímo**, změna se dělá v českém zdroji a překlad se vyrobí znovu.

## Pravidla

**Kód je anglicky, texty kolem něj česky.** Názvy funkcí, tříd, konstant a proměnných anglicky, stejně tak komentáře, docstringy a commit zprávy - historie je od zveřejnění repozitáře veřejná a čte ji stejné publikum jako `README.md`. Česky včetně diakritiky zůstávají `README.cs.md`, `SPEC.cs.md` a `PROJECT.md`, tedy zdrojový text, specifikace a pracovní dokument.

**Identifikátory nepřejmenovávej hledáním v textu.** Spousta českých slov v kódu nejsou jména, ale výstup: `class="perex"`, `class="karta"`, `id="fasety"`, klíče frontmatteru. Přepsat je znamená rozbít `styl.css` ve vaultech, tedy záruku Z40. Použij tokenizér, který rozliší jméno od řetězce, a vynech jména za `args.` - ta vyrobil argparse z přepínačů.

**Piš jen znaky z běžné klávesnice.** Žádná dlouhá pomlčka, typografické uvozovky ani výpustka; místo nich spojovník, rovné uvozovky, tři tečky. Šipka se píše `->`.

**V `README.cs.md` a `SPEC.cs.md` je jedna věta na řádek** a řádek uvnitř odstavce končí dvěma mezerami, aby zlom prošel do HTML. Doplňuj je při každé úpravě, autor je nepíše ručně.

**V commit zprávě nepoužívej dvojité uvozovky.** Zprávu předávej souborem přes `git commit -F`, ne rourou - PowerShell 5.1 přidá do roury BOM. Git volej po jednom příkazu, zvlášť `add`, zvlášť `commit`.

**Po každé změně pusť testy**, `python test_md2html.py`. Je jich 103 a běží zhruba za sekundu.

**Testy ale nestačí.** U zásahu, který nemá měnit výstup, postav navíc PKVault starou i novou verzí a porovnej - testy pokrývají konvence, ne každý detail vzhledu.

Pravidla pocházejí z `_JDStandards` (`dokumentace_JD.md`, `git_JD.md`). Tenhle repozitář není jejich cílem, takže se sem nekopírují a jsou tu opsaná jen ta, která se ho týkají.
