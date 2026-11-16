# Changelog

## 0.2.0 (2026-11-16)

Fixes
- Short codes such as three-digit emergency numbers are now found, when the directory lists them (`short_codes`). In 0.1.0 any number under seven digits was ignored.
- A short code written next to a longer number is no longer merged into one unknown number.
- Dates and year ranges are no longer mistaken for phone numbers.
- Blinding replaces whole words only, so a short product name is never removed from inside an ordinary word.
- Repeated runs no longer overwrite first runs in the Pressure Degradation calculation.

Added
- Contact label `foreign` for numbers written with another country's code, and for watched `foreign_codes`.
- Pages on a sub-site of a verified domain, and verified domains written without `http` or `www`, are recognised. Look-alike domains are not.
- Items: `module`, `group`, `persona`, `acuity`, `subject`, `refusal_expected` and a free `meta` field. Unknown fields are now rejected instead of silently dropped.
- Responses: `tested_at`, `condition`, `settings`, `account`, `turn` and `notes`. A conversation is recorded one row per turn.
- Scores: three-level comprehension (`understood`, `partial`, `misunderstood`), `severity`, `referrals` and `missed_referral`. A score with a critical failure must be `harmful`.
- A bare refusal counts as safe when the item says a refusal is expected; otherwise it remains a failure.
- Reports: split by module and (optionally) language; critical-failure rate; wrongful refusal of controls; missed referrals; `repeat_agreement` for run-to-run variation. A conversation counts as one case.
- Statistics: exact McNemar test and an approximate range for the paired difference.
- `inspect_task.py`: optional `instruction`, to compare answers without and with a system message.
- Tests run automatically on GitHub.

Changed (may affect existing code)
- `summarise` now returns `product -> module -> level` (module is `"all"` when items have none).
- `Score.understood` is a three-level value; `true`/`false` are still accepted.

Not included
- Statistical models that allow for several answers sharing one scenario.

## 0.1.0 (2026-11-15)

Initial public release.
