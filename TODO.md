# TODO

💰 = drahé (agent / scraping), ostatní je práce nad daty, která už leží na disku.

## Hotovo
- [x] Rejstřík škol (126 maturitních škol), mapa (RÚIAN)
- [x] Pilíř A přidaná hodnota, B maturita, E zájem (CERMAT)
- [x] Pilíř C excelence (olympiády, SOČ, Eurorebus; 98 % spárováno)
- [x] Výňatky ČŠI v detailu školy
- [x] Řazení podle souhrnu

## Rozdělaná data (agenti zastaveni 4. 10., výstupy jsou na disku, nezkontrolované)
- [x] `data/excelence.csv` (392 řádků): program Excelence SŠ. Zkontrolovat roky a párování, porovnat s pilířem C. Možná ho nahradí nebo zkalibruje. → `notes/excelence.md`: jen 2013–2019, r = 0,79 s pilířem C. Nebodovat.
- [x] `data/vs_admissions_vyrocni_zpravy.csv` (272 řádků): přijetí na VŠ z výročních zpráv. Zjistit pokrytí, jestli stačí na pilíř D. → `notes/vyrocni_zpravy_D_F.md`: nestačí (11 škol, strop). Zobrazeno jako údaj školy.
- [x] `data/finance.csv` (8 640 řádků): Monitor státní pokladny. Náklady na žáka jako kontext, nebodovat. → v detailu školy; `notes/finance_kraj.md`.
- [ ] `data/kraj_*.csv`: příspěvky, investice, rozpočet 2026, dotace soukromým školám. Projít, co se dá ukázat.
- [x] `data/raw/web/` (115 škol) + `notes/web_batch1_part0*.md`: výroční zprávy. Zjistit, co se stihlo vytáhnout (počty žáků, odchody → pilíř F). → nestačí, viz `notes/vyrocni_zpravy_D_F.md`.

## Další kroky (podle priority)
1. [x] Vyhodnotit rozdělaná data výše (zbývá jen kraj_*.csv)
2. [x] Pilíř D: z veřejných dat nejde. Zbývá jen žádost podle 106/1999 (viz níže).
3. [ ] Pilíř F: výroční zprávy nestačí. odchody z výročních zpráv; jinak od 2028 hrubý odhad (přijatí 2024 → přihlášení k maturitě)
4. [x] Ručně: 8 nejasných názvů škol v olympiádách (`data/olymp_school_overrides.csv`): Frenštát přiřazen, 3× ZŠ, „SPŠ Ostrava" a „POJ F-M" neidentifikovatelné
5. [x] Ověřit 28 přepsaných výsledků jazykových olympiád: 3/3 namátkově sedí, zapojeno
6. [x] Nastavitelné váhy pilířů na stránce (posuvníky A, B, C, E; přepočítá tabulku i mapu)
7. [x] Nejistota: přidaná hodnota stažená k průměru podle spolehlivosti N/(N+40), spolehlivost v detailu
8. [-] ~~💰 Dosbírat výroční zprávy~~: zrušeno, D/F z nich nejdou
9. [ ] 💰 Náboj, Astronomická olympiáda do pilíře C
11. [ ] Žádost na MŠMT podle 106/1999: počty žáků po ročnících a školách (F) a přechod absolventů na VŠ podle SŠ (D, z SIMS/matriky). Musí poslat Jakub.
10. [ ] Skript na stažení surových dat (aby šel celý výpočet zopakovat z repozitáře)

## Rozhodnutí
- Repo a stránka jsou veřejné (GitHub Pages zdarma jen pro veřejné repo). Jakub to zatím nikde nesdílí.
- Žádná jména ani iniciály žáků v repu (`data/olymp_msk*.csv` je v .gitignore).
