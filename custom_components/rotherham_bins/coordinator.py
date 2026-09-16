"""Data update coordinator for Rotherham Bins."""

from __future__ import annotations

from datetime import date
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import Collection, RotherhamBinsApi, RotherhamBinsError
from .const import UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class RotherhamBinsCoordinator(DataUpdateCoordinator[list[Collection]]):
    """Fetch and retain the upcoming collection schedule."""

    def __init__(self, hass: HomeAssistant, api: RotherhamBinsApi, premise_id: int) -> None:
        self.api = api
        self.premise_id = premise_id
        super().__init__(
            hass,
            logger=_LOGGER,
            name="Rotherham Bins",
            update_interval=UPDATE_INTERVAL,
        )

    async def _async_update_data(self) -> list[Collection]:
        """Fetch only today's and future collections."""
        try:
            collections = await self.api.get_collections(self.premise_id)
        except RotherhamBinsError as err:
            raise UpdateFailed(str(err)) from err
        return [item for item in collections if item.collection_date >= date.today()]
