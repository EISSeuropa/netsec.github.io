# Contributing to NetSec

Thanks for considering a contribution to the website of COST Action
CA24154 (NetSec). This page points you at
the right channel depending on what you want to do. The fastest path is almost always one of the first three sections below.

## I have a question or want to get in touch

Use the public contact form on the live site:
**<https://netsec-cost.eu/#contact>**. It reaches the Action
mailbox and is the right path for anything that isn't a bug report
or a feature suggestion.

For specific common questions (grants, STSMs, ITC eligibility,
meeting cadence), the FAQ at <https://netsec-cost.eu/faq.html>
covers most of them.

If you're a Management Committee representative or a Working Group
participant, the members' Wiki at
<https://github.com/EISSeuropa/netsec.github.io/wiki> has the
internal context (decisions log, meetings index, onboarding).

## I want to suggest a new feature or improvement

Open a GitHub issue via the **enhancement** template:
<https://github.com/EISSeuropa/netsec.github.io/issues/new?template=enhancement.yml>.

The form asks four short questions: what's happening, why it
matters, a fix path (no need for full code — a paragraph is fine),
and target. The maintainer triages weekly. Cross-cutting
suggestions that overlap with the EISS website also land in the
joint Project at
<https://github.com/users/EISSeuropa/projects/1>.

## I found a bug

Open a GitHub issue via the **bug report** template:
<https://github.com/EISSeuropa/netsec.github.io/issues/new?template=bug_report.yml>.
A screenshot or a console-error paste helps a lot. The form has
preflight checkboxes that prompt for the usual reproduction
details (browser, OS, what you expected vs. what happened).

## I found a typo or wrong information

Two paths, in increasing order of effort:

1. **Easiest** — open the **documentation** issue template
   (<https://github.com/EISSeuropa/netsec.github.io/issues/new?template=documentation.yml>)
   and paste the URL + the correction.
2. **If you're comfortable with git** — open a pull request
   editing the relevant `.html` file directly. The diff for a
   typo or a fact correction is usually one line.

## I want to translate or improve the French / German pages

The site is trilingual: EN (authoritative) + FR + DE (manual
translations marked as *beta*). Machine translation is explicitly
not used (see [CLAUDE.md §1](CLAUDE.md#1-language--translation)).

If you're a native or near-native FR / DE speaker and want to help
lift either pair out of beta, open an enhancement issue with the
URLs of the pages you've reviewed and any specific phrasing
recommendations. Direct PRs with translation improvements are
welcome too — see the next section for the file conventions.

## I want to contribute code

Read [`docs/architecture.md`](docs/architecture.md) first — it
covers the tech stack (no framework, no build step, vanilla
browser APIs), the data flow (cost.eu sync, Google Form sync,
Indico sync), and where each page's logic lives.

Then a few house rules:

- **No emojis in source files** unless explicitly asked. The site
  has its own visual language; emoji noise undermines it.
- **British English** in all user-facing copy. The maintainer is
  Swiss-based and the audience is European (COST evaluators,
  journalists, MC representatives, members across 30+ countries).
- **Voice rules**: no em-dashes in prose, no rule-of-three rhythm
  for cadence, no synonym cycling for the same referent. See
  [CLAUDE.md §7](CLAUDE.md#7-prose-voice-em-dashes-and-ai-patterns)
  for the full pattern.
- **Per-PR CHANGELOG entry**: every PR that ships a user-visible
  change adds a bullet under `[Unreleased]` in
  [`CHANGELOG.md`](CHANGELOG.md). The PR description should also
  explain *why*, not just *what*.
- **CI must be green before merge**: link checker, CodeQL, drift
  checkers (calendar, news, i18n). Auto-merge holds the merge
  until CI is green; opening a PR with a known break wastes
  everyone's time.
- **Squash, not merge commits**: every PR ends as a single commit
  on `main`.

The maintainer's full operating rules are in
[`CLAUDE.md`](CLAUDE.md) at the repo root. That file is
maintainer-facing rather than contributor-facing, but skim it if
you want context for why the codebase looks the way it does.

## Code of conduct

Treat each other well. Use the [COST gender-equality
plan](https://www.cost.eu/about/strategy/excellence-and-inclusiveness/)
as the underlying expectation. The maintainer reserves the right
to close issues or refuse PRs that don't follow it.

## Where this file fits

This file is the front door. Once you're in, the navigation is:

| Where | What |
| --- | --- |
| [`README.md`](README.md) | What the project is, who it's for, where to read about it |
| [`CHANGELOG.md`](CHANGELOG.md) | What's shipped per release |
| [`CLAUDE.md`](CLAUDE.md) | Maintainer operating rules |
| [`docs/architecture.md`](docs/architecture.md) | Tech stack, data flow, where things live |
| [`docs/admin-guide.md`](docs/admin-guide.md) | Day-to-day maintainer procedures |
| [`docs/roadmap-2026.md`](docs/roadmap-2026.md) | Planning context |
| [`/roadmap.html`](https://netsec-cost.eu/roadmap.html) | Public roadmap (rendered view of the above) |
| Wiki | Members' internal context (decisions, meetings, onboarding) |

Thanks for being here.
