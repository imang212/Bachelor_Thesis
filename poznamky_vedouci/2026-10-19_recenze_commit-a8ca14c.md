# Poznámky vedoucího — kritická recenze verze commit `a8ca14c` („Folder for videos change")

*Datum: 19. 10. 2026 | Autor poznámek: Ing. Roman Vaibar, Ph.D., MBA (vedoucí práce)*

Kritické stanovisko k textu práce (`thesis_text/Bachelor_thesis.tex`) a repozitáři ve verzi commit `a8ca14c`.

## 1. Práce je v aktuálním stavu NEDOKONČENÁ (blokující)

- **Kapitola Závěr** obsahuje pouze odrážky šablony: *„- Shrnutí dosažených cílů. - Zhodnocení přínosu… - Návrhy na další rozšíření."* Závěr není napsán.
- **Kapitola „Vyhodnocení výkonnosti systému"** končí odrážkovým seznamem úkolů: *„- dosažené FPS - latence - využití CPU - vliv akcelerátoru"* — žádná měření nejsou uvedena. Přitom výkon je v edge práci klíčová věc (a ve `pipelene_tested_videos/` existují JSON se statistikami — data má, nezpracoval je).
- **Kapitola Externí přílohy** obsahuje instrukce ze šablony („V této kapitole stačí uvést…") a popisuje soubory `ki-thesis.pdf`, `thesis.bib`, které v repo neexistují.

## 2. Metodika vyhodnocení — slabá a vnitřně nekonzistentní

- **Tabulka výsledků si neodpovídá sama se sobě:** sloupce Hailo 120+4+3+1 = 128, v tabulce uvedeno 127; GPU 108+11+12+0 = 131, uvedeno 132.
- **„Accuracy 0.73 / 0.74" bez definice metriky** — nikde není uvedeno, jak se accuracy počítá, na jakém základě a úrovni. Chybí precision/recall, mAP, případně tracking metriky (MOTA, IDF1).
- **Nespravedlivé srovnání:** Hailo i GPU řešení měly různé ROI oblasti („mírně se lišily") — počítají nad jinou plochou. Text to přiznává, ale nekvalifikuje to; srovnání počtů je pak spíš ilustrativní než vědecké.
- **Nevysvětlený rozpor u Bus/Truck:** GPU detekoval 11 autobusů proti GT 3 a 12 trucků proti GT 6 — 2–4× falešně pozitivních detekcí, přesto text konstatuje, že GPU „dosahuje vyšší přesnosti" a „přesně odpovídá ručnímu měření" (platí jen pro Car).
- **Rozsah experimentu = 4 minuty jednoho videa** (v sněžení). Jeden klip bez opakování, bez jiného počasí/lokality/denní doby a bez odhadu nejistoty nedovoluje zobecnění.

## 3. Nesoulad mezi abstraktem/zadáním a výsledky

- Abstrakt (i zadání) slibuje detekci a klasifikaci vozidel, chodců a cyklistů a „průchody definovanou oblastí". Výsledky: Person = 1 (GPU 0), **Bicycle = 0 — cyklisté chybí úplně**.
- Chybí směr průjezdu (direction), který zadání explicitně vyžaduje při ukládání dat.

## 4. Teorie a citace — příliš tenké a se slabými zdroji

- Teoretická část (~550 řádků, 6 sekcí) je spíš přehled než analytický text; chybí srovnání přístupů (SSD vs. YOLO vs. dvoufázové detektory), o kterém zadání píše.
- Bibliografie: 28 zdrojů, z toho řada neakademických (blog LeimaO, YouTube kanál AugmentedStartups, e-shop Arducam). Chybí: ByteTrack (používaný!), práce o kvantizaci/edge optimalizaci, kontext dopravních systémů v ČR.
- Citace shluknuty na konec dokumentu před `\printbibliography` — část zdrojů není v textu aktivně užita.

## 5. Implementační/technická kritika

- **Kompromitované přihlašovací údaje v kódu** (MQTT heslo k `mqtt.portabo.cz`, DB hesla, interní IP) ve veřejném repozitáři. Nutné rotovat hesla a odstranit z kódu (proměnné prostředí).
- **Duplikovaný kód** `pc_src` vs `rpi_src` (DatabaseManager, MQTTClient…) se rozchází — chybí společný balíček.
- **Žádné testy, žádné CI, žádný linting.**
- V repo: `__pycache__` committed, ~1,6 GB binárních dat (kalibrační dataset, modely, videa) — repozitář není udržovatelný.

## 6. Souhrn — požadavky před odevzdáním

| # | Požadavek | Priorita |
|---|---|---|
| 1 | Doplnit kapitoly Závěr a Vyhodnocení výkonnosti (data už jsou v JSON) | blokující |
| 2 | Předělat metodu vyhodnocení: definovat metriky, přidat precision/recall, opravit tabulku, rozebrat falešné detekce Bus/Truck | blokující |
| 3 | Srovnat oba systémy na stejné ROI, nebo srovnání kvalifikovat | vysoká |
| 4 | Sladit abstrakt s realitou (cyklisté/chodci) — doplnit nebo ubrat | vysoká |
| 5 | Odstranit credentials z repo + rotovat hesla | blokující (bezpečnost) |
| 6 | Rozšířit bibliografii o akademické zdroje | střední |
| 7 | Zredukovat repo (LFS) + sdílený balíček + min. 1 test | střední |

**Celkový dojem:** technická část je nadstandardní a nad mnoha BP, ale text je ve fázi polotovaru — vyhodnocení je nejtenčím místem a právě ono bývá u obhajoby rozsekáno.
