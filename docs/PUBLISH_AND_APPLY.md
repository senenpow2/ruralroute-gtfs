# Publish this project and build a credible Codex for OSS application

This repository was built as a **starting point**, not as proof of widespread
adoption. The official programme assesses the **maintainer's work and the
project's real ecosystem role**, not simply how many files it contains.

Official pages (check current terms before applying):
- https://developers.openai.com/community/codex-for-oss
- https://openai.com/form/codex-for-oss/
- https://learn.chatgpt.com/docs/codex-for-oss-terms

## One-time publish on GitHub

The intended repository URL is `https://github.com/senenpow2/ruralroute-gtfs`.
This URL **will not exist** until the repository is created and pushed.

1. Log into GitHub as `senenpow2` and create a **public**, *empty* repository
   called `ruralroute-gtfs`. Do **not** initialise a README or license in the
   GitHub wizard: the project already contains both.
2. On Windows, extract the downloaded ZIP and open PowerShell inside the
   extracted `ruralroute-gtfs` folder.
3. Install [Git for Windows](https://git-scm.com/downloads/win) if `git` isn't
   already installed, then run:

```powershell
git init -b main
git add .
git commit -m "feat: initial offline GTFS return-trip audit toolkit"
git remote add origin https://github.com/senenpow2/ruralroute-gtfs.git
git push -u origin main
```

Authenticate GitHub in the browser when Git prompts. Never place a personal
access token into the repository, terminal history or chat messages.

## Verify publication

- Check that `https://github.com/senenpow2/ruralroute-gtfs` exists and is public.
- Open the **Actions** tab: CI should run the tests across Python 3.10–3.13.
- Run the demo yourself and check that the results agree with the fictional GTFS data.
- Open **Settings → General** and add a clear project description and relevant topics:
  `gtfs`, `public-transport`, `open-source`, `rural-transport`, `python`, `civic-tech`.
- Add a first tagged `v0.1.0` release only after CI passes.

## The serious work that makes this eligible

The project is presently a functioning **prototype**, not yet a widely used
public-good dependency. Do not fabricate stars, download figures, users or
commits. A stronger application will demonstrate:

1. A reproducible case study using a legitimately reusable **real** GTFS feed,
   with provider acknowledgement, data license and known limitations.
2. At least one third-party user (researcher, council, event organiser, transit
   advocacy group) who found the audit genuinely helpful; obtain permission
   before naming them.
3. Ongoing maintenance: issues triaged, well-reviewed contributions, bugfix
   releases, security responses and documented decisions.
4. A responsible plan for data correctness; the tool must not promise travellers
   a ride merely because a timetable contains a connection.
5. A real maintenance task where Codex would help (regression tests for GTFS
   corner cases, code review, PR triage or release automation).

Once evidence exists, apply via the official form. Selection is **not** guaranteed.

## Draft application responses (revise and verify before submitting)

**Role:** Primary maintainer (only if you do actually publish and maintain it).

**Why this repository qualifies** (under 500 characters):

> I maintain RuralRoute GTFS, an MIT-licensed offline tool for identifying public
> transport return-journey gaps from GTFS timetable data. It supports service-day
> calendars, multi-vehicle journeys and batch evidence reports without paid APIs.
> The aim is to help rural transport researchers and community groups investigate
> missing evening connections. [Add verifiable links to real usage, integrations
> and maintainer activity here before applying.]

**How API credits would be used** (only if requesting credits):

> I would use credits for open-source maintenance workflows: reviewing GTFS
> parser changes, generating regression-test suggestions for timetable edge
> cases, triaging bug reports and reviewing contributor pull requests. Sensitive
> or private travel data would not be sent to third-party services without
> appropriate authorization.

Do not claim selected benefits, broad adoption, independent contributors or
completed maintenance tasks if they do not exist. OpenAI may request evidence.
