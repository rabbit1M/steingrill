# Steingrill-Planer

Plant eine U-förmige Grillumfassung aus deutschen Normalformat-Ziegeln
(NF 240×115×71 mm, Halbstein 115 mm) anhand der Maße eines Grillrosts.

## Installation

```
pip install matplotlib pytest
```

## Bedienung

```
python steingrill.py
```

Das Programm fragt interaktiv ab:

| Eingabe | Default |
|---|---|
| Rosthöhe über Grundfläche [mm] | 150 |
| Wunsch Rost-Breite / Rost-Tiefe [mm] | – |
| Wunschhöhe (Oberkante der Wände) [mm] | – |
| Spielraum Rost – Wand [mm] | 10 |
| Fugenbreite [mm] | 10 |
| Reserve [%] | 5 |

Anschließend zeigt das Programm eine Auswahl **rastertauglicher Rostgrößen**
(7 mm Luft rundherum), die sich ohne Steine schneiden zu müssen exakt mauern
lassen. Der Benutzer wählt per Nummer, ob er den Rost etwas größer oder
kleiner kaufen möchte (0 = Wunschmaß beibehalten). Danach werden ein Textplan
mit Steinbedarf und eine Visualisierung (Vorderansicht und Draufsicht)
ausgegeben.

## Annahmen

- Wandstärke 115 mm (halber Stein), offene U-Form
- Die Grundplatte wird als vorhanden angenommen und nicht mitgemauert
- Läuferverband: jede zweite Schicht (Lage B) ist um einen halben Stein
  versetzt und benötigt daher halbe Steine an den Lagenenden
- Innenmaß = Rostmaß + Spielraum; die Maße werden auf das Ziegelraster
  (Fuge 10 mm -> 250er-Modul, mit Halbsteinen 125er-Feinraster) gerundet,
  sodass keine Steine geschnitten werden müssen
- Die tatsächlich erreichbaren Maße (und der daraus folgende größere
  Spielraum) werden im Plan ausgewiesen
- Die Rosthöhe über der Grundfläche wird abgefragt und standardmäßig mit 150 mm
  geplant

## Tests

```
pytest
```
