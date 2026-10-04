# Metodika (v0.1, pilot)

Zdroj dat pro pilíře A, B a E: CZVV (CERMAT), agregovaná data škol na data.cermat.cz. Skripty: `scripts/build_cermat.py`, `scripts/build_scores.py`, `scripts/build_site.py`.

## Jednotka srovnání

Škola × typ studia: G8, G6, G4, lyceum, SOŠ. Každý ukazatel se nejdřív porovná se školami **celé ČR ve stejné skupině oborů** (16 skupin CERMAT, např. technické obory s technickými) a převede na z-skóre. Teprve pak se skupiny oborů jedné školy spojí do typu studia (vážení počtem žáků).

Pásma: z ≥ 1 výrazně nad průměrem ČR, 0,33 až 1 nad, −0,33 až 0,33 kolem průměru, −1 až −0,33 pod, pod −1 výrazně pod. Hodnotí se jen typy studia s aspoň 10 maturanty ročně (průměr 2024–2026).

## A – přidaná hodnota

Pro každou skupinu oborů celostátně: vážená regrese průměrného percentilu školy v didaktickém testu z ČJ u maturity (roky 2022–2026) na průměrný percentil uchazečů o tutéž školu a skupinu oborů v ČJ a MA u přijímaček o 4 roky dřív (G6 o 6, G8 o 8 let). Přidaná hodnota = reziduum, tedy o kolik percentilů škola dopadla líp nebo hůř, než by odpovídalo jejím uchazečům. Shoda modelu (R²): G4 0,60, G6 0,43, G8 0,35, lycea 0,35, odborné skupiny 0,02–0,50 (`data/derived/va_fit.csv`).

Omezení: přijímačky do 2023 popisují **všechny uchazeče**, ne přijaté. Přijímačky 2021 byly u čtyřletých oborů dobrovolné. Maturita zahrnuje jen ty, kdo k ní došli. Škola, která slabší žáky během studia ztratí, vypadá lépe. To má zachytit pilíř F. Školy s velkým podílem žáků s jiným mateřským jazykem (mezinárodní, polské) jsou v ČJ znevýhodněné.

## B – výsledky maturity

Průměr dvou z-skóre: průměrný percentil v ČJ a podíl úspěšných z přihlášených ke společné části (2024–2026, stav po podzimu, jen prvomaturanti). Matematika se nepoužívá, protože ji volí jen část žáků.

## E – zájem o školu

Průměr dvou z-skóre: přihlášky 1. priority na místo (logaritmus) a průměrný percentil přijatých v přijímačkách (2024–2026, 1. kolo, denní maturitní obory).

## Souhrn

Vážený průměr dostupných pilířů (A 30, B 20, E 10, přepočteno). Předběžný, dokud chybí C, D a F.
