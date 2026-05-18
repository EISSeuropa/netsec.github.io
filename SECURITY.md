# Security Policy

This repository hosts the public website of **COST Action CA24154 —
Networking European Security Knowledge (NetSec)**, served at
<https://netsec-cost.eu>. It is a static [GitHub Pages](https://pages.github.com/)
site with two scheduled Python sync jobs and one third-party form
processor. We take its security seriously and welcome reports.

## Scope

| In scope                                                            | Out of scope                                                                                |
| ------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| The current `main` branch of this repository                        | Older branches, tags, or forks                                                              |
| The deployed site at <https://netsec-cost.eu> and `*.github.io` URL | Third-party services we rely on — please report to them directly                            |
| The two GitHub Actions in `.github/workflows/`                      | Reports about COST or EU branding, funding statements, or visual identity                   |
| The Python sync scripts in `scripts/`                               | Theoretical issues that depend on a compromised contributor account or repo write access    |
| `data/bios.json`, `data/mc-members.json`, and any personal data     | Volumetric DoS against COST, the EU, GitHub, or Formspree                                   |

Third-party services in our stack — please report to the relevant
vendor rather than to us:

- **GitHub** (hosting, Pages, Actions) — <https://github.com/security>
- **Formspree** (contact-form processing) — <https://formspree.io/security/>
- **Google** (Forms + Sheets used for the bios pipeline) —
  <https://www.google.com/about/appsecurity/>
- **FlagCDN**, **Google Fonts** (passive CDN assets)

## Reporting a vulnerability

**Please do not open a public GitHub issue or pull request.** Two
private channels are available:

1. **GitHub Security Advisories** (preferred) —
   <https://github.com/EISSeuropa/netsec.github.io/security/advisories/new>.
   This is encrypted, lets us collaborate on a fix in a private fork,
   and gives you a CVE if appropriate.
2. **Email** — Dr Arthur Laudrain (site maintainer, MC member CH):
   ETH Zurich CSS, see <https://css.ethz.ch>. For data-protection
   matters specifically, contact the Data Controller (Universiteit
   Leiden) via the addresses listed in §1 of our
   [Privacy Notice](https://netsec-cost.eu/privacy.html).

When reporting, please include:

- a description of the issue and its impact;
- the URL or file path where you observed it;
- the steps needed to reproduce it (a minimal proof-of-concept is
  ideal, but not required);
- any suggested remediation, if you have one.

## What to expect from us

- **Acknowledgement**: within **5 working days** of your report.
- **Initial assessment**: within **14 working days** — we will tell
  you whether we accept the finding, need more information, or
  consider it out of scope, and we will share an indicative timeline.
- **Resolution**:
  - *Critical* (data exposure, account takeover, XSS with credential
    leakage): patch in days, hotfix deployed via a PR to `main`.
  - *High / Medium*: patch in the next sprint of work, typically two
    to four weeks.
  - *Low / informational*: rolled into routine maintenance.
- **Disclosure**: coordinated. We will not publicly discuss the
  vulnerability until a fix is deployed. We are happy to credit you
  in the resolving PR and in the GitHub Security Advisory unless you
  prefer to remain anonymous.

## Safe harbour

If you make a good-faith effort to comply with this policy when
researching and reporting an issue, we will:

- not pursue or support any legal action against you;
- work with you to understand and resolve the issue quickly;
- recognise your contribution publicly if you wish.

Good-faith research means: only acting against your own data and the
public website, avoiding privacy violations and service disruption,
not retaining personal data of others, and giving us reasonable time
to fix the issue before any public disclosure.

## What we do on our side

A short list of the security hygiene we maintain on this repository:

- **Dependencies**: Python dependencies in `scripts/requirements.txt`
  are pinned with version bounds and monitored by GitHub Dependabot.
- **Secrets**: no production credentials live in the repo. The Google
  Forms / Sheets pipeline uses **public** published-to-web CSV URLs
  and a public Forms URL; the contact form uses a Formspree project
  ID, which is a public identifier and rate-limited at the vendor.
- **GitHub Actions**: all third-party actions are pinned by full
  commit SHA where reasonable, and Action permissions follow the
  principle of least privilege (`contents: write` only on the
  PR-opening step).
- **Personal data**: handled per the
  [Privacy Notice](https://netsec-cost.eu/privacy.html). Submitters
  can ask for changes or removal at any time and we maintain a soft
  PR-review workflow before any new bio appears on the public site.
- **Content-Security-Policy**: the site loads no inline analytics,
  no advertising, and no third-party tracking pixels. External
  assets are limited to Google Fonts, FlagCDN, and the Formspree
  endpoint; see `privacy.html` for the full list.

Thank you for helping keep NetSec safe.
