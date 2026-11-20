# TransIP Dynamic DNS

<p align="center">
  <a href="../../releases/latest"><img src="https://img.shields.io/github/v/release/joohann/transip-DNS?label=release" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2026.10%2B-blue" alt="Home Assistant 2026.10 or later">
  <img src="https://img.shields.io/badge/Marketplace-custom%20repository-blue" alt="Marketplace custom repository">
  <img src="https://img.shields.io/badge/records-A%20%26%20AAAA-green" alt="A and AAAA records">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="MIT license"></a>
</p>

A Home Assistant custom integration that watches your external IP address and keeps your **TransIP** DNS records pointing at it. It authenticates with a TransIP API key pair, checks your address on a schedule, and updates an `A` or `AAAA` record only when the address has actually changed.

<p align="center">
  <img src="docs/demo.gif" width="820" alt="The TransIP DNS panel in Home Assistant: overview, settings and the notify combobox">
</p>

> Unofficial. Not affiliated with or endorsed by TransIP.

## Features

**Keeps DNS in sync**
- `A` and `AAAA` records across as many domains as you like, all in one account
- Only writes to the TransIP API when the address changed, so nothing is touched on a quiet day
- Remembers the last 20 address changes per address family, across restarts

**Its own panel**
- The gear on the integration page opens a full page instead of a dialog, the way ZHA and Z-Wave JS do
- Add, edit and remove records, change the interval, pick notify services, all without leaving the page
- Optional sidebar entry; the panel can be switched off again from inside itself

**Tells you when it changes**
- A persistent notification in Home Assistant
- A `transip_dns_updated` event for your own automations
- A direct message to any `notify.*` service you select

**Entities**
- Current and previous external IPv4 and IPv6, with the time of the change
- One sensor per managed record, carrying its status, its previous address and the last update

## The panel

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/panel-overview-dark.png">
    <img src="docs/panel-overview-light.png" width="860" alt="Panel overview with both address families, the record list and the history">
  </picture>
</p>

Addresses, records and history at a glance. The tiles show what the address is now and what it replaced; each record carries its own status, with **Edit** to load it back into the form and **Remove** to drop it. The history lists every change the integration has seen.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/panel-settings-dark.png">
    <img src="docs/panel-settings-light.png" width="430" alt="The settings dialog with the check interval, notifications and panel options">
  </picture>
  &nbsp;
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="docs/panel-notify-dark.png">
    <img src="docs/panel-notify-light.png" width="430" alt="The notify services combobox with search and custom names">
  </picture>
</p>

Every setting lives in one dialog. Notify services are a combobox with search; typing a name that is not in the list offers to add it, so a service that is not registered yet can still be configured.

## Installation

**Marketplace** (Home Assistant 2026.11 and later, where HACS became part of core)

<a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=joohann&repository=transip-DNS&category=integration"><img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Open your Home Assistant instance and add this repository to the Marketplace."></a>

The button above adds the repository to your Marketplace in one step; then install **TransIP Dynamic DNS** and restart Home Assistant. Or do it by hand:

1. Open the **Marketplace** panel, then the menu, then **Custom repositories**
2. Choose **Add from a GitHub link** and paste `https://github.com/joohann/transip-DNS`, category **Integration**
3. Install **TransIP Dynamic DNS**, then restart Home Assistant

On older versions with HACS installed separately, the same three steps live
under HACS, three dots, **Custom repositories**.

**Manual**

Copy `custom_components/transip_dns` into your `config/custom_components/` folder and restart Home Assistant.

## Setup

First, in the TransIP control panel under **My account → API**:

1. Create a **key pair**. Leave **whitelisted IP** switched **off**: the whole point of this integration is that your IP changes.
2. Copy the complete private key, including the `-----BEGIN PRIVATE KEY-----` and `-----END PRIVATE KEY-----` lines.
3. Make sure the record you want to keep updated **already exists** in the DNS zone. This integration updates the content of an existing record; it never creates one.

Then in Home Assistant: **Settings → Devices & services → Add integration → TransIP Dynamic DNS**, paste your login and private key, and add your first record.

## Options

Open them with the gear on the integration page. With the panel switched on, that gear opens the panel; with it off, you get the usual options dialog.

| Setting | Default | Notes |
| --- | --- | --- |
| Records | the one you added during setup | domain, subdomain and type per record |
| Check interval | 10 minutes | 2 to 1440 |
| Persistent notification | on | shown in Home Assistant when a record is updated |
| `transip_dns_updated` event | on | for your own automations |
| Notify services | none | any `notify.*` service, or a name you type yourself |
| Panel | off | replaces the options dialog with the panel |
| Panel in sidebar | off | the panel stays reachable from the gear either way |

The panel needs Home Assistant **2026.10 or later**, which is when the frontend started honouring `config_panel_domain`. Everything else works on older versions.

## Entities

| Entity | What it holds |
| --- | --- |
| `sensor.<account>_external_ipv4` | the address now, with `previous_ip` and `changed_at` as attributes |
| `sensor.<account>_external_ipv6` | same, for IPv6 |
| `sensor.<account>_previous_external_ipv4` | the address it replaced (diagnostic) |
| `sensor.<account>_previous_external_ipv6` | same, for IPv6 (diagnostic) |
| one sensor per record | its current content, plus `status`, `previous_ip`, `last_updated` and `error` |

Record status is one of `ok`, `updated`, `record_not_found` or `error`. Each domain becomes its own device, under the account.

## Services

```yaml
# Check now instead of waiting for the interval
action: transip_dns.refresh

# Turn the panel off again, for when its JavaScript does not load
action: transip_dns.set_panel_enabled
data:
  enabled: false
```

Both take an optional `entry_id` to limit them to one account.

## Events

```yaml
trigger:
  - trigger: event
    event_type: transip_dns_updated
# event.data: domain, name, type, old_ip, new_ip
```

## Troubleshooting

**The panel stays empty.** Reload the integration and do a hard refresh in the browser; the panel is served with a version based on the file's timestamp, and your tab may still hold the old module.

**I cannot reach the options any more.** With the panel on, it replaces the options dialog. Switch it off inside the panel, or call `transip_dns.set_panel_enabled` with `enabled: false` from Developer tools.

**Record not found.** The record has to exist in the TransIP zone first. Create it once in the control panel with any content; the integration takes it from there.

**An AAAA record while your provider has no IPv6.** The external IPv6 lookup then fails and the whole check fails with it, so your `A` records are not updated that round either. Remove the `AAAA` record if you do not actually have IPv6.

## Development

The panel is a plain ES module, no build step. Pure logic lives in modules without Home Assistant imports, so the tests run on their own:

```bash
cd custom_components/transip_dns/tests && python3 -m unittest discover
python3 custom_components/transip_dns/tools/i18n_check.py
```

`tests/panel-harness.html` runs the panel against a mocked Home Assistant with a stand-in sidebar, and `tests/mockup-macbook.html` puts that harness inside the laptop photo. Serve the integration folder over HTTP and open them; ES modules do not load over `file://`.
