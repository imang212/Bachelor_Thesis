# Poznámky vedoucího — týdenní kontrola, recenze commitu `9b5472b`

*Datum: 16. 11. 2026 | Autor poznámek: Ing. Roman Vaibar, Ph.D., MBA (vedoucí práce)*
*Týden od minulé recenze (`2026-11-09_recenze_commit-6d589a7.md`).*

## Shrnutí týdenní aktivity

Čtyři commity — dokončení obou nízkopriorních bodů z minulé recenze + finální
polishing textu práce:

| Commit | Datum | Obsah |
|---|---|---|
| `1610818` | 12. 11. | **Pinnování Dockerfile na digest** (`sha256:c1fd49c1…` v `Dockerfile.pipeline` i `Dockerfile.api`), reorganizace `script-guide.md` (204 řádků), fix `video_crop.py` |
| `c7dcd99` | 12. 11. | Vyloučení LaTeX šablon a notebooků ze statistik jazyků GitHubu (`linguist-documentation`) |
| `a1027ac` | 13. 11. | **Hlavní obsahová rekvizice**: úprava kap. 1–7 (teorie YOLO/SORT/DeepSORT, evaluace s GT=112), odstranění starých `DB_diagram.pdf` (4 209 řádků) a `ERD_diagram.png`, doplnění `preprocessing_gstreamer_final.jpg` do textu, 9 nových odkazů v `references.bib`, `script-guide.md` jako dokumentace |
| `9b5472b` | 16. 11. | **Dnešní commit — typografické opravy**: kap. 1 (maďarský algoritmus, GoogLeNet, konvoluce), kap. 2–7 drobné úpravy, přechod na `\acs{}` pro \acs{ROI}, \acs{GPU} atd. |

## Co se hotovo / ověřeno

### ✅ Bod A (minulá recenze) — Dockerfile pinnování s digestem

Oba Dockerfile (`Dockerfile.pipeline`, `Dockerfile.api`) nyní obsahují:
```
FROM python:3.11.10-slim-bookworm@sha256:c1fd49c15e2a1db5afb6b9a6f4421b606760c3638698531b53e7b6a12870fe8
```
Digest odpovídá oficiálnímu `python:3.11.10-slim-bookworm` na Docker Hub. **Hotovo.**

### ✅ Bod B (minulá recenze) — Eventuální další rozdělení `API_with_streamlit.py`

Soubor zůstává na **615 řádkách** (pod hranicí 700). Není potřeba dále rozdělovat.
`streamlit_dashboard.py` (447 řádků) zůstává samostatný. **Hotovo.**

### ✅ Reorganizace `docs/diagrams/` + text konzistentní s modelem

Staré `DB_diagram.pdf` (4 209 řádků LaTeX) a `ERD_diagram.png` odstraněny
(commit `a1027ac`). V kap. 2 se odkazuje pouze na `erd_diagram.png` (aktuální,
identický s `docs/diagrams/erd_database.png`). Diagramový kanál je sjednocený.

### ✅ Jazykové statistiky GitHubu

LaTeX šablony (`thesis_text/**`), notebooky (`rpi_src/model_compile/*.ipynb`)
a `docs/documentation.tex` vyloučeny ze statistik (`linguist-documentation`).
Repo je tak správně klasifikováno jako Python, ne LaTeX.

### ✅ `script-guide.md` — praktická příloha

204 řádků s přímými odkazy na scripts v repozitáři + oficiální Hailo GitHub repo
(branches `25.7.0`, `v5.2.0`) + odkaz na Hailo Developer Zone pro `.deb`/`.whl`.
Správně umístěno do `rpi_src/pipeline/` jako doplňující dokumentace.

### ✅ `preprocessing_gstreamer_final.jpg` — nový obrázek v textu

Přesunuto z `results/` do `thesis_text/images/` a zařazeno v kap. 1
(`\includegraphics{images/preprocessing_gstreamer_final.jpg}` v `01_theory.tex`).
Obrázek ukazuje GStreamer preprocessing pipeline — metodicky dobře doplněno.

### ✅ Citace a reference

Kap. 1 (teorie) obohaceno o 9 nových citací v `references.bib`
(szelski_computer_vision_2022, lin_coco_2014, etc.). Text je nyní
reference-rich, což je pro Bakalářskou práci v pořádku.

## ❌ NOVÉ PROBLÉMY (blokující pro odevzdání)

### **P1) Dvojitá fráze v `01_theory.tex` ř. 169 — CHYBA**

Commit `9b5472b` nechal v textu **dvojitou frázi**:
```
...z~přesným rozlišením $448 \times 448$ pixelů. 
Samotná síť se skládá z~24 konvolučních vrstev
Samotná síť se skládá z 24 konvolučních vrstev\footnote{Konvoluce...}
, které slouží k~postupné a~hluboké extrakci vizuálních příznaků z~obrazu.
, které slouží k~postupné a hluboké extrakci vizuálních příznaků z~obrazu (od jednoduchých hran až po komplexní tvary vozidel).
```

**Je to textová duplikace** — fráze „Samotná síť se skládá z 24 konvolučních vrstev"
a „, které slouží k~postupné extrakci..." se opakuje dvakrát.
Příčina: při přidávání `\footnote{Konvoluce...}` se starý text nevrátil a
nový se přidal vedle.

**Oprava:** odstranit jednu z frází (zůstat s tou, která má `\footnote`):
```
...z~přesným rozlišením $448 \times 448$ pixelů. 
Samotná síť se skládá z 24 konvolučních vrstev\footnote{Konvoluce v~počítačovém vidění...}
, které slouží k~postupné a~hluboké extrakci vizuálních příznaků z~obrazu (od jednoduchých hran až po komplexní tvary vozidel).
Za nimi následují 2 plně propojené vrstvy...
```

**Dopad na obhajobu:** komise si všimne textové duplikace při čtení kap. 1 —
metodický kontrast. Nutno opravit.

### **P2) Rozbitá citace v `01_theory.tex` ř. 173**

```
...datasetu \acs{COCO}\footnote{...} (z~angl. \textit{Common Objects in Context}).~\cite{lin_coco_2014}. Tento dataset...
```

**Bod+mezerní mezerník** `).~\cite{...}.` — je to zbytečný `~` a bod před `\cite`.
Správně by mělo být:
```
...datasetu \acs{COCO}~\cite{lin_coco_2014} (z~angl. \textit{Common Objects in Context}). Tento dataset...
```
nebo
```
...datasetu \acs{COCO}\footnote{...} (z~angl. \textit{Common Objects in Context})~\cite{lin_coco_2014}. Tento dataset...
```

**Dopad:** malá typografická chyba, ale komise si všimne rozbité citace.

### **P3) Zbytečný `deepsort_algorithm_principe_CZ.png` vs `DeepSORT_algortitm_principe.png`**

V `thesis_text/images/` jsou **tři** verze DeepSORT obrázku:
- `deepsort_algorithm_principe_CZ.png`
- `deepsort_algoritm_principe.png`
- `DeepSORT_algortitm_principe.png` (typo: „algortitm")

V kap. 1 se odkazuje pouze na `deepsort_algorithm_principe_CZ.png`.
Ostatní dva jsou **zbytečné** — odstranit.

**Dopad:** čistota repozitáře — komise si všimne trojího stejného obrázku.

### **P4) Staré `sort_algorithm_principe*.png`**

Stejný problém — `sort_algorithm_principe_CZ.png` + `sort_algorithm_principe.png`.
V textu se odkazuje pouze na `sort_algorithm_principe_CZ.png`.
Ostatní je zbytečné.

## Příští kontrola — blokující body

| # | Požadavek | Priorita |
|---|---|---|
| 1 | **Opravit dvojitou frázi v `01_theory.tex` ř. 169** — odstranit jednu z frází „Samotná síť se skládá..." | **blokující** |
| 2 | **Opravit rozbitou citaci v `01_theory.tex` ř. 173** — `).~\cite{lin_coco_2014}.` → `(z~angl. ...)~\cite{lin_coco_2014}.` | **blokující** |
| 3 | **Smazat zbytečné `thesis_text/images/`: `DeepSORT_algortitm_principe.png`, `sort_algorithm_principe.png`** | střední |
| 4 | **Smazat zbytečné `deepsort_algoritm_principe.png`** (typo) | střední |
| 5 | **Překompilovat PDF práce** po opravě bodů 1–2 | **blokující** |

## Otevřené body z minulých recenzí (stále nezavřené)

| # | Požadavek | Stav |
|---|---|---|
| 1 | Dockerfile pinnování | ✅ **hotovo** (`1610818`) |
| 2 | Rozdělení API_with_streamlit.py | ✅ **nevyžadováno** (615 řádků < 700) |
| 3 | Jediný diagramový kanál | ✅ **hotovo** (staré `DB_diagram.pdf`, `ERD_diagram.png` odstraněny) |
| 4 | Jazykové statistiky GitHubu | ✅ **hotovo** (`c7dcd99`) |
| 5 | Rotace hesel | ✅ **hotovo** (`2026-11-03_recenze`) |
| 6 | CI cesta | ✅ **hotovo** (`1da710a`) |
| 7 | LFS pro PDF | ✅ **hotovo** |

**Všechny blokující body z minulé recenze hotové.**

## Celkový dojem

Týden byl věnován **finálnímu polishing textu práce** — to je správně směřováno.
Oba nízkopriorní body z minulé recenze (Dockerfile digest, API_with_streamlit)
jsou buď hotové, nebo nevyžadované.

**Ale commit `9b5472b` (dnešní) obsahuje textové chyby** (dvojitá fráze, rozbitá
citace) — to je riziko pro obhajobu. **Komise si všimne.**

Příští kontrola očekávám po:
- **Opravě bodů P1 a P2** (typografické chyby v `01_theory.tex`).
- **Smazání zbytečných obrázků** (body P3, P4).
- **Překompilaci PDF** s aktuálním textem.

Práce je jinak **obhajobně připravena** — všechno ostatní je v pořádku.
