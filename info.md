# Frontend Translations

This integration allows fetching and managing translation files for the Home Assistant frontend.

## Features

- Automatically stores frontend translation metadata
- Provides services to fetch translations for specific languages
- WebSocket API for frontend integration
- Configurable base URL for translation files

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Frontend Translations"
3. Configure the base URL if needed

## Frontend Script Setup

Add to your `configuration.yaml`:

```yaml
frontend:
  extra_module_url:
    - /local/frontend-translations/frontend-translations.js
```

For more information, see the [README](https://github.com/alaltitov/homeassistant-frontend-translations/blob/63cd1ec20f34a79ccbca3a922dca7e9171c50234/README.md).
