#!/usr/bin/env python3
"""Rebuild Shared/termine.json from the Bundesagentur page.

Usage: python3 tools/update_termine.py [--check] [--notice TEXT] [--notice-id ID]

Fetches https://www.arbeitsagentur.de/familie-und-kinder/auszahlungstermine,
parses every "Kindergeld-Endziffer N" block, keeps older dates we already have
(the page drops past months; for overlapping months the page wins), sanity-checks the result and writes the JSON.
--check only prints what would change. Edit `amountPerChildCents` by hand
in Shared/termine.json when the Kindergeld amount changes (EStG § 66), then run this script:
it bumps the version and publishes, since apps only take a strictly newer version.
--notice sets the German home-screen hint (--notice "" removes it); --notice-id additionally announces it once
as a notification. Use a new id per announcement; fixing a typo under the same id notifies nobody again.
"""
import argparse, datetime, html, json, pathlib, re, subprocess, sys

URL = "https://www.arbeitsagentur.de/familie-und-kinder/auszahlungstermine"
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "Shared" / "termine.json"
PUBLISHED = ROOT / "docs" / "termine.json"  # served by GitHub Pages; existing installs download this
MONTHS = {m: i + 1 for i, m in enumerate(
    "Januar Februar März April Mai Juni Juli August September Oktober November Dezember".split())}


def fetch() -> str:
    # curl, not urllib: Python's bundled certs fail on some Macs.
    return subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", URL], capture_output=True, text=True, check=True).stdout


def parse(page: str) -> dict[str, list[str]]:
    page = re.sub(r"<(script|style).*?</\1>", "", page, flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
    out: dict[str, list[str]] = {}
    for digit, block in re.findall(
            r"Kindergeld-Endziffer (\d) (.*?)(?=Auszahlungstermine Kindergeld-Endziffer|Ist der Inhalt)", text):
        for year, seg in re.findall(r"Auszahlungstermine (20\d\d) (.*?)(?=Auszahlungstermine 20\d\d|$)", block):
            for day, month in re.findall(r"(\d{1,2})\. (\w+)", seg):
                out.setdefault(digit, []).append(f"{year}-{MONTHS[month]:02d}-{int(day):02d}")
    return out


def merge(old: list[str], fresh: list[str]) -> list[str]:
    """The page drops past months, so keep old dates only for months *before* the first fetched month;
    from there on the page wins (a corrected date must replace the old one, not sit beside it)."""
    if not fresh:
        return sorted(old)
    first_month = min(fresh)[:7]  # "yyyy-mm": a date corrected within its month must not survive
    return sorted({d for d in old if d[:7] < first_month} | set(fresh))


def check(dates: dict[str, list[str]]) -> None:
    assert sorted(dates) == [str(d) for d in range(10)], f"digits missing: {sorted(dates)}"
    counts = {len(v) for v in dates.values()}
    assert len(counts) == 1, f"digits have different month counts: {counts}"
    for d, days in dates.items():
        for s in days:
            try:
                day = datetime.date.fromisoformat(s)
            except ValueError:
                raise AssertionError(f"{s!r} (Endziffer {d}) is not a valid date")
            if day.weekday() >= 5:
                raise AssertionError(f"{s} (Endziffer {d}) is a weekend")
    for d, days in dates.items():
        months = [datetime.date.fromisoformat(s) for s in days]
        months = [m.year * 12 + m.month for m in months]
        assert months == list(range(months[0], months[0] + len(months))), \
            f"Endziffer {d}: months not one per month without gaps (page skipped a month or paid twice)"
    for i in range(counts.pop()):
        month = [dates[str(d)][i] for d in range(10)]
        assert len({s[:7] for s in month}) == 1, f"month index {i} mixes months: {month}"
        assert month == sorted(month), f"month {month[0][:7]} not staggered 0..9"


def check_meta(doc: dict) -> None:
    """What the app's `Termine.isValid` also enforces, so a hand-edit typo never ships silently ignored."""
    amounts = doc["amountPerChildCents"]
    assert amounts and all(k.isdigit() and 2020 <= int(k) <= 2100 for k in amounts), f"bad year keys: {list(amounts)}"
    assert all(type(v) is int and 10_000 <= v <= 100_000 for v in amounts.values()), f"amounts must be cents 10000..100000: {amounts}"
    assert doc["source"].startswith("https://www.arbeitsagentur.de/"), f"source must be the BA page: {doc['source']}"
    if "noticeID" in doc:
        assert type(doc["noticeID"]) is str and doc["noticeID"], f"noticeID must be a non-empty string: {doc['noticeID']!r}"
        assert doc.get("notice"), "noticeID without a notice would announce nothing"


def apply_notice(doc: dict, notice: str | None, notice_id: str | None) -> dict:
    doc = dict(doc)
    if notice == "":
        doc.pop("notice", None)
        doc.pop("noticeID", None)
    elif notice is not None:
        doc["notice"] = notice
    if notice_id is not None:
        assert doc.get("notice"), "--notice-id needs a notice (--notice or one already in the file)"
        doc["noticeID"] = notice_id
    return doc


def content(doc: dict) -> dict:
    return {k: v for k, v in doc.items() if k not in ("version", "updated")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--notice")
    ap.add_argument("--notice-id")
    args = ap.parse_args()
    old = json.loads(OUT.read_text())
    published = json.loads(PUBLISHED.read_text())
    fresh = parse(fetch())
    assert sorted(fresh) == [str(d) for d in range(10)], \
        f"BA page structure changed: found Endziffer {sorted(fresh)} – fix parse() before trusting '0 new dates'"
    new = apply_notice({**old, "dates": {d: merge(old["dates"].get(d, []), fresh[d]) for d in map(str, range(10))}},
                       args.notice, args.notice_id)
    check(new["dates"])
    check_meta(new)

    added = sum(len(new["dates"][d]) - len(old["dates"].get(d, [])) for d in new["dates"])
    print(f"{added} new dates; range {new['dates']['0'][0]} .. {new['dates']['0'][-1]}")
    # Anything users don't have yet (new/corrected dates, or a hand-edited amount/notice) needs a higher version:
    # apps only take a download that is strictly newer than what they have.
    if content(new) == content(published) and new == old:
        return
    if content(new) != content(published):
        new.update(version=max(old["version"], published["version"]) + 1, updated=datetime.date.today().isoformat())
    if args.check:
        print(f"would write version {new['version']}")
        return
    for path in (OUT, PUBLISHED):
        path.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT} and {PUBLISHED} (version {new['version']})")
    subprocess.run([sys.executable, str(ROOT / "tools" / "build_site.py")], check=True)  # refresh the date table page


if __name__ == "__main__":
    main()
