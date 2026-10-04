# TODO

Postup: po jednom bodu, bez paralelních agentů. 💰 = drahé (agent / scraping), ostatní je práce nad daty, která už leží na disku.

## Hotovo
- [x] Rejstřík škol (126 maturitních škol), mapa (RÚIAN)
- [x] Pilíř A přidaná hodnota, B maturita, E zájem (CERMAT)
- [x] Pilíř C excelence (olympiády, SOČ, Eurorebus; 98 % spárováno)
- [x] Výňatky ČŠI v detailu školy
- [x] Řazení podle souhrnu

## Rozdělaná data (agenti zastaveni 4. 10., výstupy jsou na disku, nezkontrolované)
- [ ] `data/excelence.csv` (392 řádků): program Excelence SŠ. Zkontrolovat roky a párování, porovnat s pilířem C. Možná ho nahradí nebo zkalibruje.
- [ ] `data/vs_admissions_vyrocni_zpravy.csv` (272 řádků): přijetí na VŠ z výročních zpráv. Zjistit pokrytí, jestli stačí na pilíř D.
- [ ] `data/finance.csv` (8 640 řádků): Monitor státní pokladny. Náklady na žáka jako kontext, nebodovat.
- [ ] `data/kraj_*.csv`: příspěvky, investice, rozpočet 2026, dotace soukromým školám. Projít, co se dá ukázat.
- [ ] `data/raw/web/` (115 škol) + `notes/web_batch1_part0*.md`: výroční zprávy. Zjistit, co se stihlo vytáhnout (počty žáků, odchody → pilíř F).

## Další kroky (podle priority)
1. [ ] Vyhodnotit rozdělaná data výše, jedno po druhém
2. [ ] Pilíř D: podle pokrytí z výročních zpráv buď zapojit, nebo nechat „nedostupné"
3. [ ] Pilíř F: odchody z výročních zpráv; jinak od 2028 hrubý odhad (přijatí 2024 → přihlášení k maturitě)
4. [ ] Ručně: 8 nejasných názvů škol v olympiádách (`data/olymp_school_overrides.csv`)
5. [ ] Ručně: ověřit 28 přepsaných výsledků jazykových olympiád, pak zapojit
6. [ ] Nastavitelné váhy pilířů na stránce
7. [ ] Intervaly nejistoty / pásma podle velikosti školy
8. [ ] 💰 Dosbírat výroční zprávy pro zbylé školy (jen pokud se D/F ukážou jako proveditelné)
9. [ ] 💰 Náboj, Astronomická olympiáda do pilíře C
10. [ ] Skript na stažení surových dat (aby šel celý výpočet zopakovat z repozitáře)

## Rozhodnutí
- Repo a stránka jsou veřejné (GitHub Pages zdarma jen pro veřejné repo). Jakub to zatím nikde nesdílí.
- Žádná jména ani iniciály žáků v repu (`data/olymp_msk*.csv` je v .gitignore).
