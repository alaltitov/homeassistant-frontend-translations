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

For more information, see the [README](https://github.com/alaltitov/hacs-frontend-translations/blob/1cca3ff3f71125a057b2e34ec13b9450c76a101d/README.md).
