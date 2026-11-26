# Testplan

## Automatisiert

```bash
python3 -m unittest discover -s tests -v
python3 scripts/check_repository.py
```

Die Standardbibliotheks-Unit-Tests importieren die Preismodule ohne Home Assistant.
API-Tests verwenden aiohttp-kompatible Mocks, keine Live-Requests. Ausserhalb
von Home Assistant wird `aiohttp` aus `requirements-dev.txt` benötigt. Auf GitHub wird
im weiteren Job HA 2026.11.3 installiert und `scripts/ha_smoke_test.py` ausgeführt.
Dieser Test verwendet Home Assistant selbst, keine nachgebauten HA-Klassen.
Hassfest und HACS-Action laufen unabhängig. Alle müssen vor Release grün sein.

## In deiner Home-Assistant-Testinstallation

Vorher ein Backup erstellen. Erste Automationen nur mit Benachrichtigungen testen.

- [ ] Repository über **Marketplace > Add from link** hinzufügen und installieren.
- [ ] Einrichtung mit Beispielschnitten oben 0.150, unten 0.050 CHF/kWh.
- [ ] Genau ein Gerät; 31 registrierte Entitäten, davon 14 aktiv und 17 deaktiviert.
- [ ] Alle 17 optionalen Sensoren aktivieren, dann die Zustände und Optionen prüfen.
- [ ] Aktuellen Preis und Intervallgrenzen mit der BKW-API vergleichen.
- [ ] Preiswechsel erfolgt ohne weiteren API-Abruf; Countdown sinkt minütlich.
- [ ] Gleiche Folgepreise erzeugen keinen fiktiven Preiswechsel.
- [ ] Heute: Zeitgewichtung, Minimum, Maximum und Tagesabdeckung kontrollieren.
- [ ] Beide Schwellen ändern, einschliesslich negativer Werte; Binary Sensoren reagieren sofort.
- [ ] Bei Gleichheit mit einer Schwelle `off`; niedrigere obere Schwelle als untere abgelehnt.
- [ ] Neustart: Schwellen erhalten, neuer API-Abruf; kein persistierter Preiscache.
- [ ] Aktualisieren-Button holt neue Daten; schnelle Klicks werden gebündelt.
- [ ] Netzwerkfehler: gültiger Cache bleibt, Diagnose meldet Fehler, Refresh bleibt bedienbar.
- [ ] Nach Ablauf ohne neuen Plan: aktueller Preis/Binary Sensoren `unavailable`, nicht null/off.
- [ ] Mitternacht: Statistiken wechseln ohne Extra-Request; bei fehlendem Tagesplan unavailable.
- [ ] Integration deaktivieren/entfernen: Timer beendet, keine verbleibenden API-Abfragen.
- [ ] Deutsche/englische Oberfläche und lokales Brand-Icon prüfen.
- [ ] Mindestens 24 Stunden Betrieb: 12-Stunden-Abrufe und potentielle Planlücken beobachten.

Das API-Intervall ist ein Coordinator-Pollingintervall, kein garantierter wall-clock
Cron-Zeitpunkt. Einrichtung, Neustarts und manuelle Abrufe sind zusätzliche Requests.


## Erweiterungstest 1.1.0

Offline bestehen **74 Tests**: 36 bisherige API-/Preis-Tests, 23 Planungs-Tests
und 15 Verhaltens-Tests der tatsächlichen Integrationsmethoden mit gemockten
Home-Assistant-Schnittstellen. Letztere sind **kein vollständiger HA-Laufzeittest**.

- [ ] Erstes Bild: günstigstes 4h-Fenster morgen und heutige 4h-Mitgliedschaft aktiv.
- [ ] Zweites Bild: genau die 17 entsprechenden Entitäten standardmässig deaktiviert.
- [ ] Aktivierte optionale Entitäten bleiben nach Neustart/Update aktiviert.
- [ ] Vorhersage-Zustand zeigt das nächste kommende Intervall; `forecast` nur Zukunft.
- [ ] Keine Zukunftsdaten: Vorhersage und morgen-Fenster unavailable, nicht erfunden.
- [ ] Zeitfenster-Sensoren haben Start/Ende und gewichteten Durchschnitt.
- [ ] Fenster-Mitgliedschaft wird am Start on und am Ende off.
- [ ] Gleiche Preise: frühestes Fenster; Prozentgruppen enthalten alle Preisgleichstände.
- [ ] Tageslücke: Ranking und Fenster unavailable, keine falschen Extremwerte.
- [ ] Letzte API-Aktualisierung ändert sich nicht bei lokalem Preiswechsel.
- [ ] `local_updated_at` und `evaluated_at` ändern sich bei lokaler Auswertung.
- [ ] Alter API-Fehler + schneller Refresh-Klick meldet keinen fiktiven neuen Fehler.
- [ ] HA-Smoke-Test aktiviert alle optionalen Entitäten und prüft das Neuladen.

Die optionale Dashboard-Beispielkarte ist YAML-/syntaktisch vorbereitet, aber
konnte hier nicht in einer realen HA-Frontend-/ApexCharts-Installation geprüft werden.

## CI bootstrap correction

The real-HA smoke test initializes `loader.async_setup(hass)` and then awaits
`async_load_base_functionality(hass)` before setting up the `homeassistant`
component. Constructing `HomeAssistant` alone does not initialize the loader
cache. This addresses the reported `KeyError: integrations` during test startup.
The repository check also guards this initialization order.

The full corrected smoke test still has to pass in GitHub Actions with HA
2026.11.3. Offline syntax/order checks are not a successful real-HA test.
