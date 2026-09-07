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
  **Ergänzt 2026-09-07 (S6):** dieselbe Lücke betrifft auch `.mtl`
  (`model.mtl`, Companion-Datei von `model.obj` in `data/model/`) — keine
  eigene Regel dafür in `classification_rules.yaml`, gleicher offener Punkt
  wie beim Viewer, siehe Teil D.
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
  **Korrektur 2026-09-07:** falsch verstanden — der Kommentar in
  `example_fdo/MD.cff` ist selbst veraltet, `MD.cff-schema.yaml` unterstützt
  `spatial`/`temporal`/`heritage_object`/`technique` inzwischen offiziell als
  optionale Felder, und das Root-`MD.cff` ist das Beispiel, das zum
  aktuellen Schema passt, nicht `example_fdo/MD.cff`. Kein Drift, kein
  Handlungsbedarf — siehe A4 und S5.
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
| `MD.cff-schema.yaml` in diesem Repo | vendorte Kopie unter `schemas/md_cff/MD.cff-schema.yaml` (Stand `fdo-squirrel@504b7af5`, 2026-09-04), nicht live von `raw.githubusercontent.com` geladen — `mdcff` bleibt damit netzwerkfrei (A3). Von Hand aktualisieren, wenn sich das Schema upstream ändert; Datei trägt einen Header-Kommentar mit Quelle/Pin | 2026-09-07 |
| Schema-Drift-Befund (A1, 2026-09-03) war ein Fehlalarm | `example_fdo/MD.cff` trägt einen veralteten Kommentar ("spatial/temporal/… intentionally omitted in v0.1"), der nicht mehr zum aktuellen `MD.cff-schema.yaml` passt — das Schema unterstützt `spatial`/`temporal`/`heritage_object`/`technique` inzwischen offiziell als optionale Felder, und das Root-`MD.cff` (nicht `example_fdo/MD.cff`) ist das Beispiel, das zum Schema passt. Kein Handlungsbedarf für uns, aber A1s alter Befund war missverständlich | 2026-09-07, Korrektur |
| `description` fehlt bei `--local` (kein CLI-Flag) bzw. manchmal bei `--sketchfab` | kein neues `--description`-Flag in `fetch` — `mdcff` erzeugt einen deterministischen Fallback-Satz aus `title`/`creator`, keine Warnung dafür (Chat-Entscheidung 2026-09-07, siehe S5) | 2026-09-07 |
| `publishers` (Pflichtfeld in MD.cff) | kein Default (auch nicht LEIZA) — `--publisher-label` ist für `mdcff` Pflicht, fehlt es, bricht der Schritt hart ab (nicht nur Warning/--strict). **Ergänzt 2026-09-07 (2):** Fallback auf `FDO_PUBLISHER_LABEL`/`FDO_PUBLISHER_ID` Env-Vars (Muster `BLENDER_BIN`), weiterhin kein Code-Default | 2026-09-07 |
| Wer ist `publisher` in der Praxis? | **immer** "Research Squirrel Engineers Network" (`https://github.com/Research-Squirrel-Engineers`), **nie** LEIZA — fast alle Modelle sind Fremdmaterial (Citizen Scientists, Museen) oder Flos private Arbeit, LEIZA hat institutionell keinen Anspruch darauf. Das LEIZA-Beispiel im ersten S5-Patch war ein irreführendes Platzhalterbeispiel in der Doku, kein realer Anwendungsfall | 2026-09-07 (2) |
| `source_info.json`'s `todo_placeholders` blockieren `mdcff`? | Vorschlag aus 2026-09-04 bestätigt als **Nein** — nur `Warning:`-Nachricht wie bei `fetch`, harter Abbruch erst mit `--strict` (Chat-Entscheidung 2026-09-07, siehe S5) | 2026-09-07, bestätigt (widerruft den Vorschlag von 2026-09-04) |
| `MD.cff.id`-Platzhalter beim `--strict`-Mechanismus | bewusst **außerhalb** der Warning/--strict-Logik oben — die Zeile "PID wird von diesem Repo nicht vergeben" (2026-09-03) ist ein Dauerzustand, kein vor Release behebbares TODO, ein `--strict`-CI-Lauf darf daran nie scheitern | 2026-09-07 |
| `keywords` in MD.cff | fixer Default (3D data / Cultural Heritage, dieselben Wikidata-IDs wie `fdo-squirrel`s Root-`MD.cff`), nicht CLI-konfigurierbar — dieses Repo packt immer dieselbe Domäne | 2026-09-07 |
| CITATION.cff `authors`-Format | CFF-*entity* (`{name, website}`), nicht *person* (`{given-names, family-names}`) — `creator` ist ein beliebiger Anzeigename (Sketchfab-Username o.ä.), der sich nicht zuverlässig splitten lässt | 2026-09-07 |
| CITATION.cff `license`-Feld | nur gesetzt, wenn `licence` wie eine SPDX-ID aussieht (Heuristik, kein echter SPDX-Abgleich) — Sketchfabs `licence`-Wert ist oft ein menschenlesbares Label ("CC Attribution") statt einer SPDX-ID, CFFs `license`-Feld verlangt aber SPDX. **Ergänzt 2026-09-07 (2):** für `--sketchfab`-Läufe hat `SKETCHFAB_LICENSE_SLUG_TO_SPDX` (`license.slug` aus `sketchfab_meta.json`) Vorrang vor der Heuristik — zuverlässiger, da Sketchfabs Slugs (`cc-by`, `cc0`, …) direkt auf echte SPDX-IDs abbildbar sind; die Heuristik bleibt Fallback für `--local` | 2026-09-07 |
| `sketchfab_meta.json` (S2-Audit-Ablage) auch inhaltlich nutzen? | ja — `mdcff` liest sie jetzt für Anreicherung (`tags`/`categories` → `keywords`, `license.slug`, `publishedAt`/`createdAt`, `viewerUrl`, `faceCount`/`vertexCount`), statt `source_info.json`s S2/S3/S4/S5-Vertrag um weitere Felder zu erweitern — hält den Vertrag stabil, `mdcff` zieht sich Zusatzfelder bei Bedarf selbst, optional (fehlt für `--local` immer, kein Fehler) | 2026-09-07 (2) |
| `user.profileUrl` in `step_fetch.py` | Bug behoben: die API liefert die Profil-URL fertig mit, `step_fetch.py` hat sie vorher immer selbst aus `username` zusammengebaut. `profileUrl` hat jetzt Vorrang, die selbstgebaute Form bleibt nur Fallback | 2026-09-07 (2) |
| Mehrere Sketchfab-URLs übergeben | wiederholbares `--sketchfab URL --sketchfab URL2 ...` (`action="append"`), nicht `--sketchfab-list FILE` | 2026-09-07 (3) |
| Rundlauf nach Batch-Fetch automatisch? | ja — `--all-slugs` führt die gewählte Schritt-Auswahl für jeden gefundenen Slug aus (nicht nur `fetch` batchen, S3–S7 bleiben nicht zwingend Einzelaufrufe) | 2026-09-07 (3) |
| Slug-Auswahl bei mehreren gefetchten Modellen | `--slug`-Flag mit Auto-Fallback, wenn genau ein Slug existiert; bei mehreren ohne `--slug` ein Fehler mit Liste der gefundenen Slugs, kein Raten | 2026-09-07 (3) |
| `data/raw/source_info.json`: Singleton oder pro Slug? | pro Slug (`data/raw/<slug>/source_info.json`) — folgt zwingend aus der Batch-Entscheidung, sonst überschreibt ein zweiter `fetch`-Aufruf den ersten, bevor S3–S5 ihn gesehen haben. Kein Migrationspfad für alte Top-Level-Dateien, `data/raw/` ist regenerierbar (A3) | 2026-09-07 (3) |
| Metadaten-Overrides (`--title` etc.) bei Batch-`--sketchfab` | harter Fehler, nicht stillschweigend ignoriert, wenn mehr als eine `--sketchfab`-URL zusammen mit `--title`/`--creator`/`--creator-profile`/`--licence`/`--licence-url`/`--source-note` übergeben wird — ein Wert kann nicht für mehrere unterschiedliche Modelle gleichzeitig richtig sein | 2026-09-07 (3) |
| Sketchfab-`license.slug`-Zuordnung war falsch | **Korrektur, kein Vorschlag:** `SKETCHFAB_LICENSE_SLUG_TO_SPDX` nutzte erfundene Slugs (`"cc-by"`), die reale API liefert `"by"` (Befund gegen echte Govan-2-Daten, 2026-09-07 im Chat hochgeladen — die vorherige "Verifikation" gegen eine inoffizielle Drittanbieter-Schema-Rekonstruktion war unzureichend). Primärer Mechanismus jetzt `_spdx_from_license_url()`: leitet die SPDX-ID aus der CC-Lizenz-URL her (`creativecommons.org/licenses/by/4.0/` → `CC-BY-4.0`), funktioniert generisch für jede CC-URL, nicht nur Sketchfab-spezifisch, und braucht `sketchfab_meta.json` gar nicht (nutzt `licence_url` aus `source_info.json`). Der (jetzt korrigierte) Slug-Abgleich bleibt als Fallback | 2026-09-07 (5), Korrektur |
| `model_file`-Pfadtrenner plattformabhängig | Bug: `str(dest.relative_to(DATA_RAW))` liefert unter Windows Backslashes, die unter POSIX (Sandkasten, potenziell CI) als einzelnes komisches Dateinamenszeichen statt als Pfadtrenner interpretiert werden — belegt an echten, in diesem Chat hochgeladenen `source_info.json`-Daten (`"govan-2\\govan-2.gltf"`). Fix: `.as_posix()` statt `str()` beim Schreiben; `DATA_RAW / model_file` liest Forward-Slashes unter Windows genauso korrekt wie unter POSIX, also keine Änderung an lesender Seite nötig | 2026-09-07 (5) |
| `--all-slugs` bei fehlschlagendem Slug | **Ergänzt/geändert 2026-09-07 (6):** springt jetzt zum nächsten Slug weiter statt den ganzen Lauf abzubrechen (Muster: Batch-Fetch) — Fehler nur, wenn **alle** Slugs fehlschlagen, sonst `Warning:` (blockiert nur `--strict`). Bei genau einem Slug (Normalfall ohne `--all-slugs`) bricht ein Fehler weiterhin sofort ab, da es nichts zum Weiterspringen gibt | 2026-09-07 (6) |
| 3DHOP-Vendoring: Version/Quelle (`bundle`, S6) | `cnr-isti-vclab/3DHOP` Tag `4.3` (Commit `a8c145d`, 2020-06-18), `minimal/`-Paket unter `assets/3dhop/` vendort — offline (A3), nicht live geladen. Trimm-Begründung und vollständige Dateiliste in `assets/3dhop/NOTICE.md`, nicht hier dupliziert | 2026-09-07 (S6) |
| 3DHOP-Template (`bundle`, S6) | `3DHOP_no_tools.html` (umbenannt `index.html`), nicht `3DHOP_all_tools.html` — reiner Präsentations-Viewer in einem citable Datenpaket, keine Editier-/Messwerkzeuge nötig | 2026-09-07 (S6) |
| ZIP-Determinismus (`bundle`, S6) | fixer Pro-Eintrag-Zeitstempel `1980-01-01` (Zip-Format-eigenes Minimum, keine RELEASE-Semantik — reine Container-Metadaten ohne fachliche Bedeutung) plus fixe Unix-Rechte `0o644` statt echter Datei-mtimes/-Rechte, die je nach Checkout/Betriebssystem streuen würden. `write_deterministic_zip()` in `fdo_3d_packager_utils.py`, als kanonischer Writer neben `write_json`/`write_yaml` gedacht — wiederverwendbar für spätere Repos der Familie mit ZIP-Output | 2026-09-07 (S6) |
| Fehlende Texturen (`bundle`, S6) | kein Fehler, kein `Warning:` — ein unbe-texturiertes Modell (z. B. das Freshford-Low-Poly-Testmodell) ist ein legitimer Fall, `data/textures/` wird einfach weggelassen statt eine falsche Warnung zu erzeugen | 2026-09-07 (S6) |
| `fetch` + Rundlauf in einem `main.py`-Aufruf | Ja — sobald `fetch` Teil der gewählten Schritte ist (`--from fetch` o. ä.), läuft `fetch` einmalig, danach automatisch der Rest **nur für die gerade neu geholten Slug(s)** (`args.fetched_slugs`, von `step_fetch.py` gesetzt), nicht für alle unter `data/raw/`. `--slug`/`--all-slugs` werden in diesem Fall ignoriert (mit Hinweis auf stderr, kein Fehler) — beide könnten die Frage "welche(r) Slug(s)" ohnehin nicht besser beantworten als `fetch` selbst | 2026-09-07 (6) |

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
| S5 | `mdcff`-Schritt: `MD.cff` + `CITATION.cff` schreiben, gegen Schema validieren | fdo-3d-packager | S2, S4 | erledigt 2026-09-07 |
| S6 | `bundle`-Schritt: `dist/<slug>.zip` im `fdo-squirrel`-Layout | fdo-3d-packager | S3, S4, S5 | erledigt 2026-09-07 |
| S7 | `dist/<slug>.zip` durch `fdo-squirrel` schicken, `fdo-metadata.ttl` als Beleg (Muster: registry S8) | fdo-3d-packager | S6 | offen |
| S8 | Batch-Fetch (`--sketchfab` wiederholbar) + Multi-Slug-Infrastruktur (`data/raw/<slug>/source_info.json`, `--slug`, `--all-slugs`) | fdo-3d-packager | S2–S5 | erledigt 2026-09-07 |

S3 und S4 sind technisch unabhängig von S5 und können in beliebiger
Reihenfolge bzw. parallel in Angriff genommen werden; S5 braucht die
deskriptiven Metadaten aus S2 (Titel/Creator/Lizenz) und prüft, dass S4
durchgelaufen ist (Vollständigkeits-Gate: `model.obj`/`model.nxs`/
`model.nxz` müssen existieren), liest dessen Checksums aber **nicht** in
MD.cff ein -- Korrektur 2026-09-07, siehe S5: A4 hatte `distributions[]`
schon am 2026-09-03 als "nicht vorbefüllen" entschieden, dieser Satz hier
war seitdem nicht mehr konsistent damit.

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
- `--nxsbuild-original-textures` (`-O`, kein Textur-Repacking) und
`--nxsbuild-ram <MB>` (`-r`) als zusätzliche Passthrough-Flags ergänzt,
nachdem der erste echte Lauf gegen die volle Donaghmore-Kirche
(1,49 Mio. Vertices, 2,67 Mio. Faces, 6 Texturen) lange gebraucht hat
— beide Flags werden 1:1 an `nxsbuild` durchgereicht, sonst keine
eigene Logik.
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

### Nachtrag 2026-09-04 — erster echter Lauf, `-O`/`-r` ergänzt

[#nachtrag-2026-09-04--erster-echter-lauf--o-r-ergänzt](#nachtrag-2026-09-04--erster-echter-lauf--o-r-ergänzt)

Erster echter `nxsbuild`/`nxscompress`-Lauf gegen die volle Donaghmore-
Kirche durchgeführt (`C:\Nexus_43\nxsbuild.exe`/`nxscompress.exe`,
`--nxsbuild-bin`/`--nxscompress-bin` wie vorgesehen benutzt). Binary
korrekt gefunden, Import/Verarbeitung liefen sichtbar (Vertices/Faces/
Texturen-Log passend zu S3s Zahlen), Ergebnis von Flo committed — S4 ist
damit gegen einen echten Fall bestätigt durchgelaufen, nicht nur gegen die
Fake-Stellvertreter im Sandkasten. Konkrete Laufzeit nicht protokolliert.

Bei den Standardparametern hat der Lauf bei 1,49 Mio. Vertices/2,67 Mio.
Faces/6 Texturen (S3-Nachtrag 2026-09-04) spürbar lange gedauert (kein
Hänger, sondern echte Rechenzeit — vermutlich vor allem das
Textur-Atlas-Repacking bei „Creating level 0"). Daraufhin `--nxsbuild-
original-textures` (`-O`) und `--nxsbuild-ram <MB>` (`-r`) als
Passthrough-Flags ergänzt (siehe A4/Substanz oben) — noch nicht gegen
einen echten Lauf mit diesen Flags verifiziert, nur die Weiterleitung an
den Subprocess im Sandkasten (Fake-Stellvertreter, unterschiedliche
Flag-Kombinationen erzeugen unterschiedliche Fake-Ausgaben — bestätigt
also nur, dass die Flags ankommen, nicht was `nxsbuild` damit tatsächlich
macht).

Nächster Testkandidat (Beschluss im Chat, nicht A4-würdig — reine
Testdaten-Wahl, keine Architekturentscheidung): „Govan 2" (Hogback-Stein,
[The Govan Stones](https://sketchfab.com/3d-models/govan-2-b9dc56bfc1d342f6b4da3281e6629c07),
236,4k Dreiecke/119,8k Vertices laut Sketchfab-Seite, CC-BY 4.0) statt
eines weiteren Gebäudes — rund Faktor 11 kleiner als Donaghmore, um die
Pipeline schneller iterieren zu können und `-O`/`-r` an einem echten,
aber kleinen Fall zu prüfen.

### Nachtrag 2026-09-04 (2) — S2–S4 komplett gegen Govan 2 durchgelaufen, `-O` bestätigt fehlerhaft für diese Pipeline

[#nachtrag-2026-09-04-2--s2s4-komplett-gegen-govan-2-durchgelaufen--o-bestätigt-fehlerhaft-für-diese-pipeline](#nachtrag-2026-09-04-2--s2s4-komplett-gegen-govan-2-durchgelaufen--o-bestätigt-fehlerhaft-für-diese-pipeline)

`fetch` → `convert` → `nexus` einmal komplett gegen Govan 2 durchlaufen
lassen (`--sketchfab` direkt mit der Sketchfab-URL, kein manuelles
`--title`/`--creator`/`--licence` nötig — die Data API liefert das):
**2,24s + 31,50s + 7,45s ≈ 41s Gesamtlaufzeit**, alle drei Schritte ohne
Fehler. `convert` fand dabei nur 2 von 4 Kandidaten-Bilddateien für
`relink_images()` (`defaultMat_baseColor.jpeg`/`defaultMat_normal.jpeg`
gematcht, `Render Result`/`Viewer Node` nicht — letztere sind interne
Blender-Compositor-Knoten ohne Dateipfad, kein Fehler). `nxsbuild` erhielt
entsprechend nur die Basisfarb-Textur, keine Normal-Map — OBJ/MTL kennt
kein `map_Bump`-Äquivalent für glTF-Normal-Maps, das ist eine
Formatgrenze, kein Bug in `_copy_textures_from_raw()` (S3).

**`-O`-Befund bestätigt, nicht nur vermutet:** erster `nexus`-Lauf mit
`--nxsbuild-original-textures --nxsbuild-ram 8000` lief technisch sauber
durch (`nxscompress` aber mit `Textures: 0`). `model.nxz` in `nxsview`
geöffnet: mit „Colors" an komplett schwarz, mit „Colors" aus
weiß-matt/nur Normalen-Schattierung — in beiden Fällen keine Spur der
Foto-Textur, nicht nur ein Anzeigeproblem. Zweiter Lauf ohne `-O` (nur
`--nxsbuild-ram 8000`): `nxscompress` meldet `Textures: 24`, `nxsview`
zeigt den Stein korrekt fotorealistisch texturiert, unabhängig vom
„Colors"-Häkchen. Damit ist bestätigt: `-O` liefert für diese Pipeline
ein texturloses `.nxz` — nicht verwendbar, da S6 (`bundle`) ein
in-sich-geschlossenes `.nxz` für den 3DHOP-Viewer braucht. Empfehlung in
README.md/`step_nexus.py`/`main.py`-Hilfetext entsprechend korrigiert:
`-O` bleibt als Opt-in-Flag bestehen, ist aber nicht mehr als
Standardempfehlung für große Modelle dokumentiert; `--nxsbuild-ram`
allein bleibt der unproblematische Hebel.

Genaue Ursache (warum `-O` beim Komprimieren zu `Textures: 0` führt —
referenziert `nxsbuild` die Original-Datei extern, statt sie einzubetten,
und geht diese Referenz beim `nxscompress`-Schritt schlicht verloren, oder
liegt es an einem Zusammenspiel mit `nxscompress` selbst) ist nicht
geklärt und für den weiteren Fortschritt auch nicht nötig — Ergebnis reicht
als Handlungsanweisung.

Damit ist **S4 jetzt auch gegen einen echten Fall mit korrekt sichtbarer
Textur bestätigt** (Donaghmore-Lauf zuvor lief zwar durch, aber ob die
Textur ankam, war nicht geprüft). Offen bleibt weiterhin: Determinismus
über zwei echte Läufe (A2 Punkt 2) und ob die Default-Parameter (`-f`
Faces pro Patch etc.) für größere Modelle wie Donaghmore sinnvoll sind.

---

## S5 — `mdcff`

[#s5--mdcff](#s5--mdcff)

**Ziel:** `data/raw/source_info.json` (S2) + Vollständigkeits-Check gegen
S4s Outputs → `dist/<slug>/MD.cff` + `dist/<slug>/CITATION.cff`, MD.cff
offline gegen die vendorte Kopie von `MD.cff-schema.yaml` validiert.

**Substanz:**

- `schemas/md_cff/MD.cff-schema.yaml`: vendorte Kopie aus `fdo-squirrel`
  (Pin `504b7af5`, 2026-09-04, siehe A4) statt Live-Fetch — `mdcff` bleibt
  damit netzwerkfrei wie A3 verlangt.
- `py/fdo_3d_packager_utils.py`: neuer `write_yaml()`-Helper (analog
  `write_json()` — Insertion-Order statt alphabetisch, damit die
  Schlüsselreihenfolge im geschriebenen `MD.cff`/`CITATION.cff` der
  Schema-Reihenfolge folgt statt zufällig zu sortieren; kein
  `datetime.now()` beteiligt).
- `py/step_mdcff.py`: baut `MD.cff` aus `source_info.json` (Titel/Creator/
  Lizenz/Source-URL) + `--publisher-label`/`--publisher-id` (neue
  CLI-Flags, auch in `main.py`s globalem Parser). `distributions[]` bleibt
  wie beschlossen leer (A4, 2026-09-03) — stattdessen prüft der Schritt nur,
  dass `dist/<slug>/model.obj`/`model.nxs`/`model.nxz` existieren, sonst
  Abbruch mit Hinweis auf `convert`/`nexus`.
- Alle sechs in diesem Chat als Form beantworteten bzw. daraus folgenden
  Entscheidungen (`description`-Fallback, `publishers` ohne Default,
  `todo_placeholders`-Warning bestätigt, `id`-Platzhalter außerhalb der
  Warning-Logik, feste `keywords`, CITATION.cff-`authors` als Entity,
  CITATION.cff-`license`-Heuristik) stehen mit Datum in A4 und ausführlicher
  im Docstring von `step_mdcff.py` selbst.

### Erledigt 2026-09-07

[#erledigt-2026-09-07](#erledigt-2026-09-07)

Implementiert und gegen zwei Fake-`source_info.json` (Sketchfab-artig mit
`source_url`/`creator_profile`, wie "Govan 2"; `--local`-artig ohne beides,
wie "Rathealy Standing Stone") plus leeren `model.obj`/`model.nxs`/
`model.nxz`-Dateien (Blender/Nexus sind im Sandkasten weiterhin nicht
verfügbar, aber `mdcff` selbst ist reines Python/YAML/JSON-Schema und
braucht sie nicht) laufen lassen:

- `python main.py --only mdcff --publisher-label ... --publisher-id ...`
  läuft für beide Fälle grün durch, `MD.cff` validiert **nicht nur gegen
  unsere eigene vendorte Schema-Kopie, sondern auch gegen `fdo-squirrel`s
  echten `ingest.metadata_ingest.validate_against_schema()`** (dessen Repo
  für diesen Test zusätzlich geklont und direkt aufgerufen — kein Mock).
  Das ist mehr, als S5 laut Abnahme verlangt (der volle Rundlauf ist S7),
  aber ein starker Beleg dafür, dass die vendorte Kopie wirklich Byte für
  Byte dem Original entspricht (per `diff` bestätigt) und unser
  MD.cff-Writer wirklich schema-konform schreibt, nicht nur laut eigenem
  Validator.
- `python main.py --only mdcff` ohne `--publisher-label` bricht hart ab
  (exit 1), ohne vorhandene `dist/<slug>/model.nx*` ebenso — beides wie in
  A4 entschieden.
- `todo_placeholders` in `source_info.json` (Test: `licence` künstlich auf
  `TODO: licence not set` gesetzt) erzeugt eine `Warning:`-Nachricht, Lauf
  bleibt exit 0; mit `--strict` schlägt derselbe Lauf fehl. Bestätigt A4s
  2026-09-04-Vorschlag wie in diesem Chat entschieden.
- Determinismus: zweimal hintereinander gegen denselben Fake-Zustand
  gelaufen, `md5sum` von `MD.cff`/`CITATION.cff` identisch (A2 Punkt 2).
- `--local`-Fall (keine `description`, keine `source_url`, keine
  `creator_profile`) erzeugt den Fallback-Beschreibungssatz, lässt
  `related_resources` komplett weg (kein leeres Array geschrieben) und
  lässt `website`/`url` in CITATION.cff weg — alles wie vorgesehen.
  `licence: "CC-BY-4.0"` landet in CITATION.cff `license`, das
  Sketchfab-artige `licence: "CC Attribution"` (mit Leerzeichen) dagegen
  nicht (SPDX-Heuristik greift korrekt in beide Richtungen).
- `--list`/`--dry-run` bleiben unverändert leichtgewichtig (keine
  `yaml`/`jsonschema`-Importe ohne echten Schritt-Aufruf, lazy Import wie
  bisher).

**Nicht geprüft:** der volle Rundlauf `dist/<slug>.zip` durch eine
`fdo-squirrel`-Instanz inklusive Klassifikation (das ist S7); ob
`nxsbuild`/`nxscompress` wirklich `model.nx*` liefern, die zu den hier
generierten `MD.cff` passen (S4 lief hier nicht real mit, nur leere
Platzhalterdateien als Existenz-Marker für das Vollständigkeits-Gate).

### Nachtrag 2026-09-07 (2) — Sketchfab-Metadaten-Anreicherung, Publisher per Env-Var, `profileUrl`-Fix

[#nachtrag-2026-09-07-2--sketchfab-metadaten-anreicherung-publisher-per-env-var-profileurl-fix](#nachtrag-2026-09-07-2--sketchfab-metadaten-anreicherung-publisher-per-env-var-profileurl-fix)

Nach dem `mdcff`-Commit kam im Chat die berechtigte Frage auf, welche
Metadaten Sketchfabs Data API v3 überhaupt liefert und ob `publisher`
daraus ableitbar wäre. Recherche (offizielle Docs + ein echtes
Produktionscode-Beispiel, das `metadata.user.profileUrl`/
`metadata.user.displayName`/`metadata.license.{label,url}` fürs
Attributions-Rendering benutzt) bestätigt das Feldset, das
`fetch_metadata()` in `step_fetch.py` schon abgreift, plus einiges, das
bisher ungenutzt blieb:

- **Kein Publisher-Konzept auf der Model-Resource.** Sketchfab liefert nur
  `user` (den Uploader) — kein institutionelles "Publisher"-Feld. Das
  bestätigt die bestehende Trennung `creator` (Uploader, aus der API) vs.
  `publisher` (wer das FDO-Paket veröffentlicht, hier fast nie derselbe):
  praktisch alle Modelle in diesem Repo sind Fremdmaterial (Citizen
  Scientists wie Anne-Karoline Distel, Museen) oder Flos private Arbeit —
  LEIZA hat institutionell keinen Anspruch, das zu publizieren. Publisher
  ist daher **immer** "Research Squirrel Engineers Network"
  (`https://github.com/Research-Squirrel-Engineers`), nie LEIZA — das
  LEIZA-Beispiel im ursprünglichen S5-Patch war ein irreführendes
  Platzhalterbeispiel, kein tatsächlicher Anwendungsfall (siehe A4).
- **`user.profileUrl` kommt schon in der API-Antwort mit** — `step_fetch.py`
  hat die Profil-URL bisher selbst aus `username` zusammengebaut, obwohl
  die API sie fertig liefert. Gefixt: `profileUrl` hat jetzt Vorrang, die
  selbstgebaute Form bleibt nur Fallback.
- **`sketchfab_meta.json` (S2, bisher nur Audit-Ablage) wird jetzt von
  `mdcff` mitgelesen** (`load_sketchfab_meta()`/`extract_enrichment()`),
  statt zusätzliche Felder in `source_info.json`s Vertrag aufzunehmen — der
  Vertrag zwischen S2 und S3/S4/S5 bleibt dadurch stabil, `mdcff` zieht
  sich die Zusatzfelder bei Bedarf selbst. Neu genutzt: `tags[]`/
  `categories[]` → zusätzliche `keywords` (neben den festen Defaults),
  `license.slug` → echtes SPDX-Mapping für CITATION.cff (`cc-by` →
  `CC-BY-4.0` usw., `st`/`ed` bewusst ohne Mapping, da nicht SPDX-fähig —
  zuverlässiger als die bisherige Label-Heuristik, die für `--local` als
  Fallback bleibt), `publishedAt`/`createdAt` → `date_released`/
  `date_created` in MD.cff und `date-released` in CITATION.cff,
  `viewerUrl` → bevorzugt gegenüber der user-eingegebenen `source_url` für
  `related_resources`/CITATION.cff `url`, `faceCount`/`vertexCount` →
  `technique.processing`-Notiz.
- **`technique.acquisition.method`** wird jetzt auch für `--local`-Läufe
  aus `--source-note` befüllt (z. B. "KiriEngine, 180 photos, 2026-03") —
  vorher lag das Feld nur in `source_info.json`, nie in `MD.cff`.
- **`--publisher-label`/`--publisher-id` fallen jetzt auf
  `FDO_PUBLISHER_LABEL`/`FDO_PUBLISHER_ID` zurück** (Muster:
  `--blender-bin`/`BLENDER_BIN`) — kein Code-Default, aber kein Eintippen
  bei jedem Lauf mehr nötig, wenn die Env-Var einmal gesetzt ist.

Getestet: dieselbe Govan-2-Fixture wie im ersten S5-Patch, jetzt zusätzlich
mit einer realistischen `sketchfab_meta.json` (Felder nach der oben
verifizierten API-Struktur, mangels Netzwerkzugriff auf `api.sketchfab.com`
im Sandkasten von Hand gebaut, keine erfundenen Werte für real geprüfte
Feldnamen). Ergebnis erneut gegen `fdo-squirrel`s echten
`ingest.metadata_ingest.validate_against_schema()` **valide** — inklusive
`technique`/`date_created`/`date_released`/angereicherter `keywords`.
Determinismus (zweimal laufen lassen, `md5sum`) weiterhin gegeben.
`--local`-Fall ohne `sketchfab_meta.json` weiterhin unverändert lauffähig
(kein Absturz, nur ohne Anreicherung). CLI-Flag sticht Env-Var wie erwartet
(Standard-argparse-Verhalten, kein Sonderfall nötig).

**Nicht geprüft:** echte Live-Daten von `api.sketchfab.com` (im Sandkasten
kein Zugriff auf die Sketchfab-API selbst, nur auf öffentliche
Such-/Doku-Treffer) — die Fixture-Feldnamen sind gegen echten
Produktionscode verifiziert, aber kein echter API-Roundtrip.

---

## S6 — `bundle`

[#s6--bundle](#s6--bundle)

**Ziel:** `dist/<slug>/` (aus S3–S5: `model.obj`+`model.mtl`+`textures/`+
`preview.png` aus `convert`, `model.nxs`+`model.nxz` aus `nexus`,
`MD.cff`+`CITATION.cff` aus `mdcff`) wird zusammen mit einem vendorten
3DHOP-Miniviewer zu `dist/<slug>.zip` im von `fdo-squirrel` erwarteten
Layout gepackt — offline, ohne eigene RDF-Erzeugung (das übernimmt S7).

**Uploads für diesen Schritt:** `PRIMER.md` + Repo-Bundle (s. A5).

**Substanz:**

- Ziel-Layout (A2, bestätigt 2026-09-03, jetzt umgesetzt): `MD.cff`/
  `CITATION.cff` oben, `data/model/` (`.obj`/`.mtl`/`.nxs`/`.nxz`),
  `data/textures/` (nur wenn in `dist/<slug>/textures/` tatsächlich etwas
  liegt — ein unbe-texturiertes Modell ist kein Fehler, siehe A4),
  `data/images/preview.png`, `viewer/` (3DHOP).
- `py/step_bundle.py`: Vollständigkeits-Gate prüft `MD.cff`, `CITATION.cff`,
  `model.obj`, `model.nxs`, `model.nxz`, `preview.png` (S3–S5 müssen
  gelaufen sein); `model.mtl` und `textures/` bleiben absichtlich optional,
  beide werden nur aufgenommen, wenn sie existieren. Entfernt ein evtl.
  vorhandenes altes `<slug>.zip` vor jedem Lauf (Idempotenz, Muster S4),
  schreibt danach neu über `write_deterministic_zip()`.
- **`write_deterministic_zip()`** (neu in `fdo_3d_packager_utils.py`, als
  kanonischer Writer neben `write_json`/`write_yaml`): fixer
  Pro-Eintrag-Zeitstempel `1980-01-01` (Zip-Format-Minimum) und fixe
  Unix-Rechte `0o644` statt echter Datei-mtimes/-Rechte. Zwei Läufe über
  unveränderte Eingaben erzeugen dadurch byte-identische ZIPs
  (`sha256sum`-geprüft, siehe Erledigt-Abschnitt).
- **3DHOP-Miniviewer, vendort unter `assets/3dhop/`** (neu, kein separates
  Deliverable, A4 vom 2026-09-03 bestätigt): echtes
  `cnr-isti-vclab/3DHOP`-Repo geklont (Tag `4.3`), `minimal/
  3DHOP_no_tools.html` als Basis (nicht `_all_tools`, siehe A4), auf die
  tatsächlich geladenen Dateien getrimmt (~970 KB statt ~9,8 MB Upstream,
  größtenteils deren Demo-Modell und fünf ungenutzte Skin-Themes). Einzige
  inhaltliche Änderung an der HTML: `models/gargo.nxz` →
  `../data/model/model.nxz` (fixer relativer Pfad, da das Bundle-Layout
  immer gleich ist — kein Templating nötig, kein Jinja2 für diesen einen
  Wert). `LICENSE.txt` (GPLv3) wandert mit in jedes `dist/<slug>.zip`
  (`viewer/LICENSE.txt`) — Lizenzpflicht, kein optionales Extra. Volle
  Begründung/Trimm-Liste in `assets/3dhop/NOTICE.md`, nicht hier
  dupliziert.
- `collect_viewer_files()` kopiert alles unter `assets/3dhop/` außer
  `NOTICE.md` (unsere eigene Vendoring-Notiz, nicht Teil des Viewers) —
  kein von Hand gepflegtes Datei-Manifest, das mit dem Ordner
  auseinanderlaufen könnte.
- `--slug` ergänzt (Teil-D-Punkt aus S8 jetzt für S6 erledigt), gleiches
  Muster wie S3–S5.

**Abnahme:** `python main.py --only bundle` schlägt mit klarer Meldung
fehl, wenn `dist/<slug>/` unvollständig ist (S3–S5 noch nicht gelaufen)
oder `assets/3dhop/` fehlt/leer ist. Mit vollständigen Eingaben:
`dist/<slug>.zip` enthält exakt das Ziel-Layout, `model.mtl`/
`data/textures/` erscheinen nur, wenn sie in `dist/<slug>/` tatsächlich
vorhanden sind. Zwei aufeinanderfolgende Läufe erzeugen byte-identische
ZIPs. `python py/step_bundle.py --slug ...` läuft eigenständig.

### Erledigt 2026-09-07

[#erledigt-2026-09-07-3](#erledigt-2026-09-07-3)

Gegen zwei Fixture-`dist/<slug>/`-Bäume verifiziert (kein echter S3/S4-
Output im Sandkasten verfügbar, siehe S3/S4 selbst) — bewusst zwei sehr
unterschiedliche Fälle: `govan-2` (mit `model.mtl` + 2 Texturen) und
`freshford-st-lachtains-well-low-poly` (ohne `textures/`, ohne
`model.mtl`), um beide Zweige der optionalen Felder wirklich zu prüfen,
nicht nur den Normalfall. Geprüft: `--only bundle` (Einzelslug und
`--all-slugs`), Standalone-Aufruf (`python py/step_bundle.py --slug ...`),
`--dry-run`, `--strict` (bleibt grün, `bundle` erzeugt aktuell nie eine
`Warning:`), Vollständigkeits-Gate (fehlende S4-Outputs → klarer Fehler,
Exit 1), fehlender `assets/3dhop/`-Ordner → klarer Fehler statt eines
kaputten ZIPs. ZIP-Inhalt per `zipfile.ZipFile.infolist()` geprüft: exaktes
Layout, fixer Zeitstempel `1980-01-01`, fixe Rechte `0o644` bei jedem der
24 Viewer-Dateien plus den slug-eigenen Dateien. Zwei aufeinanderfolgende
Läufe über unveränderte Fixtures: `sha256sum`-identische `dist/<slug>.zip`
für beide Slugs.

**Nicht geprüft (kein Browser im Sandkasten):** ob `viewer/index.html` das
gepackte `data/model/model.nxz` tatsächlich rendert — nur der eine
geänderte Pfad wurde per Diff gegen die Upstream-Datei bestätigt, nicht das
Laufzeitverhalten von SpiderGL/Nexus.js/Corto im Browser. Ebenfalls nicht
geprüft: der tatsächliche Rundlauf durch `fdo-squirrel` (S7) — insbesondere,
ob `classification_rules.yaml` `.mtl`/`.html`/`.js`/`.css` ignoriert, mit
einer Default-Rolle versieht oder abbricht (Teil D).

Nächster sinnvoller Schritt (Flo, auf der echten Windows-Maschine): der
volle Rundlauf gegen zwei echte, bereits früher erfolgreich gefetchte
Modelle (Govan 2 — texturiert, Freshford St Lachtain's Well low poly — zum
Vergleich das kleinere, ggf. unbe-texturierte Modell), diesmal bis
`bundle`:

```cmd
python main.py --from fetch --sketchfab "https://sketchfab.com/3d-models/govan-2-b9dc56bfc1d342f6b4da3281e6629c07" --sketchfab "https://sketchfab.com/3d-models/freshford-st-lachtains-well-low-poly-ae1e1f4daa7d433dbbf076407134e81e" --nxsbuild-bin "C:\Nexus_43\nxsbuild.exe" --nxscompress-bin "C:\Nexus_43\nxscompress.exe" --publisher-label "Research Squirrel Engineers Network" --publisher-id "https://github.com/Research-Squirrel-Engineers"
```

— danach `dist/govan-2.zip`/`dist/freshford-st-lachtains-well-low-poly.zip`
entpacken, `viewer/index.html` **über einen lokalen Webserver** öffnen
(nicht `file://` — Web Worker/CORS, 3DHOP braucht `http(s)://`) und prüfen,
ob sich das jeweilige Modell wirklich dreht/lädt, inklusive Textur bei
Govan 2.

### Nachtrag 2026-09-07 (2) — erster echter Lauf bei Flo, Icon-Bug gefunden und behoben, Rendering noch offen

[#nachtrag-2026-09-07-2--erster-echter-lauf-bei-flo-icon-bug-gefunden-und-behoben-rendering-noch-offen](#nachtrag-2026-09-07-2--erster-echter-lauf-bei-flo-icon-bug-gefunden-und-behoben-rendering-noch-offen)

Erster echter Lauf des genauen Befehls aus dem vorherigen Abschnitt auf
Flos Windows-Maschine, committed. **`fetch`→`convert`→`nexus`→`mdcff`→
`bundle` liefen für beide Slugs fehlerfrei durch** (`build_fdo`/S7
weiterhin No-Op-Stub, wie erwartet):

| Slug | fetch | convert | nexus | mdcff | bundle | ZIP-Größe |
|---|---|---|---|---|---|---|
| govan-2 | (Batch, 3,31s für beide) | 37,06s | 10,55s | 0,17s | 2,77s | 39 121 654 Byte |
| freshford-st-lachtains-well-low-poly | – | 30,80s | 3,62s | 0,05s | 1,02s | 22 049 205 Byte |

Govan 2: 120 797 Vertices/236 352 Faces (deckt sich mit der
Sketchfab-Seitenangabe 236,4k Dreiecke/119,8k Vertices aus S4), `nxscompress`
meldet `Textures: 24` — wie beim ersten S4-Lauf. `convert` fand nur die
Basisfarb-Textur (`1 texture(s) -> textures/`), keine Normal-Map, wie in
S3/S4 bereits als OBJ/MTL-Formatgrenze dokumentiert, kein neuer Befund.

**Korrektur einer Annahme aus dem vorherigen Abschnitt:** Freshford ist
entgegen der dort geäußerten Vermutung **nicht** unbe-texturiert — echter
Lauf zeigt `4 model file(s), 1 texture(s)` genau wie Govan 2, also inkl.
`model.mtl` und einer Basisfarb-Textur. Der "unbe-texturierte Fall" war
eine reine Sandkasten-Testannahme für die Fixture-Verifikation (siehe
Erledigt-Abschnitt oben), keine reale Eigenschaft dieses Modells — der
Code-Pfad für ein wirklich unbe-texturiertes Modell bleibt trotzdem
korrekt (ungetestet an echten Daten, aber die Fixture-Verifikation deckt
ihn ab).

**Gefundener und behobener Bug — falsche Icon-Dateinamen beim Vendoring:**
`viewer/index.html` im Browser geöffnet (`python -m http.server` im
entpackten `govan-2.zip`), Konsole zeigte zwei 404: `GET
/viewer/skins/dark/lightcontrol_on.png` und `.../lightcontrol.png`. Ursache:
beim Vendoring (siehe S6-Substanz oben) wurden die HTML-`id`-Attribute
(`id="light"`/`id="light_on"`) fälschlich als Dateinamen gelesen statt der
tatsächlichen `src`-Werte — 3DHOP hat unter `skins/dark/` sowohl
`light*.png`/`light_off.png` (ein anderes, in `index.html` gar nicht
referenziertes Icon-Paar) als auch `lightcontrol*.png` (das tatsächlich
referenzierte Paar). `assets/3dhop/skins/dark/light.png`/`light_on.png`
durch die beiden korrekten `lightcontrol.png`/`lightcontrol_on.png`
ersetzt, `assets/3dhop/NOTICE.md` entsprechend korrigiert. Kein Einfluss
auf `step_bundle.py` selbst (weiterhin 24 Viewer-Dateien, nur zwei davon
mit anderem Namen).

**Weiterhin offen — Modell rendert nicht sichtbar:** nach dem Icon-Fix
zeigt die Konsole `3DHOP version: 4.3` (Viewer initialisiert) und `GET
/data/model/model.nxz` mit Status 200 (Modell wird geladen), aber auch
eine Warnung `WebGL warning: checkFramebufferStatus: Framebuffer not
complete (status: 0x8cd7)`. Das Canvas zeigt keine erkennbare
3D-Geometrie, nur blasse, unzusammenhängende Linien statt des Hogback-
Steins. Ob die Framebuffer-Warnung ursächlich ist (0x8CD7 =
`FRAMEBUFFER_INCOMPLETE_MISSING_ATTACHMENT`, in 3DHOP typischerweise vom
Offscreen-Pick-Framebuffer, nicht zwingend vom Hauptrender-Pass), oder ob
es an der Trackball-Startdistanz (`startDistance: 2.5`,
`minMaxDist: [0.5, 3.0]`, aus `index.html`, unverändert von Upstream
übernommen) liegt, die von einem auf die reale Modellgröße bezogenen
Bounding-Sphere-Autofit abhängt, der hier möglicherweise nicht wie erwartet
greift, ist noch nicht geklärt — im Sandkasten kein Browser verfügbar, um
das selbst zu prüfen. **Nächster Schritt:** Flo prüft nach dem Icon-Fix,
ob Scrollen/Ziehen im Canvas doch ein Modell zeigt (nur falsch
positionierte Kamera) oder das Canvas tatsächlich leer bleibt (echtes
Render-Problem), und teilt die volle Browser-Konsole/Netzwerk-Liste
(nicht nur den sichtbaren Ausschnitt) für die nächste Diagnose.

---

## S8 — Batch-Fetch & Multi-Slug-Infrastruktur

[#s8--batch-fetch--multi-slug-infrastruktur](#s8--batch-fetch--multi-slug-infrastruktur)

**Ziel:** mehrere Sketchfab-URLs in einem `fetch`-Aufruf holen können
(Anlass: die "Holy Wells"-Testliste, 2026-09-07 im Chat geteilt, ~20
Modelle) und danach den Rundlauf (`convert`→`nexus`→`mdcff`→…) für jedes
geholte Modell einzeln oder gesammelt anstoßen können.

**Substanz** (Chat-Entscheidungen 2026-09-07, siehe A4):

- **`--sketchfab` ist jetzt wiederholbar** (`action="append"` in
  `main.py` und `step_fetch.py`s eigenem `__main__`-Block):
  `--sketchfab URL1 --sketchfab URL2 ...` statt einer Datei- oder
  Listen-Syntax.
- **`data/raw/source_info.json` ist kein Singleton mehr.** Liegt jetzt
  unter `data/raw/<slug>/source_info.json`, direkt neben
  `sketchfab_meta.json` (ebenfalls dorthin verschoben) und dem
  Modell-File — sonst hätte ein zweiter `fetch`-Aufruf die Handoff-Daten
  des ersten überschrieben, bevor S3–S5 sie je gesehen hätten. `model_file`
  bleibt wie bisher relativ zu `data/raw/` (also weiterhin
  `<slug>/<datei>`), nur der Ort von `source_info.json` selbst ändert
  sich — keine Änderung an `DATA_RAW / info["model_file"]` in
  `step_convert.py`/`step_nexus.py` nötig.
- **Kein Migrationspfad für alte Top-Level-`data/raw/source_info.json`.**
  `data/raw/` ist laut A3 ohnehin regenerierbar (read-only Rohdaten, aber
  aus `fetch` neu erzeugbar) — einfach `fetch` erneut laufen lassen statt
  eine alte Datei von Hand zu verschieben.
- **`fdo_3d_packager_utils.py`: `discover_slugs()`/`resolve_slug()`** neu
  — jeder Slug mit `data/raw/<slug>/source_info.json` zählt als
  "gefetcht". `resolve_slug(explicit)`: `--slug` gewinnt immer; ohne
  `--slug` wird bei genau einem gefundenen Slug automatisch dieser
  verwendet (unverändertes Verhalten für den bisherigen
  Ein-Modell-Workflow); bei mehreren wird **nicht geraten**, sondern ein
  Fehler mit der Liste der gefundenen Slugs geworfen.
- **`--slug`** ist jetzt ein CLI-Flag von `convert`/`nexus`/`mdcff` (S3–S5,
  in `main.py` und den jeweiligen `__main__`-Blöcken).
- **`--all-slugs`** (nur `main.py`, kein Schritt-eigenes Flag): führt die
  gewählte Schritt-Auswahl (`--only`/`--from`/`--skip`/Default) für jeden
  gefundenen Slug nacheinander aus, mit einer `=== slug: <name> ===`
  Trennzeile pro Modell. Guards: `--all-slugs` + `--slug` gleichzeitig ist
  ein Fehler (widersprüchlich); `--all-slugs` mit `fetch` in der Auswahl
  ist ein Fehler (`fetch` erzeugt Slugs, braucht also keinen — separat
  aufrufen). `--strict` bezieht sich weiterhin auf den **gesamten** Lauf
  über alle Slugs (eine Warnung bei irgendeinem Slug reicht für den
  Abbruch am Ende), nicht pro Slug.
- **Batch-Fetch, Teilfehler-Verhalten:** ein einzelner fehlschlagender
  URL bricht den Batch nicht ab (jeder wird einzeln versucht, Fehler
  abgefangen); Rückgabe ist `False` nur, wenn **alle** URLs fehlschlagen,
  sonst `True` mit `Warning:`-Präfix, wenn nicht alle geklappt haben —
  gleiches Muster wie überall sonst in diesem Repo (Warning blockiert nur
  `--strict`). Bei genau einer `--sketchfab`-URL bleibt die Meldung exakt
  wie vor diesem Umbau (kein `"1/1 model(s)"`-Rauschen für den nach wie
  vor häufigsten Fall).
- **Metadaten-Overrides (`--title`/`--creator`/`--creator-profile`/
  `--licence`/`--licence-url`/`--source-note`) sind bei mehr als einer
  `--sketchfab`-URL ein harter Fehler**, nicht nur ignoriert — ein Wert
  könnte sonst fälschlich auf alle Modelle angewendet werden, obwohl jedes
  längst seine eigenen Sketchfab-Metadaten mitbringt. Der Fehler kommt
  *vor* jedem Netzwerkzugriff.
- **Reihenfolge-Fix in `_fetch_one_sketchfab()`:** `sketchfab_meta.json`
  und `source_info.json` werden jetzt **nach** `copy_model_with_siblings()`
  geschrieben, nicht davor — die Funktion räumt `data/raw/<slug>/` per
  `rmtree()` leer, bevor sie es neu befüllt; vorher geschriebene Dateien
  im selben Verzeichnis wären dabei mitgelöscht worden. Nur beim
  Verschieben auf den per-Slug-Pfad aufgefallen, betraf den alten
  Top-Level-Pfad nicht (der lag außerhalb von `data/raw/<slug>/`).

### Erledigt 2026-09-07 (4)

[#erledigt-2026-09-07-4](#erledigt-2026-09-07-4)

Getestet (kein Blender/Nexus im Sandkasten, aber `fetch --local` und
`mdcff` sind reines Python und liefen echt, nicht nur gegen Fixtures):

- Echter `fetch --local`-Lauf schreibt jetzt tatsächlich nach
  `data/raw/<slug>/source_info.json` statt `data/raw/source_info.json`.
- `mdcff` ohne `--slug` bei genau einem gefetchten Modell: Auto-Detect
  funktioniert unverändert.
- Zweiten Slug per zweitem `fetch --local` angelegt: `mdcff` ohne `--slug`
  bricht jetzt korrekt mit der "multiple slugs found"-Meldung ab (exit 1,
  keine geratene Auswahl); mit `--slug <name>` funktioniert es gezielt.
- `--all-slugs --only mdcff` lief über beide Slugs durch (eine
  Sketchfab-artige Fixture mit `sketchfab_meta.json`-Anreicherung, eine
  `--local`-artige ohne) — beide `MD.cff` **valide gegen `fdo-squirrel`s
  echten Validator**, die angereicherte mit `technique`/`date_created`/
  `date_released`/zusätzlichen `keywords`, die andere ohne, kein Crash.
- Guards bestätigt: `--all-slugs --slug X` → Fehler; `--all-slugs --only
  fetch` → Fehler; `--all-slugs --dry-run` zeigt Plan **und** Slug-Liste;
  `--all-slugs` ohne jeden gefetchten Slug → sauberer Fehler statt
  Absturz.
- `api.sketchfab.com` ist vom Sandkasten aus zwar über `curl`/`requests`
  erreichbar, liefert aber `403` mit `x-deny-reason: host_not_allowed` im
  Header — bestätigt, dass es der Egress-Proxy blockiert, nicht ein echter
  API-Fehler. Damit gegen zwei erfundene UIDs geprüft: mehrere
  `--sketchfab`-URLs ohne Overrides werden unabhängig voneinander
  versucht (kein Absturz beim ersten Fehler), beide schlagen fehl → `False`
  mit beiden Fehlermeldungen aufgelistet, wie vorgesehen. Mit Overrides +
  mehreren URLs: Abbruch **vor** dem ersten Netzwerkzugriff, wie
  vorgesehen. Einzelne `--sketchfab`-URL + `--title`: kein
  Batch-Guard-Fehler, normaler (netzwerkbedingter) Fehlschlag wie vor
  diesem Umbau.
- Determinismus (`mdcff` zweimal, `md5sum`) und `--list`/`--dry-run`
  (weiterhin ohne `yaml`/`jsonschema`-Import ohne echten Schritt-Aufruf)
  weiterhin bestätigt.

**Nicht geprüft:** ein echter Batch-Fetch mit tatsächlich herunterladbaren
Modellen (Netzwerkzugriff auf `api.sketchfab.com` vom Sandkasten aus
blockiert, siehe oben) — die Schleifen-/Fehlerbehandlungslogik ist geprüft,
aber nicht der komplette Download-Pfad für mehrere echte Modelle
hintereinander. `bundle`/`build_fdo` (S6/S7) kennen `--slug`/`--all-slugs`
noch nicht, sind aber ohnehin noch S1-Stubs.

### Nachtrag 2026-09-07 (5) — echter Batch-Fetch bei Flo, zwei Bugs an echten Daten gefunden

[#nachtrag-2026-09-07-5--echter-batch-fetch-bei-flo-zwei-bugs-an-echten-daten-gefunden](#nachtrag-2026-09-07-5--echter-batch-fetch-bei-flo-zwei-bugs-an-echten-daten-gefunden)

**Echter Testfall, zum Merken:** Flo hat auf seiner Windows-Maschine
tatsächlich einen 5-URL-Batch-Fetch laufen lassen und committed:

```cmd
python main.py --only fetch --sketchfab "https://sketchfab.com/3d-models/govan-2-b9dc56bfc1d342f6b4da3281e6629c07" --sketchfab "https://sketchfab.com/3d-models/callan-st-augustines-well-re-upload-9feacac0fda14a189a1a59d2e129b1e4" --sketchfab "https://sketchfab.com/3d-models/freshford-st-lachtains-well-low-poly-ae1e1f4daa7d433dbbf076407134e81e" --sketchfab "https://sketchfab.com/3d-models/ballymakeera-st-abbans-grave-fc5578e364cf4ec6b6ec871229654690" --sketchfab "https://sketchfab.com/3d-models/cork-ogham-stone-ciic-83-ucc-14-4346e42eff7e4a979dbbec2264afc87d"
```

Alle 5/5 erfolgreich geholt (`[fetch] fetched 5/5 Sketchfab model(s)`),
danach `python main.py --all-slugs --from convert`: Blender 5.2.1 LTS
konvertierte `ballymakeera-st-abbans-grave` (erster Slug alphabetisch)
tatsächlich real — 7 Mesh-Objekte importiert, `relink_images()` fand 2
Texturen, `model.obj`+`preview.png` erfolgreich geschrieben (57,80s). Das
ist die erste echte End-to-End-Bestätigung von `convert` (S3) und `fetch`
(S2/S8) in Produktion, nicht nur im Sandkasten. Danach schlug `nexus`
(S4) fehl: `nxsbuild binary 'nxsbuild' not found`. Das ist **kein**
Kapazitäts-/Größenproblem (Flos eigene Vermutung im Chat, "vielleicht
sind die 5 auch zu viel") — der Lauf hatte schlicht kein
`--nxsbuild-bin`/`NXSBUILD_BIN` gesetzt (in früheren S4-Tests wurde
`C:\Nexus_43\nxsbuild.exe` benutzt); wäre bei einem einzelnen Modell
identisch aufgetreten. Vor diesem Fix (Nachtrag 2026-09-07 (6) unten)
hätte dieser eine Fehler außerdem den gesamten `--all-slugs`-Lauf
abgebrochen, ohne die anderen 4 Slugs überhaupt zu versuchen.

Die echten `source_info.json`/`sketchfab_meta.json` für `govan-2` aus
diesem Lauf wurden im Chat hochgeladen und haben zwei echte Bugs
aufgedeckt, beide gefixt:

- **`SKETCHFAB_LICENSE_SLUG_TO_SPDX` war komplett falsch.** Die echte API
  liefert `license.slug: "by"` für CC Attribution, nicht `"cc-by"` wie im
  ersten S5-Patch angenommen (aus einer inoffiziellen
  Drittanbieter-Schema-Rekonstruktion übernommen, nie gegen echte Daten
  geprüft — die damalige "Verifikation" war unzureichend, siehe A4-Zeile
  dazu). Primärmechanismus jetzt `_spdx_from_license_url()` in
  `step_mdcff.py`: leitet die SPDX-ID direkt aus der CC-Lizenz-URL her
  (`.../licenses/by/4.0/` → `CC-BY-4.0`, `.../publicdomain/zero/1.0/` →
  `CC0-1.0`) — generisch, nicht Sketchfab-spezifisch, funktioniert auch
  für `--local` mit einer Standard-CC-URL als `--licence-url`. Der
  (jetzt korrigierte) Slug-Abgleich bleibt als zweiter Fallback für den
  Fall, dass die URL mal nicht parsbar ist, aber der Slug vorliegt.
- **`model_file` enthielt Windows-Backslashes** (`"govan-2\\govan-2.gltf"`)
  — `str(dest.relative_to(DATA_RAW))` liefert unter Windows
  `WindowsPath.__str__()`, also Backslashes; unter POSIX (Sandkasten,
  potenzielle CI-Runner) wird das nicht als Pfadtrenner erkannt, sondern
  als ein einzelnes Zeichen im Dateinamen — `DATA_RAW / model_file` würde
  dort ins Leere laufen. Fix: `.as_posix()` statt `str()` in
  `step_fetch.py` (beide Stellen: `_fetch_one_sketchfab()`, `run_local()`).
  Lesende Seite (`step_convert.py`: `DATA_RAW / info["model_file"]`)
  brauchte keine Änderung — Windows-`pathlib` akzeptiert Forward-Slashes
  beim Aufbau eines Pfads genauso wie Backslashes.

Beide echten Govan-2-Dateien (nach dem Fix, `model_file`-Trenner von Hand
auf Forward-Slash umgestellt, da hier nicht neu gefetcht werden kann)
durch `mdcff` gejagt: `MD.cff` validiert weiterhin gegen `fdo-squirrel`s
echten Validator, `CITATION.cff` bekommt jetzt korrekt `license:
CC-BY-4.0` (vorher hätte die falsche Slug-Zuordnung nie gegriffen, wäre
also stumm auf die Label-Heuristik zurückgefallen — mit demselben Ergebnis
in diesem einen Fall zufällig, aber nicht verlässlich für andere
CC-Varianten wie `by-sa`/`by-nc-nd`). `_spdx_from_license_url()` zusätzlich
gegen vier synthetische CC-URL-Varianten (`by`, `by-sa`, `by-nc-nd`,
`publicdomain/zero`) sowie `None`/eine Nicht-CC-URL geprüft — alle korrekt.
Determinismus erneut bestätigt.

### Nachtrag 2026-09-07 (6) — `--all-slugs` überspringt Fehler, `fetch` + Rundlauf kombinierbar

[#nachtrag-2026-09-07-6--all-slugs-überspringt-fehler-fetch--rundlauf-kombinierbar](#nachtrag-2026-09-07-6--all-slugs-überspringt-fehler-fetch--rundlauf-kombinierbar)

Zwei Chat-Entscheidungen (Form, siehe A4), ausgelöst durch den echten
Batch-Testfall oben:

- **`--all-slugs` bricht nicht mehr beim ersten fehlschlagenden Slug ab.**
  `main.py`s neue `run_over_slugs()`-Funktion versucht jeden Slug
  unabhängig, sammelt Fehlschläge, und meldet nur dann einen harten
  Fehler (exit 1), wenn **alle** Slugs fehlgeschlagen sind — sonst
  `Warning: N/M slug(s) failed: ...` (blockiert nur `--strict`). Bei genau
  einem Slug (kein `--all-slugs`, der bei weitem häufigste Fall) bleibt
  das alte Verhalten exakt erhalten: ein Fehler bricht sofort ab, es gibt
  nichts zum Weiterspringen.
- **`fetch` kann jetzt Teil derselben `main.py`-Auswahl sein**
  (`--from fetch ...`), statt zwingend ein separater Aufruf zu sein.
  `main.py`s neue `_run_fetch_then_rest()`: `fetch` läuft einmalig (nie
  pro Slug — die Slugs existieren ja noch nicht), danach der Rest der
  Auswahl automatisch für genau die Slug(s), die `fetch` gerade erzeugt
  hat (`args.fetched_slugs`, neu von `step_fetch.py`s `run()` gesetzt) —
  nicht für alle unter `data/raw/` gefundenen. `--slug`/`--all-slugs`
  werden in diesem Fall ignoriert (Hinweis auf stderr, kein Fehler) — der
  alte harte `SystemExit`-Guard gegen `--all-slugs`+`fetch` ist damit
  hinfällig und entfernt.

**Getestet** (kein Blender/Nexus im Sandkasten, aber die Orchestrierung
selbst ist reines Python):

- `--all-slugs`-Fehlertoleranz: zwei `--local`-Slugs angelegt, einem
  bewusst `model.nxz` vorenthalten (mdcff-Vollständigkeits-Gate greift) —
  `--all-slugs --only mdcff` verarbeitet den intakten Slug trotzdem,
  meldet `Warning: 1/2 slug(s) failed`, exit 0 ohne `--strict`, exit 1
  mit `--strict`. Beide Slugs kaputt gemacht (auch `model.nxz` beim
  ersten gelöscht) → `All 2 slug(s) failed`, exit 1 auch ohne `--strict`.
- Kombinierter `fetch`+Rundlauf: direkt gegen `_run_fetch_then_rest()`
  getestet (nicht über die volle CLI, da `--skip` nur einen Schritt auf
  einmal ausschließen kann und `convert`/`nexus` im Sandkasten ohnehin
  fehlschlagen würden) — ein Slug (`fetch`+`mdcff`), zwei Slugs
  (`fetch` liefert `args.fetched_slugs = [s1, s2]`, `mdcff` läuft über
  beide mit `=== slug: ... ===`-Trennzeilen), `--only fetch` (kein
  Rundlauf danach, nur `fetch`s eigenes Ergebnis), `--slug`/`--all-slugs`
  zusammen mit `fetch` in der Auswahl (Hinweis statt Fehler, Lauf
  trotzdem erfolgreich). `--dry-run --from fetch` zeigt den Plan inkl.
  `fetch` und einen Hinweis statt einer `--all-slugs`-Slug-Liste.
  Alle erzeugten `MD.cff` weiterhin valide gegen `fdo-squirrel`s echten
  Validator.

**Nicht geprüft:** der kombinierte Modus über die echte CLI mit echtem
Blender/Nexus (nur die Orchestrierungslogik direkt getestet, siehe oben);
ob `--all-slugs`s Fehlertoleranz sich mit dem kombinierten `fetch`-Modus
gleich verhält, wenn `convert`/`nexus` bei einem von mehreren echten
Modellen real fehlschlagen (z. B. bei einem korrupten glTF) — dafür fehlt
im Sandkasten weiterhin Blender.

### Nachtrag 2026-09-07 (7) — erster echter Produktions-Rundlauf, 5/5 Modelle, alles bestätigt

[#nachtrag-2026-09-07-7--erster-echter-produktions-rundlauf-55-modelle-alles-bestätigt](#nachtrag-2026-09-07-7--erster-echter-produktions-rundlauf-55-modelle-alles-bestätigt)

Flo hat den in Nachtrag (6) neu gebauten kombinierten Modus real gegen
Windows/Blender 5.2.1 LTS/Nexus mit den 5 Holy-Wells-URLs aus Nachtrag (5)
laufen lassen — diesmal mit korrekt gesetztem `--nxsbuild-bin`/
`--nxscompress-bin` (siehe Nachtrag (5): der frühere Fehlschlag war ein
fehlendes Flag, kein Bug):

```cmd
python main.py --from fetch --sketchfab "..." --sketchfab "..." --sketchfab "..." --sketchfab "..." --sketchfab "..." --nxsbuild-bin "C:\Nexus_43\nxsbuild.exe" --nxscompress-bin "C:\Nexus_43\nxscompress.exe" --publisher-label "Research Squirrel Engineers Network" --publisher-id "https://github.com/Research-Squirrel-Engineers"
```

**Ergebnis: 5/5 Modelle komplett durch `fetch`→`convert`→`nexus`→`mdcff`
(→`bundle`/`build_fdo` als No-Op-Stubs), kein einziger Fehler.** Das ist
der erste echte End-to-End-Beleg für die *gesamte* aktuell implementierte
Pipeline in einem Lauf — bisher war jeder Schritt nur einzeln oder gegen
Fixtures bestätigt (Sandkasten hat kein Blender/Nexus). Insbesondere: das
ist der erste echte Lauf von `mdcff` gegen **echten** `nexus`-Output
(vorher immer leere Platzhalterdateien als Existenz-Marker) und der erste
echte Beleg, dass der kombinierte `fetch`+Rundlauf-Modus (Nachtrag (6))
und die Mehrfach-Slug-Schleife über die volle CLI tatsächlich funktionieren,
nicht nur direkt gegen `_run_fetch_then_rest()` getestet.

**Kennzahlen der 5 Modelle** (aus Terminal-Log + `dir /s`-Inventar,
zum Nachschlagen für künftige Kapazitätsplanung):

| Slug | Vertices | Faces | Texturen (`.nxz`) | `convert` | `nexus` | `.nxz`-Größe |
|---|--:|--:|--:|--:|--:|--:|
| `govan-2` | 120.797 | 236.352 | 24 | 39,1s | 13,7s | 9,9 MB |
| `callan-st-augustines-well-re-upload` | 830.170 | 1.450.181 | 150 | 72,8s | 97,1s | 67,4 MB |
| `freshford-st-lachtains-well-low-poly` | 7.719 | 11.347 | 3 | 55,2s | 5,3s | 6,4 MB |
| `ballymakeera-st-abbans-grave` | 381.970 | 644.990 | 66 | 60,3s | 251,4s | 104,5 MB |
| `cork-ogham-stone-ciic-83-ucc-14` | 894.209 | 1.499.990 | 144 | 57,2s | 66,1s | 14,9 MB |

Gesamt: `fetch` 16,5s + `convert`/`nexus` zusammen ≈ 718s ≈ 12 Minuten für
alle 5. Auffällig: `ballymakeera-st-abbans-grave` hat weniger
Vertices/Faces als `callan-...`/`cork-...`, aber mit Abstand die längste
`nexus`-Zeit (251s) — Ursache nicht geklärt (evtl. Patch-Zerlegung
abhängig von Mesh-Topologie, nicht nur Face-Count; kein bestätigter
Befund, nur eine Beobachtung).

**Weitere Bestätigungen aus diesem Lauf:**

- **`-O`-Vermeidung war richtig** (A4, 2026-09-04/2026-09-07 (2)): alle
  5 `.nxz` haben `Textures: N > 0` (24/150/3/66/144) — kein einziges
  `Textures: 0` wie beim `-O`-Fehlschlag damals.
  Keines der Flags wurde diesmal gesetzt, wie vorgesehen.
- **`relink_images()` verhält sich wie in S3 dokumentiert**: bei jedem
  Modell werden 2 von 4 (oder 1 von 3) Image-Datablocks nicht gematcht —
  das sind durchgehend die internen Blender-Compositor-Knoten
  ("Render Result"/"Viewer Node"), kein neuer Bug.
- **`bundle`/`build_fdo` (S6/S7) stören die Kette nicht**, obwohl sie
  noch No-Op-Stubs sind — `nothing to do (...)` wird korrekt als Erfolg
  gewertet, die Schleife läuft für jeden der 5 Slugs sauber bis zum Ende
  durch.
- **Preview-Renderings** (`preview.png`, alle fünf im Chat geteilt)
  sehen alle plausibel aus: erkennbare Objekte (Holy-Well-Schrein mit
  Kreuz, gemauerter Brunnentrog mit Wasser, Ogham-Stein-Fragment,
  ummauerte Anlage mit Wasserbecken, Govan-Hogback mit sichtbarem
  Flechtband-Muster am unteren Rand — passend zur echten
  Sketchfab-Beschreibung aus Nachtrag (5)). Keine offensichtlichen
  Render-Fehler (verzerrte Texturen, falsche Kamera, schwarze Flächen).

Flos Vorschlag, für schnellere Iterationszyklen künftig auf 2 URLs
zurückzugehen (Govan + ein kleineres Modell, z. B.
`freshford-st-lachtains-well-low-poly` mit nur 60s Gesamtlaufzeit) ist
sinnvoll und braucht keine Code-Änderung — einfach zwei `--sketchfab`
statt fünf übergeben.

**Damit als real bestätigt gelten jetzt (vorher nur gegen Fixtures/
Einzelmodelle geprüft):** `fetch`-Batch mit 5 echten URLs (S2/S8),
`convert` gegen 5 unterschiedliche echte Modelle (S3, vorher nur
Donaghmore/Govan 2 einzeln), `nexus` gegen 5 unterschiedliche echte
Modelle ohne `-O` (S4), `mdcff` gegen echten `nexus`-Output statt
Platzhalterdateien (S5), kombinierter `fetch`+Rundlauf-Modus über die
volle CLI (S8, Nachtrag (6)).

**Weiterhin nicht geprüft:** `bundle`/`build_fdo` selbst (S6/S7, noch
nicht implementiert); `--all-slugs`s Fehlertoleranz mit einem *echten*
partiellen Fehlschlag (z. B. ein korruptes Modell mitten in einem
Mehrfach-Lauf) — dieser Lauf hatte 5/5 Erfolge, kein Fehlerfall dabei.

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
- **`classification_rules.yaml`-Lücke für Viewer und `.mtl`, konkret zu
  prüfen in S7.** Da der Viewer laut A4 mit ins Paket kommt, aber
  `.html`/`.js`/`.css` keine Rolle in `fdo-squirrel`s
  `classification_rules.yaml` haben — und, beim Implementieren von S6
  gefunden: `.mtl` (`model.mtl`, Companion-Datei von `model.obj`) auch
  nicht: erster echter Rundlauf zeigt, ob `fdo-squirrel` unklassifizierte
  Dateien ignoriert, mit einer Default-Rolle versieht oder abbricht. Je
  nach Befund entweder in `fdo-squirrel` eine `auxiliary`-Regel für
  `viewer/` (und ggf. `.mtl`) ergänzen (Beschluss: dort nachbessern, nicht
  hier umgehen — siehe A4) oder, falls ein Abbruch droht, die betroffenen
  Dateien vorerst unter einem bereits klassifizierten Pfad ablegen
  (`data/documentation/viewer/`) als Übergangslösung. **Ergänzt 2026-09-07
  (S6):** dieselbe Lücke gilt auch, ob `data/textures/` (Pfadpräfix
  `textures/`, nicht `data/textures/`) von `classification_rules.yaml`
  tatsächlich noch als `auxiliary` erkannt wird, oder ob der Pfad-Präfix
  nur auf ein Top-Level-`textures/` passt — im S6-Layout (A2, seit
  2026-09-03 so festgelegt, hier nicht neu verhandelt) liegt es unter
  `data/textures/`. Auch das zeigt sich erst am echten Rundlauf.
- **`MD.cff.id` nach Zenodo-Upload:** manuell nachtragen, oder ein späterer
  Schritt (`S7`?), der das automatisiert? Zenodo-Upload selbst ist ohnehin
  außerhalb dieses Repos (kein Netzwerk-Schreibzugriff hier vorgesehen).
- **Eigenes menschenlesbares Begleit-YAML** (wie das `metadata.yaml" aus dem
  Sketchfab-Prototyp) zusätzlich zu `MD.cff` führen, oder reicht `MD.cff`
  allein als Quelle der Wahrheit? Tendenz: nur `MD.cff`, um keine zwei
  Wahrheiten zu pflegen — aber nicht entschieden.
- **Schema-Drift im `fdo-squirrel`-Repo** war ein Fehlalarm, siehe A4
  (2026-09-07, „Schema-Drift-Befund war ein Fehlalarm") — kein offener
  Punkt mehr, nur zur Erinnerung falls upstream danach gefragt wird.
- **`spatial`/`temporal`/`heritage_object`/`identifiers`/`version`** bleiben
  in `MD.cff` für S5 vorerst ungenutzt (optionale Felder, keine verlässliche
  Datenquelle aus `source_info.json`/`sketchfab_meta.json`).
  **Erledigt 2026-09-07 (2):** `date_created`/`date_released` (aus
  Sketchfabs `createdAt`/`publishedAt`) und `technique` (aus
  `--source-note` bzw. `faceCount`/`vertexCount`) sind jetzt umgesetzt, war
  vorher hier als offener Punkt notiert.
- **`identifiers[]` nach Zenodo-Upload:** wenn `id` manuell durch die echte
  DOI ersetzt wird (siehe `ID_PLACEHOLDER` in `step_mdcff.py`), sollte
  vermutlich auch ein `identifiers`-Eintrag `{scheme: doi, value: ...}`
  ergänzt werden (Muster: `example_fdo/MD.cff`) — aktuell manueller
  Nacharbeitsschritt, nicht automatisiert.
- **`--publisher-label`/`--publisher-id` sind Singular** (ein Publisher,
  kein wiederholbares Flag) — reicht für den aktuellen Anwendungsfall
  (immer "Research Squirrel Engineers Network"). Falls künftig mehrere
  Publisher gebraucht werden, Flag-Design dann erweitern.
- **Mehrere Sketchfab-URLs auf einmal fetchen (Batch)?** **Erledigt
  2026-09-07 (S8):** echter Umbau (Option b), nicht der Shell-Loop —
  `data/raw/<slug>/source_info.json` pro Modell, `--sketchfab` wiederholbar,
  `--slug`/`--all-slugs` in `main.py`. Details siehe S8 in Teil C.
- **Testkandidaten "Holy Wells" (Wikidata-Query, 2026-09-07 im Chat
  geteilt):** ~20 weitere Sketchfab-3D-Modelle irischer Holy Wells
  (Wikidata-Items mit `3d`-Property auf Sketchfab-URLs, u. a. Saint
  Augustine's Well/Q122189562, Kenny's Well/Q114439798, St Leonard's
  Well/Q126454422, …) — zusätzlich zu Donaghmore/Govan 2 als reale
  Testfälle für künftige `--sketchfab`-Läufe, sobald Netzwerk/Blender/Nexus
  verfügbar sind. Liste liegt nur im Chat-Verlauf, nicht in diesem Dokument
  dupliziert. **Vier davon bereits real erfolgreich gefetcht** (Nachtrag
  2026-09-07 (5)): `callan-st-augustines-well-re-upload`,
  `freshford-st-lachtains-well-low-poly`, `ballymakeera-st-abbans-grave`,
  `cork-ogham-stone-ciic-83-ucc-14` — alle fünf inzwischen real durch
  den kompletten `fetch`→`convert`→`nexus`→`mdcff`-Rundlauf gelaufen,
  siehe Nachtrag 2026-09-07 (7).
- **`bundle`/`build_fdo` (S6/S7) kennen `--slug` noch nicht** — sind aber
  ohnehin noch S1-Stubs (`nothing_to_do()`), betrifft niemanden, bis S6
  tatsächlich angegangen wird. Beim Implementieren von S6 `--slug`/
  `getattr(args, "slug", None)` nach demselben Muster wie S3–S5 ergänzen.
  **Erledigt 2026-09-07 (S6):** `bundle` hat jetzt `--slug`, gleiches
  Muster wie S3–S5 (siehe S6 in Teil C). `build_fdo` (S7) ist weiterhin
  ein reiner Stub, betrifft also weiterhin niemanden — der Punkt bleibt
  bis S7 offen, nur für `bundle` erledigt.
- **Echter Batch-Fetch gegen reale, herunterladbare Modelle: erledigt**
  (Nachtrag 2026-09-07 (7)) — 5/5 Modelle real gefetcht, konvertiert,
  komprimiert und beschrieben, kein Fehler.
- **S6 (`bundle`) implementiert und gegen Fixtures verifiziert** (siehe S6
  in Teil C, Erledigt 2026-09-07) — nicht mehr der offene Punkt. Nächster
  offener Punkt ist jetzt **S7** (`build_fdo`, Rundlauf durch
  `fdo-squirrel`) — und, davor, Flos echter Lauf von S6 gegen Govan 2 +
  Freshford auf der Windows-Maschine (siehe S6-Erledigt-Abschnitt für den
  genauen Befehl), um `viewer/index.html` wirklich im Browser zu prüfen.
- **3DHOP-Viewer zeigt kein sichtbares Modell im Browser.** Echter Lauf
  bei Flo (S6, Nachtrag 2026-09-07 (2)): `model.nxz` lädt (HTTP 200),
  3DHOP initialisiert (`3DHOP version: 4.3` in der Konsole), aber das
  Canvas bleibt ohne erkennbare Geometrie, dazu eine WebGL-
  Framebuffer-Warnung. Ein falscher Icon-Dateiname wurde dabei gefunden
  und behoben (siehe Nachtrag), löste das Rendering-Problem aber
  vermutlich nicht, da Icons und WebGL-Canvas unabhängige Teile sind. Noch
  nicht geklärt: Framebuffer-Warnung ursächlich oder harmlos (Pick-
  Framebuffer, nicht Hauptrender-Pass)? Trackball-Startdistanz
  (`startDistance`/`minMaxDist` aus `index.html`, unverändert von
  Upstream) korrekt für real-skalierte `nxsbuild`-Ausgabe, oder muss sie
  angepasst werden? Nächster Schritt liegt bei Flo (Browser-Diagnose, kein
  Browser im Sandkasten verfügbar) — siehe Nachtrag für Details.
