#!/usr/bin/env python3
"""Generate the website in docs/ from Shared/termine.json.

Usage: python3 tools/build_site.py   (update_termine.py runs it after writing new dates; so does the daily workflow)
Writes index.html (all dates), one page per month in MONTH_PAGES, one page per Endziffer, sitemap.xml, robots.txt,
and adds the shared head tags (canonical, Open Graph, Smart App Banner) to the hand-written kontakt.html.
privacy.html and impressum.html get the same tags from tools/legal.py, which imports head() and LEGAL from here.
Every run checks that the rendered dates match termine.json, the German copy rules and that local links resolve.
"""
import datetime, html, json, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
SITE = "https://kindergeld-termine.vercel.app/"
APP_ID = "6832220805"
APP_STORE_URL = f"https://apps.apple.com/de/app/id{APP_ID}"
MONTHS = "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split()
WEEKDAYS = "Mo Di Mi Do Fr Sa So".split()
WEEKDAYS_FULL = "Montag Dienstag Mittwoch Donnerstag Freitag Samstag Sonntag".split()
MONTH_PAGES = ["2026-12", "2027-01", "2027-02"]  # search peak: December to February
LEGAL = {"privacy.html": "Datenschutzerklärung der Kindergeld App: welche Daten die App speichert und sendet.",
         "impressum.html": "Impressum der Kindergeld App mit Kontaktdaten des Anbieters.",
         "kontakt.html": "Kontakt zur Kindergeld App: Fragen und Feedback per Formular oder E-Mail."}
FOOTER = """<p class="muted">Inoffizielles Angebot, nicht von der Familienkasse oder der Bundesagentur für Arbeit.<br>
<a href="./">Alle Termine</a> · <a href="privacy.html">Datenschutz</a> · <a href="impressum.html">Impressum</a></p>"""


def month_slug(ym: str) -> str:
    return f"kindergeld-{MONTHS[int(ym[5:]) - 1].lower().replace('ä', 'ae')}-{ym[:4]}.html"


def digit_slug(d: int) -> str:
    return f"kindergeld-endziffer-{d}.html"


def long_date(d: datetime.date) -> str:
    return f'<time datetime="{d.isoformat()}">{WEEKDAYS_FULL[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} {d.year}</time>'


def head(path: str, title: str, desc: str) -> str:
    url = SITE + ("" if path == "index.html" else path)
    t, d = html.escape(title), html.escape(desc)
    return f"""<!-- seo -->
<meta name="description" content="{d}">
<link rel="canonical" href="{url}">
<meta name="apple-itunes-app" content="app-id={APP_ID}">
<meta property="og:type" content="website">
<meta property="og:locale" content="de_DE">
<meta property="og:site_name" content="Kindergeld Termine">
<meta property="og:title" content="{t}">
<meta property="og:description" content="{d}">
<meta property="og:url" content="{url}">
<!-- /seo -->
"""


def page(path: str, title: str, desc: str, body: str, extra_head: str = "") -> tuple[str, str]:
    return path, f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="style.css">
{head(path, title, desc)}{extra_head}</head>
<body><main>
{body}
{FOOTER}
</main></body>
</html>
"""


def amount_note(t: dict, year: int) -> str:
    """Only amounts that are in termine.json, i.e. law. A draft (e.g. 267 EUR for 2027) is never stated."""
    amounts = {int(y): c for y, c in t["amountPerChildCents"].items()}
    if year in amounts:
        return f"Das Kindergeld beträgt {year} {amounts[year] // 100} Euro je Kind und Monat."
    known = max((y for y in amounts if y < year), default=None)
    return f"Der Betrag für {year} steht noch nicht fest." + (
        f" {known} sind es {amounts[known] // 100} Euro je Kind und Monat." if known else "")


def source_note(t: dict) -> str:
    return (f'<p class="muted">Die Termine veröffentlicht die Familienkasse der Bundesagentur für Arbeit auf '
            f'<a href="{html.escape(t["source"])}">arbeitsagentur.de</a>. Die Termine sind unverbindlich. Es gibt keinen '
            "Anspruch auf Zahlung an einem bestimmten Tag. Das Geld ist oft erst 1 bis 2 Bankarbeitstage später auf "
            f"dem Konto. Stand der Daten: {datetime.date.fromisoformat(t['updated']).strftime('%d.%m.%Y')}.</p>")


APP_BOX = (f'<p><a class=cta href="{APP_STORE_URL}">Kindergeld App für iPhone laden</a></p>\n'
           "<p>Die App zeigt Ihren nächsten Zahltag und erinnert Sie am Vortag und am Zahltag. Kein Konto, keine Werbung.</p>")


def more_links() -> str:
    months = " · ".join(f'<a href="{month_slug(ym)}">{MONTHS[int(ym[5:]) - 1]} {ym[:4]}</a>' for ym in MONTH_PAGES)
    digits = " · ".join(f'<a href="{digit_slug(d)}">Endziffer {d}</a>' for d in range(10))
    return f"<h2>Weitere Termine</h2>\n<p>Nach Monat: {months}</p>\n<p>Nach Endziffer: {digits}</p>"


def table(dates: dict[str, list[str]], year: int) -> str:
    by_month: dict[int, dict[str, datetime.date]] = {}
    for digit, days in dates.items():
        for s in days:
            d = datetime.date.fromisoformat(s)
            if d.year == year:
                by_month.setdefault(d.month, {})[digit] = d
    head_ = "".join(f"<th scope=col>{d}</th>" for d in range(10))
    rows = []
    for m in sorted(by_month):
        cells = "".join(
            f'<td><time datetime="{x.isoformat()}">{WEEKDAYS[x.weekday()]} {x.day}.</time></td>'
            if (x := by_month[m].get(str(d))) else "<td>-</td>" for d in range(10))
        ym = f"{year}-{m:02d}"
        name = f'<a href="{month_slug(ym)}">{MONTHS[m - 1]}</a>' if ym in MONTH_PAGES else MONTHS[m - 1]
        rows.append(f"<tr><th scope=row>{name}</th>{cells}</tr>")
    return (f"<h2 id=termine-{year}>Kindergeld-Auszahlungstermine {year}</h2>\n"
            f"<div class=scroll><table><thead><tr><th scope=col>Monat / Endziffer</th>{head_}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table></div>")


def index_page(t: dict, years: list[int], span: str) -> tuple[str, str]:
    year = datetime.date.today().year
    tables = "\n".join(table(t["dates"], y) for y in years)
    amount = t["amountPerChildCents"].get(str(year))
    amount_line = (f"<p>Kindergeld {year}: <strong>{amount // 100} € pro Kind und Monat</strong>. "
                   "Kinderzuschlag wird am selben Tag überwiesen.</p>") if amount else ""

    # Questions people ask Google ("Weitere Fragen", Apify SERP 2026-11). Plain text answers, also as FAQPage JSON-LD.
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

    body = f"""<h1>Kindergeld-Auszahlungstermine {span}</h1>
<p>Die Familienkasse überweist das Kindergeld gestaffelt nach der <strong>letzten Ziffer Ihrer Kindergeldnummer</strong> (Endziffer).
Beispiel: 123FK45678<strong>9</strong> → Endziffer 9. Die Nummer steht auf dem Kindergeldbescheid und im Verwendungszweck der Überweisung.</p>
{amount_line}
<p><a class=cta href="{APP_STORE_URL}">Kindergeld App für iPhone</a>. Erinnerung am Zahltag, Countdown-Widget. Kein Konto, keine Werbung.</p>

{tables}

<p class="muted">Stand: {html.escape(t["updated"])}. Termine unverbindlich. Es besteht kein Rechtsanspruch auf Zahlung an einem bestimmten Tag.
Wochenenden und Feiertage können den Geldeingang verschieben. Quelle: <a href="{html.escape(t["source"])}">arbeitsagentur.de</a>.</p>

{more_links()}

<h2>Häufige Fragen</h2>
{faq_html}
<h2>Kontakt</h2>
<p>E-Mail: <a href="mailto:cloudedgetech101@gmail.com">cloudedgetech101@gmail.com</a> · <a href="kontakt.html">Kontaktformular</a></p>"""
    return page("index.html", f"Kindergeld Auszahlungstermine {span} nach Endziffer | Kindergeld App",
                f"Alle Kindergeld-Auszahlungstermine {span} für Endziffer 0 bis 9 als Tabelle. Mit App: Erinnerung am Zahltag, Countdown-Widget.",
                body, f'<script type="application/ld+json">{faq_ld}</script>\n')


def month_page(t: dict, ym: str) -> tuple[str, str]:
    year, name = int(ym[:4]), MONTHS[int(ym[5:]) - 1]
    days = {d: datetime.date.fromisoformat(s) for d in range(10) for s in t["dates"][str(d)] if s.startswith(ym)}
    assert sorted(days) == list(range(10)), f"{ym}: termine.json has no date for Endziffer {set(range(10)) - set(days)}"
    rows = "".join(f'<tr><th scope=row><a href="{digit_slug(d)}">{d}</a></th><td>{long_date(days[d])}</td></tr>' for d in range(10))
    first, last = days[0], days[9]
    title = f"Kindergeld {name} {year}: Auszahlungstermine"
    body = f"""<h1>{title}</h1>
<p>Im {name} {year} überweist die Familienkasse das Kindergeld zwischen dem {first.day}. und dem {last.day}. {name}.
Der Tag hängt von der letzten Ziffer Ihrer Kindergeldnummer ab. Das ist die Endziffer. Den Kinderzuschlag zahlt die Familienkasse am selben Tag.</p>
<p>{amount_note(t, year)}</p>
<h2>Termine im {name} {year} nach Endziffer</h2>
<table class=list><thead><tr><th scope=col>Endziffer</th><th scope=col>Auszahlung</th></tr></thead><tbody>{rows}</tbody></table>
{source_note(t)}
{APP_BOX}
{more_links()}"""
    return page(month_slug(ym), title,
                f"Wann kommt das Kindergeld im {name} {year}? Alle Auszahlungstermine für die Endziffern 0 bis 9 vom {first.day}. bis {last.day}. {name}.",
                body)


def digit_page(t: dict, d: int, years: list[int]) -> tuple[str, str]:
    days = [x for s in t["dates"][str(d)] if (x := datetime.date.fromisoformat(s)).year in years]
    shown = sorted({x.year for x in days})
    span = " und ".join(map(str, shown)) if len(shown) <= 2 else f"{shown[0]} bis {shown[-1]}"
    sections = []
    for y in shown:
        rows = "".join(f"<tr><th scope=row>{MONTHS[x.month - 1]}</th><td>{long_date(x)}</td></tr>" for x in days if x.year == y)
        sections.append(f"<h2>Endziffer {d}: Termine {y}</h2>\n<p>{amount_note(t, y)}</p>\n"
                        f"<table class=list><thead><tr><th scope=col>Monat</th><th scope=col>Auszahlung</th></tr></thead><tbody>{rows}</tbody></table>")
    title = f"Kindergeld Endziffer {d}: alle Auszahlungstermine {span}"
    body = f"""<h1>{title}</h1>
<p>Endet Ihre Kindergeldnummer auf {d}? Dann finden Sie hier alle Tage, an denen die Familienkasse Ihr Kindergeld {span} überweist.
Die Endziffer ist die letzte Ziffer der Nummer, zum Beispiel 123FK45678<strong>{d}</strong>. Die Nummer steht auf Ihrem Bescheid
und im Verwendungszweck der Überweisung. Den Kinderzuschlag zahlt die Familienkasse am selben Tag.</p>
{chr(10).join(sections)}
{source_note(t)}
{APP_BOX}
{more_links()}"""
    return page(digit_slug(d), title,
                f"Wann kommt das Kindergeld für Endziffer {d}? Alle Auszahlungstermine {span} auf einen Blick, mit Wochentag.",
                body)


def with_head(path: str, desc: str) -> str:
    """Add the shared head tags to a hand-written page (replaces an earlier copy)."""
    s = re.sub(r"<!-- seo -->.*?<!-- /seo -->\n", "", (DOCS / path).read_text(), flags=re.S)
    title = html.unescape(re.search(r"<title>(.*?)</title>", s).group(1))
    anchor = '<link rel="stylesheet" href="style.css">\n'
    assert anchor in s, f"{path}: stylesheet link not found"
    return s.replace(anchor, anchor + head(path, title, desc), 1)


def visible_text(s: str) -> str:
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def verify(t: dict, pages: dict[str, str], years: list[int]) -> None:
    # Dates: each new page shows exactly the termine.json dates it should, and the index shows every date in `years`.
    want = {month_slug(ym): {s for v in t["dates"].values() for s in v if s.startswith(ym)} for ym in MONTH_PAGES}
    want |= {digit_slug(d): {s for s in t["dates"][str(d)] if int(s[:4]) in years} for d in range(10)}
    want["index.html"] = {s for v in t["dates"].values() for s in v if int(s[:4]) in years}
    for path, dates in want.items():
        got = re.findall(r'<time datetime="([\d-]+)">', pages[path])
        assert len(got) == len(set(got)) and set(got) == dates, f"{path}: rendered dates differ from termine.json"
    # Weekday/day labels match the datetime attribute.
    for path, s in pages.items():
        for iso, label in re.findall(r'<time datetime="([\d-]+)">(.*?)</time>', s):
            x = datetime.date.fromisoformat(iso)
            assert label in (long_date(x).split(">", 1)[1][:-7], f"{WEEKDAYS[x.weekday()]} {x.day}."), f"{path}: {iso} shown as {label}"
    # Copy rules for the new pages: no dashes or semicolons, no "Pro", no app price, no unconfirmed amount.
    for path, s in pages.items():
        text = visible_text(s) + " ".join(re.findall(r'content="([^"]*)"', s))
        if path != "index.html":  # index keeps its older copy ("pro Kind")
            assert not re.search(r"[–—;]|\bpro\b|€|\bEUR\b|\bAbo|Preis", text, flags=re.I), f"{path}: copy rule broken"
        if "2027" not in t["amountPerChildCents"]:
            assert "267" not in text, f"{path}: states the 2027 draft amount"
    assert all('name="apple-itunes-app"' in s and 'rel="canonical"' in s for s in pages.values())


def check_links() -> None:
    for f in DOCS.glob("*.html"):
        path, s = f.name, f.read_text()
        assert 'name="apple-itunes-app"' in s and 'rel="canonical"' in s, f"{path}: head tags missing (run tools/legal.py?)"
        for href in re.findall(r'(?:href|src)="([^"]+)"', s):
            if href.startswith(SITE):
                href = href[len(SITE):]
            elif re.match(r"(https?:|mailto:|#)", href):
                continue
            target = href.split("#")[0].removeprefix("./") or "index.html"
            assert (DOCS / target).is_file(), f"{path}: broken link {href}"


def main() -> None:
    t = json.loads((ROOT / "Shared" / "termine.json").read_text())
    this_year = datetime.date.today().year
    years = sorted({int(s[:4]) for days in t["dates"].values() for s in days if int(s[:4]) >= this_year})
    span = f"{years[0]}" if len(years) == 1 else " und ".join(map(str, years)) if len(years) == 2 else f"{years[0]} bis {years[-1]}"

    pages = dict([index_page(t, years, span)] + [month_page(t, ym) for ym in MONTH_PAGES]
                 + [digit_page(t, d, years) for d in range(10)])
    verify(t, pages, years)
    pages["kontakt.html"] = with_head("kontakt.html", LEGAL["kontakt.html"])
    for path, s in pages.items():
        (DOCS / path).write_text(s)
    check_links()

    order = ["index.html"] + [month_slug(ym) for ym in MONTH_PAGES] + [digit_slug(d) for d in range(10)] + list(LEGAL)
    urls = "".join(f"<url><loc>{SITE}{'' if p == 'index.html' else p}</loc></url>\n" for p in order)
    (DOCS / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n'
                                      f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls}</urlset>\n')
    (DOCS / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")
    print(f"wrote docs/: {len(pages)} pages, sitemap.xml, robots.txt ({', '.join(map(str, years))})")


if __name__ == "__main__":
    main()
