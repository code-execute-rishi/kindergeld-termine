#!/usr/bin/env python3
"""Generate docs/index.html (support page + full payment-date table) from Shared/termine.json.

Usage: python3 tools/build_site.py   (update_termine.py runs it after writing new dates)
The table makes the page useful from Google searches like "kindergeld auszahlungstermine 2027".
"""
import datetime, html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_STORE_URL = "https://apps.apple.com/de/app/idXXXXXXXXXX"  # TODO: real App Store link after release
MONTHS = "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split()
WEEKDAYS = "Mo Di Mi Do Fr Sa So".split()


def table(dates: dict[str, list[str]], year: int) -> str:
    by_month: dict[int, dict[str, datetime.date]] = {}
    for digit, days in dates.items():
        for s in days:
            d = datetime.date.fromisoformat(s)
            if d.year == year:
                by_month.setdefault(d.month, {})[digit] = d
    head = "".join(f"<th scope=col>{d}</th>" for d in range(10))
    rows = []
    for m in sorted(by_month):
        cells = "".join(
            f"<td>{WEEKDAYS[x.weekday()]} {x.day}.</td>" if (x := by_month[m].get(str(d))) else "<td>–</td>"
            for d in range(10))
        rows.append(f"<tr><th scope=row>{MONTHS[m - 1]}</th>{cells}</tr>")
    return (f"<h2 id=termine-{year}>Kindergeld-Auszahlungstermine {year}</h2>\n"
            f"<div class=scroll><table><thead><tr><th scope=col>Monat / Endziffer</th>{head}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def main() -> None:
    t = json.loads((ROOT / "Shared" / "termine.json").read_text())
    this_year = datetime.date.today().year
    years = sorted({int(s[:4]) for days in t["dates"].values() for s in days if int(s[:4]) >= this_year})
    tables = "\n".join(table(t["dates"], y) for y in years)
    span = f"{years[0]}" if len(years) == 1 else " und ".join(map(str, years)) if len(years) == 2 else f"{years[0]}–{years[-1]}"
    amount = t["amountPerChildCents"].get(str(datetime.date.today().year))
    amount_line = (f"<p>Kindergeld {datetime.date.today().year}: <strong>{amount // 100} € pro Kind und Monat</strong>. "
                   "Kinderzuschlag wird am selben Tag überwiesen.</p>") if amount else ""

    page = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kindergeld Auszahlungstermine {span} nach Endziffer – Kindergeld App</title>
<meta name="description" content="Alle Kindergeld-Auszahlungstermine {span} für Endziffer 0–9 als Tabelle. Mit App: Erinnerung am Vortag, Countdown-Widget (Pro).">
<link rel="stylesheet" href="style.css">
</head>
<body><main>
<h1>Kindergeld-Auszahlungstermine {span}</h1>
<p>Die Familienkasse überweist das Kindergeld gestaffelt nach der <strong>letzten Ziffer Ihrer Kindergeldnummer</strong> (Endziffer).
Beispiel: 123FK45678<strong>9</strong> → Endziffer 9. Die Nummer steht auf dem Kindergeldbescheid und im Verwendungszweck der Überweisung.</p>
{amount_line}
<p><a class=cta href="{APP_STORE_URL}">Kindergeld App für iPhone</a> – Erinnerung am Vortag, Countdown-Widget mit Pro. Kein Konto, kein Tracking.</p>

{tables}

<p class="muted">Stand: {html.escape(t["updated"])}. Termine unverbindlich – es besteht kein Rechtsanspruch auf Zahlung an einem bestimmten Tag;
Wochenenden und Feiertage können den Geldeingang verschieben. Quelle: <a href="{html.escape(t["source"])}">arbeitsagentur.de</a>.</p>

<h2>Häufige Fragen</h2>
<p><strong>Das Geld kam an einem anderen Tag.</strong><br>Banklaufzeiten, Wochenenden und Feiertage können den Geldeingang verschieben.
Bei Fragen zur Zahlung hilft die Familienkasse: 0800&nbsp;4&nbsp;555533 (gebührenfrei).</p>
<p><strong>Pro in der App wiederherstellen</strong><br>Einstellungen → Pro → „Käufe wiederherstellen“.</p>

<h2>Kontakt</h2>
<p>E-Mail: <a href="mailto:[E-MAIL]">[E-MAIL]</a></p>

<p class="muted">Inoffizielles Angebot – nicht von der Familienkasse oder der Bundesagentur für Arbeit.<br>
<a href="privacy.html">Datenschutz</a> · <a href="impressum.html">Impressum</a></p>
</main></body>
</html>
"""
    (ROOT / "docs" / "index.html").write_text(page)
    print(f"wrote docs/index.html ({', '.join(map(str, years))})")


if __name__ == "__main__":
    main()
