# Release Process

This repository is distributed to Home Assistant users through GitHub releases and HACS.

YnBlue has been listed in the default HACS integration catalog since July 2, 2026. New versions still become available to users only after a matching GitHub release is published.

## Release checklist

1. Confirm the working tree is clean.
2. Update documentation if user-visible behavior changed.
3. Run local validation:

   ```bash
   ./.venv/bin/ruff check .
   ./.venv/bin/pytest
   ```

   The workflow runs two Python 3.14 compatibility lanes:

   - `requirements_test_ha_2026_6.txt` pins the published helper for Home Assistant 2026.6.4, the live-validated minimum.
   - `requirements_test.txt` pins the helper commit for Home Assistant 2026.8.1, the reported login-regression basis.

   Keep both requirements files, workflow matrix, `hacs.json`, and user-facing support claims aligned when updating either baseline. A live smoke test on an intermediate version complements but does not replace automated regression coverage.

4. Push the change to `main`.
5. Confirm the GitHub `Validate` workflow is green on the exact release commit.
6. Update `custom_components/ynblue/manifest.json` version if needed.
7. Update `CHANGELOG.md`.
8. Create a GitHub release with structured notes.
9. After release, verify HACS sees the new version.

## Release note structure

Use these sections in every release:

- Added
- Changed
- Fixed
- Breaking changes
- Upgrade notes
- Validation

## Upgrade-note rules

Include explicit upgrade notes when:

- an entity is renamed or removed
- command behavior changes
- minimum Home Assistant version changes
- diagnostics or stale-state semantics change in a way users may notice

## Example release note skeleton

```markdown
## Added
- ...

## Changed
- ...

## Fixed
- ...

## Breaking changes
- None

## Upgrade notes
- Restart Home Assistant after upgrading.
- Reload the YnBlue config entry if entities were previously stale.

## Validation
- local/current: `./.venv/bin/ruff check .`, `./.venv/bin/pytest`
- local/minimum when dependencies are available: install `requirements_test_ha_2026_6.txt`, then run the same commands
- GitHub Actions: both test matrix entries plus HACS and hassfest green on the exact release commit
```
