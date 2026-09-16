# Rotherham Bins for Home Assistant

A custom Home Assistant integration that exposes upcoming Rotherham bin collections as sensors.

This integration uses the reverse-engineered, undocumented API used by the Rotherham Bins application. It is not affiliated with or endorsed by Rotherham Council, Bartec Municipal Technologies, or Home Assistant. The service may change, become unavailable, or stop returning data without notice. Use reasonable polling intervals and do not rely on it for critical services.

## Features

- Configure a property by postcode and address selection, or by entering a Premise ID manually.
- A next-collection sensor for the property.
- Separate sensors for each bin type returned by the API, such as black, pink, and green.
- Address, Premise ID, days remaining, and a compact upcoming schedule in entity attributes.
- Daily refreshes to avoid unnecessary requests to the unofficial service.

## Installation

### HACS custom repository

Once this repository is published on GitHub:

1. Open HACS and choose **Integrations**.
2. Open the three-dot menu and choose **Custom repositories**.
3. Add this repository URL and choose **Integration**.
4. Install **Rotherham Bins** and restart Home Assistant.
5. Add **Rotherham Bins** from **Settings > Devices & services > Add integration**.

This repository is currently being developed locally. Until it is public, use the manual method below.

### Manual installation

1. Copy the `custom_components/rotherham_bins` directory into the `custom_components` directory of your Home Assistant configuration directory.
2. Restart Home Assistant.
3. Add **Rotherham Bins** from **Settings > Devices & services > Add integration**.

The installed layout must be:

```text
/config/custom_components/rotherham_bins/manifest.json
```

## Configuration

The setup flow offers two choices:

- **Look up an address by postcode**: enter a postcode and select the matching property.
- **Enter a Premise ID manually**: useful if you already know the Premise ID from a postcode lookup or another Rotherham Bins client. Enter a descriptive address name and optional postcode as well.

One Home Assistant config entry represents one property. Add another config entry if you want to monitor another property.

## Entities

Entity names are based on the configured address. The exact entity IDs can be checked under **Settings > Devices & services > Rotherham Bins**.

- **Next collection**: the next collection date for any bin type.
- **`<bin type> collection`**: the next date for each bin type returned by the service.

Entity attributes include:

- `bin_type` for the next collection represented by that entity
- `days_until_collection`
- `address`
- `postcode`
- `premise_id`
- `local_authority`
- `upcoming_collections`, containing up to ten future `{date, bin_type}` entries

The API returns labels such as `BLACK BIN`, `PINK BIN`, and `GREEN BIN`. The integration preserves the normalized label and does not assume that Rotherham will only use these three types.

## Dashboard example

The repository includes [dashboard.example.yaml](dashboard.example.yaml), which contains a complete Lovelace view. It displays the `upcoming_collections` attribute in API order with formatted dates and bin colours/types, followed by the next date for each example bin sensor.

Before importing the view, replace `sensor.rotherham_bins_next_collection` and the example per-bin entity IDs with the entity IDs created for your property. The markdown card remains generic and will show any bin types returned by the API.

## Discord notification automation

Home Assistant's Discord integration must be configured first. Its notification action name depends on the name of the Discord application you create. The current Discord documentation is available at <https://www.home-assistant.io/integrations/discord/>.

Replace these placeholders before saving the automation:

- `notify.home_assistant_notifications` with your actual Discord notification action
- `sensor.rotherham_bins_next_collection` with the next-collection sensor created for your property
- `YOUR_DISCORD_CHANNEL_ID` with the Discord channel ID
- `YOUR_DISCORD_ROLE_ID` with an optional role ID, or remove the mention

This example checks once each morning and sends a message when any bin is collected tomorrow. The bin colour/type is read from the sensor's `bin_type` attribute:

```yaml
alias: Rotherham Bins - Collection tomorrow
description: Notify Discord about tomorrow's bin collection
triggers:
  - trigger: time
    at: "06:00:00"
conditions:
  - condition: template
    value_template: >-
      {% set collection = states('sensor.rotherham_bins_next_collection') %}
      {{ collection not in ['unknown', 'unavailable', 'none']
         and as_datetime(collection).date() == (now().date() + timedelta(days=1)) }}
actions:
  - action: notify.home_assistant_notifications
    data:
      target: "YOUR_DISCORD_CHANNEL_ID"
      message: >-
        The {{ state_attr('sensor.rotherham_bins_next_collection', 'bin_type') | lower
        }} is collected tomorrow ({{ states('sensor.rotherham_bins_next_collection') }}).

        <@&YOUR_DISCORD_ROLE_ID>
      data:
        embed:
          title: Rotherham Bins
          description: >-
            {{ state_attr('sensor.rotherham_bins_next_collection', 'bin_type') }}
            collection tomorrow
          url: http://homeassistant.local:8123
          color: 199363
mode: single
```

The Discord bot needs permission to send messages and embed links in the target channel. Discord channel IDs can be copied after enabling Developer Mode in Discord.

## Troubleshooting

- If no addresses are returned, check the postcode formatting and confirm that it is a Rotherham property.
- If setup cannot connect, the unofficial API may be unavailable. Retry later and check Home Assistant logs for `rotherham_bins`.
- If the API changes its response format, entities may become unavailable until the integration is updated.
- Collection dates are refreshed once per day. Reload the integration from its device page if you need to force an immediate refresh.

## Development

The parser tests do not call the live service. They are intended to run in a Home Assistant Core development environment, which provides Home Assistant and the test dependencies:

```bash
python3 -m pytest tests
```

The integration itself is intended to run inside a Home Assistant installation. For a full Home Assistant integration test suite, copy the integration into a checked-out Home Assistant Core development environment and run its component tests and hassfest validation there. The exact Home Assistant version used for validation should be recorded when a release is made.

## Attribution

The API endpoint and response shape are documented in the supplied correspondence about the Rotherham Bins application. This repository consumes live responses only and does not redistribute council schedule files or the source application's raw schedule data.
