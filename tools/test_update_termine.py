"""Run: python3 tools/test_update_termine.py"""
import update_termine as u

# BA corrects 4 Nov -> 5 Nov: the old date must not survive; past months the page dropped are kept.
assert u.merge(["2026-10-05", "2026-11-04", "2026-12-03"], ["2026-11-05", "2026-12-03", "2027-01-08"]) == \
    ["2026-10-05", "2026-11-05", "2026-12-03", "2027-01-08"]
assert u.merge(["2026-10-05"], []) == ["2026-10-05"]

for bad in ({str(d): ["2026-11-07"] for d in range(10)},                      # Saturday
            {str(d): [day] for d, day in enumerate(reversed(                   # 9 paid before 0
                ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05", "2026-11-06",
                 "2026-11-09", "2026-11-10", "2026-11-11", "2026-11-12", "2026-11-13"]))},
            {str(d): ["2026-02-30"] for d in range(10)},                      # not a date
            {str(d): ["2026-11-02", "2026-12-01", "2026-12-02"] for d in range(10)},  # paid twice in Dec
            {str(d): ["2026-11-02", "2027-01-04"] for d in range(10)}):               # December dropped
    try:
        u.check(bad)
        raise SystemExit(f"check() accepted bad data: {bad}")
    except AssertionError:
        pass
for meta in ({"amountPerChildCents": {"2026": "25900"}, "source": u.URL},         # string amount
             {"amountPerChildCents": {"2027 ": 25900}, "source": u.URL},         # bad year key
             {"amountPerChildCents": {"2026": 25900}, "source": "javascript:alert(1)"}):
    try:
        u.check_meta(meta)
        raise SystemExit(f"check_meta() accepted bad data: {meta}")
    except AssertionError:
        pass
u.check_meta({"amountPerChildCents": {"2026": 25900}, "source": u.URL})
for meta in ({"amountPerChildCents": {"2026": 25900}, "source": u.URL, "noticeID": "x"},               # id, no text
             {"amountPerChildCents": {"2026": 25900}, "source": u.URL, "notice": "Hinweis", "noticeID": ""}):
    try:
        u.check_meta(meta)
        raise SystemExit(f"check_meta() accepted bad data: {meta}")
    except AssertionError:
        pass

# --notice / --notice-id
doc = {"version": 3, "notice": "alt", "noticeID": "a"}
assert u.apply_notice(doc, None, None) == doc
assert u.apply_notice(doc, "neu", None) == {**doc, "notice": "neu"}, "typo fix keeps the id: nobody is notified again"
assert u.apply_notice(doc, "neu", "b") == {**doc, "notice": "neu", "noticeID": "b"}
assert u.apply_notice(doc, "", None) == {"version": 3}, '--notice "" removes notice and id'
assert u.apply_notice({"version": 3}, None, None) == {"version": 3}, "old files stay without noticeID"
assert doc == {"version": 3, "notice": "alt", "noticeID": "a"}, "input not mutated"
for notice, nid in ((None, "b"), ("", "b")):
    try:
        u.apply_notice({"version": 3}, notice, nid)
        raise SystemExit(f"apply_notice() accepted an id without text: {notice!r}, {nid!r}")
    except AssertionError:
        pass
u.check_meta(u.apply_notice({"amountPerChildCents": {"2026": 25900}, "source": u.URL}, "Hinweis", "2027-01"))
print("ok")
