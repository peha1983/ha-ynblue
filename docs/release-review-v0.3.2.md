# Technical release review: YnBlue v0.3.2 candidate

Review date: 2026-08-30

## Executive thesis

The v0.3.2 candidate is technically sound for review: the login deadlock has a minimal lock-boundary fix, repeated timeout warnings are bounded without losing first-failure/reminder/recovery transitions, controller identifiers are removed from known runtime warning/error paths, and HACS/version documentation is internally consistent. Publication still depends on remote validation of the exact release commit.

## Validated strengths

- Authentication validation no longer calls an auth-taking account request while holding the authentication lock.
- Metadata failures retain cached device data; snapshot failures retain the existing retry backoff and freshness/availability semantics.
- Warning suppression is stateful, per controller where applicable, and reset by successful recovery.
- Runtime log labels and diagnostics mapping keys no longer expose cloud controller identifiers; API errors no longer include vendor response bodies.
- The Home Assistant compatibility strategy has two explicit lanes: the live-validated 2026.6.4 minimum and the 2026.8.1 login-regression basis.
- Manifest version, changelog, release notes and HACS minimum are aligned for v0.3.2.
- The default HACS catalog contains `peha1983/ha-ynblue`; a full GitHub release tagged `v0.3.2` is the intended upgrade source.

## Findings and conditions

### P2 — exact-commit remote validation is outstanding

Publication is authorized, but GitHub Actions cannot run both test lanes, hassfest and repository validation against the exact release commit until that commit is pushed. Any earlier green run against unchanged remote `main` is not candidate evidence.

Required action: run `Validate` on the exact release commit and require all jobs to pass before tagging or creating the GitHub release.

### Closed — minimum-version automation passed locally

The published test helper for Home Assistant 2026.6.4 is pinned in the new CI lane. Its isolated local lane passed all 34 tests, complementing the completed redacted live smoke test on Home Assistant 2026.6.4. The exact automated remote lane remains a release gate.

### P2 — HACS container validation is outstanding for the candidate

The local HACS action container was not executed with its mutable remote `main` tag and a writable full-workspace mount. Safe static alternatives passed: JSON/YAML parsing, required manifest/HACS fields, one-integration repository layout, version/minimum consistency, default-catalog membership and release-path review.

Required action: require the remote HACS job and verify HACS discovers `v0.3.2` after the GitHub release is created.

### P3 — destructive timeout simulation remains unperformed live

The live gate did not deliberately force an offline or transport-timeout incident. Cached-state behavior, retry backoff, warning suppression and redaction are covered by automated tests, and historical evidence supports the fallback behavior. Monitor the first post-release real timeout/recovery cycle for the intended warning cadence.

## Release and rollback

- Publish only from the exact commit that passes all remote gates.
- Create a full GitHub release tagged `v0.3.2`; a tag alone is insufficient for the intended HACS path.
- If a release regression occurs, reinstall the previously published v0.3.1 release and restart Home Assistant. Existing config-entry data is unchanged by v0.3.2.

## Release posture

**ready with conditions**

Conditions: exact-commit remote matrix/hassfest/HACS validation must pass, then the published `v0.3.2` release must be observed by HACS. No evidence currently justifies publishing before those gates.
