# <img width="30px" src="https://github.com/alaltitov/hacs-frontend-translations/blob/2a944f4f9d958a946e66df3e2699ee3a0c9b8041/docs/icons/icon%402x.png"> Frontend Translations for Home Assistant

This integration allows fetching and managing translation files for the Home Assistant frontend. It provides services and WebSocket API endpoints to retrieve translations and metadata for different languages, enabling dynamic language switching without requiring a restart.

## Features

- Automatically stores frontend translation metadata
- Provides services to fetch translations for specific languages
- WebSocket API for frontend integration
- Configurable base URL for translation files

## Installation

### HACS Installation (Recommended)

1. Make sure [HACS](https://hacs.xyz) is installed in your Home Assistant instance
2. Go to HACS → Integrations → "+ Explore & Download Repositories"
3. Search for "Frontend Translations"
4. Click "Download"
5. Copy the `www/frontend-translations/frontend-translations.js` file to your Home Assistant's `www/frontend-translations/` directory
6. Registry script (see item "Frontend Script Setup")
7. Restart Home Assistant

### Manual Installation

1. Download the files from this repository
2. Copy the `custom_components/frontend_translations` directory to your Home Assistant's `custom_components` directory
3. Copy the `www/frontend-translations/frontend-translations.js` file to your Home Assistant's `www/frontend-translations/` directory
4. Registry script (see item "Frontend Script Setup")
5. Restart Home Assistant

## Configuration

1. Go to Settings → Devices & Services → Add Integration
2. Search for "Frontend Translations"
3. Configure the base URL if needed (default is http://homeassistant.local:8123)

## Frontend Script Setup

!IMPORTANT For registry JS script, add the following to your `configuration.yaml`:

```yaml
frontend:
  extra_module_url:
    - /local/frontend-translations/frontend-translations.js
```

## Usage

### Services

The integration provides the following service:

- `frontend_translations.get_translation`: Retrieves translation data for a specific language
  
  <img width="400px" src="https://github.com/alaltitov/hacs-frontend-translations/blob/5bbdf6e52df28528375c673644be3d687d268a16/docs/images/example.png">

### WebSocket API

The integration provides the following WebSocket API endpoints:

- `frontend_translations/get_all_metadata`: Get metadata for all available languages
- `frontend_translations/get_language`: Get translation data for a specific language

## Troubleshooting

If you encounter issues:

- Check the Home Assistant logs for any error messages
- Verify that the base URL is correctly configured
- Make sure the frontend script is properly loaded

## License

This project is licensed under the MIT License - see the LICENSE file for details.
