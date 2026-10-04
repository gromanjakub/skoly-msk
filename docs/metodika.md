# Metodika (v0.1, pilot)

Zdroj dat pro pilíře A, B a E: CZVV (CERMAT), agregovaná data škol na data.cermat.cz. Skripty: `scripts/build_cermat.py`, `scripts/build_scores.py`, `scripts/build_site.py`.

## Jednotka srovnání

Škola × typ studia: G8, G6, G4, lyceum, SOŠ. Každý ukazatel se nejdřív porovná se školami **celé ČR ve stejné skupině oborů** (16 skupin CERMAT, např. technické obory s technickými) a převede na z-skóre. Teprve pak se skupiny oborů jedné školy spojí do typu studia (vážení počtem žáků).

Pásma: z ≥ 1 výrazně nad průměrem ČR, 0,33 až 1 nad, −0,33 až 0,33 kolem průměru, −1 až −0,33 pod, pod −1 výrazně pod. Hodnotí se jen typy studia s aspoň 10 maturanty ročně (průměr 2024–2026).

## A – přidaná hodnota

Pro každou skupinu oborů celostátně: vážená regrese průměrného percentilu školy v didaktickém testu z ČJ u maturity (roky 2022–2026) na průměrný percentil uchazečů o tutéž školu a skupinu oborů v ČJ a MA u přijímaček o 4 roky dřív (G6 o 6, G8 o 8 let). Přidaná hodnota = reziduum, tedy o kolik percentilů škola dopadla líp nebo hůř, než by odpovídalo jejím uchazečům. Shoda modelu (R²): G4 0,60, G6 0,43, G8 0,35, lycea 0,35, odborné skupiny 0,02–0,50 (`data/derived/va_fit.csv`).

Stabilita: přidaná hodnota jednoho ročníku koreluje s následujícím ročníkem téže školy r = 0,40 (celá ČR, 4 566 dvojic; G8 0,63, G4 0,34). Jeden ročník je tedy hodně zašuměný. Průměr přes až 5 ročníků má odhadovanou spolehlivost kolem 0,77 (Spearman–Brown), proto se zobrazují jen pásma. Malé školy se navíc stahují k průměru (empirický Bayes): reziduum se násobí spolehlivostí N / (N + 40), kde N je počet maturantů ve všech použitých ročnících a 40 vychází z korelace 0,40 při mediánové velikosti ročníku 27 žáků. Spolehlivost je uvedená v detailu školy.

Omezení: přijímačky do 2023 popisují **všechny uchazeče**, ne přijaté. Přijímačky 2021 byly u čtyřletých oborů dobrovolné. Maturita zahrnuje jen ty, kdo k ní došli. Škola, která slabší žáky během studia ztratí, vypadá lépe. To má zachytit pilíř F. Školy s velkým podílem žáků s jiným mateřským jazykem (mezinárodní, polské) jsou v ČJ znevýhodněné.

## B – výsledky maturity

Průměr dvou z-skóre: průměrný percentil v ČJ a podíl úspěšných z přihlášených ke společné části (2024–2026, stav po podzimu, jen prvomaturanti). Matematika se nepoužívá, protože ji volí jen část žáků.

## C – excelence

Výsledky v soutěžích 2021/22–2025/26 z veřejných výsledkových listin: celostátní kola MO, FO, ChO, BiO, olympiády v informatice, SOČ, Eurorebusu, ekonomické, zeměpisné, dějepisné, jazykových olympiád a krajská kola MO, FO, ChO, BiO a informatiky v MSK. Body: celostátní kolo 1.–3. místo 5, úspěšný řešitel 3, ostatní účastníci 1,5; krajské kolo úspěšný řešitel 0,5, ostatní 0,2. Týmový výsledek se počítá jednou. Index = body za rok na 100 žáků (počet maturantů za rok × 4). Z-skóre z log(1 + index) se počítá jen v rámci MSK, zvlášť pro gymnázia a pro lycea s odbornými školami, protože celostátní data nemáme. Pilíř se počítá za celou školu, ne zvlášť pro typ studia. Výsledky jazykových olympiád 2023/24–2024/25 existují jen jako obrázky a skeny a byly přepsané ručně (28 řádků). Namátková kontrola tří listin proti originálu: vše sedí. Názvy škol se párují s rejstříkem (98 % řádků). Známé mezery: jazykové olympiády jsou jen od 2023/24, z olympiády v českém jazyce se zveřejňuje jen první desítka, krajská kola chybí u ekonomické, zeměpisné, dějepisné a jazykových olympiád. Školy silné v humanitních oborech, jazycích a ekonomii jsou proto podhodnocené proti školám silným v přírodních vědách. Úspěchy z let před 2021/22 se záměrně nepočítají, pilíř popisuje školu, jaká je teď. Krajská kola mají olympiády hlavně gymnaziální, takže odborné školy mají cestu hlavně přes SOČ.

## E – zájem o školu

Průměr dvou z-skóre: přihlášky 1. priority na místo (logaritmus) a průměrný percentil přijatých v přijímačkách (2024–2026, 1. kolo, denní maturitní obory).

## Souhrn

Vážený průměr dostupných pilířů (A 30, B 20, C 15, E 10, přepočteno). Předběžný, dokud chybí D a F.
