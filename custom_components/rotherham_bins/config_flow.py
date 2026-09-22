"""Config flow for Rotherham Bins."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import Address, RotherhamBinsApi, RotherhamBinsConnectionError, RotherhamBinsResponseError
from .const import (
    CONF_ADDRESS,
    CONF_LOCAL_AUTHORITY,
    CONF_POSTCODE,
    CONF_PREMISE_ID,
    DOMAIN,
    LOCAL_AUTHORITY,
)

def _migrated_object_id(unique_id: str, premise_id: str) -> str | None:
    """Return the stable object ID for a legacy sensor unique ID."""
    prefix = f"{premise_id}_"
    if not unique_id.startswith(prefix):
        return None
    suffix = unique_id.removeprefix(prefix)
    if suffix == "next":
        return "rotherham_bins_next_collection"
    if not suffix.endswith("_bin"):
        return None
    return f"rotherham_bins_{suffix.removesuffix('_bin')}_collection"


class RotherhamBinsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle setup of a Rotherham property."""

    VERSION = 1

    def __init__(self) -> None:
        self._addresses: list[Address] = []
        self._postcode = ""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose postcode lookup or manual setup."""
        return self.async_show_menu(step_id="user", menu_options=["postcode", "manual"])

    async def async_step_postcode(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Look up addresses from a postcode."""
        if user_input is None:
            return self.async_show_form(
                step_id="postcode",
                data_schema=vol.Schema({vol.Required(CONF_POSTCODE): str}),
            )

        self._postcode = " ".join(user_input[CONF_POSTCODE].upper().split())
        try:
            self._addresses = await RotherhamBinsApi(async_get_clientsession(self.hass)).get_addresses(self._postcode)
        except (RotherhamBinsConnectionError, RotherhamBinsResponseError):
            return self.async_show_form(
                step_id="postcode",
                data_schema=vol.Schema({vol.Required(CONF_POSTCODE, default=self._postcode): str}),
                errors={"base": "cannot_connect"},
            )
        if not self._addresses:
            return self.async_show_form(
                step_id="postcode",
                data_schema=vol.Schema({vol.Required(CONF_POSTCODE, default=self._postcode): str}),
                errors={"base": "no_addresses"},
            )
        return await self.async_step_address()

    async def async_step_address(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Choose one address from the postcode results."""
        choices = {str(address.premise_id): address.label for address in self._addresses}
        if user_input is not None:
            address = next(item for item in self._addresses if str(item.premise_id) == user_input[CONF_PREMISE_ID])
            return await self._async_create_entry(
                address.premise_id,
                address.label,
                address.postcode or self._postcode,
                "address",
            )
        return self.async_show_form(
            step_id="address",
            data_schema=vol.Schema({vol.Required(CONF_PREMISE_ID): vol.In(choices)}),
        )

    async def async_step_manual(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Set up a premise ID without postcode lookup."""
        schema = vol.Schema(
            {
                vol.Required(CONF_PREMISE_ID): vol.Coerce(int),
                vol.Required(CONF_ADDRESS): str,
                vol.Optional(CONF_POSTCODE, default=""): str,
            }
        )
        if user_input is None:
            return self.async_show_form(step_id="manual", data_schema=schema)
        return await self._async_create_entry(
            user_input[CONF_PREMISE_ID],
            user_input[CONF_ADDRESS],
            " ".join(user_input[CONF_POSTCODE].upper().split()),
            "manual",
        )

    async def _async_create_entry(
        self,
        premise_id: int,
        address: str,
        postcode: str,
        step_id: str,
    ) -> ConfigFlowResult:
        """Validate a premise and create the config entry."""
        await self.async_set_unique_id(str(premise_id))
        self._abort_if_unique_id_configured()
        if step_id == "address":
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_PREMISE_ID): vol.In(
                        {str(item.premise_id): item.label for item in self._addresses}
                    )
                }
            )
        else:
            data_schema = vol.Schema(
                {
                    vol.Required(CONF_PREMISE_ID, default=premise_id): vol.Coerce(int),
                    vol.Required(CONF_ADDRESS, default=address): str,
                    vol.Optional(CONF_POSTCODE, default=postcode): str,
                }
            )
        try:
            collections = await RotherhamBinsApi(async_get_clientsession(self.hass)).get_collections(premise_id)
        except (RotherhamBinsConnectionError, RotherhamBinsResponseError):
            return self.async_show_form(
                step_id=step_id,
                data_schema=data_schema,
                errors={"base": "cannot_connect"},
            )
        if not collections:
            return self.async_show_form(
                step_id=step_id,
                data_schema=data_schema,
                errors={"base": "no_collections"},
            )
        data = {
            CONF_PREMISE_ID: premise_id,
            CONF_ADDRESS: address,
            CONF_POSTCODE: postcode,
            CONF_LOCAL_AUTHORITY: LOCAL_AUTHORITY,
        }
        return self.async_create_entry(title=address or f"Premise {premise_id}", data=data)

    @staticmethod
    @config_entries.callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        """Return the options flow for an existing property."""
        return RotherhamBinsOptionsFlow()


class RotherhamBinsOptionsFlow(config_entries.OptionsFlow):
    """Handle optional entity ID migration for an existing property."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Show available maintenance actions."""
        return self.async_show_menu(step_id="init", menu_options=["migrate"])

    async def async_step_migrate(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Migrate existing address-based entity IDs on explicit request."""
        if user_input is None:
            return self.async_show_form(step_id="migrate")

        entity_registry = er.async_get(self.hass)
        premise_id = str(self.config_entry.data[CONF_PREMISE_ID])
        for entity in er.async_entries_for_config_entry(entity_registry, self.config_entry.entry_id):
            if entity.domain != "sensor":
                continue
            object_id = _migrated_object_id(entity.unique_id, premise_id)
            if object_id is None:
                continue
            new_entity_id = f"sensor.{object_id}"
            if entity.entity_id != new_entity_id and entity_registry.async_get(new_entity_id) is None:
                entity_registry.async_update_entity(entity.entity_id, new_entity_id=new_entity_id)

        return self.async_create_entry(title="", data={})
