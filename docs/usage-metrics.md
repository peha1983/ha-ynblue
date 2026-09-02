# Usage Metrics And Measurement Limits

YnBlue does not collect product telemetry. HACS and Home Assistant also do not expose an exact count of distinct YnBlue users.

## What the package counter measures

Starting with the ZIP tracking activation, every release contains one canonical asset named `ynblue.zip`. HACS downloads that file for an installation, update, or redownload. GitHub's release-asset `download_count` is therefore a package-request proxy, not a count of people or active installations.

The counter has these limits:

- one user can generate multiple requests through updates or redownloads
- a direct GitHub download is counted even when HACS did not request it
- users who remain on an older release are represented by that release's counter
- source installs from before ZIP tracking cannot be reconstructed
- uninstallations are not observable

Home Assistant's public custom-integration analytics can provide a separate active-installation signal only for installations that opt in to usage analytics. It does not distinguish HACS from manual installations.

## Baseline: June 4 To September 2, 2026

The first 90-day baseline predates the package counter, so it uses only weak public signals:

- YnBlue [entered the default HACS catalog](https://github.com/hacs/default/pull/7723) on July 2 and was [first seen by the independent hacs-stats crawler](https://hacs-stats.dev/r/peha1983/ha-ynblue) on July 3.
- Two releases were published during the window: [v0.3.1](https://github.com/peha1983/ha-ynblue/releases/tag/v0.3.1) on June 21 and [v0.3.2](https://github.com/peha1983/ha-ynblue/releases/tag/v0.3.2) on August 30.
- One external user [explicitly reported](https://github.com/peha1983/ha-ynblue/issues/1) an YnBlue 0.3.1 installation from a HACS custom repository. This proves at least one external HACS installation but not the total.
- That report identified a login deadlock; v0.3.2 fixed it, and the issue was closed on September 2.
- At the end of the window the repository had zero stars, forks, and subscribers.
- GitHub's owner-only traffic window covered only August 19 through September 1: 51 clone events from 10 unique cloners, one repository view, and no external referrer. Clone activity is not equivalent to HACS package downloads and may include development or automation.
- [Home Assistant's public custom-integration analytics](https://analytics.home-assistant.io/custom_integrations.json) had no `ynblue` record on September 2.

The defensible conclusion is that external adoption exists but is still early and too weakly instrumented to calculate a 90-day install total or growth rate. Do not extrapolate the 14-day clone figures into a 90-day installation estimate.

## Maintainer checks

List the package counter for every release:

```bash
gh api 'repos/peha1983/ha-ynblue/releases?per_page=100' \
  --jq '.[] | {tag: .tag_name, package_requests: ([.assets[] | select(.name == "ynblue.zip") | .download_count] | first // 0)}'
```

Check the opt-in Home Assistant active-installation signal:

```bash
curl -sS https://analytics.home-assistant.io/custom_integrations.json | jq '.ynblue // "not listed"'
```

Check the short GitHub traffic window available to repository owners:

```bash
gh api repos/peha1983/ha-ynblue/traffic/clones
gh api repos/peha1983/ha-ynblue/traffic/views
gh api repos/peha1983/ha-ynblue/traffic/popular/referrers
```

For release reporting, keep package requests, opt-in active installations, confirmed external issue reporters, and repository engagement as separate metrics. Combining them into a single "users" number would overstate confidence.
