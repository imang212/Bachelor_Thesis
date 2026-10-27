# Návrh zadání závěrečné práce (Bakalářská práce)
## Název tématu v češtině:
Systém pro monitorování a analýzu dopravy pomocí počítačového vidění

## Název tématu v angličtině:
System for Traffic Monitoring and Analysis using Computer Vision

### Anotace tématu
Sběr dat o dopravě, jako je hustota provozu, typy vozidel nebo pohyb chodců a cyklistů, je klíčový pro plánování a optimalizaci dopravní infrastruktury. Tradiční metody, například manuální sčítání, jsou časově náročné a náchylné k chybám. Možným řešením je využití automatizovaného systému, který dokáže v reálném čase analyzovat videosignál z dopravní lokality, detekovat a klasifikovat různé účastníky provozu (auta, chodce, cyklisty) a sbírat o nich data.

Cílem práce je navrhnout, implementovat a otestovat prototyp systému pro automatické sčítání a analýzu průjezdů vozidel a průchodů osob v definované lokalitě. Systém bude postaven na platformě Raspberry Pi s AI modulem a bude schopen v reálném čase zpracovávat obraz, tj. analyzovat videosignál z dopravní lokality, detekovat a klasifikovat objekty (vozidla, chodci, cyklisté), sbírat data o nich a vizualizovat je v přehledné aplikaci.

Dílčí cíle:

* přehled metod pro detekci, sledování a klasifikaci objektů v reálném čase (např. YOLO, SSD, DeepSORT),
* analýza dostupných řešení pro dopravní monitoring,
* návrh architektury systému zahrnující kamerový modul, zpracovatelskou jednotku a softwarovou aplikaci,
* sběr a příprava dat s využitím existujících veřejných datových sad (např. COCO, BDD100K) nebo vytvoření vlastní malé datové sady pro trénování nebo fine-tuning modelu,
* integrace, optimalizace a nasazení modelu,
* vývoj softwaru s následující funkčností:
    * analýza videosignálu z kamery v reálném čase,
    * detekce průjezdů a průchodů objektů definovanou čarou nebo oblastí,
    * uložení dat (typ objektu, čas, směr) do databáze nebo souboru,
    * vizualizace dat v podobě grafů a statistik (např. v jednoduchém webovém rozhraní),
* testování a evaluace v reálném prostředí, zhodnocení přesnosti detekce a sčítání ve srovnání s manuálním pozorováním.

Výstupem práce bude funkční prototyp zařízení a softwarová aplikace pro monitorování dopravy. Součástí výstupu bude i dokumentace popisující návrh, implementaci a vyhodnocení přesnosti systému.

Osnova:

Teoretická část
1.   metody počítačového vidění pro detekci a sledování objektů
2.   přehled systémů pro analýzu a zpracování dat z dopravy
3.   AI na vestavěných systémech (Edge AI)
4.   metodika testování a srovnání s referenčními daty

Praktická část
1. celková architektura řešení
2. výběr hardwaru pro zpracování videosignálu
3. návrh softwarových komponent (detekční modul, databáze, vizualizační rozhraní)
4. příprava prostředí a dat
5. konfigurace a nasazení detekčního modelu
6. vývoj aplikace pro zpracování videa a sběr dat
7. vytvoření vizualizačního rozhraní
8. definice benchmarkové úlohy, analýza přesnosti a výkonu systému
9. prezentace a interpretace výsledků


### Literatura:

1. LI, En, Liekang ZENG, Zhi ZHOU a Xu CHEN. Edge AI: On-Demand Accelerating Deep Neural Network Inference via Edge Computing. IEEE Transactions on Wireless Communications [online]. 2020, 19(1), s. 447-457 [cit. 2026-02-14]. Dostupné z: doi:10.1109/TWC.2019.2946140
2. LIN, Tsung-Yi, Michael MAIRE, Serge BELONGIE, James HAYS, Pietro PERONA, Deva RAMANAN, Piotr DOLLÁR a C. Lawrence ZITNICK. Microsoft COCO: Common Objects in Context. Lecture Notes in Computer Science [online]. Springer, 2014, 740-755 [cit. 2026-04-15]. ISBN 9783319106014. ISSN 0302-9743. Dostupné z: doi:10.1007/978-3-319-10602-1_48
3. REDMON, Joseph, Santosh DIVVALA, Ross GIRSHICK a Ali FARHADI. You Only Look Once: Unified, Real-Time Object Detection. 2016 IEEE Conference on Computer Vision and Pattern Recognition (CVPR) [online]. IEEE, 2016, 779-788 [cit. 2026-02-13]. Dostupné z: doi:10.1109/cvpr.2016.91
4. WOJKE, Nicolai, Alex BEWLEY a Dietrich PAULUS. Simple online and realtime tracking with a deep association metric. 2017 IEEE International Conference on Image Processing (ICIP) [online]. IEEE, 2017, 2017, 3645-3649 [cit. 2026-02-13]. Dostupné z: doi:10.1109/icip.2017.8296962
5. ZHOU, Wei, Li YANG, Lei ZHAO, Runyu ZHANG, Yifan CUI, Hongpu HUANG, Kun QIE a Chen WANG. Vision Technologies with Applications in Traffic Surveillance Systems: A Holistic Survey. ACM Computing Surveys [online]. Association for Computing Machinery (ACM), 2025, 2025-9-9, 58(3), 1-47 [cit. 2026-02-13]. ISSN 0360-0300. Dostupné z: doi:10.1145/3760525
6. WEN, Longyin, Dawei DU, Zhaowei CAI, et al. UA-DETRAC: A new benchmark and protocol for multi-object detection and tracking. Computer Vision and Image Understanding [online]. Elsevier BV, 2020, 193, 102907 [cit. 2026-04-15]. ISSN 1077-3142. Dostupné z: doi:10.1016/j.cviu.2020.102907
