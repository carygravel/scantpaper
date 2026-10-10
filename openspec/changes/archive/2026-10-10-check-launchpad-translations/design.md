## Context

The check has to answer one question — "has anything moved on Launchpad since we
last pulled the catalogs?" — and every decision follows from what Launchpad
actually serves to an unauthenticated client, and from *which* surface carries
*which* timestamp. Both were measured, not assumed.

**Two independent triggers, with different sources.** The template and the
individual languages move on different events, and Launchpad exposes their
timestamps in different places:

- *Template (the message set / `.pot`).* The JSON API resource
  `GET https://api.launchpad.net/devel/scantpaper/trunk/+pots/scantpaper`
  returns `message_count` (549), `language_count` (36),
  `date_last_updated` (`2026-09-27T14:19:54.066364+00:00`) and an `http_etag`.
  It is a versioned (`devel`) contract with no authentication, and it honours
  `If-None-Match`: replaying the tag yields `304 Not Modified` with an empty
  body.
- *Per-language translation activity.* This timestamp is **only** on the HTML
  series page, `GET
  https://translations.launchpad.net/scantpaper/trunk/+translations`, one row
  per language with its percentage translated, untranslated count,
  unreviewed-suggestion count and last-changed time (43 rows with a date on
  2026-10-10, Italian carrying 14 suggestions).

**The template timestamp does not track translations.** This is the fact that
shapes the whole design, and it is why the sources are split the way they are:

```
template date_last_updated      2026-09-27T14:19:54.066364+00:00   (API)
pot/language import window      2026-09-27T14:10 … 14:22Z          (HTML rows)
Italian date_changed            2026-09-27T16:07:54.872024+00:00   (HTML row)
```

The template's `14:19:54` falls *inside* the import window and is roughly when
the `.pot` landed; the Italian row's `16:07:54` is ~1h48m later — a real, later
event (the Italian details page names a different latest contributor and 14 new
suggestions). Translation activity after the pot did not move the template
timestamp. So the template field answers "did the message set change?" and the
per-language field answers "did this language change?", and neither substitutes
for the other.

The Italian value is genuinely UTC: the server-rendered markup is
`<time datetime="2026-09-27T16:07:54.872024+00:00" title="2026-09-27 16:07:54
UTC">`, with an explicit `+00:00` offset, not a local-time rendering.

**The API cannot supply the per-language timestamp.** The `translation_file`
resource exposes only `http_etag, id, resource_type_link, self_link, web_link`
— no date. The `translation_files` collection carries no aggregate `http_etag`
(its top-level keys are `entries, resource_type_link, start, total_size`).
Polling 44 per-file tags would be 44 requests, worse than the single page
review.

**The page cannot be polled conditionally.** `+translations` sends no `ETag` and
no `Last-Modified`, so each run transfers the full ~76 KB page. There is no
cheaper translation signal.

**Catalogs are not anonymously downloadable.** `+export` in every form —
`/trunk/+export`, `/trunk/+pots/scantpaper/<lang>/+export`, with or without
`format=po` — answers an anonymous request with `303 See Other` to `.../+login`.
There is no OAuth path for it and no API operation that returns the file.

**`robots.txt` allows ordinary clients but not AI crawlers.** `User-agent: *`
allows `/`; a list of named AI assistants and the `Scrapy` user agent get
`Disallow: /`, and the file advertises `Content-Signal: ai-train=no`. A
legitimate maintainer tool is welcome as long as it is not one of those agents
and does not swamp the service.

The repository already contains small `argparse`/`print` developer scripts
(`dev/release.py`, `dev/check_po.py`, `dev/summarise_po.py`) that are tested by
driving them as a subprocess from `src/scantpaper/tests/`. This change follows
that shape.

## Goals / Non-Goals

**Goals:**

- Answer "has upstream changed?" without authentication, from a single
  committed reference point.
- Name *which* languages moved and by how much, when a translation changed.
- Contain the fragility: the answer must never be wrong in the dangerous
  direction (reporting "unchanged" when the page simply failed to parse).
- Never gate a release, add no dependencies, and stay testable offline.

**Non-Goals:**

- Downloading or committing catalogs. That needs a login and stays the manual
  release-procedure step.
- Authenticating to Launchpad in any form, or storing a session for the tool.
- Judging translation quality. The tool reports movement and counts; a native
  supplies the wording, exactly as `dev/check_po.py` advisories do.
- Deriving the reference point from git. See the decision below.
- Auto-advancing the baseline. It records what the catalogs were last synced
  from, so advancing it is a deliberate act.

## Decisions

### Each trigger is read from the only source that carries it

The template trigger comes from the API resource; the translation trigger comes
from the HTML page. Neither is "primary": they answer different questions and
the run needs both.

- The template read is a conditional `GET`, so a run where only translations
  moved costs one `304` plus the page.
- The page is read on **every** run, because a translation can move without the
  template moving (proven above), so there is no earlier signal to skip it on.
- *Rejected — template-only, from the API.* It would miss exactly the event the
  change exists to surface: a translator working on a language, with no change
  to the message set.
- *Rejected — page-only.* It works for translations today (the full message
  count 549 appears per row) but leans entirely on presentation markup for both
  triggers, when a stable, conditional JSON source exists for one of them.

### The catalog export is out of scope, by evidence

The tool does not try to fetch `.po` files. This is not a limitation the design
works around; it is the boundary the evidence draws. Documenting it in the
proposal is deliberate so the question is not re-litigated: the export is
`303 → +login`, and no API operation substitutes for it.

### The baseline is a snapshot sampled from Launchpad, not derived from git

`po/launchpad-state.json` records what Launchpad reported at the last sync:

```jsonc
{
  "series": "trunk",
  "pot": "scantpaper",
  "captured": "2026-09-27T16:10:00+00:00",   // provenance of the sample
  "template": {                               // trigger A: message set / pot
    "date_last_updated": "2026-09-27T14:19:54.066364+00:00",
    "etag": "\"1052062c…-ce98fe81…\""
  },
  "languages": {                           // trigger B: per-language activity
    "it": { "last_changed": "2026-09-27 16:07:54",
            "untranslated": 7, "suggestions": 14 }
  }
}
```

"Newer" is then a per-unit comparison against the snapshot, comparing like with
like (both sides of each field come from Launchpad, so there is no cross-clock
or format conversion):

```
template.etag / date_last_updated
    vs baseline.template            -> message set changed
languages[lang].last_changed
    vs baseline.languages[lang]     -> that language changed
lang present live, absent in baseline -> new locale
```

Any difference is a change. In normal operation a `last_changed` only moves
forward, so this is effectively "newer than the baseline"; a straight inequality
is used so a data correction that moves a value backwards is still reported.

- *Rejected — derive the reference from the local catalogs.* Launchpad's export
  rewrites headers, and a web-UI edit has no reliable counterpart in the local
  `.po` files, so there is nothing in the tree to compare against.
- *Rejected — derive the reference from git.* Appealing, since it needs no new
  file, but this repository's history cannot carry it:
  - The only commit touching `po/scantpaper/it.po` is `74a6b010`, the *Rosetta
    template-directory layout reorg* — a structural move, not a sync.
  - The catalog directory also carries ~20 local *fuzzy-review* and *re-merge*
    commits, which edit `.po` content with no Launchpad involvement at all.
  - Almost every commit object is dated `T00:00:00Z`; the timestamps have been
    normalised, so commit time cannot even give a time of day.
  - Even a clean commit time records *when we committed*, not *what Launchpad
    reported*: a download at 14:00 that Launchpad finishes importing at 14:05
    would read as "new" on the next check.
- *Rejected — no baseline, report the current totals.* The page shows only the
  present; without a stored snapshot there is no way to say what changed, which
  is the entire question.

The baseline advances only via `--update`, after a sync. If the maintainer
forgets, the tool keeps reporting the same change — the safe direction.

### Advisory by default; the only default failure is a check that could not run

Finding that translators translated is not a defect, so the default exit is `0`
whether or not a change is found. `AGENTS.md` reserves hard failures for defects
in shipped output, and a busy translation week is not one. CI that wants a
signal passes `--fail-on-change`.

There is one genuine failure: a run that cannot determine some part of the state
(a network failure, an unexpected API shape, or an unparseable page) exits
non-zero. This keeps "could not determine" separate from "unchanged", which is
the distinction the whole change turns on.

### A page that will not parse is "could not determine", not "detail missing"

Because the translation signal exists only on the HTML page, a parse failure is
not a cosmetic loss — it means the translation question cannot be answered at
all. The page is therefore on the critical path for that part of the answer, and
a parse failure must be reported as "not determined" (non-zero), never folded
into "nothing new". The template part, read from the stable API, can still be
reported when the page fails.

The row parser is an `html.parser.HTMLParser` subclass keyed on the anchors the
page already emits — the per-language `…/<lang>/+translate` link, plus the
optional `+translate?show=untranslated` and `+translate?show=new_suggestions`
links — not on presentational class names. When even those are absent, parsing
yields nothing and the run is "not determined".

### No new dependencies

The tool uses `urllib.request`, `json`, `html.parser` and `argparse` from the
standard library.

- *Rejected — `requests` and `beautifulsoup4`.* They would be dev-only
  dependencies, but adding a dependency is itself a spec-worthy change and
  `AGENTS.md` prefers what the distributions already ship. The standard library
  is sufficient for two GETs and a table of anchors.

### URLs are overridable, so tests never touch the network

`--api-url` and `--html-url` default to the live endpoints but accept any URL,
including `file://`. Tests drive the script as a subprocess over `file://`
fixtures, matching how `dev/release.py` is tested, and requiring no HTTP server
or mocking framework. This also makes the tool usable offline against a captured
page.

### Notification is one idempotent issue, not a failed job

The weekly workflow opens or updates a single labelled issue rather than failing
the scheduled run.

- *Rejected — fail the scheduled job.* It turns GitHub's failure notification
  into the signal, which mails the last committer on every run until the
  baseline moves and produces an undifferentiated red mark. A failed run is
  reserved for "could not determine", which genuinely needs attention.
- *Rejected — write only to the run summary.* A summary is easy to miss
  entirely; an issue is where a pending task belongs.

The workflow searches for an open issue carrying a dedicated label and creates
or updates it, so a change produces one living reminder rather than one per run.
A "could not determine" run fails the job instead.

### Requests are identified and bounded

Every request sends a descriptive `User-Agent` naming the project. A run makes
exactly one page request and one conditional API request — two requests, always.
This respects the service and the `robots.txt` posture; the tool is a
well-behaved client, not a crawler, and never uses a blocked agent identity.

## Risks / Trade-offs

- **The HTML page is on the critical path and is not a contract.** A Launchpad
  redesign can break the translation answer. → Contained by the
  "could not determine" rule: the failure is loud (non-zero, a failed workflow
  run) rather than a silent all-clear, and the template part is still reported.
- **Every run transfers the full ~76 KB page.** There is no conditional or
  incremental form. → Accepted: one request of that size, weekly, is negligible
  and gentle; the alternative (44 per-file API requests) is worse.
- **The API's `devel` version can change.** If a field the template trigger
  relies on disappears, that part cannot be determined. → Treated as "could not
  determine" (non-zero), so a broken check is loud rather than a silent
  all-clear.
- **The baseline can go stale if `--update` is forgotten.** → It fails safe:
  the tool keeps reporting the change, and the fix is the one command it prints.
- **Issue noise.** A single issue updated in place, not one per run, keeps the
  tracker quiet. The label makes it filterable and closable.
- **Scheduled workflows are best-effort on GitHub** (they can be delayed, and
  are disabled after long repository inactivity) and Launchpad can be
  unreachable. → The check is one of several release reminders, not the gate;
  the existing workflows already guard on Launchpad reachability, and the manual
  release procedure is unchanged.
- **A change to the message set fires the check**, so a new `.pot` uploaded
  because of a source edit is itself reported. → Accepted: that upload is a real
  upstream event, and `--update` clears it in the same release cycle.
