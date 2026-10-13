# Changelog

## 0.5.1

- Added GitHub maintainer metadata for @spueli99, documentation and issue-tracker URLs.

- Fixed Home Assistant Store startup failure when upgrading from 0.4.x by keeping the call-log store at version 1; the integration already performs the legacy data-shape migration itself.

## 0.5.0

- Refactored and prepared for public GitHub/HACS use.
- Added configurable default country calling code.
- Added configurable call-log retention and sensor exposure.
- Active calls are now tracked by call ID instead of a single global call.
- Added safe fallback when exactly one active call exists and an event lacks a call ID.
- Avoids guessing when several calls are active and an event has no call ID.
- Added migration from the 0.4.x single-active-call storage shape.
- Kept the `google_phonebook` domain for upgrade compatibility.
- Integrated the 0.4 setup hotfix; service registration no longer checks for LOADED while setup is in progress.
- Added privacy documentation.
- Added English translations.
- Added HACS metadata, license, changelog, test skeleton and lint configuration.
