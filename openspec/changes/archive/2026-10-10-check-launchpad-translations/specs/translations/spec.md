## ADDED Requirements

### Requirement: Upstream changes are detected against a baseline
The project SHALL provide a check that compares the current public Launchpad
state of the `scantpaper` translation template, and of each of its languages,
against a committed baseline, and reports every unit that has changed since the
baseline was last advanced. The check SHALL NOT authenticate to Launchpad, and
SHALL NOT attempt to download any translation catalog, because Launchpad
requires a logged-in session to export a catalog.

The check SHALL detect two independent triggers, each read from the only public
surface that carries it:

- the **template** (the message set), from the Launchpad JSON API resource for
  the translation template, using the template's `date_last_updated` and its
  HTTP entity tag, with a conditional request so that an unchanged template is
  detected without transferring a response body;
- **per-language translation activity**, from the public series translation
  page, whose per-language last-changed timestamps exist on no other public
  surface. This page SHALL be read on every run, because a translation can
  change without the template changing.

The baseline SHALL record the values Launchpad reported at the last sync, and
SHALL be advanced only by a distinct, explicit action, so that it continues to
represent the upstream state the catalogs were last synced from rather than the
latest state observed.

#### Scenario: The message set changed
- **WHEN** the template's entity tag or `date_last_updated` differs from the
  baseline and the series translation page is readable
- **THEN** the check reports that the template changed and exits successfully

#### Scenario: A translation changed but the template did not
- **WHEN** the template's entity tag matches the baseline but a language's
  last-changed time on the series translation page is newer than that language
  in the baseline
- **THEN** the check reports that language as changed, with its new
  untranslated and unreviewed counts, and exits successfully

#### Scenario: Nothing changed
- **WHEN** the template matches the baseline and every language's last-changed
  time equals its value in the baseline
- **THEN** the check reports that there is nothing new and exits successfully

#### Scenario: A new language appears
- **WHEN** the series translation page lists a language that is absent from the
  baseline
- **THEN** the check reports that language as new

#### Scenario: No catalog is downloaded
- **WHEN** the check runs, whether or not a change is detected
- **THEN** it sends no request to any Launchpad catalog export endpoint and
  provides no credentials

#### Scenario: Baseline is advanced only when asked
- **WHEN** the check runs without the explicit baseline-advancing option and a
  change is present
- **THEN** the committed baseline is left unchanged and the next run reports the
  same change again

#### Scenario: Baseline is advanced after a sync
- **WHEN** the check runs with the explicit baseline-advancing option after the
  catalogs have been synced
- **THEN** the baseline records the current template and per-language values,
  and a subsequent run reports that there is nothing new

### Requirement: Undetermined state is distinct from unchanged
The check SHALL NOT report a unit as unchanged unless it actually read that
unit's current state. When it cannot determine a unit's state — because a
request failed, the API returned an unexpected shape, or the series translation
page could not be parsed into language records — it SHALL report that unit as
not determined and SHALL exit non-zero, which is distinguishable from both
"changed" and "unchanged". A unit that could be read SHALL still be reported.

The check SHALL NOT be wired into the release gate: the default exit SHALL be
successful when the state was read, whether or not a change was found. CI MAY
request a non-zero exit on change through an explicit option.

Requests issued by the check SHALL identify the tool with a descriptive
`User-Agent` and SHALL be limited to those needed to answer the question: one
request to the API for the template and one to the series translation page.

#### Scenario: The series translation page cannot be parsed
- **WHEN** the template read succeeds but the series translation page's
  structure no longer matches what the parser expects
- **THEN** the check reports the template result, reports the per-language
  detail as not determined, and exits non-zero

#### Scenario: The API cannot be read
- **WHEN** the API request fails, times out, or returns an unexpected shape
  such that the template state cannot be determined
- **THEN** the per-language result is still reported and the check exits
  non-zero

#### Scenario: Undetermined state does not advance the baseline
- **WHEN** the check is asked to advance the baseline but any part of the state
  could not be determined
- **THEN** it refuses and leaves the baseline unchanged

#### Scenario: A change does not fail the default run
- **WHEN** the check detects that a change occurred and is run without the
  explicit fail-on-change option
- **THEN** it prints its report and exits successfully

#### Scenario: Explicit fail-on-change
- **WHEN** the check is run with the fail-on-change option and a change is
  detected
- **THEN** it exits non-zero, and when no change is detected it exits zero

#### Scenario: Requests are identified and bounded
- **WHEN** the check runs
- **THEN** each request carries a `User-Agent` naming the tool, and the run
  issues exactly one API request and one translation-page request
