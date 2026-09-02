# Migration 2026-08-25

Das vollständige YnBlue-Repository wurde aus `mac setup/YNBlue-Connector` in
dieses eigenständige Produktverzeichnis übernommen.

Erhalten sind Git-Historie, Remote-Konfiguration, Produktcode, Tests,
Dokumentation und die bislang unversionierte MQTT-Befehlsdokumentation. Nicht
übernommen wurden die 543-MB-virtuelle Umgebung, Caches und `.DS_Store`-Dateien.
Der übernommene Inhalt wurde per Prüfsummenvergleich gegen die Quelle geprüft.

Zum Migrationszeitpunkt folgte `main` unverändert `origin/main`; die
MQTT-Befehlsdokumentation und diese Migrations-/Regeldateien waren zunächst
noch nicht committet. Bei der anschließenden Repository-Bereinigung wurden nur
diese Dokumente aufgenommen; es wurde weder veröffentlicht noch eine neue
Version erzeugt.
