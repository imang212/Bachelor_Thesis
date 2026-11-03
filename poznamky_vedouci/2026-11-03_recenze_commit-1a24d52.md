# Poznámky vedoucího — recenze nové verze commit `1a24d52`

*Datum: 3. 11. 2026 | Autor poznámek: Ing. Roman Vaibar, Ph.D., MBA (vedoucí práce)*

Opakovaná recenze po reorganizaci repositaři (repo public release `b8dc9a9` + 4 work commits → `1a24d52`).
Srovnání s předchozí verzí `272680e` (viz `2026-10-26_recenze_commit-272680e.md` a addendum k `729b979`).

Student odpověděl na předchozí recenzi výrazně a v celém rozsahu — viz níže.

## Co se ZLEPŠILO (kredit za revizi)

1. **Metodika GPU-vs-Hailo srovnání sjednocena na stejný model YOLOv8m** — nově přibyl
   měřený `results/recording_20261030_141106_GPU_yolov8m_stats.json`
   (5 113 snímků, 199,43 s, **25,64 FPS**), staré GPU měření (yolov11l, 15 FPS vstupní strop)
   ponecháno jako historická s výrazným přejmenováním `_yolov11l_`. Text práce (kap. 4)
   přepisuje metodiku: stejná architektura sítě, shodný crop 640×640, identický
   pětiúhelníkový polygon ROI, sjednocené prahy (conf 0,60; NMS IoU 0,50), vysvětlený
   rozdíl počtu snímků (4 957 vs 5 113) jako důsledek `queue leaky=downstream max-size-buffers=5`
   v GStreameru vs. bezztrátná blokující fronta na PC. Původní „blokující" bod 1 recenze je
   tím podstatně vyřešen — viz ale nové poznámky k zbytkovým metodickým hranicím.
2. **Matice záměn metodicky upřesněna** — text explicitně označuje aritmetický
   odvoz jako metodické omezení, uvádí důvod (absence snímkové IoU anotace GT) a
   navrhuje kompenzaci (MOTA/IDF1 nad annotated datasetem pro budoucí práce).
   Splněno dle body 2 z původního seznamu — v akceptovatelné formě.
3. **Latence vs. propustnost striktně odlišená** — text (kap. 4) explicitně rozlišuje
   „převrácenou hodnotu propustnosti" 34,02 ms a end-to-end latenci živého RTSP kanálu
   (≈185–200 ms kvůli `rtspsrc latency=150` + `leaky=downstream`). Původní bod 3 vyřešen.
4. **Modulární struktura LaTeX práce** — původní 1 228-řádkový `Bachelor_thesis.tex`
   nahrazen hlavním `Bachelor_Thesis_CS.tex` (219 řádků) + 8 `\input` kapitol v
   `thesis_text/chapters/cs/`. Splněno dle body 7 z původního seznamu.
5. **Modulární struktura GPU skriptu** — `pc_src/yoloTrafficDetectionSystem_PC_GPU.py`
   z 1 107 řádků na **760**; nově oddělený `pc_src/traffic_stats.py` (239 řádků)
   pro agregaci metrik; `client_API.py` (549 řádků) odstraněn (funkčnost přesunuta
   do `API_with_streamlit.py` na RPi straně). Částečné splnění body 7.
6. **Oprava regression z commitu `729b979`** — `rpi_src/pipeline/API_with_streamlit.py`
   nyní používá `get_db_config()`/`get_mqtt_config()` z `common/config.py`
   (ř. 28, 30–31), `DB_CONFIG`/`MQTT_CONFIG` jsou proměnné, ne chybějící globály.
   Původní bod 5 (NameError) vyřešen.
7. **Oprava nefunkčního importu `Config`** — `pc_src/yoloTrafficDetectionSystem_PC_GPU.py`
   už neimportuje `from common.config import Config` (třída neexistuje); z `common.config`
   importuje funkce `get_camera_rtsp_url()`. Duplicitní `MQTTPublisher` import odstraněn.
   Původní bod 4 vyřešen.
8. **Credentials z aktuálního stromu odstraněny** — `grep -rn "REDACTED_CAMERA_PASS\|REDACTED_MQTT_PASS"
   rpi_src/ pc_src/ common/ docs/ thesis_text/chapters/` vrací nula výskytů (jediná
   zmínka je v těchto poznámkách vedoucího). `.env.example` obsahuje jen placeholdery.
   Původní bod 6 je vyřešen **na úrovni aktuálního stromu** — viz ale zbytkové poznámky
   k rotaci a historii.
9. **Nový Docker simulaci (rpi_src/docker/)** — `docker_simulation/` přejmenováno
   na `rpi_src/docker/`; kompletní simulace s mediаmtx RTSP serverem, ffmpeg simulatorem
   kamery, Hailo pipeline kontejnerem, DB subscriberem, API a dashboardem.
   Pinnované image (`postgres:15`, `mediаmtx:1.9.3`, `ffmpeg:6.1-alpine`),
   zdokumentovanou architekturu s diagramem v README. Původní bod 9 (docker cesty)
   vyřešen pro rpi side; `pc_src/docker-compose.yml` má nyní správné relativní cesty
   a pinnovaný image `ultralytics/ultralytics:8.3.0`.
10. **CI (`.github/ci/ci.yml`) + testy (`tests/`)** — pytest unit testy ověřují
    `get_mqtt_config`/`get_db_config`/`get_camera_rtsp_url` + ROI polygon;
    CI job běží `pytest tests/` + `docker compose config` pro obě compose soubory;
    druhý job nasazuje k8s deploy. Původní bod 10 vyřešen (viz ale pozn. 1 níže).
11. **Git LFS zavedeno** — `.gitattributes` s `videos/sample_video.mp4` pod LFS;
    `.gitignore` rozšířeno o `.hef`, `.pt`, `.onnx`, `.har`, datasety, wheels.
    Původní bod 13 částečně vyřešen (viz pozn. 3 níže).
12. **Rebrand + MIT license** — README s badges (Hailo-8, YOLOv8m, MQTT, PostgreSQL,
    Docker, MIT), `LICENSE` MIT, struktura repo čitelná; příloha 7 (`07_appendices.tex`)
    tabulka struktury úložiště aktualizovaná na nové cesty (`common/`, `pc_src/`,
    `rpi_src/`, `results/`, `thesis_text/chapters/`). Původní body 8 a 11 vyřešeny.
13. **Komentář pro Patrika odstraněn** — původní ř. 1126 `% POZNÁMKA PRO PATRIKA: …`
    již v textu není. Původní bod 11 částečně vyřešen.

## Stav předchozích požadavků (recenze 26. 10. 2026)

| # | Požadavek | Stav | Komentář |
|---|---|---|---|
| 1 | Opravit metodiku GPU-vs-Hailo srovnání | ✅ vyřešeno | Stejný model YOLOv8m, stejný polygon ROI, sjednocené prahy; rozdíl 4 957 vs 5 113 snímků metodicky vysvětlen (leaky queue). Zbylí jen drobné hranice v body 1 níže |
| 2 | Zpřesnit matici záměn | ✅ vyřešeno | Explicitní omezení metodiky + plán (MOTA/IDF1) v Diskuzi a Závěru |
| 3 | Opravit záměnu latence/propustnosti | ✅ vyřešeno | Text kap. 4 striktně odlišuje převrácenou hodnotu FPS a end-to-end latenci |
| 4 | Opravit import `Config` + duplicitní `MQTTPublisher` | ✅ vyřešeno | Importy opraveny, ověřeno |
| 5 | Opravit regression `NameError` v `API_with_streamlit.py` | ✅ vyřešeno | `get_db_config()`/`get_mqtt_config()` z `common/config.py` |
| 6 | Odstranit zbytková RTSP/MQTT hesla + **rotace hesel** | ⚠️ částečně | Aktuální strom čistý; **rotace hesel (MQTT broker i kamera) zůstává povinná** — hesla jsou v git historii od `0f39998` a repo je veřejné |
| 7 | Rozdělit soubory > 1 000 řádků | ⚠️ částečně | tex ✅ (8 kapitol), GPU skript ✅ (760 + 239); `rpi_src/pipeline/API_with_streamlit.py` stále **1 196 řádků** |
| 8 | Sjednotit ROI obou platforem | ✅ vyřešeno | Identický pětiúhelníkový polygon normalizovanými vrcholy; v Diskuzi i u měření |
| 9 | Opravit cesty v docker-compose + pinnovat image + shapely | ✅ vyřešeno | Cesty `../` správně; image pinnované (`ultralytics:8.3.0`, `mediаmtx:1.9.3`, `ffmpeg:6.1-alpine`); `shapely>=2.0.1` v `pc_src/requirements.txt` |
| 10 | Funkční testy projektové logiky + CI | ✅ vyřešeno | `tests/test_common.py` (config + ROI); `.github/ci/ci.yml` — viz ale pozn. 1 níže (cesta v CI) |
| 11 | Aktualizovat tabulku struktury + odstranit komentář + opravit 69,35 | ✅ vyřešeno | Tabulka v `07_appendices.tex` aktualizovaná; komentář odstraněn; 69,35 ms odstraněn s původním měřením |
| 12 | Zmínit Docker/k8s nasazení v textu práce | ✅ vyřešeno | Nová sekce 3.2 „Modularizace kódu, správa konfigurace a kontejnerizace (Docker)"; k8s v CI; Závěr zmíní kontejnerizaci |
| 13 | Git LFS / úklid historie | ⚠️ částečně | `.gitattributes` pro `videos/sample_video.mp4`; LFS funkční; **velikost `.git` vzrostla na ~1,2 GB** — bináry z předchozích verzí (PDF 53 MB, 39 MB, `.hef`, datasety) stále v historii od `b8dc9a9`; PDF výstup práce (5,9 MB) není pod LFS |

## NOVÉ PROBLÉMY (aktuální verze `1a24d52`)

**A) CI — cesta k rpi compose souboru je zastaralá (blokující)**

1. `.github/ci/ci.yml` (ř. 34) odkazuje
   `docker compose -f rpi_src/docker_simulation/docker-compose.yml config > /dev/null`,
   ale složka `rpi_src/docker_simulation/` již neexistuje — složení bylo přejmenováno
   na `rpi_src/docker/` (viz `rpi_src/docker/docker-compose.yml`). CI job
   `test-and-validate` tedy **padne na `config` kroku** a k testovacím krokům
   ani nedojde. Opravit cestu na `rpi_src/docker/docker-compose.yml`.
   Doporučuji zároveň ověřit, že `pytest` i `docker compose config` projdou i na
   druhém CI environmentu (aktuálně jen `ubuntu-latest`).

**B) Bezpečnost — aktuální stav je čistý, ale rotace hesel a historii**

2. **Rotace hesel zůstává povinná.** I když `grep -rn "REDACTED_CAMERA_PASS\|REDACTED_MQTT_PASS"`
   v aktuálním stromu vrací nula, hesla jsou v git historii od commitu `0f39998`
   a repo je veřejné (`imang212/Bachelor_Thesis`). Stažení souborů z HEAD nestačí.
   Doporučuji:
   - rotace hesla MQTT brokeru na `mqtt.portabo.cz` (použité ve `.env`),
   - rotace hesla IP kamery na `192.168.37.99` (RTSP),
   - případně rotace DB hesla, pokud bylo kdykoliv commitnuté,
   - případný úklid historii (BFG / `git filter-repo`), pokud je repo
     definitivně veřejné a obsahuje citlivá hesla.
   Potvrzení rotace prosím zaznamenat do poznámek vedoucího (nebo přímo do commitu).

**C) Rozsah a velikost**

3. **`.git` ≈ 1,2 GB** — soubory z předchozích verzí (PDF 53 MB `yolov8_architectures_make-05-00083-v2.pdf`,
   39 MB `Szeliski_Book_Computer_Vision_Draft_2020-09.pdf`, 10 MB `2e.pdf`,
   7 MB `sensors-23-07719.pdf`, 6 MB `Surveillance_Systems_3760525.pdf`, 6 MB
   `Bachelor_thesis.pdf`, 5 MB `YOLO_1506.02640v5.pdf`) jsou v commitu `b8dc9a9`
   „Initial public release" jako binárky mimo LFS. PDF výstup práce (5,9 MB)
   není pod LFS. Doporučuji:
   - velké soubory v `thesis_text/thesis_literature_resources/` přesunout pod LFS
     (přidat do `.gitattributes`),
   - `thesis_text/Bachelor_thesis.pdf` pod LFS,
   - případně `videos/sample_video.mp4` je už pod LFS — OK.
   Pokud je repo veřejné a obsahuje citlivá hesla → viz bod 2.

4. **`rpi_src/pipeline/API_with_streamlit.py` stále 1 196 řádků** — původní požadavek
   body 7 byl rozdělení velkých souborů; tex a GPU skript jsou rozdělené, ale
   `API_with_streamlit.py` zůstává monolit. Doporučuji rozdělit na separátní
   moduly: FastAPI endpointy (`api.py`), Streamlit dashboard (`dashboard.py`),
   MQTT/DB wiring (`services.py`), případně sdílené konstanty (`config_local.py`).
   Toto je nízkopriornitní ale dlouhodobě potřebné.

**D) Drobnosti**

5. **Abstrakt — zbytková stará verze.** V `Bachelor_Thesis_CS.tex` (ř. 195, okomentováno)
   zůstává anglický abstrakt v původní podobě (cyklisté, obecnější popis).
   Řádek 197 je nový. Ověřit, který z nich je reálně vytažen jako „Abstract"
   v PDF výstupu; doporučuji starý okomentovaný řádek odškrtnout (nejen `%`).

6. **Tabulka 4.1 (confidence_stats) — Person řádek je plně 0.** Obojí platformy
   detekovaly 0 chodců v ROI (což je správně — chodec je mimo polygon),
   takže řádek je informativně nulový. Je OK, ale doporučuji buď odstranit
   (a v poznámce pod tabulkou vysvětlit, proč chodec není v detekcích),
   nebo zanechat s explicitní poznámkou „chodec byl v GT, ale leží mimo polygon ROI
   a je tak u obou platforem odfiltrován".

7. **`rpi_src/docker/Dockerfile` a `Dockerfile.pipeline`** — doporučuji ověřit,
   že základní image je pinnované (jako v compose souboru) a že `Dockerfile.pipeline`
   nainstaluje všechny runtime závislosti (GStreamer pluginy, Hailo runtime,
   `python3-gi`), nejen development balíčky. Bez tohoto se simulace s `--build`
   nespustí na čistém stroji.

8. **`docs/diagrams/`** — `architecture.png` a `diagram_converter.py` jsou v docs;
   odesílám jako doplňující materiál — ověřit, že `\includegraphics` v textu
   odkazuje na správnou cestu (kap. 2 nebo 3). V minulé recenzi jsem to
   ověřil pro ř. 607; po rozdělení na kapitoly je `\includegraphics` v jiné
   souboru (02_system_design.tex / 03_implementation.tex).

## Aktualizovaný seznam požadavků

| # | Požadavek | Priorita |
|---|---|---|
| 1 | Opravit cestu `rpi_src/docker_simulation/` → `rpi_src/docker/` v `.github/ci/ci.yml` (ř. 34); ověřit, že CI job `test-and-validate` proběhne | blokující |
| 2 | Potvrdit rotaci hesel (MQTT broker `mqtt.portabo.cz`, IP kamera RTSP `192.168.37.99`, případně DB) a zaznamenat potvrzení; volitelně úklid git historie (BFG/filter-repo) | vysoká (bezpečnost) |
| 3 | Rozdělit `rpi_src/pipeline/API_with_streamlit.py` (1 196 řádků) na menší moduly (FastAPI endpoints, Streamlit dashboard, MQTT/DB wiring) | střední |
| 4 | Přesunout velké binárky pod LFS: `thesis_text/Bachelor_thesis.pdf`, soubory v `thesis_text/thesis_literature_resources/` (PDF > 5 MB) | střední |
| 5 | V `rpi_src/docker/Dockerfile.pipeline` ověřit, že jsou pinnované image a všechny runtime závislosti (GStreamer pluginy, Hailo runtime) nainstalovány — simulace má projít `docker compose up --build` na čistém stroji | střední |
| 6 | Čistě odškrtnout (nejen okomentovat) starou verzi abstraktu v `Bachelor_Thesis_CS.tex` ř. 195; ověřit, že se v PDF tiskne nová (ř. 197) | nízká |
| 7 | Tabulka 4.1 (confidence_stats) — buď odstranit Person řádek (vše 0) a dodat poznámku pod tabulkou, nebo zanechat s explicitní poznámkou o odfiltrování chodce | nízká |
| 8 | Ověřit, že `\includegraphics{architecture.png}` v kapitole (02 nebo 03) vede na správnou cestu po rozdělení tex | nízká |

## Celkový dojem

Výrazný posun — **původní blokující body 1, 4, 5, 6 (aktuální strom), 9, 10, 11, 12 jsou vyřešeni**
a práce je metodicky i technicky mnohem odolnější proti útokům na obhajobě.
Nový měřicí soubor `GPU_yolov8m` s 25,64 FPS a 94,07 % Accuracy_count
(proti 92,37 % u Hailo) je přesně to, co jsem v bodě 1 původní recenze požadoval —
srovnání stejného modelu na stejném videu se stejnou ROI.
Diskuze a Závěr tento výsledek konzistentně reflektují a explicitně uvádějí
zbytlé metodické hranice (leaky queue, aritmetická matice záměn) — to je
poctivé a správné.

Repositorium je po reorganizaci (public release `b8dc9a9`) **čistší a
lépe documentované** — `common/`, `.env.example`, LFS, CI, Docker simulace s
README, rozdělený tex, MIT license. To je výrazný krok ke kvalitě,
kterou očekávám od bakalářské práce s praktickým nasazením.

**Zbývající blokující bod je jeden**: CI job `test-and-validate` padne na
zastaralé cestě `rpi_src/docker_simulation/` (bod 1 aktualizovaného seznamu).
To je rychle opravitelné (jedno řádek), ale **musí projít** před další
verzí — jinak CI je nevěrohodné jako zdroj informace pro budoucí změny.
Body 2 (rotace hesel) je povinný z bezpečnostních důvodů — stažení souborů
z HEAD nestačí, když je repo veřejné a hesla jsou v historii.

Zbytek jsou nižší priority (LFS pro velká PDF, rozdělení `API_with_streamlit.py`,
čistota abstraktu). Před odevzdáním a obhajobou doporučuji jedno kolečko
`git pull` + `pytest` + `docker compose config` u obou compose souborů
a ověření, že PDF se přeloží. Pak je práce z mého pohledu hotová.

Příští kontrola po opravě bodů 1 (CI) a 2 (rotace).
