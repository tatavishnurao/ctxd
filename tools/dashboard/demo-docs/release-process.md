# Release process

Fictional sample content for the ctxd dashboard demo.

## Release cadence

Mobile apps ship every two weeks on Tuesday. The web app and backend services ship continuously from the main branch, several times a day. A release train leaves on schedule: a feature that is not ready waits for the next train instead of delaying everyone else.

## Versioning

Public libraries and the mobile apps use semantic versioning. A major version means a breaking change, a minor version adds features without breaking anything, and a patch version only fixes bugs. Backend services are identified by the commit hash that is deployed, not by a version number.

## Release branches and code freeze

For mobile, the release branch is cut from main on Thursday before the release. After the cut, only fixes for bugs found in that release are cherry-picked onto the branch, each with its own review. New features never go onto a release branch. The release manager for the train approves every cherry-pick.

## Feature flags

Unfinished or risky features ship behind a feature flag that is off by default. Turn a flag on for internal users first, then for 5% of customers, then for everyone. Each flag has an owner and a removal date. Flags older than ninety days are listed in the weekly engineering report until they are removed.

## Release checklist

Before a release goes out, the release manager checks that all tests pass on the release branch, the changelog is written, database migrations are backwards compatible, the support team has the release notes and nobody has an open blocker on the release ticket. The checklist lives in the release ticket so that every step is recorded.

## Staged rollout

Backend changes go to the canary environment first and receive a small share of real traffic for thirty minutes. The deploy tool compares error rate and latency between the canary and the rest of the fleet. If the canary is healthy, the change rolls out to all regions one at a time. Mobile releases use the app stores' phased rollout over seven days.

## Rollback

Any engineer can roll back a backend deploy with one command, without asking for permission first. Roll back first and investigate after. A mobile release cannot be rolled back, so the team halts the phased rollout and ships a patch version. Database migrations must be reversible or split so that the previous version of the code still runs.

## Release notes and communication

Customer-facing changes get a short entry in the public release notes, written in plain language. The support team receives the notes one day before the release. Breaking API changes are announced at least ninety days ahead and listed in the deprecation schedule.
