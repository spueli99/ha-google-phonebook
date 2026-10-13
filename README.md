# Google Phonebook for Home Assistant

Custom Home Assistant integration that synchronizes **Google Contacts via the
Google People API**, resolves telephone numbers locally and optionally keeps a
persistent SIP/Yealink call log.

## Features

- Google People API with `contacts.readonly`
- local contact cache; no Google request while the phone is ringing
- international number normalization / E.164 output
- configurable default country calling code
- `google_phonebook.lookup`
- `google_phonebook.lookup_and_set`
- persistent call history
- incoming / outgoing / missed / completed / cancelled calls
- Google contact name lookup for the remote party
- own called/used number
- call ID
- timestamps and connected-call duration
- missed-call counter and "mark as seen" action
- `google_phonebook_call_finalized` event, useful for Pushover or other notifications
- works with Yealink Action URLs; the call-log API is not tied to a specific Yealink model

## Privacy

The contact cache stores only normalized telephone numbers and display names.

The call log may contain names, phone numbers and call timestamps. It is stored
in Home Assistant's private storage. If call-log entries are exposed through
the `sensor.google_phonebook_anrufprotokoll` `calls` attribute, Home Assistant
Recorder may also retain those state attributes.

Set **"Expose this many entries as sensor attributes" to 0** in integration
options if you do not want call details exposed as entity attributes.

## Installation

### HACS custom repository

Once this repository is published, add it as a custom HACS repository of type
**Integration**, install **Google Phonebook**, and restart Home Assistant.

### Manual

Copy:

```text
custom_components/google_phonebook/
```

to:

```text
/config/custom_components/google_phonebook/
```

and restart Home Assistant.

## Google setup

1. Create or select a Google Cloud project.
2. Enable **Google People API**.
3. Create an OAuth client of type **Web application**.
4. Add this redirect URI exactly:

```text
https://my.home-assistant.io/redirect/oauth
```

5. Add the integration in Home Assistant.
6. Enter the OAuth Client ID and Client Secret when Home Assistant asks for
   application credentials.
7. Authorize read-only access to Google Contacts.

The integration requests:

```text
https://www.googleapis.com/auth/contacts.readonly
```

## Yealink Action URL example

The exact menu labels vary by firmware. The following webhook URLs are a
recommended mapping for a Yealink phone that supports Action URLs.

Replace `HOME_ASSISTANT_IP` as required.

### Incoming call

```text
http://HOME_ASSISTANT_IP:8123/api/webhook/yealink_ringing?remote=$remote&local=$local&active_user=$active_user&call_id=$call_id
```

### Outgoing call

```text
http://HOME_ASSISTANT_IP:8123/api/webhook/yealink_calling?remote=$remote&local=$local&active_user=$active_user&call_id=$call_id
```

### Call established / answered

```text
http://HOME_ASSISTANT_IP:8123/api/webhook/yealink_connected?remote=$remote&local=$local&active_user=$active_user&call_id=$call_id
```

### On hook / ended

Prefer sending the call ID here as well:

```text
http://HOME_ASSISTANT_IP:8123/api/webhook/yealink_idle?remote=$remote&local=$local&active_user=$active_user&call_id=$call_id
```

Yealink documents `$remote`, `$local`, `$active_user` and `$call_id` as Action
URL variables. Supplying `$call_id` on end events is especially useful if the
phone can handle multiple simultaneous calls.

## Example central Home Assistant automation

```yaml
alias: Yealink T54W - Telefonstatus
triggers:
  - trigger: webhook
    webhook_id: yealink_ringing
    allowed_methods: [GET]
    id: ringing
  - trigger: webhook
    webhook_id: yealink_calling
    allowed_methods: [GET]
    id: calling
  - trigger: webhook
    webhook_id: yealink_connected
    allowed_methods: [GET]
    id: connected
  - trigger: webhook
    webhook_id: yealink_idle
    allowed_methods: [GET]
    id: idle

actions:
  - variables:
      remote: "{{ trigger.query.remote | default('', true) }}"
      local: "{{ trigger.query.local | default('', true) }}"
      active_user: "{{ trigger.query.active_user | default('', true) }}"
      call_id: "{{ trigger.query.call_id | default('', true) }}"

  - action: google_phonebook.call_event
    data:
      event: "{{ trigger.id }}"
      remote: "{{ remote }}"
      local: "{{ local }}"
      active_user: "{{ active_user }}"
      call_id: "{{ call_id }}"

mode: queued
max: 20
```

The phone-status helpers and visual/voice automations are intentionally not
required by the integration.

## Missed-call event

Every finalized call fires:

```text
google_phonebook_call_finalized
```

Example:

```yaml
alias: Missed call notification
triggers:
  - trigger: event
    event_type: google_phonebook_call_finalized

conditions:
  - condition: template
    value_template: "{{ trigger.event.data.status == 'missed' }}"

actions:
  - action: notify.pushover
    data:
      title: Verpasster Anruf
      message: >-
        {{ trigger.event.data.remote_name }}
        Rufnummer: {{ trigger.event.data.remote_number }}
        Angerufen: {{ trigger.event.data.own_number }}
```

## Call states

- `missed`: incoming call ended before connection
- `completed`: connected call ended
- `cancelled`: outgoing call ended before connection
- `ended`: final fallback state when direction cannot be determined

## Concurrency

Version 0.5 tracks active calls by `call_id`. If an event has no call ID and
exactly one call is active, that call can still be resolved. If several calls
are active and an end event has no call ID, the integration deliberately does
not guess which call ended.

## Upgrading from 0.4.x

The integration domain remains `google_phonebook`, so the existing OAuth config
entry and entities remain usable.

0.5 migrates a legacy single active-call storage entry to the new
multi-call format when possible.

After upgrading, update the Yealink "on hook/ended" Action URLs to include
`$call_id` if your firmware provides it.

## Development

The repository includes a small pure-Python phone-normalization test suite and
Ruff configuration. Home Assistant runtime testing should still be performed
against a test Home Assistant instance before release.

## Author

Andreas Spielhagen ([@spueli99](https://github.com/spueli99))

## Contributing

Issues and pull requests are welcome. Please use the GitHub issue tracker for bugs and feature requests.
