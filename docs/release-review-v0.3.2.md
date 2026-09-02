# Technical post-release review: YnBlue v0.3.2

Review date: 2026-09-02

## Executive thesis

YnBlue v0.3.2 is publicly released and the post-release gates are complete. The
published release is anchored to the exact validated commit, all main, tag and
scheduled validation runs through the review date are green, HACS distribution
is confirmed, and a production HACS installation passed live acceptance. No
P0, P1 or P2 release blockers remain.

## Publication and artifact integrity

- The full [GitHub release](https://github.com/peha1983/ha-ynblue/releases/tag/v0.3.2)
  was published as `v0.3.2`; it is neither a draft nor a prerelease.
- The `v0.3.2` tag peels to release commit
  `dc867d3971ebad815b7ccb30ee3c2226dbb7a79f`.
- The release commit was the exact `origin/main` commit validated before
  publication. The post-release documentation cleanup does not move or replace
  the release tag.
- Manifest version, changelog, release notes and HACS compatibility metadata
  remain aligned with v0.3.2.

## Validation evidence

- The `Validate` workflow passed on the release commit for both the `main` push
  and the `v0.3.2` tag push.
- Both exact-commit runs completed all four required jobs successfully: Home
  Assistant 2026.6.4 tests, Home Assistant 2026.8.1 tests, hassfest and HACS
  validation.
- Daily scheduled `Validate` runs on the release commit remained green through
  2026-09-02.
- The default HACS integration catalog contains `peha1983/ha-ynblue`, and HACS
  resolves the published v0.3.2 release as the stable installation source.
- v0.3.2 was installed from HACS on a production Home Assistant system and
  passed live acceptance. No household data, credentials or controller
  identifiers are retained in this review.

## Release safety and rollback

- Operational backups and the rollback path were checked as part of release
  acceptance.
- If a regression is discovered, reinstall the previously published v0.3.1
  release through HACS and restart Home Assistant. v0.3.2 introduced no config
  entry migration, so existing account configuration and entities are retained.
- The login deadlock fixed in v0.3.2, timeout handling, warning throttling,
  recovery transitions and identifier redaction are covered by automated tests.
- There are no open P0, P1 or P2 findings blocking continued use of v0.3.2.

## Monitor later

The production acceptance did not deliberately force a destructive controller
offline or transport-timeout incident. Automated coverage validates cached
state, retry backoff, bounded warning cadence, identifier redaction and recovery
transitions. Monitor the next naturally occurring timeout/recovery cycle to
confirm the same behavior in production; this is an operational observation,
not a release blocker.

## Release posture

**technically credible**

Publication, distribution, automated validation, production installation and
rollback readiness are complete. Routine monitoring is the only remaining
post-release activity.
