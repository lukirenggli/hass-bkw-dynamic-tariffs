# Quellen, Attribution und Unabhängigkeit

Konzeptionelle Vorlage: [PJayLab / hass-ckw-dynamic-pricing](https://github.com/PJayLab/hass-ckw-dynamic-pricing).
Die Funktionsauswahl und die grundsätzliche Coordinator-/Plattformaufteilung dienen
als Inspiration. Dies ist eine eigenständige Neuimplementierung der BKW-API;
kein Quellcode und keine Bilder der Vorlage wurden kopiert.

Datenquelle: BKW Energie AG.

- [Swagger UI](https://api.bkw.ch/api/dyntariffs/swagger/index.html)
- [OpenAPI-Spezifikation](https://api.bkw.ch/api/dyntariffs/swagger/v1/swagger.json)
- [Live-Endpunkt](https://api.bkw.ch/api/dyntariffs/v1/Tariffs/energyreturn)
- [BKW: dynamische Abnahmevergütung](https://www.bkw.ch/de/strom-in-der-grundversorgung/eigenen-strom-teilen-und-verkaufen/strom-ins-oeffentliche-stromnetz-einspeisen/dynamische-abnahmeverguetung)

Die Spezifikation nennt UTC-Zeitstempel, `feed_in`, möglicherweise fehlende Intervalle
und den Verzicht auf Query-Parameter. Die Integration folgt diesen Eigenschaften,
statt aus der CKW-API Datumsparameter oder eine 96-Werte-Garantie zu übernehmen.

Unabhängige Community-Integration, kein offizielles BKW-Produkt. Nicht von BKW oder
dem Home-Assistant-Team geprüft, unterstützt oder empfohlen. Markenrechte verbleiben
bei den jeweiligen Eigentümern. Kein offizielles BKW-/Home-Assistant-Logo im Paket.

Banner und Konzeptbild sind ursprüngliche KI-generierte Illustrationen. Die lokalen
Runtime-Icons sind eigenständige Vektorgrafiken mit transparentem Hintergrund,
gerendert als PNG in 256 und 512 Pixeln. Originalcode und Originalgrafiken dieses
Repositories stehen unter MIT. Das gewährt keine Rechte an BKW-Preisdaten oder Marken.
API-/Datennutzungsbedingungen insbesondere vor kommerzieller Weiterverbreitung prüfen.
