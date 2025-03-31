"""Config flow for Frontend Translations integration."""
from __future__ import annotations

import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN, DEFAULT_BASE_URL

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    vol.Optional("base_url", default=DEFAULT_BASE_URL): str
})

class FrontendTranslationsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """
    Config flow handler for Frontend Translations integration.
    
    This class handles the creation and setup of the integration's configuration
    through the UI and from YAML imports.
    """
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """
        Handle a flow initialized by the user.
        
        This method is called when a user initiates the setup of this integration
        through the UI. It validates that only one instance of the integration exists
        and processes the user's configuration input.
        
        Args:
            user_input (dict, optional): Configuration provided by the user
            
        Returns:
            FlowResult: The result of the configuration flow step
        """
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is not None:
            user_input["base_url"] = user_input["base_url"].rstrip('/')
            return self.async_create_entry(
                title="Frontend Translations",
                data=user_input
            )

        return self.async_show_form(
            step_id="user",
            data_schema=CONFIG_SCHEMA,
        )

    async def async_step_import(self, import_data):
        """
        Handle import from YAML configuration.
        
        This method is called when the integration is configured via YAML.
        It delegates to the user step to create the config entry.
        
        Args:
            import_data (dict): Configuration imported from YAML
            
        Returns:
            FlowResult: The result of the configuration flow step
        """
        return await self.async_step_user(import_data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """
        Get the options flow handler for this integration.
        
        This method creates an options flow handler that allows users to update
        the integration's configuration after it's been set up.
        
        Args:
            config_entry (ConfigEntry): The current configuration entry
            
        Returns:
            OptionsFlowHandler: The options flow handler
        """
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """
    Options flow handler for Frontend Translations integration.
    
    This class handles the modification of integration options through the UI
    after the integration has been set up.
    """
    def __init__(self, config_entry):
        """
        Initialize the options flow.
        
        Args:
            config_entry (ConfigEntry): The current configuration entry
        """
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """
        Handle the initial options step.
        
        This method presents a form to the user for updating the integration's
        configuration options and processes the submitted values.
        
        Args:
            user_input (dict, optional): Options provided by the user
            
        Returns:
            FlowResult: The result of the options flow step
        """
        if user_input is not None:
            user_input["base_url"] = user_input["base_url"].rstrip('/')
            return self.async_create_entry(title="", data=user_input)

        current_url = self.config_entry.options.get(
            "base_url",
            self.config_entry.data.get("base_url", DEFAULT_BASE_URL)
        ).rstrip('/')

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional("base_url", default=current_url): str
            })
        )
