# Garmin / Strava běžecká analýza

Sada Python skriptů, která ze Strava exportu (GPX + FIT.GZ aktivity) generuje:

- Měsíční / roční přehled nájezdu (km) a osobních rekordů (1 míle, 5 km, 10 km, půlmaraton, maraton)
- Per-rok Excel "heatmap" — 1000 buněk = 1 km plán, každý běh obarven podle průměrného tempa
- Interaktivní HTML stránku s živě nastavitelnými barevnými kategoriemi

## Soubory

### Vstupní data
| Soubor | Popis |
|---|---|
| `export_9612673.zip` | Originální Strava export |
| `extracted/activities/` | Rozbalené GPX a FIT.GZ aktivity (~1080 souborů) |
| `activities.json` | Naparsovaná data všech aktivit (sport, datum, čas, trackpoints) — ~38 MB |

### Skripty
| Skript | Co dělá |
|---|---|
| [`parse_activities.py`](parse_activities.py) | Načte GPX/FIT/FIT.GZ z `extracted/activities/`, čistí GPS glitche a pauzy, ukládá `activities.json` |
| [`filters.py`](filters.py) | Distance-aware filtr "co je ještě plausibilní běh" (vs. kolo/chůze). Zakotveno na PR: 5 km @ 4:07/km, HM @ 4:24/km |
| [`analyze.py`](analyze.py) | Měsíční přehled km + rekordy. Generuje `prehled.txt` |
| [`analyze_yearly.py`](analyze_yearly.py) | Tabulka po rocích × měsících. Generuje `prehled_rocni.txt` |
| [`analyze_2026.py`](analyze_2026.py) | Transponovaná tabulka 2026 (měsíce ve sloupcích). Generuje `prehled_2026.txt` |
| [`heatmap_2026.py`](heatmap_2026.py) | 1000-buňkový Excel kde každá buňka = 1 km, barvy podle individuálního tempa každého km |
| [`heatmap2_2025.py`](heatmap2_2025.py), [`heatmap2_2026.py`](heatmap2_2026.py) | Excel kde celý běh = jeden barevný blok, 8 barev, černá čára na konci běhu |
| [`heatmap_all_years.py`](heatmap_all_years.py) | Hromadná verze pro všechny roky najednou (mřížka se škáluje pro roky > 1000 km) |
| [`build_web.py`](build_web.py) | Self-contained HTML s živým nastavením barev/hranic, paletami, přidáváním kategorií |

### Výstupy
- `prehled.txt`, `prehled_rocni.txt`, `prehled_2026.txt` — textové reporty
- `plan_2020_behy.xlsx` … `plan_2026_behy.xlsx` — per-rok Excel heatmapy
- `plan_2026.xlsx` — varianta kde každý km má vlastní barvu
- [`plan_web.html`](plan_web.html) — **interaktivní webová verze**, otevřete přímo v prohlížeči

## Reprodukce

```bash
pip install fitparse gpxpy openpyxl

# 1. Rozbalit Strava export
unzip export_9612673.zip -d extracted/

# 2. Naparsovat všechny aktivity do JSON (běží ~minutu)
python parse_activities.py

# 3. Vygenerovat výstupy
python analyze.py
python analyze_yearly.py
python heatmap_all_years.py
python build_web.py
```

## Klíčová rozhodnutí filtru

Sport `running` v exportu zahrnoval i cyklistické aktivity manuálně přeznačené v Garmin Connect. Filter v [`filters.py`](filters.py) je vyhazuje pomocí distance-aware minimálního tempa:

| Vzdálenost | Min. tempo |
|---|---|
| < 5 km | 3:30/km |
| 5–10 km | 4:07/km (5 km PR) |
| ≥ 10 km | 4:24/km (HM PR) |

Aktivity pomalejší než 10:00/km jsou vyřazeny jako chůze/túra.

GPS glitche (instantní rychlost > 7 m/s) a pauzy (> 30 s mezi body) se odřezávají uvnitř [`analyze.py:clean_series`](analyze.py).

## Celkové statistiky (2020–2026)

| Rok | km |
|---|---|
| 2020 | 768 |
| 2021 | 1 047 |
| 2022 | **1 955** |
| 2023 | 497 |
| 2024 | 571 |
| 2025 | 952 |
| 2026 (k 7.6.) | 394 |
| **Celkem** | **~6 184** |

Absolutní PR (před opravou filtru, zjištěné ze stop):
- 5 km: 21:38 (2022-10), uživatelem hlášený PR 4:07/km = 20:35 (2022-10-30)
- 10 km / HM: PR z půlmaratonu 1:33 (4:24/km)
- 1 míle: 5:51 (2024-06)
