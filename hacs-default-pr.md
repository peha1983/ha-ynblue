## Context

This repository provides a Home Assistant integration for YNEOM's YnBlue connected pool controllers. YnBlue is a cloud-connected pool automation and water-treatment platform with automated filtration, pH correction, chemical treatment management, alerts, and optional connected equipment such as heating, lighting, robotic cleaners, and auxiliary relays. Upstream product references: <https://www.yneom.com/en/connected-pool/>, <https://www.yneom.com/en/faq/>, and <https://www.yneom.com/en/ynblue-app/>.

The integration exposes those controller capabilities in Home Assistant as native entities for telemetry, online state, freshness, setpoints, modes, and supported equipment controls. It uses the official YnBlue cloud REST and MQTT endpoints and ships local brand assets in `custom_components/ynblue/brand/`.

## Checklist

- [x] I've read the [publishing documentation](https://hacs.xyz/docs/publish/start).
- [x] I've added the [HACS action](https://hacs.xyz/docs/publish/action) to my repository.
- [x] (For integrations only) I've added the [hassfest action](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) to my repository.
- [x] The actions are passing without any disabled checks in my repository.
- [x] I've added a link to the action run on my repository below in the links section.
- [x] I've created a new release of the repository after the validation actions were run successfully.

## Links

Link to current release: <https://github.com/peha1983/ha-ynblue/releases/tag/v0.3.1>
Link to successful HACS action (without the `ignore` key): <https://github.com/peha1983/ha-ynblue/actions/runs/27900866365>
Link to successful hassfest action (if integration): <https://github.com/peha1983/ha-ynblue/actions/runs/27900866365>

Note: `home-assistant/brands` no longer accepts custom integration brand pull requests. This repository therefore ships local brand assets in `custom_components/ynblue/brand/`.
