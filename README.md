# Kindergeld-Auszahlungstermine

Data and website for the iOS app "Kindergeld App: Termine".

- `docs/termine.json`: the payment dates the app downloads (served by GitHub Pages).
- `.github/workflows/update.yml`: runs daily, reads the official dates from
  https://www.arbeitsagentur.de/familie-und-kinder/auszahlungstermine, checks them and publishes.
  A failed run sends an email and publishes nothing.
- Kindergeld amount changes (by law, about once a year): edit `amountPerChildCents` in
  `Shared/termine.json`, run `python3 tools/update_termine.py`, push. In December the workflow opens
  an issue if next year's amount is missing.
- Announcement to all users (one notification): `python3 tools/update_termine.py --notice "Text" --notice-id 2027-amount`, push.
