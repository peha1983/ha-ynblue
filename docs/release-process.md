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
8. Build and inspect the HACS package locally:

   ```bash
   bash scripts/build-hacs-zip.sh
   unzip -l dist/ynblue.zip
   ```

9. Create a GitHub release with structured notes. Publishing the release triggers `Publish HACS package`, which validates the tag against the integration manifest and attaches `ynblue.zip`.
10. Confirm that the release contains exactly one `ynblue.zip` asset and that its contents start with `manifest.json`, `__init__.py`, and the other integration files rather than a wrapper directory.
11. Verify HACS sees and can install the new version.

## One-time ZIP tracking activation

The release workflow measures only package requests made after a release asset exists. Before the `zip_release` and `filename` settings in `hacs.json` are published to `main`:

1. Run `bash scripts/build-hacs-zip.sh /tmp/ynblue.zip` on the v0.3.2 code.
2. Confirm that `custom_components/ynblue` is unchanged from the v0.3.2 tag.
3. With explicit release approval, attach `/tmp/ynblue.zip` to the existing v0.3.2 GitHub release.
4. Verify a clean HACS installation of v0.3.2 from that asset.
5. Only then publish the new HACS manifest and release workflow.

This ordering prevents HACS from looking for `ynblue.zip` before the current release provides it. Historical source installs remain uncounted.

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
