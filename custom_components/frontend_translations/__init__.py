"""
Frontend Translations integration for Home Assistant.

This integration allows fetching and managing translation files for the Home Assistant frontend.
It provides services and WebSocket API endpoints to retrieve translations and metadata for
different languages, enabling dynamic language switching without requiring a restart.
"""
from __future__ import annotations

import asyncio
import logging
import aiohttp
import async_timeout
import voluptuous as vol
import json
import time

from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.typing import ConfigType
from homeassistant.components import websocket_api
from homeassistant.helpers import config_validation as cv, aiohttp_client
from homeassistant.helpers.storage import Store

from .const import DOMAIN, STORAGE_KEY, STORAGE_VERSION, REFRESH_INTERVAL, DEFAULT_BASE_URL

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {   
        DOMAIN: vol.Schema({
            vol.Optional("base_url"): cv.url,
        })  
    },  
    extra=vol.ALLOW_EXTRA,
)

GET_TRANSLATION_SCHEMA = vol.Schema({
    vol.Required('language'): cv.string,
})

def _has_metadata_changed(old_metadata: dict, new_metadata: dict) -> bool:
    """
    Check if translation metadata has changed.
    
    This function compares old and new metadata to determine if there are any changes
    that would require updating the stored metadata.
    
    Args:
        old_metadata (dict): The currently stored metadata
        new_metadata (dict): The new metadata to compare against
        
    Returns:
        bool: True if metadata has changed, False otherwise
    """
    if not old_metadata and new_metadata:
        return True
        
    if len(old_metadata) != len(new_metadata):
        return True
        
    for lang, data in new_metadata.items():
        if lang not in old_metadata:
            return True
        if old_metadata[lang].get('hash') != data.get('hash'):
            return True
            
    return False

def _get_base_url(hass: HomeAssistant) -> str:
    """
    Get the base URL for translation requests.
    
    This function determines the appropriate base URL to use for fetching translations,
    checking configuration entries, options, and Home Assistant URLs in order of preference.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        
    Returns:
        str: The base URL to use for translation requests
    """
    entries = hass.config_entries.async_entries(DOMAIN)
    if entries:
        config_entry = entries[0]
        if "base_url" in config_entry.data:
            return config_entry.data["base_url"].rstrip('/')
        if "base_url" in config_entry.options:
            return config_entry.options["base_url"].rstrip('/')
    
    if DOMAIN in hass.data and "base_url" in hass.data[DOMAIN]:
        return hass.data[DOMAIN]["base_url"].rstrip('/')
    
    if hass.config.internal_url:
        return hass.config.internal_url.rstrip('/')
    
    if hass.config.external_url:
        return hass.config.external_url.rstrip('/')
    
    return DEFAULT_BASE_URL.rstrip('/')

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """
    Set up the Frontend Translations integration from configuration.
    
    This function initializes the integration from YAML configuration
    by creating a config flow.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        config (ConfigType): The configuration data
        
    Returns:
        bool: True if setup was successful
    """
    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, 
                context={"source": "import"}, 
                data=config[DOMAIN]
            )
        )
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up the Frontend Translations integration from a config entry.
    
    This function initializes the integration's data structures, loads stored metadata,
    and registers services and WebSocket API endpoints.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        entry (ConfigEntry): The configuration entry
        
    Returns:
        bool: True if setup was successful
    """
    store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
    stored_data = await store.async_load() or {"metadata": {}, "last_update": 0}
    
    hass.data[DOMAIN] = {
        "metadata": stored_data["metadata"],
        "store": store,
        "last_update": stored_data["last_update"],
        "base_url": entry.data.get("base_url", DEFAULT_BASE_URL).rstrip('/')
    }

    if entry.options:
        hass.data[DOMAIN]["base_url"] = entry.options.get(
            "base_url", 
            hass.data[DOMAIN]["base_url"]
        ).rstrip('/')

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    async def fetch_translation(language: str) -> dict:
        """
        Fetch translation data for a specific language.
        
        This function retrieves translation data for the requested language
        using the stored metadata to construct the appropriate URL.
        
        Args:
            language (str): The language code to fetch translations for
            
        Returns:
            dict: A dictionary containing the translation data or error information
        """
        metadata = hass.data[DOMAIN]["metadata"]
        
        if not metadata or language not in metadata:
            return {"success": False, "error": f"Language {language} not found"}
        
        lang_hash = metadata[language].get('hash')
        if not lang_hash:
            return {"success": False, "error": f"No hash for {language}"}

        base_url = _get_base_url(hass)
        translation_url = f"{base_url}/static/translations/{language}-{lang_hash}.json"
        
        try:
            websession = aiohttp_client.async_get_clientsession(hass)
            async with async_timeout.timeout(10):
                response = await websession.get(translation_url)
                
                if response.status != 200:
                    return {
                        "success": False, 
                        "error": f"HTTP error {response.status}"
                    }
                    
                data = await response.json()
                return {
                    "success": True,
                    "language": language,
                    "nativeName": metadata[language].get('nativeName', language),
                    "isRTL": metadata[language].get('isRTL', False),
                    "hash": lang_hash,
                    "data": data
                }
                
        except (asyncio.TimeoutError, aiohttp.ClientError) as err:
            _LOGGER.error("Error fetching translation: %s", err)
            return {"success": False, "error": str(err)}
        except json.JSONDecodeError as err:
            _LOGGER.error("JSON decode error: %s", err)
            return {"success": False, "error": "Invalid JSON response"}

    async def handle_get_translation(call: ServiceCall) -> dict:
        """
        Service handler for getting translation data.
        
        This function handles the 'get_translation' service call by delegating
        to the fetch_translation helper function.
        
        Args:
            call (ServiceCall): The service call containing the language parameter
            
        Returns:
            dict: The translation data or error information
        """
        return await fetch_translation(call.data['language'])

    hass.services.async_register(
        DOMAIN, 
        'get_translation', 
        handle_get_translation,
        schema=GET_TRANSLATION_SCHEMA,
        supports_response=True
    )

    websocket_api.async_register_command(hass, websocket_get_all_metadata)
    websocket_api.async_register_command(hass, websocket_get_language)
    websocket_api.async_register_command(hass, websocket_store_metadata)

    hass.data[DOMAIN]["fetch_translation"] = fetch_translation

    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Handle options update.
    
    This function is called when the integration's options are updated through the UI.
    It updates the base_url if it has changed in the options.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        entry (ConfigEntry): The updated configuration entry
    """
    if entry.options:
        hass.data[DOMAIN]["base_url"] = entry.options.get(
            "base_url", 
            hass.data[DOMAIN]["base_url"]
        ).rstrip('/')

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload the integration when removed via UI.
    
    This function cleans up resources used by the integration when it's removed.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        entry (ConfigEntry): The configuration entry being removed
        
    Returns:
        bool: True if unload was successful
    """
    hass.services.async_remove(DOMAIN, 'get_translation')
    hass.data.pop(DOMAIN, None)
    return True

@websocket_api.websocket_command({vol.Required("type"): "frontend_translations/get_all_metadata"})
@callback
def websocket_get_all_metadata(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict
) -> None:
    """
    WebSocket API endpoint to get all available language metadata.
    
    This endpoint returns metadata for all available languages, including
    native names, RTL status, and content hashes.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        connection (websocket_api.ActiveConnection): The active WebSocket connection
        msg (dict): The received message
    """
    metadata = hass.data[DOMAIN].get("metadata", {})
    connection.send_result(msg["id"], {
        "languages": {
            lang: {
                "nativeName": data.get("nativeName", lang),
                "isRTL": data.get("isRTL", False),
                "hash": data.get("hash", "")
            }
            for lang, data in metadata.items()
        }
    })

@websocket_api.websocket_command({
    vol.Required("type"): "frontend_translations/get_language",
    vol.Required("language"): cv.string
})
@websocket_api.async_response
async def websocket_get_language(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict
) -> None:
    """
    WebSocket API endpoint to get translation data for a specific language.
    
    This endpoint retrieves the translation data for a requested language
    using the fetch_translation helper function.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        connection (websocket_api.ActiveConnection): The active WebSocket connection
        msg (dict): The received message containing the language parameter
    """
    fetch_translation = hass.data[DOMAIN]["fetch_translation"]
    result = await fetch_translation(msg["language"])
    connection.send_result(msg["id"], result)

@websocket_api.websocket_command({
    vol.Required("type"): "frontend_translations/store_metadata",
    vol.Required("metadata"): dict
})
@websocket_api.async_response
async def websocket_store_metadata(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict
) -> None:
    """
    THIS IS AN INTERNAL METHOD, DON'T USE IT!!!
    
    WebSocket API endpoint to store translation metadata.
    
    This endpoint receives and stores metadata about available translations.
    It checks if the metadata has changed before saving it to avoid unnecessary updates.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        connection (websocket_api.ActiveConnection): The active WebSocket connection
        msg (dict): The received message containing the metadata
    """
    try:
        current_metadata = hass.data[DOMAIN].get("metadata", {})
        new_metadata = msg["metadata"]
        
        if not _has_metadata_changed(current_metadata, new_metadata):
            return connection.send_result(msg["id"], {"unchanged": True})

        hass.data[DOMAIN]["metadata"] = new_metadata
        hass.data[DOMAIN]["last_update"] = time.time()

        await hass.data[DOMAIN]["store"].async_save({
            "metadata": new_metadata,
            "last_update": hass.data[DOMAIN]["last_update"]
        })

        connection.send_result(msg["id"], {"success": True})
    except Exception as e:
        _LOGGER.error("Error storing metadata: %s", e)
        connection.send_error(msg["id"], "storage_error", str(e))

    # Register service for getting translations
    hass.services.async_register(
        DOMAIN, 
        'get_translation', 
        handle_get_translation,
        schema=GET_TRANSLATION_SCHEMA,
        supports_response=True,
    )
    
    # Register WebSocket API endpoints
    websocket_api.async_register_command(hass, websocket_get_all_metadata)
    websocket_api.async_register_command(hass, websocket_get_language)
    websocket_api.async_register_command(hass, websocket_store_metadata)
    
    # Save helper function in hass.data for use in WebSocket API
    hass.data[DOMAIN]["fetch_translation"] = fetch_translation
    
    _LOGGER.info("Frontend Translations integration setup completed")
    return True

async def async_update_options(hass: HomeAssistant, entry: ConfigEntry):
    """
    Handle options update.
    
    This function is called when the integration's options are updated through the UI.
    It updates the base_url if it has changed in the options.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        entry (ConfigEntry): The updated configuration entry
    """
    _LOGGER.debug("Options updated: %s", entry.options)
    
    # Update baseUrl if it changed in options
    if "base_url" in entry.options:
        hass.data[DOMAIN]["base_url"] = entry.options["base_url"]
        _LOGGER.debug("Updated base_url from options: %s", entry.options["base_url"])

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload the integration when removed via UI.
    
    This function cleans up resources used by the integration when it's removed.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        entry (ConfigEntry): The configuration entry being removed
        
    Returns:
        bool: True if unload was successful
    """
    # Unregister service
    hass.services.async_remove(DOMAIN, 'get_translation')
    
    # Remove data from hass.data
    hass.data.pop(DOMAIN)
    
    return True

@websocket_api.websocket_command({
    vol.Required("type"): "frontend_translations/get_all_metadata",
})
@websocket_api.async_response
async def websocket_get_all_metadata(hass, connection, msg):
    """
    WebSocket API endpoint to get all available language metadata.
    
    This endpoint returns metadata for all available languages, including
    native names, RTL status, and content hashes.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        connection (websocket_api.ActiveConnection): The active WebSocket connection
        msg (dict): The received message
    """
    metadata = hass.data[DOMAIN].get("metadata", {})
    
    languages = {}
    for lang_code, lang_data in metadata.items():
        languages[lang_code] = {
            "nativeName": lang_data.get("nativeName", lang_code),
            "isRTL": lang_data.get("isRTL", False),
            "hash": lang_data.get("hash", "")
        }
    
    connection.send_result(msg["id"], {"languages": languages})

@websocket_api.websocket_command({
    vol.Required("type"): "frontend_translations/get_language",
    vol.Required("language"): cv.string,
})
@websocket_api.async_response
async def websocket_get_language(hass, connection, msg):
    """
    WebSocket API endpoint to get translation data for a specific language.
    
    This endpoint retrieves the translation data for a requested language
    using the fetch_translation helper function.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        connection (websocket_api.ActiveConnection): The active WebSocket connection
        msg (dict): The received message containing the language parameter
    """
    language = msg["language"]
    fetch_translation = hass.data[DOMAIN]["fetch_translation"]
    
    result = await fetch_translation(language)
    connection.send_result(msg["id"], result)

@websocket_api.websocket_command({
    vol.Required("type"): "frontend_translations/store_metadata",
    vol.Required("metadata"): dict,
})
@websocket_api.async_response
async def websocket_store_metadata(hass, connection, msg):
    """
    THIS IS AN INTERNAL METHOD, DON'T USE IT!!!
    
    WebSocket API endpoint to store translation metadata.
    
    This endpoint receives and stores metadata about available translations.
    It checks if the metadata has changed before saving it to avoid unnecessary updates.
    
    Args:
        hass (HomeAssistant): The Home Assistant instance
        connection (websocket_api.ActiveConnection): The active WebSocket connection
        msg (dict): The received message containing the metadata
    """
    try:
        metadata = msg["metadata"]
        
        # Get current metadata
        current_metadata = hass.data[DOMAIN].get("metadata", {})
        
        # Check if metadata has changed
        if _has_metadata_changed(current_metadata, metadata):
            # Save metadata
            hass.data[DOMAIN]["metadata"] = metadata
            hass.data[DOMAIN]["last_update"] = time.time()
            
            # Asynchronously save to storage
            store = hass.data[DOMAIN]["store"]
            await store.async_save({
                "metadata": metadata,
                "last_update": hass.data[DOMAIN]["last_update"]
            })
            
            _LOGGER.info("Translation metadata updated with %d languages", len(metadata))
            connection.send_result(msg["id"], {"success": True})
        else:
            _LOGGER.debug("Translation metadata unchanged, skipping update")
            connection.send_result(msg["id"], {"success": True, "unchanged": True})
    except Exception as e:
        _LOGGER.error("Error in websocket_store_metadata: %s", str(e), exc_info=True)
        connection.send_error(msg["id"], "server_error", f"Error storing metadata: {str(e)}")

