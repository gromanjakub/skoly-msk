# TODO

Stav k 4. 10. 2026. Stránka: https://gromanjakub.github.io/skoly-msk/ · přepočet: `scripts/rebuild.sh [--fetch]`
Poznámky ke každému zdroji jsou v `notes/` (lokálně, nejsou v gitu).

## Hotovo
- Seznam 129 škol (rejstřík MŠMT, včetně škol jen s nástavbou)
- Pilíře A přidaná hodnota (stažená k průměru podle spolehlivosti), B maturita, C excelence, E zájem
- Nastavitelné váhy, filtr podle typu a oboru, řazení podle souhrnu, odkaz na školu (`#s=REDIZO-TYP`), CSV ke stažení
- Detail školy: čísla pilířů, vývoj 2015–2026, angličtina, naplněnost, hospodaření, údaj školy o VŠ, výňatek ČŠI, historie (jen část)
- Metodika `docs/metodika.md`; prověřené a zamítnuté zdroje: InfoAbsolvent, NPI nezaměstnanost, výroční zprávy pro D/F

## Rozdělané (agenti zastaveni, výstupy na disku)
1. [ ] **Historie, zbytek.** Hotovo jen MO/FO/ChO/P/EO (`data/historie_sci.csv`, 38 řádků, `notes/historie_sci.md`).
   Stažená surová data bez výstupu: `data/raw/historie/{soc,bio,intl,zo,do}/`. Jazyky, ČJ, Eurorebus, Náboj a astronomie zatím nezačaté.
   Po doplnění přidat soubor do `hist` v `scripts/build_site.py` a upravit poznámku v `histBlock` v `docs/index.html`.
   Kontrola: GMK Bílovec má mít 4× vítěze FJ (asi 2015/16–2018/19, https://www.gmk.cz/mes-amis-a-mon-ami/).
2. [ ] **Tabulky Excelence** (`excelence.nidm.cz/result-table/show/N`, ~980 snímků ve Wayback): IČO školy + umístění ve všech soutěžích. Fetcher v `scripts/historie_sci.py` skončil, když Wayback vypadl (17 uloženo).

## Další
3. [ ] **Žádost na MŠMT** (pilíře D a F): návrh v `notes/zadost_msmt.md`. **Posílá Jakub.**
4. [ ] Mezery v pilíři C: jazykové olympiády před 2023/24, celé výsledky olympiády v ČJ, krajská kola EO/ZO/DO/jazyků.
5. [ ] Konzervatoře (2) jako vlastní typ; praktické školy a učiliště (14) jako seznam bez hodnocení.
6. [ ] Neidentifikované názvy v olympiádách: „SPŠ Ostrava" (MO krajské), „POJ Frýdek-Místek" (FO krajské).
7. [ ] Ověřit, že `scripts/rebuild.sh --fetch` projde na čistém klonu (zatím testováno jen se staženými daty).

## Rozhodnutí
- Repo a stránka jsou veřejné (GitHub Pages zdarma jen pro veřejné repo). Jakub to zatím nikde nesdílí.
- Žádná jména ani iniciály žáků v repu (`data/olymp_msk*.csv` je v .gitignore).
- Pilíř C počítá jen 2021/22–2025/26, starší úspěchy patří do historie.
- Mapa odstraněna (k ničemu).
