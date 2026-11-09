#!/usr/bin/env python3
"""Generate docs/index.html (support page + full payment-date table) from Shared/termine.json.

Usage: python3 tools/build_site.py   (update_termine.py runs it after writing new dates)
The table makes the page useful from Google searches like "kindergeld auszahlungstermine 2027".
"""
import datetime, html, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP_STORE_URL = "https://apps.apple.com/de/app/id6832220805"  # App Store Connect app 6832220805 (live after release)
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
            f"<td>{WEEKDAYS[x.weekday()]} {x.day}.</td>" if (x := by_month[m].get(str(d))) else "<td>-</td>"
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
    span = f"{years[0]}" if len(years) == 1 else " und ".join(map(str, years)) if len(years) == 2 else f"{years[0]} bis {years[-1]}"
    amount = t["amountPerChildCents"].get(str(datetime.date.today().year))
    amount_line = (f"<p>Kindergeld {datetime.date.today().year}: <strong>{amount // 100} € pro Kind und Monat</strong>. "
                   "Kinderzuschlag wird am selben Tag überwiesen.</p>") if amount else ""

    # Questions people ask Google ("Weitere Fragen", Apify SERP 2026-11). Plain text answers, also as FAQPage JSON-LD.
    year = datetime.date.today().year
    faq = [(f"Wann wird das Kindergeld {span} überwiesen?",
            "Das hängt von der letzten Ziffer Ihrer Kindergeldnummer ab. Die Familienkasse zahlt jeden Monat nach Endziffern von 0 bis 9. "
            "Die Tabellen oben zeigen alle Auszahlungstermine.")]
    if amount:
        faq.append((f"Wie hoch ist das Kindergeld {year}?",
                    f"{amount // 100} Euro pro Kind und Monat. Der Betrag für {year + 1} wird hier ergänzt, sobald er feststeht."))
    faq += [("Kann das Kindergeld später kommen?",
             "Ja. Die Bank braucht oft 1 bis 2 Werktage, Wochenenden und Feiertage verschieben den Geldeingang. "
             "Bei Fragen zur Zahlung hilft die Familienkasse: 0800 4 555533 (gebührenfrei)."),
            ("Wann wird der Kinderzuschlag ausgezahlt?", "Am selben Tag wie das Kindergeld."),
            ("Hat die Familienkasse eine App?",
             "Diese Kindergeld App ist inoffiziell und steht in keiner Verbindung zur Familienkasse. Sie zeigt die öffentlichen Termine "
             "der Bundesagentur für Arbeit und erinnert Sie am Zahltag. Anträge stellen Sie weiter bei der Familienkasse auf arbeitsagentur.de."),
            ("Kauf oder Abo wiederherstellen", "In der App: Einstellungen, Widget & Kalender, Käufe wiederherstellen."),
            ("Abo kündigen", "In der App unter Einstellungen, Abo kündigen oder verwalten, oder in den Einstellungen Ihres Apple Accounts. "
             "Wer im Gratismonat spätestens 24 Stunden vor dessen Ende kündigt, zahlt nichts.")]
    faq_html = "\n".join(f"<p><strong>{html.escape(q)}</strong><br>{html.escape(a)}</p>" for q, a in faq)
    faq_ld = json.dumps({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}, ensure_ascii=False)

    page = f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kindergeld Auszahlungstermine {span} nach Endziffer | Kindergeld App</title>
<meta name="description" content="Alle Kindergeld-Auszahlungstermine {span} für Endziffer 0-9 als Tabelle. Mit App: Erinnerung am Zahltag, Countdown-Widget.">
<link rel="stylesheet" href="style.css">
<script type="application/ld+json">{faq_ld}</script>
</head>
<body><main>
<h1>Kindergeld-Auszahlungstermine {span}</h1>
<p>Die Familienkasse überweist das Kindergeld gestaffelt nach der <strong>letzten Ziffer Ihrer Kindergeldnummer</strong> (Endziffer).
Beispiel: 123FK45678<strong>9</strong> → Endziffer 9. Die Nummer steht auf dem Kindergeldbescheid und im Verwendungszweck der Überweisung.</p>
{amount_line}
<p><a class=cta href="{APP_STORE_URL}">Kindergeld App für iPhone</a>. Erinnerung am Zahltag, Countdown-Widget. Kein Konto, keine Werbung.</p>

{tables}

<p class="muted">Stand: {html.escape(t["updated"])}. Termine unverbindlich. Es besteht kein Rechtsanspruch auf Zahlung an einem bestimmten Tag.
Wochenenden und Feiertage können den Geldeingang verschieben. Quelle: <a href="{html.escape(t["source"])}">arbeitsagentur.de</a>.</p>

<h2>Häufige Fragen</h2>
{faq_html}
<h2>Kontakt</h2>
<p>E-Mail: <a href="mailto:cloudedgetech101@gmail.com">cloudedgetech101@gmail.com</a></p>

<p class="muted">Inoffizielles Angebot, nicht von der Familienkasse oder der Bundesagentur für Arbeit.<br>
<a href="privacy.html">Datenschutz</a> · <a href="impressum.html">Impressum</a></p>
</main></body>
</html>
"""
    (ROOT / "docs" / "index.html").write_text(page)
    print(f"wrote docs/index.html ({', '.join(map(str, years))})")


if __name__ == "__main__":
    main()
