# Release Process

This repository is distributed to Home Assistant users through GitHub releases and HACS.

## Release checklist

1. Confirm the working tree is clean.
2. Update documentation if user-visible behavior changed.
3. Run local validation:

   ```bash
   ./.venv/bin/ruff check .
   ./.venv/bin/pytest
   ```

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
- local: `./.venv/bin/ruff check .`, `./.venv/bin/pytest`
- GitHub Actions: `Validate` green on the release commit
```
