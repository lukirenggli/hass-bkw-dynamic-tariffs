# BKW Dynamic Tariffs im Marketplace veröffentlichen

Stand der geprüften Dokumentation: 26. November 2026.
Das Paket ist vorbereitet; Repository, Release und Katalog-PR musst du selbst
publizieren. Eine Katalogaufnahme oder bestandene GitHub-Checks werden nicht behauptet.

## 1. Repository anlegen

Auf [GitHub / neues Repository](https://github.com/new) als **lukirenggli**:

- Name: **hass-bkw-dynamic-tariffs**
- Sichtbarkeit: **Public**
- Beschreibung: **BKW dynamic feed-in tariffs for Home Assistant with price sensors and configurable thresholds.**
- Noch keine README, Lizenz oder .gitignore automatisch erzeugen; sie sind im Paket.

Das ZIP lokal entpacken und **den Inhalt des Repository-Ordners** hochladen,
nicht das ZIP und nicht noch einen zusätzlichen äusseren Ordner.
Am zuverlässigsten mit GitHub Desktop: Repository klonen, alle Dateien hinein
kopieren, committen und pushen. Versteckte Dateien/Ordner **.github** und
**.gitignore** unbedingt einschliessen.

Das Root muss u. a. `README.md`, `LICENSE`, `hacs.json`, `.github` und
`custom_components/bkw_dynamic_tariffs` enthalten. Nur **eine** Integration in
`custom_components`.

## 2. GitHub-Metadaten setzen

Unter **About** die Beschreibung und Topics setzen:
`home-assistant`, `homeassistant`, `marketplace`, `hacs`, `bkw`, `dynamic-tariffs`,
`feed-in`, `switzerland`, `energy`.

Unter **Settings > General > Features** **Issues** einschalten.
GitHub muss die MIT-Lizenz erkennen. Unter **Actions** die Workflows zulassen.
Keine Secrets, Tokens oder BKW-Zugangsdaten ins Repository schreiben.

## 3. Checks und realen Test bestehen

Der vorbereitete Workflow **Validate** enthält:

- **Marketplace validation (HACS action)**: `hacs/action`, Kategorie `integration`,
  **keine ignorierten Prüfungen**.
- **hassfest**: offizieller Home-Assistant-Validator.
- **unit-tests**: reine Python-Preis-/API-Tests und Struktur-/Asset-Prüfung.
- **ha-smoke-test**: Import, Einrichtung, alle elf Entitäten, Options-/Number-
  Änderung ohne Netzwerkabruf, lokale Uhr, Refresh und Unload in echtem HA,
  mit gemockter BKW-API. Python 3.14.2, HA 2026.11.3.

Warte, bis **alle Jobs grün sind**. Bei einem Fehler die Meldung beheben und erneut
pushen. Der Offline-Erstellungstest ersetzt Hassfest und HA-Laufzeittests nicht.
Teste anschliessend in deiner eigenen Home-Assistant-Installation gemäss [TESTING.md](TESTING.md).

## 4. Vollständiges GitHub-Release publizieren

Nach bestandenen Checks **Releases > Draft a new release**:

- Tag: **v1.0.0**, Zielbranch: **main**.
- Titel: **BKW Dynamic Tariffs 1.0.0**.
- Release Notes aus [CHANGELOG.md](CHANGELOG.md), plus bekannte Einschränkung
  der 12-Stunden-Abdeckung.
- Als normales Release veröffentlichen, nicht Draft und nicht Pre-release.

`manifest.json` enthält die Version `1.0.0`. Nur ein Tag reicht für den Katalog nicht.
Ein zusätzliches ZIP-Release-Asset ist nicht nötig: `zip_release` ist nicht gesetzt.
Marketplace installiert die Integration aus den Repository-Dateien am Release-Tag.

## 5. Vorabinstallation aus Link testen

In Home Assistant als Administrator **Einstellungen > Marketplace > Aus Link
hinzufügen / Add from link** und folgende URL verwenden:

https://github.com/lukirenggli/hass-bkw-dynamic-tariffs

GitHub verbinden, wenn angefordert. Integration installieren und einrichten;
einen vom Marketplace angeforderten Neustart ausführen. Noch nicht katalogisierte
Repos benötigen eine GitHub-Verbindung, normale Kataloginstallationen nicht.
Dies ist bereits öffentlich nutzbar, aber **noch keine globale Kataloglistung**.

## 6. Aufnahme in den Standardkatalog beantragen

1. [hacs/default](https://github.com/hacs/default) unter deinem persönlichen
   Account forken. Der Name des Katalog-Repositories bleibt trotz Marketplace so.
2. Einen neuen Branch von **master** erstellen, nicht direkt auf master arbeiten.
3. Die Datei **integration** bearbeiten. In der JSON-Liste alphabetisch den Eintrag
   `lukirenggli/hass-bkw-dynamic-tariffs` einfügen. Kommas und Sortierung beachten;
   bestehende Einträge nicht entfernen.
4. Pull Request zum Ursprungsrepository eröffnen, **Allow edits by maintainers**
   aktivieren und die aktuelle PR-Vorlage vollständig und wahrheitsgetreu ausfüllen.
5. Links zu deinem vollständigen Release, dem bestandenen HACS-Action-Lauf ohne
   `ignore` und dem bestandenen Hassfest-Lauf eintragen. Die Links erst nach den
   realen erfolgreichen Läufen verwenden; nicht behaupten, dass sie schon bestehen.
6. Review abwarten und Rückfragen bearbeiten. Keine Personen für ein Review anfordern.

Du bist als Repository-Eigentümer berechtigt, den PR zu stellen. Eine Aufnahme ist
nicht garantiert und kann laut offizieller Dokumentation Monate dauern. Nach dem
Merge wird das Repository beim nächsten Katalogscan aufgenommen und ist ohne
manuellen Link im Marketplace suchbar. Regionseintrag `country: CH` ist vorhanden.

**Nicht verwechseln:** Eine Marketplace-Listung macht das Projekt nicht zu einer
von Home Assistant geprüften, offiziell unterstützten Core-Integration. Dafür
wäre ein eigener Entwicklungs- und Review-Prozess erforderlich.

## 7. Nach der Veröffentlichung

Issues beantworten, neue HA-Versionen testen, Version und Changelog bei Updates
anpassen, GitHub-Checks bestehen lassen und ein neues Release erstellen. Repository
nicht einfach löschen, wenn es im Katalog gelistet ist. Erst eine Entfernung beantragen.

## Konformität: vorbereitet vs. noch offen

| Im Paket vorhanden | Vor der Einreichung durch dich nötig |
|---|---|
| Eigenständige Domain, eine Integration | Domainkonflikt im aktuellen Core/Katalog prüfen |
| Manifest, `hacs.json`, Kategorie Energiepreise | Öffentliche Repo und About-Metadaten |
| UI-Flow, stabile Unique IDs, DE/EN | Reale erfolgreiche HA-Tests |
| Lokales `brand/icon.png` 256 px und `icon@2x.png` 512 px | Bestandene HACS-Action und Hassfest |
| MIT-Lizenz und Community-Kennzeichnung | Vollständiges GitHub-Release |
| README, Banner, Test-/CI-Dateien | Katalog-PR und Annahme durch Maintainer |

## Offizielle Quellen

- [Marketplace nutzen und aus Link installieren](https://www.home-assistant.io/integrations/marketplace/)
- [HACS wird Marketplace; Katalog bleibt gleich](https://www.hacs.xyz/docs/marketplace/)
- [Aktuelle Katalogaufnahme](https://contributors.home-assistant.io/marketplace/guides/catalog/)
- [Validierungsregeln](https://contributors.home-assistant.io/marketplace/reference/validation/)
- [Repository-Struktur und README-Ausschlussmarker](https://contributors.home-assistant.io/marketplace/reference/repository-structure/)
- [hacs.json](https://contributors.home-assistant.io/marketplace/reference/hacs-json/)
- [Lokale Brand-Assets](https://contributors.home-assistant.io/core/integrations/brands/)

README-Ausschlussmarker sind schon vorbereitet; ihre Ausblendung im Marketplace
beginnt gemäss Dokumentation erst mit Home Assistant 2026.12.
