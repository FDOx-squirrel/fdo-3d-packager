# PRIMER — fdo-3d-packager

Arbeitsplan für `FDOx-squirrel/fdo-3d-packager`. Dieses Dokument wird zu
Beginn jedes Chats vollständig hochgeladen und am Ende zurückgeschrieben.

---

## Teil A — Immer gültig

### A1 Ausgangslage

| Repo | Org | Rolle |
|---|---|---|
| `fdo-squirrel` | FDOx-squirrel | Referenzimplementierung: liest ein FDO-Paket (ZIP), schreibt `fdo-metadata.ttl` |
| `fdo-squirrel-registry` | FDOx-squirrel | Erntet von Zenodo (Concept-/Version-DOI), baut DCAT-Katalog, SHACL-Gate |
| `fdo-squirrel-spec` | FDOx-squirrel | ReSpec-HTML-Doku des Metadatenformats |
| `fdo-squirrel-md-generator` | FDOx-squirrel | Web-Generator für `MD.cff` |
| `fdo-architecture` | FDOx-squirrel | Meta-Repo: `registry.yaml` + Mermaid-Übersicht der Familie |
| **`fdo-3d-packager`** | **FDOx-squirrel** | **dieses Repo: Sketchfab/lokales 3D-Modell → fertiges FDO-Paket für `fdo-squirrel`** |

**Befunde (geprüft 2026-09-03, `fdo-squirrel@master` geklont):**

- `ingest/package_source.py` und `ingest/metadata_ingest.py` lesen eine ZIP
  mit genau zwei Top-Level-Dateien: `MD.cff` und `CITATION.cff` (beide YAML,
  Membernamen konfigurierbar, Default-Kandidaten `MD.cff` /
  `CITATION.cff`/`citation.cff`). Kein eigenes `metadata.yaml`-Schema wird
  gelesen — unser bisheriger Sketchfab-Prototyp (Nachbar-Chat) schreibt genau
  das Falsche fürs Ingest.
- `MD.cff` wird gegen ein aus `schemas/md_cff/MD.cff-schema.yaml` abgeleitetes
  JSON Schema (Draft 2020-12) validiert (`ingest/metadata_ingest.py:
  validate_against_schema`).
- `fdo_class`/`fdo_type` kennt bereits den Wert **„3D Data" / `fdo:3DDataFDO`**
  — genau unsere Objektklasse, keine Erweiterung nötig.
- `fdo/classification_rules.yaml` klassifiziert Distributionen beim
  Einlesen automatisch nach Extension/Pfad für `fdo:3DDataFDO`:
  `.obj/.ply/.stl/.glb/.gltf/.nxs/.nxz/.xyz/.pts/.ptx/.dae` → Rolle `model`;
  Bilder/Docs (`.jpg/.png/.tif/.pdf/.csv/.xml/.json`) → Rolle `documentation`;
  Pfadpräfix `textures/` → Rolle `auxiliary`. Für `.html`/`.js`/`.css`
  existiert **keine** Regel — ein 3DHOP-Viewer im Paket würde nicht erfasst.
- Referenzbeispiel `example_fdo/` ist buchstäblich unser Anwendungsfall: ein
  irischer Ogham-Stein als `.glb` unter `data/model/`, Bilder unter
  `data/images/`, plus `MD.cff` (`fdo_type: fdo:3DDataFDO`) und
  `CITATION.cff` auf oberster Ebene.
- **Schema-Drift im fdo-squirrel-Repo selbst:** Das `MD.cff` im Repo-Root
  nutzt Felder (`spatial`, `temporal`, `heritage_object`, `technique`,
  `created`/`modified`), die der Kommentar in `example_fdo/MD.cff` als
  „intentionally omitted in v0.1 schema" bezeichnet. Nicht unser Problem zu
  lösen — wir richten uns nach `MD.cff-schema.yaml` als Quelle der Wahrheit,
  nicht nach dem reicheren Root-Beispiel, bis das upstream geklärt ist.
- `distributions[]` ist im Schema vorgesehen (`path`, `media_type`, `role`,
  `sha256`, `byte_size`), wird im Referenzbeispiel aber **nicht** von Hand
  befüllt — offen, ob `fdo-squirrel` sie selbst aus der Klassifikation
  ableitet oder ob Packager sie liefern sollen (Teil D).
- PID-Konvention der Familie (aus `fdo-squirrel-registry`, andere Chats
  dieses Projekts): Die FDO-Instanz wird über die **Zenodo-DOI**
  (Concept-/Version-DOI, `fdoreg:conceptDoi`/`versionDoi`) identifiziert;
  `w3id.org/fdo-squirrel/…` ist für Vokabular-/Registry-IRIs reserviert,
  nicht für einzelne FDO-Objekte. `MD.cff.id` folgt demselben Muster
  (`https://doi.org/10.5281/zenodo.…`, siehe `example_fdo/MD.cff`).
- Sketchfab-Vorarbeit (Nachbar-Chat, `sketchfab_fdo_prototype/`): `main.py`
  mit `--sketchfab URL` / `--local PATH`, Blender-Konvertierung
  (glTF/GLB/OBJ → OBJ+Textur+Preview), `nxsbuild`/`nxscompress` →
  `.nxs`/`.nxz`, gebündelter 3DHOP-Miniviewer (offizielles
  `cnr-isti-vclab/3DHOP`-„minimal"-Paket, GPLv3, getrimmt auf ~1 MB). Diese
  Logik wird nach S2–S4 migriert, aber der Output wechselt von
  `metadata.yaml` auf `MD.cff`+`CITATION.cff`.
- **Rundlauf-Muster aus `fdo-squirrel-registry` S8** („Registry als FDO,
  Release und CI", andere Chats dieses Projekts): dort wird der eigene
  Bundle (Index + Shapes) als ZIP „durch `fdo-squirrel` geschickt" — die
  Registry katalogisiert sich selbst, und genau dieser Rundlauf ist laut
  eigener Primer-Formulierung „der beste Integrationstest". Gleiches Prinzip
  für uns: statt RDF-Erzeugung selbst nachzubauen, schicken wir
  `dist/<slug>.zip` durch eine lokale `fdo-squirrel`-Instanz und nehmen deren
  `fdo-metadata.ttl` als Beleg, dass das Paket wirklich passt — nicht nur,
  dass es gegen das Schema validiert. Genauer Einbindungsmechanismus (pip
  aus GitHub, Git-Submodule, oder Pfad-Konfiguration wie in
  `ingest/package_source.py` vorgesehen) ist noch offen, siehe Teil D.

**Befund (geprüft 2026-09-04):** `fdo-squirrel` und `fdo-squirrel-registry`
sind von `Research-Squirrel-Engineers` nach `FDOx-squirrel` umgezogen (die
alte Org-URL liefert weiterhin `200`, ist aber nur noch GitHubs
Auto-Weiterleitungsseite). Referenzen in `README.md` und hier korrigiert.

### A2 Zielbild

```
Sketchfab-Modell (--sketchfab URL)      Lokale Datei (--local PATH)
        \                                      /
         v                                    v
              data/raw/<slug>.<ext> (+ source_info.json)      [S2, network nur hier]
                              |
                              v
              Blender: Konvertierung + Preview-Render          [S3]
              dist/<slug>/model.obj (+Texturen), preview.png
                              |
                              v
              nxsbuild / nxscompress                           [S4]
              dist/<slug>/model.nxs, model.nxz
                              |
                              v
              MD.cff + CITATION.cff schreiben                  [S5]
              fdo_type: fdo:3DDataFDO, gegen MD.cff-schema.yaml validiert
                              |
                              v
              Bundle: dist/<slug>.zip im fdo-squirrel-Layout    [S6]
              (MD.cff, CITATION.cff, data/model/, data/images|textures/,
               viewer/ -- 3DHOP-Miniviewer, Klassifikation ungeprüft)
                              |
                              v
              dist/<slug>.zip durch fdo-squirrel schicken       [S7]
              (Rundlauf-Muster wie fdo-squirrel-registry S8;
               fdo-metadata.ttl als Beleg, nicht nur Schema-Validierung)
                              |
                              v
              -> später (außerhalb dieses Repos): Zenodo-Upload -> DOI als PID
```

Eigenschaften, an denen sich ein Lauf messen lässt:

1. `dist/<slug>.zip` läuft unbeanstandet durch eine lokale
   `fdo-squirrel`-Instanz und erzeugt `fdo-metadata.ttl` — nicht nur
   Schema-Validierung, sondern der volle Rundlauf (Muster: registry S8).
2. Zwei Läufe mit demselben `--local`/`--sketchfab`-Input erzeugen
   byte-identische `dist/`-Dateien; Netzwerkzugriff bleibt auf `fetch`
   beschränkt. Einschränkung für `preview.png` (S3): die Kamera-/
   Licht-Platzierung ist eine reine Funktion der Mesh-Bounding-Box (kein
   Zufall, kein `datetime`), aber ob das Rendering selbst über
   Blender-Versionen/GPU-Treiber hinweg wirklich byte-identisch bleibt,
   konnte mangels Blender im Sandkasten nicht geprüft werden — Annahme,
   kein verifizierter Fakt (siehe S3).
3. `python main.py --list` zeigt alle Schritte samt Abhängigkeiten, ohne
   Blender/rdflib/jsonschema zu importieren.
4. Jede Modell-Datei im Paket bekommt beim Rundlauf durch `fdo-squirrel`
   (S7) einen `distributions[]`-Eintrag mit korrekter `role` und `sha256` —
   wir liefern selbst keine Vorbefüllung (A4).
5. `python main.py --only bundle` läuft offline, wenn `data/raw/` und
   `dist/` aus einem vorherigen Lauf schon vorhanden sind.

### A3 Querschnittsregeln

- `data/raw/` unverändert wie erhalten, read-only. Was ein Schritt daraus
  macht, geht nach `dist/`.
- Kein `datetime.now()` im Output. Versionsstand kommt aus der
  `RELEASE`-Konstante in `py/fdo_3d_packager_utils.py`.
- Zweimal laufen lassen, `git status` muss beim zweiten Mal leer sein.
- Netzwerkzugriff bleibt auf den `fetch`-Schritt beschränkt (Sketchfab-API);
  alles andere läuft offline gegen `data/raw/`.
- Kopierter Code (Blender-/Nexus-Subprocess-Aufrufe) behält seine
  `check=True`-Guards.
- PRIMER.md Deutsch, alles andere (Code, Kommentare, README) Englisch.
- Referenzplattform Windows: Befehle für `cmd`, je einer pro Zeile.
- Ein Thema pro Chat, ein Repo pro Chat.

### A4 Beschlusslage

| Frage | Beschluss | seit |
|---|---|---|
| Name / Org | `fdo-3d-packager` in `FDOx-squirrel` | 2026-09-03 |
| Output-Format | `MD.cff` + `CITATION.cff` statt eigenem `metadata.yaml`, exakt wie von `ingest/package_source.py` erwartet | 2026-09-03 |
| `fdo_class`/`fdo_type` | `"3D Data"` / `fdo:3DDataFDO` (bereits im Schema vorgesehen) | 2026-09-03 |
| Zwei Eingabewege | `--sketchfab URL` / `--local PATH`, aus dem Prototyp übernommen, aber neuer Output | 2026-09-03 |
| Texturablage im Paket | unter `textures/`, damit `classification_rules.yaml` sie als `auxiliary` statt `documentation` einstuft | 2026-09-03, Vorschlag |
| PID | wird von diesem Repo **nicht** vergeben; `MD.cff.id` bleibt Platzhalter bis ein manueller Zenodo-Upload eine DOI liefert (Konvention aus `fdo-squirrel-registry`) | 2026-09-03 |
| 3DHOP-Miniviewer im Paket? | ja, ins `dist/<slug>.zip` — kein separates Deliverable. `classification_rules.yaml` hat dafür noch keine Regel (`.html`/`.js`/`.css`); wird als echter Befund in S7 (Rundlauf durch `fdo-squirrel`) sichtbar, ggf. dort nachzubessern statt hier zu umgehen | 2026-09-03 |
| `distributions[]` vorbefüllen? | nein — `fdo-squirrel` klassifiziert selbst (`classification_rules.yaml`), wir liefern keine eigene Vorbefüllung. Lücken (siehe Viewer-Zeile) werden dort nachgebessert, nicht hier kompensiert | 2026-09-03 |
| FDO-Build via `fdo-squirrel` | `dist/<slug>.zip` wird durch eine lokale `fdo-squirrel`-Instanz geschickt statt RDF-Erzeugung selbst nachzubauen (Muster: `fdo-squirrel-registry` S8) | 2026-09-03 |
| Einbindungsmechanismus für `fdo-squirrel` | offen (pip aus GitHub? Git-Submodule? Pfad-Config?) — siehe Teil D | Vorschlag ausstehend |
| `source_info.json`-Vertrag (S2→S3/S4/S5) | eine Datei, von `fetch` geschrieben: `slug`, `model_file` (Pfad **relativ zu `data/raw/`**, kann ein Unterverzeichnis enthalten — z. B. `donaghmore-church-ruin/donaghmore-church-ruin.gltf`, korrigiert 2026-09-04, siehe S2-Nachtrag), `title`/`description`/`creator`/`creator_profile`/`licence`/`licence_url`/`source_url`/`sketchfab_uid`/`source_note`, plus `todo_placeholders` (Liste fehlender Pflichtfelder). Bei `--local` ohne `--title`/`--creator`/`--licence` werden `"TODO: … not set"`-Platzhalter geschrieben und `fetch` gibt eine mit `Warning:` beginnende Meldung zurück — nicht fatal im Normallauf, aber `--strict` (= CI) schlägt fehl, bis die Felder gesetzt sind. Dieselbe `Warning:`-Mechanik greift jetzt auch, wenn vom Modell referenzierte Begleitdateien (`scene.bin`, `textures/…`, `.mtl`) fehlen. `mdcff` (S5) soll den Bau verweigern, solange `todo_placeholders` nicht leer ist (Vorschlag, in S5 zu bestätigen) | 2026-09-04, korrigiert 2026-09-04 |
| Begleitdateien eines Modells (`scene.bin`, `textures/…` bei `.gltf`; `.mtl`+Texturen bei `.obj`) | werden von `fetch` erkannt (`resolve_sibling_files()`) und unter denselben relativen Pfaden neben das Modell nach `data/raw/<slug>/` kopiert, statt nur die eine Modell-Datei zu kopieren — sonst bricht Blender (S3) an der relativen URI-Auflösung ab. `.glb` hat keine externen Begleitdateien (self-contained) | 2026-09-04, Befund aus erstem echten `--sketchfab`-Lauf |
| Verhältnis zum künftigen Software-FDO-Packager (Git-Link → `fdo:SoftwareFDO`) | eigenes Repo (`fdo-software-packager`?), nicht dasselbe wie hier — `fetch`+`convert` sind fachlich verschieden (Sketchfab/Blender/Nexus vs. Git-Clone+Repo-Analyse), und A3 verlangt ohnehin Kopieren statt Referenzieren, ein gemeinsames Repo spart also keine Duplizierung, nur Übersicht. Was kopiert werden sollte, sobald das Schwester-Repo startet: MD.cff/CITATION.cff-Writer, Bundle-Layout, `build_fdo`-Schritt (S5–S7) | 2026-09-03, Vorschlag |

### A5 Was in welchem Chat hochgeladen wird

Bundle vor jedem Chat (Windows):

```cmd
robocopy . ..\fdo-3d-packager-bundle /E /XD .git .venv __pycache__ data\raw dist
powershell Compress-Archive -Path ..\fdo-3d-packager-bundle\* -DestinationPath ..\fdo-3d-packager-bundle.zip -Force
```

Nicht hochladen: `.git/`, `.venv/`, `__pycache__/`, `data/raw/` (können
große Downloads/lokale Scans enthalten), `dist/` (generiert), Blender-/
Nexus-Binaries.

### A6 IRI-Landkarte

Nicht anwendbar in S1 — dieses Repo veröffentlicht selbst keine RDF-IRIs
(das übernimmt `fdo-squirrel` downstream aus dem gepackten `MD.cff`).

---

## Teil B — Schrittübersicht

| ID | Schritt | Repo | hängt ab von | Status |
|---|---|---|---|---|
| S0 | Festlegungen: Org, Name, Output-Format, PID-Konvention | fdo-3d-packager | – | erledigt 2026-09-03 |
| S1 | Skeleton: Repo-Layout, `main.py`, Schritt-Stubs, `requirements.txt`, `LICENSE`, `CITATION.cff` | fdo-3d-packager | S0 | erledigt 2026-09-03 |
| S2 | `fetch`-Schritt: `--sketchfab`/`--local` → `data/raw/` (aus dem Prototyp migriert) | fdo-3d-packager | S1 | erledigt 2026-09-04 |
| S3 | `convert`-Schritt: Blender → `dist/<slug>/model.obj` + `preview.png` | fdo-3d-packager | S2 | erledigt 2026-09-04 |
| S4 | `nexus`-Schritt: `nxsbuild`/`nxscompress` → `dist/model.nxs`/`.nxz` | fdo-3d-packager | S3 | erledigt 2026-09-04 |
| S5 | `mdcff`-Schritt: `MD.cff` + `CITATION.cff` schreiben, gegen Schema validieren | fdo-3d-packager | S2, S4 | offen |
| S6 | `bundle`-Schritt: `dist/<slug>.zip` im `fdo-squirrel`-Layout | fdo-3d-packager | S3, S4, S5 | offen |
| S7 | `dist/<slug>.zip` durch `fdo-squirrel` schicken, `fdo-metadata.ttl` als Beleg (Muster: registry S8) | fdo-3d-packager | S6 | offen |

S3 und S4 sind technisch unabhängig von S5 und können in beliebiger
Reihenfolge bzw. parallel in Angriff genommen werden; S5 braucht sowohl die
deskriptiven Metadaten aus S2 (Titel/Creator/Lizenz) als auch die Checksums
aus S4, ist also sinnvollerweise der letzte Implementierungsschritt vor S6.

---

## Teil C — Die Schritte

## S0 — Festlegungen

**Ziel:** Name, Org und die grundlegenden Format-Entscheidungen stehen, bevor
Code entsteht, der sie sonst nachträglich umbauen müsste.

**Uploads:** keine (Neuanlage).

Entscheidungen siehe A4. Grundlage: `fdo-squirrel@master` geklont und
`ingest/package_source.py`, `ingest/metadata_ingest.py`,
`schemas/md_cff/MD.cff-schema.yaml`, `fdo/classification_rules.yaml` sowie
`example_fdo/` gelesen (siehe A1-Befunde).

**Abnahme:** A4-Tabelle gefüllt, Name/Org festgelegt.

### Erledigt 2026-09-03

Name und Org im Chat entschieden (`fdo-3d-packager`, `FDOx-squirrel`).
Format-Entscheidung (`MD.cff`/`CITATION.cff` statt `metadata.yaml`) ergab
sich zwingend aus dem tatsächlichen Ingest-Code, nicht aus einer Annahme —
ohne den Klon hätte S1 das falsche Zielformat einprogrammiert.

## S1 — Skeleton

**Ziel:** `python main.py` läuft durch und meldet für jeden Schritt „nothing
to do", `git status` bleibt nach zwei Läufen sauber.

**Uploads:** keiner (Neuanlage).

Layout, `main.py`-Vertrag (`--list`/`--only`/`--from`/`--skip`/`--dry-run`/
`--strict`) und `py/fdo_3d_packager_utils.py` wie im `primer-repo`-Skill
vorgegeben. Sechs Schritt-Module (`py/step_fetch.py` … `py/step_bundle.py`)
plus `py/step_build_fdo.py` (S7, Rundlauf durch `fdo-squirrel`), jedes
einzeln lauffähig, jedes gibt bis S2ff. nur `nothing_to_do()` zurück.
`--sketchfab`/`--local` sind als CLI-Flags bereits vorhanden (dokumentieren
die künftige Schnittstelle über `--list`/`--dry-run` hinweg), werden aber
erst ab S2 ausgewertet.

**Abnahme:** `python main.py --list` zeigt alle sieben Schritte;
`python main.py` (Default-Lauf, `fetch` als Network-Schritt ausgenommen)
beendet mit Exit 0 und „nothing to do" je Schritt; zweiter Lauf ändert
nichts (`git status --short` leer nach `git init` + erstem Commit).

### Erledigt 2026-09-03

Verifiziert in einer frischen Kopie (kein Blender/Nexus/Netzwerk nötig, da
S1 reine Stubs sind): `python main.py --list`, `python main.py`,
`python main.py --dry-run`, `python main.py --only bundle`, zweiter Lauf
ohne Änderungen. Details in `PATCH-README.md` dieses Patches.

## S2 — `fetch`

**Ziel:** `--sketchfab URL` bzw. `--local PATH` liefert genau eine
Modell-Datei unter `data/raw/<slug>.<ext>` plus `data/raw/source_info.json`
als Übergabevertrag an S3–S5 (siehe A4).

**Uploads für diesen Schritt:** `PRIMER.md` + Repo-Bundle (s. A5).

**Substanz:**
- `py/step_fetch.py`: `--sketchfab`-Pfad (Data-API-Metadaten, Download-API,
  glTF/GLB-Archiv laden+entpacken, Aufräumen der Zwischenstände) und
  `--local`-Pfad (Datei kopieren, Endung prüfen, Metadaten nur aus
  CLI-Flags) aus `sketchfab_fdo_prototype` (Nachbar-Chat) migriert —
  Zielformat aber `source_info.json` statt `metadata.yaml`, Zielordner
  `data/raw/` statt `out/<slug>/`.
- `main.py`: `--token`/`--title`/`--creator`/`--creator-profile`/
  `--licence`/`--licence-url`/`--source-note` als globale Flags ergänzt
  (vorher nur `--sketchfab`/`--local`), damit `python main.py --only fetch
  ...` alle Metadaten-Overrides entgegennimmt, nicht nur der
  Standalone-Aufruf `python py/step_fetch.py`.
- `--strict`-Kopplung: fehlende Pflichtfelder bei `--local` erzeugen eine
  mit `Warning:` beginnende Rückmeldung — `main.py`s bestehende
  `--strict`-Logik (S1, unverändert) erkennt das automatisch und lässt den
  Lauf fehlschlagen, ohne dass `step_fetch.py` selbst etwas von `--strict`
  wissen muss.
- `README.md`, alle `Research-Squirrel-Engineers`-Referenzen auf
  `FDOx-squirrel` korrigiert (s. A1-Befund).

**Abnahme:** `python main.py --only fetch --local <Datei>` läuft ohne
Netzwerk; ohne `--title`/`--creator`/`--licence` Exit 0 im Normallauf, Exit 1
mit `--strict`; mit allen drei Flags Exit 0 in beiden Modi. Zwei
aufeinanderfolgende Läufe mit identischem Input erzeugen byte-identische
`data/raw/<slug>.<ext>` und `data/raw/source_info.json`. `--sketchfab`-Pfad
gegen simulierte HTTP-Antworten geprüft (kein `api.sketchfab.com` im
Sandkasten-Netzwerk) — Metadaten-Extraktion, Download, Entpacken,
Aufräumen der Zwischenstände (`_sketchfab_download/`, `archive.zip`,
`gltf_src/`) laufen wie erwartet.

### Erledigt 2026-09-04

Wie oben. `data/raw/source_info.json`-Feldnamen sind jetzt der verbindliche
Vertrag für S3 (`model_file`) und S5 (alle Metadatenfelder plus
`todo_placeholders`) — siehe A4. Echter `--sketchfab`-Lauf gegen die echte
API konnte im Sandkasten nicht verifiziert werden (Domain nicht im
Netzwerk-Allowlist); nur simulierte HTTP-Antworten getestet. Erste echte
Probe mit einem von Anne-Karolines Sketchfab-Links steht noch aus — sinnvoll
als erster Schritt der nächsten Chat-Session vor S3.

### Nachtrag 2026-09-04 — erster echter `--sketchfab`-Lauf, echter Bug

Erste echte Probe durchgeführt: "Donaghmore Church ruin"
(`a602439f3513431ea1b306358a2581e5`). Dabei kam ein echter, blockierender
Bug ans Licht: `run_sketchfab()` kopierte bisher nur die `.gltf`-Datei
selbst nach `data/raw/<slug>.gltf` und ließ ihre Begleitdateien fallen —
jeder reale Sketchfab-glTF-Export splittet aber Geometrie (`scene.bin`,
referenziert über `buffers[].uri`) und Texturen (`textures/*.jpeg`, über
`images[].uri`) in separate Dateien. Blender (S3) wäre bei jedem echten
Modell mit „Datei nicht gefunden" abgebrochen, weil die relative
URI-Auflösung des glTF ins Leere gelaufen wäre.

Fix: `resolve_sibling_files()` liest bei `.gltf` die `buffers[]`/`images[]`-
URIs (data:-URIs ausgenommen), bei `.obj` `mtllib` plus alle
Textur-Referenzen im `.mtl` (`MTL_TEXTURE_KEYS`, jetzt in
`fdo_3d_packager_utils.py`, geteilt mit S3). `.glb` hat keine externen
Begleitdateien (self-contained). `data/raw/`-Layout geändert von
`data/raw/<slug>.<ext>` auf `data/raw/<slug>/<slug>.<ext>` plus
Begleitdateien unter denselben relativen Pfaden (z. B.
`data/raw/<slug>/textures/foo.jpeg`) — das hält die relativen URIs im
Modell gültig, ohne sie umschreiben zu müssen. `source_info.json.model_file`
ist entsprechend jetzt ein Pfad *relativ zu `data/raw/`* (kann ein
Unterverzeichnis enthalten), nicht mehr ein nackter Dateiname direkt unter
`data/raw/` — **A4-Vertrag entsprechend angepasst.** Fehlen Begleitdateien
tatsächlich (Netzwerk-Abbruch, unvollständiges Archiv), wird das jetzt als
`Warning:`-Meldung sichtbar (gleicher Mechanismus wie fehlende
Pflichtfelder), statt erst in S3 stumm zu scheitern. Betrifft auch den
`--local`-Pfad (`.obj` mit `mtllib`/Texturen hatte denselben Fehler).

Verifiziert im Sandkasten (kein echtes Sketchfab-Netzwerk verfügbar, daher
simuliert): `--sketchfab`-Pfad gegen die reale Donaghmore-`sketchfab_meta.json`
plus ein nachgebautes ZIP-Archiv mit `scene.gltf`+`scene.bin`+6
`textures/*.jpeg` (Netzwerk-Aufrufe gemockt) — alle 7 Begleitdateien korrekt
erkannt und an den richtigen relativen Pfaden kopiert, `source_info.json`
identisch zum echten Lauf bis auf `model_file`. `--local`-Pfad mit
`.obj`+`.mtl`+2 Texturen getestet, inklusive Fall mit einer fehlenden
Textur (`Warning:`-Meldung wie erwartet). Zwei aufeinanderfolgende Läufe
mit identischem Input: `data/raw/` byte-identisch (`sha256sum`-Vergleich
über alle Dateien).

## S3 — `convert`

**Ziel:** `data/raw/<model_file>` (aus `source_info.json`) wird per
Blender headless nach `dist/<slug>/model.obj` (+`textures/`) und
`dist/<slug>/preview.png` konvertiert — offline, gegen das, was `fetch`
bereits abgelegt hat.

**Uploads für diesen Schritt:** `PRIMER.md` + Repo-Bundle (s. A5).

**Substanz:**
- `py/blender_convert_headless.py`: läuft *innerhalb* Blenders eigenem
  Python (`bpy`), nicht mit dem Repo-Interpreter — aufgerufen als
  `blender -b --python py/blender_convert_headless.py -- --in … --obj-out …
  --preview-out …`. Aus `blender_convert.py` im `sketchfab_fdo_prototype`
  migriert: `import_model()` unterscheidet `.gltf`/`.glb`
  (`bpy.ops.import_scene.gltf`) und `.obj` (`bpy.ops.wm.obj_import`),
  Export via `bpy.ops.wm.obj_export(path_mode="COPY", export_materials=True)`,
  Preview-Render mit fixer 3-Punkt-Beleuchtung aus der Mesh-Bounding-Box
  (kein Zufall, siehe A2 Punkt 2 zur Determinismus-Einschränkung).
- `py/step_convert.py`: sucht Blender (`--blender-bin`/`BLENDER_BIN`/
  `blender`), ruft es per `subprocess.run(check=True)` auf (A3: Guard
  bleibt erhalten), räumt `dist/<slug>/` vor jedem Lauf leer (keine
  Textur-Leichen aus einem vorherigen Lauf). Danach: `_organize_textures()`
  verschiebt alles, was Blender neben `model.obj`/`model.mtl`/`preview.png`
  kopiert hat, nach `textures/` und schreibt die `map_*`-Zeilen im `.mtl`
  entsprechend um — **diff-basiert** (alles außer den drei bekannten
  Dateinamen), nicht anhand angenommener Blender-Dateinamen, weil Blender
  bei Namenskollisionen selbst umbenennt (`foo.jpeg` → `foo.001.jpeg`).
  `textures/` als eigener Ordner ist Absicht (A4: `auxiliary`-Rolle in
  `classification_rules.yaml`, nicht `documentation`).
- `main.py`: globales `--blender-bin`-Flag ergänzt (gleiches Muster wie
  `--token` für `fetch`).

**Abnahme:** `python main.py --only convert` schlägt mit klarer Meldung
fehl, wenn kein `blender`-Binary gefunden wird (`shutil.which` +
Pfad-Check). Mit einem funktionierenden Blender: `dist/<slug>/model.obj`,
`model.mtl`, `textures/*`, `preview.png` vorhanden; zwei aufeinanderfolgende
Läufe erzeugen dieselbe Dateiliste (siehe A2 Punkt 2 zur Einschränkung bei
`preview.png` selbst).

### Erledigt 2026-09-04

Python-seitige Orchestrierung (Blender-Aufruf, Fehlerbehandlung bei
fehlendem Binary, `dist/`-Aufräumen, Texturen-Diff-und-Umzug,
`.mtl`-Rewrite, Idempotenz) gegen einen Fake-`blender`-Stellvertreter
verifiziert, der ein realistisches, kollidierendes Textur-Namensschema
nachbildet (`material_0_baseColor.jpeg` + `material_0_baseColor.001.jpeg`)
— zwei Läufe erzeugen dieselbe `dist/`-Dateiliste mit identischen Hashes.
Ein echter Bug dabei gefunden und gefixt: die erste Fassung verschob
`preview.png` fälschlich mit nach `textures/`, weil der Diff nur
`model.obj`/`model.mtl` ausnahm.

**Nicht verifiziert, da kein Blender im Sandkasten verfügbar:** ob
`blender_convert_headless.py` gegen eine echte Blender-Installation
tatsächlich importiert/exportiert/rendert wie erwartet (Operator-Namen wie
`bpy.ops.wm.obj_export`/`bpy.ops.wm.obj_import` sind Blender-4.x-API, aus
dem Prototyp übernommen, dort ebenfalls nie gegen echtes Blender getestet)
— das ist der erste sinnvolle Schritt der nächsten Session: `python main.py
--only convert` gegen den echten Donaghmore-Fund aus S2 laufen lassen und
das Ergebnis (`dist/donaghmore-church-ruin/`) mit echten Augen/einem
OBJ-Viewer prüfen, bevor S4 (Nexus) draufsetzt.

### Nachtrag 2026-09-04 — erster echter Blender-Lauf, echter Bug

Erster echter Lauf gegen Blender 5.2.1 LTS (Windows): Import (26 Meshes aus
dem glTF, 7,93s), OBJ-Export und Preview-Render liefen alle durch
(`python main.py --only convert`, 116,41s Gesamtlaufzeit) — aber alle sechs
Texturen wurden beim Export übersprungen:

    WARNING Missing source file 'C:\material_1_baseColor.jpeg', not copying
    (× 6, je einmal pro Material)

`dist/donaghmore-church-ruin/` enthielt danach nur `model.obj`+`model.mtl`+
`preview.png`, kein `textures/`-Ordner — `preview.png` entsprechend fast
schwarz (mittlere Helligkeit 50/255, Maximum 69/255: Materialien ohne
Basisfarbe rendern dunkel).

**Ursache:** Blenders glTF-Importer löst relative Bild-Pfade
(`textures/foo.jpeg`) intern gegen `bpy.data.filepath` auf (Blenders
`//`-Konvention — relativ zur *aktuell gespeicherten `.blend`-Datei*), nicht
gegen das Verzeichnis der importierten `.gltf`. Da dieses Skript nie eine
`.blend`-Datei speichert, existiert diese Basis nicht, und Blender fällt auf
etwas Unbrauchbares zurück (beobachtet: die Laufwerkswurzel, `textures/`
dabei komplett verschluckt). Der OBJ-Exporter (`path_mode="COPY"`) findet
die Quelldatei dort folgerichtig nicht und kopiert nichts.

**Fix:** `relink_images()` in `blender_convert_headless.py`, direkt nach
`import_model()`: durchsucht das Modellverzeichnis (`data/raw/<slug>/`, das
S2 ja bereits vollständig mit allen Begleitdateien befüllt) nach Dateien,
deren Name zum Bild-Datenblock passt, und setzt `image.filepath`/
`filepath_raw` explizit auf den gefundenen absoluten Pfad — unabhängig
davon, was Blenders eigene Pfad-Auflösung ergeben hätte. Noch nicht erneut
gegen echtes Blender verifiziert (nächster Schritt: `python main.py --only
convert` wiederholen, `dist/donaghmore-church-ruin/textures/` sollte jetzt
6 Dateien enthalten, `preview.png` sollte deutlich heller/farbig sein).

### Nachtrag 2026-09-04 (2) — `relink_images()` wirkungslos, Ansatz gewechselt

`relink_images()` erneut gegen echtes Blender 5.2.1 LTS getestet: **keine
Wirkung.** `preview.png` byte-für-byte identisch zum vorherigen (fehlerhaften)
Lauf (mittlere Helligkeit 49.97/49.71/48.98, Max 69 — auf die Dezimalstelle
gleich), dieselben sechs `Missing source file 'C:\material_N_baseColor.jpeg'`-
Warnungen beim Export. Warum genau `bpy.data.images`-Manipulation hier nichts
bewirkt, ist ungeklärt (Diagnose-Prints in `relink_images()` ergänzt für den
nächsten Lauf, falls das noch relevant wird) — vermutlich löst Blenders seit
4.0 in C++ implementierter OBJ-Exporter den Bildpfad nicht (mehr) einfach
über das Python-sichtbare `image.filepath` zum Exportzeitpunkt auf.

**Ansatz gewechselt, statt weiter an Blenders interner Pfad-Auflösung zu
doktern:** `bpy.ops.wm.obj_export()` läuft jetzt mit `path_mode="STRIP"`
statt `"COPY"` — Blender soll nur noch den Dateinamen pro Material in die
`.mtl` schreiben, keinen Kopierversuch mehr unternehmen (dieser produzierte
ohnehin nur irreführende Warnungen). Das eigentliche Kopieren übernimmt jetzt
`step_convert.py` selbst: `_copy_textures_from_raw()` liest die
`map_*`-Zeilen aus der von Blender geschriebenen `.mtl`, sucht jeden
referenzierten Dateinamen unter `data/raw/<slug>/` (wo S2 garantiert alle
Begleitdateien abgelegt hat) und kopiert ihn direkt nach
`dist/<slug>/textures/` — komplett unabhängig davon, was Blender intern für
Pfade verwendet. Fehlt eine referenzierte Textur tatsächlich (z. B. weil sie
nie in `data/raw/` landete), wird das als `Warning:`-Meldung sichtbar statt
still zu scheitern.

Im Sandkasten gegen einen Fake-Blender verifiziert, der das reale
Fehlerbild nachbildet (`.mtl` mit Dateinamen, aber keine kopierten Bytes):
alle 6 echten Donaghmore-Texturen korrekt gefunden und byte-identisch
kopiert; separat auch der Fall einer tatsächlich fehlenden Textur getestet
(korrekte `Warning:`-Meldung, Zeile in der `.mtl` bleibt unverändert statt
falsch auf `textures/` umgeschrieben zu werden). Zwei Läufe erzeugen
identische `dist/`-Dateien.

**Weiterhin offen:** ob damit auch `preview.png` korrekt eingefärbt wird,
ist unklar — `_copy_textures_from_raw()` behebt das exportierte Paket
(`dist/<slug>/textures/`), aber die *Render*-Farben hängen weiterhin davon
ab, ob `relink_images()` (oder irgendein anderer Mechanismus) Blender zur
Renderzeit die echten Pixel liefert. Falls `preview.png` nach diesem Fix
weiterhin dunkel bleibt, ist das ein separater, noch ungelöster Punkt — die
Diagnose-Prints in `relink_images()` sollten dafür beim nächsten Lauf
zeigen, ob/wie viele Bilder überhaupt in `bpy.data.images` auftauchen.

### Nachtrag 2026-09-04 (3) — Texturen korrekt geladen, `preview.png` trotzdem gleich: Beleuchtung, nicht Texturen

`relink_images()`-Diagnose ausgewertet: alle 6 Bilder werden korrekt in
`bpy.data.images` gefunden, `image.filepath` zeigte schon *vor* dem Relink
auf den vollständigen, korrekten absoluten Pfad
(`C:\git\fdo-3d-packager\data\raw\donaghmore-church-ruin\textures\material_N_baseColor.jpeg`),
`source='FILE'`, alle als `MATCH` erkannt, `reload()` ohne Fehler. Die
ursprüngliche „`//`-Pfad relativ zur nie gespeicherten `.blend`-Datei"-Theorie
aus Nachtrag (1) war damit **widerlegt** — Blenders glTF-Importer hatte die
Bildpfade die ganze Zeit korrekt aufgelöst. Auch `_copy_textures_from_raw()`
(Nachtrag 2) hat korrekt alle 6 Texturen ins Paket kopiert
(`[convert] ... 6 texture(s) -> textures/`). Trotzdem: `preview.png`
byte-für-byte identisch zu den beiden vorherigen (fehlerhaften) Läufen.

Damit ist die Textur-Ladung als Ursache ausgeschlossen — das Problem liegt
in der Beleuchtung selbst. Der ursprüngliche Drei-Punkt-Aufbau (aus dem nie
gegen echtes Blender getesteten Prototyp übernommen) nutzte `AREA`-Lichter
mit `light_data.size = radius` bei fester Watt-Energie. Ein `AREA`-Licht
strahlt bei fester Energie über eine mit der Emitterfläche quadratisch
wachsende Fläche ab — je größer `radius` (bei der Donaghmore-Kirche
vermutlich mehrere zehn Meter, bei den bisherigen Testfällen im Prototyp ein
einzelner ~1m-Ogham-Stein), desto lichtschwächer wird die Beleuchtung bei
gleicher Energie. Für ein Gebäude dieser Größenordnung reichten die festen
Energiewerte (1200/500/700 W) praktisch nicht aus — die Szene war schlicht
nahezu unbeleuchtet, unabhängig von den Texturen.

**Fix:** Drei-Punkt-Aufbau auf `SUN`-Lichter umgestellt statt `AREA`.
`SUN`-Energie ist Bestrahlungsstärke (W/m²), unabhängig von Distanz oder
der (ohnehin nur für `TRACK_TO` relevanten) Objekt-Position/-Größe — dieselben
festen Werte (3.0/1.2/1.5) beleuchten damit einen Stein genauso wie eine
Kirche. Das war die naheliegende, aber bislang übersehene Fehlerquelle:
skalierungsabhängige Beleuchtung, kein Textur-Problem.

**Nicht verifiziert, da kein Blender im Sandkasten:** ob die gewählten
`SUN`-Energiewerte (3.0/1.2/1.5) tatsächlich ein sinnvoll helles,
nicht-überbelichtetes Bild ergeben — plausible Heuristik, keine kalibrierten
Werte. Nächster Schritt: `python main.py --only convert` erneut, `preview.png`
ansehen. Falls zu dunkel/hell, sind die drei Energiewerte am Anfang von
`setup_camera_and_lights()` die Stellschraube.

### Nachtrag 2026-09-04 (4) — bestätigt: S3 funktioniert jetzt end-to-end

Von Flo verifiziert: `preview.png` zeigt jetzt plausibel beleuchtetes
Mauerwerk mit Moos, korrekten Texturen, keine Über-/Unterbelichtung. Eigene
Messung: mittlere Helligkeit `[68.75, 68.07, 65.75]` (vorher `~50/50/49`),
Maximum `197` (vorher `69`) — deutlich heller, keine ausgebrannten Bereiche.
Die drei aufeinanderfolgenden Bugs (fehlende Begleitdateien in S2, Blenders
nicht kopierende Textur-Pfade, unterbeleuchtete `AREA`-Lichter) sind damit
alle real gegen den Donaghmore-Fall verifiziert, nicht nur im Sandkasten
simuliert. **S3 ist damit vollständig erledigt.**

Weiterhin offen (kein Blocker, nur nicht geprüft): ob zwei aufeinanderfolgende
`convert`-Läufe wirklich byte-identische `dist/`-Ausgaben liefern (A2 Punkt 2)
— insbesondere `preview.png`s Rendering-Determinismus über Blender-Version/
GPU-Treiber hinweg. Nicht dringend, da `preview.png` reines Anschauungsbild
ist und nicht in die FDO-Metadaten (Checksums etc.) einfließt.

## S4 — `nexus`

[#s4--nexus](#s4--nexus)

**Ziel:** `dist/<slug>/model.obj` (aus S3) wird per `nxsbuild`/`nxscompress`
nach `dist/<slug>/model.nxs` (multiresolution) und `dist/<slug>/model.nxz`
(komprimiert) konvertiert — offline, gegen das, was `convert` bereits
abgelegt hat.

**Uploads für diesen Schritt:** `PRIMER.md` + Repo-Bundle (s. A5).

**Substanz:**

- `py/step_nexus.py`: liest `slug` aus `data/raw/source_info.json` (S2,
derselbe Vertrag wie S3), findet `dist/<slug>/model.obj` (von S3
geschrieben, inkl. `model.mtl` mit bereits korrekten
`textures/<file>`-Zeilen, siehe S3-Nachtrag 2). Ruft `nxsbuild
<model.obj> -o model.nxs` und danach `nxscompress model.nxs -o
model.nxz` per `subprocess.run(check=True)` auf (A3: Guard bleibt
erhalten). `nxsbuild` liest `model.mtl`/`textures/` automatisch über
den `mtllib`-Mechanismus des OBJ-Formats — kein eigener Texturen-Umzug
nötig wie in S3, da S3 bereits alles relativ zu `model.obj` korrekt
abgelegt hat.
- Bindet nur die zwei Dateien, die dieser Schritt selbst besitzt
(`model.nxs`/`model.nxz`), vor jedem Lauf frisch — nicht den ganzen
`dist/<slug>/`-Ordner wie S3, sonst gingen `model.obj`/`textures/`/
`preview.png` aus S3 verloren.
- `main.py`: globale Flags `--nxsbuild-bin`/`--nxscompress-bin` ergänzt
(gleiches Muster wie `--blender-bin` für S3, inkl. `NXSBUILD_BIN`/
`NXSCOMPRESS_BIN`-Env-Fallback).
- Recherchiert (nicht angenommen) aus `cnr-isti-vclab/nexus`s eigener
Doku (`doc/nxsbuild.md`, `doc/nxsedit.md`, README): `nxsbuild [PLY/OBJ
INPUT] -o <output.nxs>` — `.obj` wird laut Tool-Hilfetext
(`vcg.isti.cnr.it/vcgtools/nexus`) direkt akzeptiert, nicht nur `.ply`.
`nxscompress` ist ein eigenes Executable (README: `gargo.nxs -->
nxscompress.exe --> gargo.nxz`), keine Notlösung über `nxsedit -z` —
das wäre eine Alternative, aber die Familie hat sich (A1-Befund,
Sketchfab-Vorarbeit) bereits auf `nxsbuild`/`nxscompress` festgelegt.

**Abnahme:** `python main.py --only nexus` schlägt mit klarer Meldung
fehl, wenn `nxsbuild`/`nxscompress` nicht gefunden werden
(`shutil.which` + Pfad-Check, wie bei `--blender-bin`) oder wenn
`dist/<slug>/model.obj` fehlt (S3 noch nicht gelaufen). Mit
funktionierenden Binaries: `dist/<slug>/model.nxs` und `model.nxz`
vorhanden; ein fehlschlagender `nxsbuild`/`nxscompress`-Lauf
(`check=True`) stoppt die Pipeline statt sie stillschweigend fortzusetzen.

### Erledigt 2026-09-04

[#erledigt-2026-09-04-2](#erledigt-2026-09-04-2)

Wie bei S3 (kein Blender im Sandkasten) ist auch hier kein echtes
`nxsbuild`/`nxscompress` im Sandkasten verfügbar — Nexus ist nicht
pip-installierbar und ein Bau aus Quellcode braucht Qt/vcglib
(Referenzplattform ist ohnehin Windows, A3). Verifiziert wurde daher die
Python-seitige Orchestrierung gegen zwei Fake-Stellvertreter
(`fake_nxsbuild.py`/`fake_nxscompress.py`, nicht Teil des Patches — reines
Sandkasten-Werkzeug), die deterministische Ausgaben aus den echten
Eingabedateien (inkl. `model.mtl`/`textures/`) ableiten: `--only nexus`
über `main.py` und standalone über `py/step_nexus.py`, beide mit
CLI-Flags und mit `NXSBUILD_BIN`/`NXSCOMPRESS_BIN`-Env-Fallback getestet.
Zwei aufeinanderfolgende Läufe erzeugen byte-identische `model.nxs`/
`model.nxz` (`sha256sum`-Vergleich), `model.obj`/`model.mtl`/`textures/`/
`preview.png` aus S3 bleiben dabei unverändert (nur die zwei S4-eigenen
Dateien werden vor jedem Lauf neu geschrieben). Fehlerpfade geprüft:
fehlendes `nxsbuild`-Binary, fehlendes `nxscompress`-Binary, fehlendes
`model.obj` (S3 nicht gelaufen), sowie ein `nxsbuild`, das mit Exit 1
abbricht (`check=True` propagiert den Fehler korrekt, `main.py` stoppt
die Pipeline statt fortzufahren).

**Nicht verifiziert, da kein echtes `nxsbuild`/`nxscompress` im
Sandkasten:** ob die beiden Binaries `model.obj` inkl. `textures/`
tatsächlich korrekt einlesen (insbesondere `-O`/Textur-Repacking-Verhalten,
standardmäßig *ohne* `-O` — Texturen werden ins `.nxs` eingebettet, nicht
nur referenziert), ob die Default-Parameter (`-f`/Faces pro Patch etc.) für
ein Gebäude wie die Donaghmore-Kirche sinnvoll sind, und ob zwei echte
Läufe wirklich byte-identische `model.nxs`/`model.nxz` liefern (A2 Punkt 2
— unklar, ob z. B. `nxsbuild`s Patch-Zerlegung von Ausführung zu
Ausführung deterministisch ist, anders als bei `preview.png` gibt es dafür
noch keinen konkreten Hinweis in der Upstream-Doku). Nächster sinnvoller
Schritt: `python main.py --only nexus` gegen den echten
`dist/donaghmore-church-ruin/model.obj` aus S3 laufen lassen, `model.nxs`/
`model.nxz` mit `nxsview` ansehen, danach zweimal hintereinander laufen
lassen und `sha256sum` vergleichen.

---

## Teil D — Offene Punkte

- **Schwester-Repo für Software-FDOs.** Angekündigt 2026-09-03: ein Repo,
  das aus einem Git-Link ein `fdo:SoftwareFDO`-Paket baut, mit „viel
  Automatismus". Vorschlag in A4: eigenes Repo (`fdo-software-packager`),
  nicht Zusammenlegung mit `fdo-3d-packager`. Wenn es soweit ist: S5
  (`mdcff`), S6 (`bundle`) und S7 (`build_fdo`) aus diesem Repo als Vorlage
  kopieren (nicht importieren, A3), dabei `fdo_type` und die
  domänenspezifischen `distributions[]`-Rollen anpassen. Kein Schritt in
  diesem Repo, bis das Schwester-Repo tatsächlich startet.
- **Wie wird `fdo-squirrel` in S7 eingebunden?** Drei Optionen, keine
  geprüft: (a) `pip install git+https://github.com/FDOx-squirrel/fdo-squirrel`
  und `ingest.package_source`/`ingest.metadata_ingest` direkt importieren;
  (b) Git-Submodule, lokal per Pfad aufgerufen (näher an `main.py`s
  eigenem `--package`/`config.local.json`-Muster); (c) `fdo-squirrel` als
  externe Voraussetzung dokumentieren (wie Blender/Nexus), Pfad per
  `--fdo-squirrel-path` CLI-Flag. (b) und (c) vermeiden eine Paketierungs-
  Abhängigkeit von einem Repo, das selbst noch v0.1 ist. Zu klären, sobald
  S7 ansteht.
- **`classification_rules.yaml`-Lücke für den Viewer, konkret zu prüfen in
  S7.** Da der Viewer laut A4 mit ins Paket kommt, aber `.html`/`.js`/`.css`
  keine Rolle in `fdo-squirrel`s `classification_rules.yaml` haben: erster
  echter Rundlauf zeigt, ob `fdo-squirrel` unklassifizierte Dateien
  ignoriert, mit einer Default-Rolle versieht oder abbricht. Je nach Befund
  entweder in `fdo-squirrel` eine `auxiliary`-Regel für `viewer/` ergänzen
  (Beschluss: dort nachbessern, nicht hier umgehen — siehe A4) oder, falls
  ein Abbruch droht, den Viewer vorerst unter einem bereits klassifizierten
  Pfad ablegen (`data/documentation/viewer/`) als Übergangslösung.
- **`MD.cff.id` nach Zenodo-Upload:** manuell nachtragen, oder ein späterer
  Schritt (`S7`?), der das automatisiert? Zenodo-Upload selbst ist ohnehin
  außerhalb dieses Repos (kein Netzwerk-Schreibzugriff hier vorgesehen).
- **Eigenes menschenlesbares Begleit-YAML** (wie das `metadata.yaml" aus dem
  Sketchfab-Prototyp) zusätzlich zu `MD.cff` führen, oder reicht `MD.cff`
  allein als Quelle der Wahrheit? Tendenz: nur `MD.cff`, um keine zwei
  Wahrheiten zu pflegen — aber nicht entschieden.
- **Schema-Drift im `fdo-squirrel`-Repo** (Root-`MD.cff` nutzt Felder, die
  laut `example_fdo/MD.cff` „intentionally omitted" sind) ist kein Punkt für
  dieses Repo, aber ein Hinweis wert, falls upstream danach gefragt wird.
