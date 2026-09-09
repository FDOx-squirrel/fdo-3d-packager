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
| Einbindungsmechanismus für `fdo-squirrel` | Pip aus GitHub, gepinnt (`fdo-squirrel@504b7af`), Konsolenskript per `sysconfig.get_path("scripts")` gefunden (Muster: `fdo-squirrel-registry` S8, wortwörtlich kopiert, siehe S7) | 2026-09-07 (S7), entschieden |
| `source_info.json`-Vertrag (S2→S3/S4/S5) | eine Datei, von `fetch` geschrieben: `slug`, `model_file` (Pfad **relativ zu `data/raw/`**, kann ein Unterverzeichnis enthalten — z. B. `donaghmore-church-ruin/donaghmore-church-ruin.gltf`, korrigiert 2026-09-04, siehe S2-Nachtrag), `title`/`description`/`creator`/`creator_profile`/`licence`/`licence_url`/`source_url`/`sketchfab_uid`/`source_note`, plus `todo_placeholders` (Liste fehlender Pflichtfelder). Bei `--local` ohne `--title`/`--creator`/`--licence` werden `"TODO: … not set"`-Platzhalter geschrieben und `fetch` gibt eine mit `Warning:` beginnende Meldung zurück — nicht fatal im Normallauf, aber `--strict` (= CI) schlägt fehl, bis die Felder gesetzt sind. Dieselbe `Warning:`-Mechanik greift jetzt auch, wenn vom Modell referenzierte Begleitdateien (`scene.bin`, `textures/…`, `.mtl`) fehlen. `mdcff` (S5) soll den Bau verweigern, solange `todo_placeholders` nicht leer ist (Vorschlag, in S5 zu bestätigen) | 2026-09-04, korrigiert 2026-09-04 |
| Begleitdateien eines Modells (`scene.bin`, `textures/…` bei `.gltf`; `.mtl`+Texturen bei `.obj`) | werden von `fetch` erkannt (`resolve_sibling_files()`) und unter denselben relativen Pfaden neben das Modell nach `data/raw/<slug>/` kopiert, statt nur die eine Modell-Datei zu kopieren — sonst bricht Blender (S3) an der relativen URI-Auflösung ab. `.glb` hat keine externen Begleitdateien (self-contained) | 2026-09-04, Befund aus erstem echten `--sketchfab`-Lauf |
| Verhältnis zum künftigen Software-FDO-Packager (Git-Link → `fdo:SoftwareFDO`) | eigenes Repo (`fdo-software-packager`?), nicht dasselbe wie hier — `fetch`+`convert` sind fachlich verschieden (Sketchfab/Blender/Nexus vs. Git-Clone+Repo-Analyse), und A3 verlangt ohnehin Kopieren statt Referenzieren, ein gemeinsames Repo spart also keine Duplizierung, nur Übersicht. Was kopiert werden sollte, sobald das Schwester-Repo startet: MD.cff/CITATION.cff-Writer, Bundle-Layout, `build_fdo`-Schritt (S5–S7) | 2026-09-03, Vorschlag |
| `MD.cff-schema.yaml` in diesem Repo | vendorte Kopie unter `schemas/md_cff/MD.cff-schema.yaml` (Stand `fdo-squirrel@504b7af5`, 2026-09-04), nicht live von `raw.githubusercontent.com` geladen — `mdcff` bleibt damit netzwerkfrei (A3). Von Hand aktualisieren, wenn sich das Schema upstream ändert; Datei trägt einen Header-Kommentar mit Quelle/Pin | 2026-09-07 |
| Schema-Drift-Befund (A1, 2026-09-03) war ein Fehlalarm | `example_fdo/MD.cff` trägt einen veralteten Kommentar ("spatial/temporal/… intentionally omitted in v0.1"), der nicht mehr zum aktuellen `MD.cff-schema.yaml` passt — das Schema unterstützt `spatial`/`temporal`/`heritage_object`/`technique` inzwischen offiziell als optionale Felder, und das Root-`MD.cff` (nicht `example_fdo/MD.cff`) ist das Beispiel, das zum Schema passt. Kein Handlungsbedarf für uns, aber A1s alter Befund war missverständlich | 2026-09-07, Korrektur |
| `description` fehlt bei `--local` (kein CLI-Flag) bzw. manchmal bei `--sketchfab` | kein neues `--description`-Flag in `fetch` — `mdcff` erzeugt einen deterministischen Fallback-Satz aus `title`/`creator`, keine Warnung dafür (Chat-Entscheidung 2026-09-07, siehe S5) | 2026-09-07 |
| `publishers` (Pflichtfeld in MD.cff) | kein Default (auch nicht LEIZA) — `--publisher-label` ist für `mdcff` Pflicht, fehlt es, bricht der Schritt hart ab (nicht nur Warning/--strict). **Ergänzt 2026-09-07 (2):** Fallback auf `FDO_PUBLISHER_LABEL`/`FDO_PUBLISHER_ID` Env-Vars (Muster `BLENDER_BIN`), weiterhin kein Code-Default | 2026-09-07 |
| Wer ist `publisher` in der Praxis? | **immer** "Research Squirrel Engineers Network", **nie** LEIZA — fast alle Modelle sind Fremdmaterial (Citizen Scientists, Museen) oder Flos private Arbeit, LEIZA hat institutionell keinen Anspruch darauf. Das LEIZA-Beispiel im ersten S5-Patch war ein irreführendes Platzhalterbeispiel in der Doku, kein realer Anwendungsfall. **`--publisher-id` geändert 2026-09-07 (S9):** jetzt der Wikidata-Eintrag `http://www.wikidata.org/entity/Q73901970` statt der GitHub-Org-URL `https://github.com/Research-Squirrel-Engineers` — Wikidata-IRI passt besser zu einem RDF/LOD-Kontext (N4O-KG) als eine GitHub-Org, real im ersten kompletten S0–S7-Rundlauf verwendet (Nachtrag 2026-09-07 (2) unter S7). Die GitHub-URL bleibt technisch gültig (`--publisher-id` ist Freitext, keine Validierung), ist aber nicht mehr die empfohlene README-Beispielangabe | 2026-09-07 (2), 2026-09-07 (S9) |
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
| Infrastrukturübersicht (Sketchfab/lokal → FDO) | Mermaid-Diagramm direkt in `README.md` eingebettet (rendert nativ auf GitHub), Quelle zusätzlich als `docs/infrastructure.mmd`; `docs/render_infrastructure_diagram.py` rendert daraus `docs/infrastructure.jpg` (mmdc → temp. PNG → Pillow-JPG-Konvertierung, `--no-sandbox` als Root) — Muster wortwörtlich aus `fdo-squirrel`s eigenem `fdo_finalize.py:render_mermaid_to_jpg` kopiert (A3). Kein Pipeline-Schritt (keine `STEPS`-Eintragung in `main.py`), reine Doku-Tooling, von Hand nach Änderungen an der `.mmd`-Quelle laufen lassen. `mmdc`/Pillow bewusst nicht in `requirements.txt` — für die eigentliche Pipeline nicht gebraucht | 2026-09-07 |
| Wo liegt der lokale Metadaten-Override (`mdcff`, S10)? | `data/local-metadata/<slug>/MD.cff` und/oder `CITATION.cff`, unabhängig voneinander, optional. Kein neuer `.gitignore`-Eintrag nötig — `data/*` deckt das schon ab (A5), genau wie `data/raw/` | 2026-09-08 (S10, bestätigt aus dem hochgeladenen S10-Vorschlagsdokument) |
| Ersetzt der Override die generierte Datei komplett, oder wird gemerged? | **Feld-Ebene-Merge, nicht Datei-Ersetzung.** `build_md_cff()`/`build_citation_cff()` laufen unverändert (inklusive Sketchfab-Anreicherung), danach überschreibt jeder in der lokalen Datei genannte Top-Level-Key den generierten Wert; ein nicht genannter Key bleibt unverändert. Bewusst **kein** Deep-Merge — ein überschriebenes `technique`/`heritage_object` ersetzt das ganze generierte Objekt, keine Sub-Feld-Fusion, passt zu den zwei Anwendungsfällen (Felder, die `mdcff` nie generiert, oder eine bewusste Komplettkorrektur eines falschen generierten Werts) | 2026-09-08 (S10, bestätigt) |
| Wird die gemergte Datei trotzdem validiert? | ja — MD.cff nach dem Merge unverändert gegen `MD.cff-schema.yaml` geprüft (real gegen `fdo-squirrel`s echten Validator gegengetestet, nicht nur die vendorte Kopie), ein Override der das Schema verletzt bricht genauso hart ab wie ein Generator-Fehler. CITATION.cff hat weiterhin kein Schema in diesem Repo (unverändert seit S5) — auch nach dem Merge keine Schema-Validierung dafür, nur der strukturelle Feld-Check (nächste Zeile) | 2026-09-08 (S10, bestätigt) |
| MD.cff/CITATION.cff unabhängig überschreibbar? | ja — nur `MD.cff` lokal vorhanden, `CITATION.cff` nicht (oder umgekehrt) ist ein gültiger Fall, jede Datei wird für sich gelesen/gemerged, real getestet | 2026-09-08 (S10, bestätigt) |
| Kollidiert ein lokaler Wert mit einem strukturellen Feld? | **Warnung, kein Fehler**, wenn der lokale Wert vom generierten abweicht — `--strict` macht daraus einen Abbruch, ein Override der zusätzlich das Schema verletzt bricht unabhängig von `--strict` sofort ab (Zeile oben). MD.cff: `md_cff_version`/`fdo_type`/`id`. **Ergänzt 2026-09-08 (S10, nicht im ursprünglichen Vorschlagsdokument):** dieselbe Prüfung jetzt auch für CITATION.cff, dort mit `cff-version` als einzigem strukturellen Feld — `type`/`authors`/... haben in diesem Repo kein Schema-Gate, also keine sinnvollen Kandidaten für diese Liste | 2026-09-08 (S10, bestätigt + ergänzt) |
| Neues CLI-Flag nötig? | nein — reine Auto-Erkennung über `data/local-metadata/<slug>/`, kein `--local-metadata`-Pfad-Flag, passt zum bestehenden `sketchfab_meta.json`-Muster (auch nur automatisch gelesen, wenn vorhanden) | 2026-09-08 (S10, bestätigt) |
| Kaputte/unlesbare lokale Override-Datei (`MD.cff`/`CITATION.cff` unter `data/local-metadata/`)? | **Neue Entscheidung, nicht im ursprünglichen Vorschlagsdokument:** harter Abbruch (`load_local_override()` wirft `ValueError` mit Dateiname, `run()` fängt das und meldet klar welche Datei betroffen ist), **nicht** wie `sketchfab_meta.json` still als „nicht vorhanden" behandelt. Begründung: `sketchfab_meta.json` ist maschinengeschrieben, „lesen fehlgeschlagen → als unangereichert weiterlaufen" ist dort ein vernünftiger Default; ein lokaler Override ist dagegen von Hand geschriebene, bewusst kuratierte Eingabe — ein still ignorierter Parse-Fehler würde ein Paket erzeugen, das aussieht als sei der Override angewendet worden, tatsächlich aber weiterhin die generischen Werte trägt. Das ist schlimmer als ein klarer Abbruch | 2026-09-08 (S10) |
| Erster echter Rundlauf gegen CIIC 81 + Freshford (kuratierter lokaler Override, --from fetch, Flos Maschine) | Beide Slugs erfolgreich, fdo-squirrel round-trip confirmed. Bestaetigt dabei: keine TODO: id not set-Platzhalter mehr, Creator/Datum kommen aus CITATION.cff, alle vier S8-Diagramme entstehen (resvg-py gezogen), und das classification_rules.yaml-Problem (.mtl/viewer/*/data/textures/* -> generische Rolle) ist jetzt zusaetzlich an echten Produktionsdaten belegt, nicht nur an der Fixture. CIIC 81s MD.cff-Override auf id (reservierte Zenodo-DOI 10.5281/zenodo.18724635) hat die eingebaute Wrong-Slug-Warnung ausgeloest -- von Flo bestaetigt: kein Bug, das Objekt war schon einmal publiziert. creators[].id fehlte bei beiden Slugs (kein --creator-profile) und hat den Lauf nicht blockiert -- die in S9 vermutete Crosswalk-Pflicht dafuer griff hier nicht, nicht weiter untersucht | 2026-09-09, Befund aus echtem Lauf |
| --publish-only-Aufraeum-Modus (S11) | Nach einem Lauf, der build_fdo enthaelt: dist/<slug>/, dist/<slug>.zip und alles in dist/<slug>_release/ ausser <slug>-fdo-bundle.zip loeschen -- dieses Bundle ist bereits vollstaendig selbstenthaltend (fdo_finalize.build_finished_bundle() faltet Originalpaket + alle generierten Dateien hinein, gegengeprueft an fdo-squirrels main.py), nichts geht verloren. Opt-in, Default bleibt unveraendert -- Flos Entscheidung: dist/<slug>/dist/<slug>.zip sind genau das, worauf der --from/--skip-Wiederaufnahme-Vertrag angewiesen ist, ein automatisches Loeschen nach jedem Lauf wuerde den kaputt machen. Kein eigener Schritt in STEPS (kein Pipeline-Schritt, reines Post-Processing nach run_selection_once), sondern ein Flag, das nach einer erfolgreichen Selection greift, die build_fdo enthaelt -- sonst No-op mit Hinweis auf stderr | 2026-09-09 (S11) |

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
| S7 | `dist/<slug>.zip` durch `fdo-squirrel` schicken, `fdo-metadata.ttl` als Beleg (Muster: registry S8) | fdo-3d-packager | S6 | erledigt 2026-09-07 |
| S8 | Batch-Fetch (`--sketchfab` wiederholbar) + Multi-Slug-Infrastruktur (`data/raw/<slug>/source_info.json`, `--slug`, `--all-slugs`) | fdo-3d-packager | S2–S5 | erledigt 2026-09-07 |
| S9 | `--all-slugs`-Fix für `build_fdo` ohne `data/raw/`; CI (`--strict`-Smoke-Test gegen Fakes für Blender/nxsbuild/nxscompress, echter Rundlauf durch `fdo-squirrel`) | fdo-3d-packager | S7, S8 | erledigt 2026-09-07 |
| S10 | `mdcff`-Erweiterung: lokale Metadaten-Overrides (`data/local-metadata/<slug>/MD.cff`/`CITATION.cff`, Feld-Ebene-Merge, für `heritage_object`/`spatial`/`temporal` u. a., die `mdcff` nie selbst herleitet) | fdo-3d-packager | S5 | erledigt 2026-09-08 |
| S11 | `--publish-only`-Flag: nach einem Lauf mit `build_fdo` alles außer `dist/<slug>_release/<slug>-fdo-bundle.zip` löschen | fdo-3d-packager | S9 | erledigt 2026-09-09 |

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

### Nachtrag 2026-09-07 (3) — Ursache gefunden: Firefox/Intel-UHD-Graphics/ANGLE-Bug, kein Repo-Bug — S6 vollständig real bestätigt

[#nachtrag-2026-09-07-3--ursache-gefunden-firefoxintel-uhd-graphicsangle-bug-kein-repo-bug--s6-vollständig-real-bestätigt](#nachtrag-2026-09-07-3--ursache-gefunden-firefoxintel-uhd-graphicsangle-bug-kein-repo-bug--s6-vollständig-real-bestätigt)

Nach dem Icon-Fix (Nachtrag (2)): keine 404 mehr, `model.nxz` lädt
vollständig (HTTP 200, 9,92 MB/9,92 MB, `Content-Length: 9915392` passt),
die Framebuffer-Warnung (`checkFramebufferStatus: Framebuffer not
complete, status: 0x8cd7`) blieb aber bestehen, Canvas weiterhin ohne
erkennbare Geometrie.

**Eingrenzung per Vergleichstest:** das offizielle, unveränderte
3DHOP-Minimal-Paket mit dessen eigenem Demo-Modell (`gargo.nxz`, nicht
Teil dieses Repos, siehe `assets/3dhop/NOTICE.md`) lokal per
`python -m http.server` geladen — **identisches Symptom**, dasselbe leere/
verkritzelte Canvas, in demselben Browser. Damit ausgeschlossen: unser
Vendoring, unser Modell (Govan 2), unser ZIP-Layout — der Fehler tritt
auch bei 3DHOPs eigenem, gänzlich unverändertem Paket auf.

`about:support` → Grafik zeigt: `WebGL-1-Treiber: Renderer` = „Google
Inc. (Intel) -- ANGLE (Intel, Intel(R) UHD Graphics (0x00008A56)
Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.100.9316)", `Compositing`:
„WebRender Layer Compositor" — hardwarebeschleunigt (keine Software-
Renderer-Zeile wie SwiftShader/llvmpipe, keine Blocklist-Einträge), läuft
über Firefoxs ANGLE-Schicht auf einer echten Intel-UHD-Graphics-GPU, per
Direct3D11 übersetzt.

**Bestätigt:** in Chrome (gleiche Maschine, gleiches `dist/govan-2.zip`,
gleicher `viewer/index.html`) wird das Modell korrekt angezeigt. **Damit
ist die Ursache identifiziert und liegt außerhalb dieses Repos:** ein
Firefox/ANGLE/Direct3D11-spezifischer WebGL-Bug auf dieser Intel-
UHD-Graphics-Kombination (bekannte Bug-Kategorie bei dieser Konstellation,
oft nach einem Grafiktreiber-Update ausgelöst — erklärt auch, warum es bei
Flo früher schon lief). Kein Code-Fix in diesem Repo möglich oder nötig;
betrifft 3DHOP/ANGLE/den Intel-Grafiktreiber, nicht `fdo-3d-packager`.

**S6 ist damit vollständig real bestätigt**, nicht mehr nur gegen
Fixtures im Sandkasten: kompletter Rundlauf `fetch`→`convert`→`nexus`→
`mdcff`→`bundle` gegen zwei echte Sketchfab-Modelle (Govan 2, Freshford
St Lachtain's Well), beide ZIPs korrekt aufgebaut, Viewer lädt das
gepackte Modell vollständig und rendert es sichtbar korrekt (Chrome,
Govan 2 mit Textur). Offen bleibt nur noch S7 (`build_fdo`, Rundlauf durch
`fdo-squirrel`).

---

## S7 — `build_fdo`

[#s7--build_fdo](#s7--build_fdo)

**Ziel:** `dist/<slug>.zip` (aus S6) wird durch eine echte `fdo-squirrel`-
Instanz geschickt statt RDF-Erzeugung selbst nachzubauen (A4, Muster:
`fdo-squirrel-registry` S8) -- `fdo-metadata.ttl` als Beleg, dass das Paket
wirklich brauchbar ist, nicht nur schema-valide.

**Uploads für diesen Schritt:** kein Repo-Bundle -- stattdessen der
GitHub-Link (`FDOx-squirrel/fdo-3d-packager`), im Chat frisch geklont.

**Substanz:**

- **Einbindungsmechanismus (Teil-D-Punkt aus S0/A4, jetzt entschieden):**
  Pip-Abhängigkeit (`requirements.txt`, gepinnt auf
  `fdo-squirrel@504b7af` -- exakt der Commit, den auch
  `fdo-squirrel-registry`s eigene `requirements.txt` für ihr S8 pinnt, und
  zufällig auch `fdo-squirrel@master`s aktueller Stand), aufgerufen als das
  von `pip` installierte Konsolenskript. `_fdo_squirrel_executable()` in
  `py/step_build_fdo.py` ist **wortwörtlich aus
  `fdo-squirrel-registry/py/step_release.py` kopiert** (A3: Wiederverwendung
  heißt Kopieren, nicht Referenzieren) -- weder `shutil.which()` (findet
  eine nicht aktivierte venv nicht) noch `sys.executable -m main`
  (Namenskollision: `fdo-squirrel`s Einstiegsmodul heißt `main`, genau wie
  dieses Repos eigener Orchestrator) funktionieren hier, aus denselben
  Gründen wie in der Registry. Anders als dort ist bei uns kein eigener
  Staging-Schritt nötig: `dist/<slug>.zip` liegt schon im von
  `fdo-squirrel` erwarteten Layout (S6 baut es genau dafür), geht also
  unverändert als `--package` rein.
- `py/step_build_fdo.py`: Vollständigkeits-Gate prüft nur `dist/<slug>.zip`
  (S6 muss gelaufen sein). **Slug-Auflösung bewusst nicht über
  `resolve_slug()`/`load_source_info()` (data/raw/-basiert, wie S3-S6),
  sondern über eine neue `resolve_bundle_slug()`/`discover_bundle_slugs()`
  in `fdo_3d_packager_utils.py`, die direkt `dist/*.zip` abfragt** -- Grund
  im Erledigt-Abschnitt unten (echter Bug am ersten Testlauf gefunden, nicht
  vorab entschieden). Ruft `fdo-squirrel --package dist/<slug>.zip
  --outdir dist/<slug>_release/` per `subprocess.run(..., check=True)` --
  unbuffered, Ausgabe läuft direkt durch, gleiches Muster wie die
  nxsbuild/nxscompress/Blender-Aufrufe in S3/S4, bewusst *nicht* das
  `capture_output=True`-Muster der Registry (deren eigener Stil, nicht
  dieses Repos). Ein fehlendes `fdo-squirrel` im Interpreter bricht den
  Schritt hart ab (`return False`), unabhängig von `--strict` -- gleiches
  Verhalten wie ein fehlendes Blender/nxsbuild in S3/S4, kein Sonderfall.
- **Output-Verzeichnis `dist/<slug>_release/`, gitignored** -- neue
  `.gitignore`-Regel `dist/*_release/`, gleiche Begründung wie
  `fdo-squirrel-registry`s eigenes `dist/release/`: ein rebuildbares
  Nebenprodukt aus einer bereits committeten Quelle (`dist/<slug>.zip`
  selbst), keine zweite zitierbare Fassung. Der Zenodo-Publish bleibt
  Handarbeit für einen Menschen mit Zugangsdaten (A3/A4, gleiche Begründung
  wie bei `fetch`).

**Abnahme:** `python main.py --only build_fdo` schlägt mit klarer Meldung
fehl, wenn `dist/<slug>.zip` fehlt (S6 nicht gelaufen) oder `fdo-squirrel`
nicht installiert ist. Mit vollständigen Eingaben: `dist/<slug>_release/`
enthält `fdo-metadata.ttl` und die übrigen von `fdo-squirrel` erzeugten
Dateien, Exit 0.

### Erledigt 2026-09-07

[#erledigt-2026-09-07-6](#erledigt-2026-09-07-6)

Gegen echte S6-Outputs verifiziert, nicht gegen Fixtures: die beiden real
gefetchten/konvertierten/gebauten `dist/<slug>.zip` aus S6 (`govan-2.zip`,
39 121 654 Byte; `freshford-st-lachtains-well-low-poly.zip`, 22 049 205
Byte), beide schon vor diesem Schritt im Repo committed. `fdo-squirrel`
in einer echten venv im Sandkasten aus dem gepinnten
`fdo-squirrel@504b7af` installiert (`pip install -r requirements.txt`
gegen einen frischen Klon, nicht die Arbeitskopie), Konsolenskript per
`sysconfig.get_path("scripts")` gefunden -- bestätigt für alle drei
Layout-Fälle relevant hier (POSIX-venv).

**Echter Bug am ersten echten Testlauf gefunden, nicht nur ein Fixture-
Unterschied:** `data/raw/govan-2/source_info.json` existiert in diesem
Repo **gar nicht** -- nur `dist/govan-2.zip` selbst ist committed (S6 hat
nie `dist/<slug>/` oder `data/raw/` mit committed, nur das fertige ZIP).
Die erste Fassung von `step_build_fdo.py` (Substanz oben, jetzt korrigiert)
rief `load_source_info()` einzig auf, um an `slug` zu kommen, und scheiterte
prompt mit `FileNotFoundError` gegen genau die beiden echten Fixtures, die
dieser Schritt beweisen soll. Fix: eigene `resolve_bundle_slug()`/
`discover_bundle_slugs()` in `fdo_3d_packager_utils.py`, die `dist/*.zip`
direkt abfragt statt über `data/raw/` zu gehen -- S7 hat keinen fachlichen
Grund, `data/raw/` vorauszusetzen, das Bundle ist selbsttragend. Nach dem
Fix: `python py/step_build_fdo.py --slug govan-2` und `python main.py
--only build_fdo --slug ...` (beide Slugs) laufen sauber durch, `--strict`
bleibt grün, ein nicht existierender Slug bricht klar ab (Exit 1), zwei
Bundles ohne `--slug` bricht mit Namensliste ab (wie `resolve_slug()`s
Verhalten bei S3-S6). Zweifacher Lauf gegen dasselbe ZIP geprüft: kein
Absturz bei bereits vorhandenem `dist/<slug>_release/` (Idempotenz-`rmtree`
greift).

**Zweiter echter Befund, nicht von uns verursacht:** `fdo-metadata.ttl`
ist zwischen zwei Läufen gegen dasselbe unveränderte `dist/govan-2.zip`
**nicht** byte-identisch -- eingegrenzt per Diff auf genau zwei der vier
generierten Zusatz-Distributionen, `rdf_modelling_report.json` und
`rdf_modelling_report.html`. Ursache: `fdo-squirrel`s eigener
`generated_at`-Zeitstempel (`datetime.utcnow()`, in `main.py` bereits als
`DeprecationWarning` sichtbar) landet im Report, ändert dessen SHA-256 und
damit die davon abgeleitete `urn:fdo-squirrel:dist/<hash>`-IRI dieser
beiden Distributionen bei jedem Lauf neu. `fdo-metadata.ttl` selbst und
`fdo_overview.mermaid` (die anderen beiden generierten Distributionen)
blieben in beiden Läufen identisch. Betrifft `fdo-squirrel`s eigenen
Determinismus, nicht diesen Schritt hier (A3s "kein `datetime.now()`"-Regel
gilt für unsere eigenen Generatoren, `step_build_fdo.py` selbst ruft nirgends
die Uhr auf) -- notiert als Befund für einen künftigen `fdo-squirrel`-Chat,
kein Fix hier.

**Echter Befund (beantwortet den Teil-D-Punkt aus S6 abschließend, statt
ihn nur zu bestätigen):** `fdo/classification_rules.yaml` bricht bei
unklassifizierten Dateien **nicht** ab und ignoriert sie auch nicht --
jede unbekannte Distribution bekommt stillschweigend die Fallback-Rolle
`"data"`. Konkret an Govan 2 geprüft (`fdo:role` pro `fdo:path` aus dem
geschriebenen `fdo-metadata.ttl`):

| Pfad | erwartete Rolle | tatsächliche Rolle |
|---|---|---|
| `data/model/model.mtl` | `model` | `data` (keine `.mtl`-Regel) |
| `data/textures/defaultMat_baseColor.jpeg` | `auxiliary` | `documentation` (Regel matcht nur ein Top-Level-`textures/`-Präfix, nicht `data/textures/`) |
| `viewer/index.html`, `viewer/js/*.js`, `viewer/stylesheet/3dhop.css`, `viewer/LICENSE.txt` | (neue Rolle, z. B. `auxiliary`) | `data` (keine Regel) |
| `viewer/skins/**/*.png`, `viewer/skins/backgrounds/light.jpg` | -- | `documentation` (trifft zufällig die Bild-Extension-Regel) |

Kein Pipeline-Fehler in keinem der beiden Fälle -- `fdo-metadata.ttl` ist in
beiden Läufen vollständig und valide, nur mit falscher/generischer Rolle
für diese Distributionen. Der A4-Beschluss aus S6 ("dort nachbessern, nicht
hier umgehen") gilt damit unverändert, ist aber jetzt an echten Daten
belegt statt nur vermutet -- der eigentliche Fix (drei neue/erweiterte
Regeln in `fdo-squirrel/fdo/classification_rules.yaml`) ist ein separater
Patch in einem `fdo-squirrel`-Chat (A5: ein Repo pro Chat), nicht Teil
dieses Schritts.

**Nicht geprüft:** `pyshacl`/SHACL-Validierung von `fdo-metadata.ttl` selbst
(kein SHACL-Gate in `fdo-squirrel`, das ist `fdo-squirrel-registry`s Job,
S5) und der tatsächliche Zenodo-Upload (bewusst außerhalb dieses Schritts,
siehe Substanz oben). Ebenfalls offen (neuer Teil-D-Punkt): `python main.py
--only build_fdo --all-slugs` scheitert in einem Checkout ohne `data/raw/`
(wie diesem hier) an `main.py`s eigener `discover_slugs()`, bevor
`build_fdo` überhaupt läuft -- `--slug` explizit umgeht das, siehe Teil D.

### Nachtrag 2026-09-07 (2) — erster echter Produktions-Rundlauf bei Flo, gesamte Kette S0–S7 bestätigt

[#nachtrag-2026-09-07-2--erster-echter-produktions-rundlauf-bei-flo-gesamte-kette-s0s7-bestätigt](#nachtrag-2026-09-07-2--erster-echter-produktions-rundlauf-bei-flo-gesamte-kette-s0s7-bestätigt)

Erster echter Lauf der kompletten Kette in einem Aufruf, auf Flos
Windows-Maschine, committed:

```cmd
python main.py --from fetch --sketchfab "https://sketchfab.com/3d-models/govan-2-b9dc56bfc1d342f6b4da3281e6629c07" --sketchfab "https://sketchfab.com/3d-models/freshford-st-lachtains-well-low-poly-ae1e1f4daa7d433dbbf076407134e81e" --nxsbuild-bin "C:\Nexus_43\nxsbuild.exe" --nxscompress-bin "C:\Nexus_43\nxscompress.exe" --publisher-label "Research Squirrel Engineers Network" --publisher-id "https://github.com/Research-Squirrel-Engineers"
```

`fetch`→`convert`→`nexus`→`mdcff`→`bundle`→`build_fdo` liefen für **beide**
Slugs fehlerfrei durch -- erstmals inklusive `build_fdo` in einem einzigen
`--from fetch`-Aufruf, nicht mehr einzeln nachgestellt:

| Slug | convert | nexus | mdcff | bundle | build_fdo | Gesamt |
|---|---|---|---|---|---|---|
| govan-2 | 50,00s | 24,12s | 0,47s | 6,27s | 16,41s | ~97s |
| freshford-st-lachtains-well-low-poly | 60,12s | 6,72s | 0,11s | 2,38s | 6,34s | ~76s |

`build_fdo`s eigener Anteil (16,41s bei Govan 2, deutlich mehr als
`nexus`/`mdcff`/`bundle` zusammen) erklärt sich aus dem nächsten Punkt.

**Präzisierung des "vier vs. fünf generierte Distributionen"-Befunds aus
dem vorherigen Abschnitt:** bei Flo zeigt das Log `RDF updated with 5
generated-file distribution(s)`, nicht vier wie im Sandkasten, und zusätzlich
`✔ Mermaid diagram rendered as high-res JPG: ...fdo_overview.jpg` -- eine
Zeile, die im Sandkasten als `⚠ Mermaid image render skipped: mmdc failed`
auftauchte (kein Chrome/Puppeteer dort verfügbar). Gegen das von Flo
hochgeladene `govan-2-fdo-bundle.zip` bestätigt: **37** `dcat:Distribution`-
Einträge (32 Bundle-Inhalt + 5 generiert: `fdo-metadata.ttl`,
`rdf_modelling_report.json`, `rdf_modelling_report.html`,
`fdo_overview.mermaid`, **zusätzlich** `fdo_overview.jpg`), gegenüber 36
(4 generiert) im Sandkasten-Lauf. Die Menge der generierten Distributionen
ist damit selbst umgebungsabhängig (ob `mmdc`/Chrome verfügbar ist), nicht
nur ihre Hashes/IRIs wie im vorherigen Nachtrag beschrieben -- verschärft
den dortigen Befund, ändert aber nichts an der Einordnung: weiterhin
`fdo-squirrel`s eigener Determinismus, nicht dieser Schritt.

**Klassifikations-Befund (siehe oben) an der echten Produktions-Bundle
reproduziert, nicht nur an der Sandkasten-Fixture:** identische vier
Lücken (`.mtl` → `data`, `data/textures/*` → `documentation` statt
`auxiliary`, `viewer/*.html`/`.js`/`.css`/`LICENSE.txt` → `data`,
`viewer/skins/**` → `documentation` über die Bild-Extension-Regel) --
zusätzlich jetzt auch `fdo_overview.jpg`/`rdf_modelling_report.json`
selbst mit `documentation` beziehungsweise `rdf_modelling_report.html`/
`fdo_overview.mermaid`/`fdo-metadata.ttl` mit `data` klassifiziert (gleiche
Fallback-Logik, trifft auch die von `fdo-squirrel` selbst neu erzeugten
Dateien). Bestätigt: der S6/S7-Befund ist kein Sandkasten-Artefakt, gilt
identisch am echten Bundle. `viewer/skins/dark/lightcontrol.png`/
`lightcontrol_on.png` tragen im echten Bundle die korrekten Namen (S6s
Icon-Fix, Nachtrag 2026-09-07 (2), bestätigt vorhanden).

**Damit ist die gesamte S0–S7-Kette erstmals in einem einzigen Aufruf,
gegen zwei echte Sketchfab-Modelle, End-to-End real bestätigt** -- vorher
immer einzeln oder in Teilstrecken verifiziert (S2-S5 in Nachtrag (7) von
S8, S6 separat in S6s eigenen Nachträgen, S7 gegen bereits committete
Bundles statt gegen einen frischen `fetch`). Kein Fehler, keine Warnung in
keinem der beiden Läufe.

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

## S9 — `--all-slugs`-Fix + CI

[#s9--all-slugs-fix--ci](#s9--all-slugs-fix--ci)

**Ziel:** zwei der in S7 offen gebliebenen Punkte schließen: `--all-slugs`
verlangt auch dann `data/raw/`, wenn nur `build_fdo` gewählt ist (Teil D);
und es gibt noch keine CI (`.github/workflows/`), anders als
`fdo-squirrel-registry`. Zenodo-Nachbereitung bleibt bewusst draußen
(Chat-Entscheidung 2026-09-07) — der nächste Schritt danach ist
`fdo-squirrel-md-generator`, wo `MD.cff` interaktiv geladen/bearbeitet
werden soll, bevor überhaupt etwas Richtung Zenodo geht.

**Uploads für diesen Schritt:** kein Repo-Bundle -- GitHub-Link, frisch
geklont (der committete Stand enthielt bereits Flos `fix bugs`-Commit, der
`dist/govan-2.zip`/`dist/freshford-...zip` aus git entfernt und
`data/*`/`PATCH-README.md`/`cache*` neu ignoriert hat -- nicht Teil dieses
Schritts, aber relevant für dessen Substanz, siehe unten).

**Substanz:**

- **`--all-slugs`-Fix:** neue `_discover_slugs_for(selection)` in
  `main.py`, an beiden Stellen verwendet, die vorher hart `discover_slugs()`
  (data/raw/-basiert) aufriefen (`--dry-run`-Zweig und der echte Lauf).
  Regel: `selection == ["build_fdo"]` (die einzige Kombination, die
  `--only build_fdo` oder `--from build_fdo` je erzeugen -- `build_fdo`
  steht als letztes in `STEPS`, `--skip` nimmt nur einen einzelnen Schritt)
  → `discover_bundle_slugs()` (dist/*.zip-basiert, S7); jede andere
  Auswahl → weiterhin `discover_slugs()`, weil `bundle`/`convert`/`nexus`/
  `mdcff` alle über `load_source_info()` gehen und `data/raw/` brauchen.
  Keine allgemeinere Neukonstruktion des Auswahl-Modells (das wäre größer
  als dieser Punkt) -- gezielter Fix für genau die eine bekannte Lücke.
- **CI (`.github/workflows/build.yml`), Muster `fdo-squirrel-registry`s
  `build.yml` (A3: kopiert, nicht neu erfunden), aber angepasst:** die
  Registry ist reines Python, ihr Default-Lauf braucht nichts, was in
  GitHub-hosted Runnern fehlt. Dieses Repo braucht Blender und
  `nxsbuild`/`nxscompress` für `convert`/`nexus` -- beides weder
  pip-installierbar noch ohne Weiteres in CI verfügbar (`nxsbuild` bräuchte
  einen Build aus Quellcode gegen Qt/vcglib). Deshalb:
  - **`fetch` bleibt ungetestet** (network=True, bräuchte einen Sketchfab-
    Token) -- wie bei der Registry automatisch ausgeschlossen, kein Flag
    nötig.
  - **`data/raw/ci-smoke/` wird synthetisch erzeugt**
    (`.github/ci-fixtures/seed_fixture.py`), nicht committed (`data/*` ist
    seit Flos `fix bugs`-Commit ohnehin ignoriert) -- exakt der
    `source_info.json`-Vertrag, den ein echter `fetch`-Lauf auch schreiben
    würde, von Hand befüllt statt über Sketchfab geholt.
  - **Fakes für Blender/`nxsbuild`/`nxscompress`**
    (`.github/ci-fixtures/fake_blender.py`/`fake_nxsbuild.py`/
    `fake_nxscompress.py`, neu **committed**, anders als die früheren
    Sandkasten-Fakes aus S3/S4, die "nicht Teil des Patches" waren) --
    prüfen nicht die reale 3D-Qualität (nicht dieses Repos Aufgabe, A3),
    sondern nur, dass `convert`/`nexus` die Binaries korrekt aufrufen, ihre
    Outputs an den erwarteten Pfaden finden und weiterreichen. Gleiches
    "Existenz-Marker"-Prinzip, das eine frühere Sandkasten-Verifikation
    schon ad hoc genutzt hatte (S5), jetzt aber dauerhaft im Repo statt
    einmalig im Chat.
  - **`build_fdo` (S7) läuft in CI echt**, nicht gefaked -- `fdo-squirrel`
    ist eine echte Pip-Abhängigkeit, der Rundlauf ist damit ein echter
    Determinismus-/Schema-Test, kein weiterer Fake.
  - `fake_blender.py` schreibt bewusst ein `model.mtl`, das
    `texture.jpg` referenziert (von `seed_fixture.py` mitgeliefert), nicht
    nur ein texturloses Modell -- damit läuft `_copy_textures_from_raw()`
    (S3) auch in CI mit, nicht nur der unbe-texturierte Zweig.
- **Echter Fund beim ersten CI-Testlauf, nicht vorab bekannt:** die erste
  Fassung der Fixture ließ `creator_profile` leer (ein legitimer Fall --
  z. B. ein echter `--local`-Fetch ohne `--creator-profile`). `build_fdo`
  brach daraufhin an `fdo-squirrel` ab: `creators[0] must contain keys
  'id' and 'label'`. Unser eigenes (und `fdo-squirrel`s eigenes!)
  `MD.cff-schema.yaml` nennt `id` für `creators` aber ausdrücklich optional
  (`idLabelEntityOptionalId`, siehe `_entity()` in `step_mdcff.py`) --
  `fdo-squirrel`s Crosswalk (`require_id_label()`) verlangt es trotzdem
  hart, im Widerspruch zum eigenen Schema. Betrifft nicht nur die
  CI-Fixture: **jeder echte `--local`-Fetch ohne `--creator-profile` würde
  denselben Absturz in `build_fdo` produzieren.** Kein Fix hier (A4:
  gehört nach `fdo-squirrel`, separater Chat) -- die Fixture bekam
  stattdessen einen echten `creator_profile`-Wert, damit CI die eigene
  Verdrahtung testet statt an einem fremden Bug hängenzubleiben; der Bug
  selbst bleibt dokumentiert, nicht verschwiegen.
- **`README.md` nachgezogen:** fehlender `build_fdo`-Nutzungsabschnitt
  ergänzt (war seit dem S7-Patch schlicht vergessen -- `bundle` hatte
  einen, `build_fdo` keinen), `--publisher-id`-Beispiele auf den
  Wikidata-Eintrag umgestellt (siehe A4), echtes `--from fetch`-Beispiel
  (Flos tatsächlicher Befehl, S7-Nachtrag) neben dem generischen ergänzt.

**Abnahme:** `python main.py --only build_fdo --all-slugs` gegen ein
Checkout ohne `data/raw/`, aber mit `dist/*.zip`, findet die Slugs und
läuft; jede andere Schrittauswahl verlangt weiterhin `data/raw/` wie
zuvor. `.github/workflows/build.yml` läuft grün gegen einen frischen Push/
PR (`--strict`, kein manuelles Zutun).

### Erledigt 2026-09-07

[#erledigt-2026-09-07-9](#erledigt-2026-09-07-9)

`--all-slugs`-Fix gegen echte Szenarien geprüft (frischer venv-Klon): leere
`dist/`+`data/raw/` → `build_fdo --all-slugs` meldet klar "no
dist/<slug>.zip found"; zwei Dummy-ZIPs in `dist/` ohne `data/raw/` →
`--only build_fdo --all-slugs --dry-run` und `--from build_fdo --all-slugs
--dry-run` finden beide Slugs korrekt; jede andere Schrittauswahl
(`--only bundle --all-slugs` u. Ä.) verlangt weiterhin `data/raw/` wie vor
dem Fix -- keine Regression. `--all-slugs`+`--slug` zusammen weiterhin ein
Fehler, `--list`/Default-`--dry-run` unverändert.

CI-Workflow lokal simuliert (nicht nur gelesen): frischer venv,
`pip install -r requirements.txt` (zieht `fdo-squirrel@504b7af` echt),
`seed_fixture.py`, dann `main.py --strict --slug ci-smoke` mit den drei
Fakes -- **komplette Kette `convert`→`nexus`→`mdcff`→`bundle`→`build_fdo`
läuft grün durch, `fdo-metadata.ttl` real erzeugt** (17 249 Byte, 36
`dcat:Distribution`-Einträge, `fdo-squirrel`-Rundlauf also echt, nicht
gefaked). Zweiter Lauf gegen dieselbe Fixture: weiterhin grün, keine
Regression, gleiche 36 Distributionen. `test -s dist/ci-smoke_release/
fdo-metadata.ttl` (der letzte Workflow-Schritt) bestätigt non-empty.

**Damit ist der Zusammenhang mit Flos `fix bugs`-Commit geklärt, nicht nur
zur Kenntnis genommen:** dass `dist/govan-2.zip`/`dist/freshford-...zip`
nicht mehr committed sind, betrifft diese CI **nicht** -- sie hängt an
keiner committeten Fixture mehr, sondern erzeugt ihre eigene synthetisch,
bei jedem Lauf neu. Ob die beiden großen ZIPs künftig wieder committed
werden (z. B. für S7-artige manuelle Verifikationen wie in dessen eigenem
Erledigt-Abschnitt) oder bewusst draußen bleiben, ist weiterhin offen --
für CI ist es aber irrelevant geworden.

### Nachtrag 2026-09-07 (2) — `chmod` auf Windows real gescheitert, `.cmd`-Wrapper ergänzt

[#nachtrag-2026-09-07-2--chmod-auf-windows-real-gescheitert-cmd-wrapper-ergänzt](#nachtrag-2026-09-07-2--chmod-auf-windows-real-gescheitert-cmd-wrapper-ergänzt)

Echter Befund bei Flo, nicht im Sandkasten aufgefallen (der läuft POSIX):
die `PATCH-README.md`-Anleitung für lokales Testen vor dem Push riet zu
`chmod +x .github/ci-fixtures/fake_*.py` -- auf `cmd.exe` (Referenzplattform,
A3) gibt es `chmod` schlicht nicht. Grundsätzlicher als nur der fehlende
Befehl: selbst mit einem Exec-Bit-Äquivalent würde `subprocess.run([...],
check=True)` (ohne `shell=True`, wie `step_convert.py`/`step_nexus.py` es
schon immer aufrufen) eine reine `.py`-Datei unter Windows gar nicht
direkt starten können -- `CreateProcess` konsultiert keine
Datei-Assoziationen, anders als ein Doppelklick im Explorer.

**Fix:** drei neue `.cmd`-Wrapper unter `.github/ci-fixtures/`
(`fake_blender.cmd`/`fake_nxsbuild.cmd`/`fake_nxscompress.cmd`), je drei
Zeilen (`@echo off` + Kommentar + `python "%~dp0fake_blender.py" %*`) --
`.cmd`/`.bat` sind der eine Windows-Dateityp, den `CreateProcess` auch ohne
`shell=True` direkt über `cmd.exe` startet, `%~dp0` findet die
gleichnamige `.py` unabhängig vom Arbeitsverzeichnis, `%*` reicht alle
Argumente unverändert durch (inklusive des führenden `-b --python <script>
--`, das `fake_blender.py`s eigenes `parse_args()` ohnehin ignoriert).
**Nur für lokales Testen auf Windows relevant** -- die eigentliche CI
(GitHub-hosted `ubuntu-latest`) bleibt unverändert bei den `.py`-Dateien
und ihrem eigenen `chmod +x`-Schritt in `build.yml`, der dort korrekt
funktioniert (POSIX-Runner). `PATCH-README.md` entsprechend korrigiert:
kein `chmod` mehr in den Windows-Anleitungen, stattdessen die
`.cmd`-Wrapper, jeder Befehl als Einzeiler.

**Erster echter Actions-Lauf bei Flo: grün.** Damit ist auch der letzte in
der S9-`PATCH-README.md` offen gelassene Punkt ("der echte Actions-Lauf
selbst wurde hier nicht geprüft, keine Möglichkeit, Actions aus diesem
Sandkasten anzustoßen") geschlossen -- die lokale Simulation in diesem
Chat (venv, `pip install`, Fakes, `--strict`) und der echte
`ubuntu-latest`-Runner kommen zum selben Ergebnis. S9 ist damit
vollständig real bestätigt, nicht nur simuliert.

---

## S10 — Lokale Metadaten-Overrides

[#s10--lokale-metadaten-overrides](#s10--lokale-metadaten-overrides)

**Ziel:** `data/local-metadata/<slug>/MD.cff`/`CITATION.cff`, falls
vorhanden, werden auf Feld-Ebene über die von `mdcff` (S5) generierten
Dateien gelegt, bevor das Ergebnis validiert und geschrieben wird --
schließt die Lücke, dass `heritage_object`/`spatial`/`temporal` (u. a.)
nie generiert werden, obwohl das Schema sie vorsieht (Befund im
hochgeladenen S10-Vorschlagsdokument, gegen `build_md_cff()` bestätigt).

**Substanz:**

- `py/fdo_3d_packager_utils.py`: neue Konstante `LOCAL_METADATA` (`data/
  local-metadata/`), analog `DATA_RAW`/`DIST`. Kein neuer
  `.gitignore`-Eintrag -- `data/*` deckt das Verzeichnis schon ab (A5).
- `py/step_mdcff.py`: `load_local_override(slug, filename) -> dict | None`
  liest `data/local-metadata/<slug>/<filename>`, `None` falls nicht
  vorhanden. Anders als `load_sketchfab_meta()` wird eine vorhandene, aber
  kaputte Datei **nicht** still wie "nicht vorhanden" behandelt, sondern
  wirft `ValueError` -- `run()` fängt das und meldet klar, welche Datei
  betroffen ist (harter Abbruch, neue Entscheidung, siehe A4).
  `merge_local_override(generated, local, structural_keys)` überschreibt
  jeden vom Override genannten Top-Level-Key, lässt alle anderen
  unangetastet, und liefert zusätzlich `overridden_keys` (für die
  Erfolgsmeldung) sowie `structural_collisions` (für die
  Warnung/`--strict`-Logik) zurück. Kein Deep-Merge (A4).
- `run()`: liest beide Override-Dateien vor dem Bauen von `MD.cff`/
  `CITATION.cff`; merged nach `build_md_cff()`/`build_citation_cff()`;
  validiert das gemergte `MD.cff` (nicht nur das generierte) gegen
  `MD.cff-schema.yaml`. `MD_CFF_STRUCTURAL_KEYS`
  (`md_cff_version`/`fdo_type`/`id`) und `CITATION_CFF_STRUCTURAL_KEYS`
  (`cff-version`, neu gegenüber dem Vorschlagsdokument, A4) lösen bei
  Kollision eine `Warning:`-Zeile aus (bestehendes `warn_reasons`-Muster
  aus `step_fetch.py`, jetzt auch hier verwendet statt des alten
  Einzel-`if`).
- Kein neues CLI-Flag, keine Änderung an `main.py`s Argument-Parser.

**Abnahme:**

1. Ohne jede lokale Override-Datei: `python main.py --only mdcff --slug
   <slug> --publisher-label ... --publisher-id ...` verhält sich exakt wie
   vor S10 (keine Regression).
2. Fake-`data/local-metadata/govan-2/MD.cff` mit `heritage_object`/
   `spatial`/`temporal` gefüllt: derselbe Lauf liefert ein `MD.cff`, das
   diese drei Felder enthält (vorher nie der Fall) *und* weiterhin die
   Sketchfab-Anreicherung für `keywords`/`technique` zeigt -- beides
   gleichzeitig im selben Lauf.
3. Ein zweiter Fake-Override mit abweichendem `fdo_type` löst die
   Warnung aus (exit 0), unter `--strict` bricht derselbe Lauf ab (exit
   1). Ein Override, der `fdo_type` auf einen Nicht-Enum-Wert setzt,
   bricht unabhängig von `--strict` immer ab (Schema-Validierung).
4. `CITATION.cff`-Override ohne `MD.cff`-Override (und umgekehrt) läuft
   für sich allein.
5. Kaputtes YAML in einer Override-Datei bricht den Lauf hart ab, mit
   Dateiname in der Fehlermeldung.
6. Zwei Läufe hintereinander gegen denselben Fake-Zustand: `MD.cff`/
   `CITATION.cff` bytegleich (`md5sum`).
7. Das gemergte `MD.cff` validiert nicht nur gegen die vendorte
   Schema-Kopie, sondern auch gegen `fdo-squirrel`s echten
   `ingest.metadata_ingest.validate_against_schema()` (Repo dafür
   zusätzlich geklont).

### Erledigt 2026-09-08

[#erledigt-2026-09-08](#erledigt-2026-09-08)

Implementiert und gegen ein Fake-`data/raw/govan-2/` (`source_info.json` +
`sketchfab_meta.json`, Muster wie in S5, plus leere `dist/govan-2/
model.obj`/`model.nxs`/`model.nxz` als Vollständigkeits-Marker) laufen
lassen -- alle sieben Abnahme-Punkte oben bestätigt, keiner davon nur
behauptet:

- Ohne Override: identische Ausgabe/Meldung wie vor S10, keine Regression.
- Mit `heritage_object`/`spatial`/`temporal`-Override: alle drei Felder im
  geschriebenen `MD.cff`, `keywords` weiterhin mit den Sketchfab-Tags
  (`hogback`, `govan`, `Cultural Heritage & History`) angereichert,
  `technique.processing` weiterhin mit der Mesh-Stats-Notiz -- beides im
  selben Lauf, nicht nur getrennt getestet.
- **Real gegen `fdo-squirrel`s echten Validator geprüft**, nicht nur die
  vendorte Schema-Kopie: `fdo-squirrel` zusätzlich geklont,
  `ingest.metadata_ingest.validate_against_schema()` direkt gegen das
  gemergte `MD.cff` aufgerufen -- **valide**.
- Struktureller Kollisionsfall (`fdo_type: fdo:SoftwareFDO` im Override
  bei generiertem `fdo:3DDataFDO`): `Warning: ...overrides structural
  field(s) fdo_type...` in der Meldung, exit 0 ohne `--strict`, exit 1
  mit `--strict` ("--strict: warnings present, failing.").
- Schema-brechender Override (`fdo_type: not-a-real-type`): bricht sofort
  ab, unabhängig von `--strict` -- `$.fdo_type: 'not-a-real-type' is not
  one of [...]`.
- Nur `CITATION.cff`-Override (`license`, `keywords`), kein
  `MD.cff`-Override: läuft für sich, `MD.cff` bleibt unverändert generiert,
  `CITATION.cff` trägt die überschriebenen Felder -- Unabhängigkeit
  bestätigt.
- Kaputtes YAML in `CITATION.cff`-Override: bricht sofort ab, Meldung
  nennt den vollen Pfad der betroffenen Datei.
- Determinismus: zwei Läufe hintereinander gegen denselben Fake-Zustand
  (mit Override), `md5sum` von `MD.cff`/`CITATION.cff` identisch.
- **Regressionstest gegen die bestehende CI-Fixture:** kompletter
  `convert → nexus → mdcff → bundle → build_fdo`-Rundlauf gegen
  `.github/ci-fixtures/seed_fixture.py`s `ci-smoke`-Slug mit `--strict`,
  ohne jede lokale Override-Datei -- weiterhin grün, `fdo-metadata.ttl`
  wird geschrieben, keine Regression durch den S10-Code selbst.

**Nicht geprüft:** ein echter Produktionslauf mit den tatsächlichen
CIIC-81-Werten (Wikidata-Objekttyp/Material, OSM-Spatial-ID,
ChronOntology-Periode aus den alten Folien) -- das braucht Blender/
Sketchfab-Zugriff, im Sandkasten weiterhin nicht verfügbar, bleibt laut
dem hochgeladenen Vorschlagsdokument bewusst ein eigener Schritt danach
(siehe Teil D).

### Nachtrag 2026-09-08 (2) — Slug im Voraus kennen (vor `fetch`)

[#nachtrag-2026-09-08-2--slug-im-voraus-kennen-vor-fetch](#nachtrag-2026-09-08-2--slug-im-voraus-kennen-vor-fetch)

Berechtigter Einwand im Chat: um `data/local-metadata/<slug>/` anzulegen,
muss der Slug bekannt sein -- aber `mdcff` (und damit die Kenntnis, wie
der Slug lautet) läuft normalerweise erst *nach* `fetch`. Klingt nach
einem Henne-Ei-Problem, ist aber keins: `guess_slug()`/`extract_uid()`
(`step_fetch.py`) sind reines Regex-Parsing der Eingabe, kein API-Call --
der Slug ist schon vor jedem Netzwerkzugriff aus der Eingabe selbst
ableitbar:

- **`--sketchfab URL`**: Slug = der Teil der URL zwischen `/3d-models/`
  und der abschließenden 32-stelligen Hex-UID (gegen ein echtes README-
  Beispiel bestätigt: `.../3d-models/donaghmore-church-ruin-a602439f...`
  -> `donaghmore-church-ruin`).
- **`--local PATH`**: Slug = `model_in.stem`, der Dateiname ohne Endung
  -- kennt man ohnehin, bevor man überhaupt fetcht.

Das reicht für den Normalfall (`--only fetch`, dann `--only mdcff` als
getrennte Aufrufe -- dazwischen liegt `data/raw/<slug>/` sowieso schon
auf der Platte, der Slug ist ablesbar, kein Vorausberechnen nötig).
Relevant wird es erst für den kombinierten `--from fetch ...`-Aufruf
(S8/Nachtrag 2026-09-07 (6)): dort läuft `mdcff` automatisch direkt nach
`fetch` im selben `main.py`-Aufruf, ohne Gelegenheit, den Override-Ordner
dazwischen anzulegen -- der muss also *vor* dem Aufruf existieren, mit
dem von Hand aus der URL abgeleiteten Slug als Ordnernamen.

Kein Code geändert (reine Doku-Ergänzung) -- README.md (`mdcff`-Abschnitt,
direkt nach dem S10-Override-Absatz) und dieser Nachtrag sind die
komplette Ergänzung.

---

## S11 — `--publish-only`-Aufräum-Modus

[#s11---publish-only-aufräum-modus](#s11---publish-only-aufräum-modus)

**Ziel:** nach einem Lauf, der `build_fdo` einschließt, auf Wunsch alles
außer der einen tatsächlich zu verschickenden Datei löschen --
`dist/<slug>_release/<slug>-fdo-bundle.zip` -- statt `dist/<slug>/`,
`dist/<slug>.zip` und den Rest von `dist/<slug>_release/` (Diagramme,
TTL-Snippets, HTML-/JSON-Reports) auf der Platte liegen zu lassen. Flos
Anstoß nach dem ersten echten CIIC-81/Freshford-Lauf (A4): für einen
"fertig, raus damit"-Lauf ist das der Normalfall, nicht das Aufheben aller
Zwischenstände.

**Substanz:**

- `py/fdo_3d_packager_utils.py`: neue Funktion `publish_only_cleanup(slug)`
  -- löscht `dist/<slug>/` (rekursiv) und `dist/<slug>.zip`, und leert
  `dist/<slug>_release/` bis auf die Datei, die auf `*-fdo-bundle.zip`
  endet. Gibt die Liste der entfernten Pfade zurück (relativ zum
  Repo-Root, sortiert), fürs Logging. Sicher, weil das Bundle bereits
  alles enthält -- gegengeprüft an `fdo-squirrel`s `main.py`:
  `generated_files` dort ist exakt dieselbe Liste, die `fdo-3d-packager`
  nach `<slug>_release/` schreibt, plus `fdo-metadata.ttl` und
  `rdf_modelling_report.json`, alle über `fdo_finalize.
  build_finished_bundle()` ins Bundle-ZIP gefaltet.
- `main.py`: neues `--publish-only`-Flag (kein neuer STEPS-Eintrag --
  reines Post-Processing, kein Pipeline-Schritt). Hook am Ende von
  `run_selection_once()`, nach erfolgreichem Durchlauf: wenn `build_fdo`
  Teil der gerade gelaufenen `selection` war, `resolve_bundle_slug()`
  **vor** dem Aufräumen aufrufen (liest `dist/<slug>.zip`, das
  `publish_only_cleanup()` gleich löscht), dann aufräumen und melden, was
  weg ist. War `build_fdo` nicht Teil der Selection, No-op mit Hinweis auf
  stderr statt stillem Nichtstun (Muster: `--slug`/`--all-slugs` bei
  `fetch`-Läufen).
- `--all-slugs` + `--publish-only`: funktioniert unverändert, weil der
  Hook pro Slug in `run_selection_once()` sitzt, das `run_over_slugs()`
  ohnehin einmal pro Slug aufruft -- kein Sonderfall nötig.
- `.github/workflows/build.yml`: zwei neue Schritte nach dem bestehenden
  `--strict`-Smoke-Test -- `--only build_fdo --slug ci-smoke
  --publish-only` (regeneriert `_release/` frisch und räumt danach auf),
  dann harte Checks (`test ! -e dist/ci-smoke`, `test ! -e
  dist/ci-smoke.zip`, `test -s .../ci-smoke-fdo-bundle.zip`, genau eine
  Datei in `_release/`).

**Abnahme:**

1. Voller Lauf (`convert`..`build_fdo`) mit `--publish-only` gegen die
   CI-Fixture: `dist/<slug>/` und `dist/<slug>.zip` weg,
   `dist/<slug>_release/` enthält nur noch `<slug>-fdo-bundle.zip`.
2. Derselbe Lauf **ohne** `--publish-only`: keine Regression, alle drei
   (`dist/<slug>/`, `dist/<slug>.zip`, `dist/<slug>_release/` komplett)
   bleiben stehen wie vor S11.
3. `--only build_fdo --publish-only` (Bundle-ZIP existiert schon aus
   einem früheren Lauf, kein `convert`/`nexus` in dieser Invocation):
   räumt trotzdem korrekt auf.
4. `--publish-only` ohne `build_fdo` in der Selection (z. B. `--only
   convert --publish-only`): No-op, Hinweis auf stderr, nichts gelöscht.
5. Bundle-ZIP enthält nach dem Aufräumen tatsächlich alles, was gelöscht
   wurde (`unzip -l`) -- kein Datenverlust, nur Redundanz entfernt.

### Erledigt 2026-09-09

[#erledigt-2026-09-09](#erledigt-2026-09-09)

Implementiert und gegen die vorhandene CI-Fixture-Infrastruktur
(`.github/ci-fixtures/`, S9) laufen lassen, nicht nur behauptet:

- Voller `--strict`-Lauf gegen `ci-smoke` mit `--publish-only`: 22
  Zwischenpfade entfernt, `dist/ci-smoke_release/ci-smoke-fdo-bundle.zip`
  blieb als einzige Datei stehen (Abnahme 1).
- Derselbe Lauf ohne `--publish-only`: `dist/ci-smoke`,
  `dist/ci-smoke.zip`, `dist/ci-smoke_release/` (voll) unverändert stehen
  geblieben (Abnahme 2).
- `--only build_fdo --slug ci-smoke --publish-only` gegen ein bereits
  bestehendes `dist/ci-smoke.zip` aus einem vorherigen Lauf: räumt
  ebenfalls korrekt auf (Abnahme 3) -- das ist jetzt auch der zweite
  CI-Schritt in `build.yml`.
- `unzip -l` gegen das übriggebliebene Bundle-ZIP bestätigt: alle 20
  gelöschten `_release/`-Dateien (Diagramme, TTL, Reports, `FDOx.yaml`)
  stecken tatsächlich mit drin, plus das komplette Originalpaket
  (`viewer/`, `data/model/`, `data/textures/`) -- 52 Dateien insgesamt.
- Abnahme 4 (No-op ohne `build_fdo`) nicht separat als eigener Testlauf
  ausgeführt, sondern durch Code-Inspektion des Hooks bestätigt (`if
  "build_fdo" in selection` -- eindeutig).
- Zusätzlich am 2026-09-09 real gegen CIIC 81 + Freshford bestätigt (auf
  Flos Maschine, siehe A4): beide finished bundles enthalten tatsächlich
  alles, echte Sketchfab-/Blender-/Nexus-Daten inklusive.

---

## Teil D — Offene Punkte

*(Aufgeräumt 2026-09-07: vollständig erledigte Punkte wurden hier entfernt,
nicht nur mit "Erledigt" markiert -- die Details bleiben in Teil C
(Nachtrag-Historie je Schritt) und Teil A4 (Beschlüsse) erhalten. Diese
Liste enthält ab jetzt nur, was tatsächlich noch offen ist.)*

- **Schwester-Repo für Software-FDOs.** Angekündigt 2026-09-03: ein Repo,
  das aus einem Git-Link ein `fdo:SoftwareFDO`-Paket baut. Vorschlag in A4:
  eigenes Repo (`fdo-software-packager`), nicht Zusammenlegung mit
  `fdo-3d-packager` -- S5 (`mdcff`), S6 (`bundle`) und S7 (`build_fdo`) aus
  diesem Repo als Vorlage kopieren (nicht importieren, A3), dabei
  `fdo_type` und die domänenspezifischen `distributions[]`-Rollen
  anpassen. Kein Schritt in diesem Repo, bis das Schwester-Repo tatsächlich
  startet.
- **`classification_rules.yaml`-Lücke in `fdo-squirrel`** -- `.mtl`,
  `viewer/*.html`/`.js`/`.css`/`LICENSE.txt` und `data/textures/*` fallen
  alle auf die generische Rolle `data`/`documentation` zurück statt
  `model`/`auxiliary`, an echten Daten bestätigt (S7). Fix gehört nach
  `fdo-squirrel/fdo/classification_rules.yaml`, separater Chat (A4/A5).
- **`fdo-squirrel`s Crosswalk verlangt `creators[].id` entgegen dem
  eigenen Schema**, das `id` dort ausdrücklich optional nennt
  (`idLabelEntityOptionalId`) -- trifft jeden echten `--local`-Fetch ohne
  `--creator-profile` (S9-Fund). Gleiches Muster: Fix gehört nach
  `fdo-squirrel`, separater Chat.
- **Zenodo-Nachbereitung bleibt Handarbeit** (Chat-Entscheidung
  2026-09-07): `MD.cff.id` durch die echte DOI ersetzen und einen
  `identifiers[]`-Eintrag (`{scheme: doi, value: ...}`, Muster
  `example_fdo/MD.cff`) ergänzen, beides manuell nach dem Upload.
  Automatisierung zurückgestellt, bis `fdo-squirrel-md-generator` als
  interaktiver Zwischenschritt steht.
- **Eigenes menschenlesbares Begleit-YAML** zusätzlich zu `MD.cff`? Tendenz
  weiterhin: nein, nur eine Quelle der Wahrheit -- nicht endgültig
  entschieden.
- **`identifiers`/`version`** bleiben in `MD.cff` weiterhin ungenutzt --
  anders als `heritage_object`/`spatial`/`temporal` (S10 erledigt das)
  gibt es dafür noch keinen konkreten Anwendungsfall in Flos aktuellen
  Testkandidaten; der generische Override-Mechanismus aus S10 könnte sie
  bei Bedarf genauso setzen, ohne weiteren Code.
- **`--publisher-label`/`--publisher-id` sind Singular** (ein Publisher,
  kein wiederholbares Flag) -- reicht für den aktuellen Anwendungsfall
  (immer "Research Squirrel Engineers Network"). Bei Bedarf später
  erweitern.
- **Weitere "Holy Wells"-Testkandidaten** (Wikidata-Query, 2026-09-07 im
  Chat geteilt, Liste nicht in diesem Dokument dupliziert) -- vier davon
  bereits real gefetcht (S8), der Rest offen für künftige Läufe.
