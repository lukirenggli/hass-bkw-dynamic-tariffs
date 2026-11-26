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
- [ ] Genau ein Gerät; sechs Sensoren, zwei Binary Sensoren, zwei Numbers, ein Button.
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
