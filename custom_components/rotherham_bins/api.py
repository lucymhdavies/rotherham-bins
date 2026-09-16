"""Async client and response parsing for the Rotherham Bins API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import API_BASE_URL, LOCAL_AUTHORITY


class RotherhamBinsError(Exception):
    """Base exception for API and response errors."""


class RotherhamBinsConnectionError(RotherhamBinsError):
    """Raised when the API cannot be reached."""


class RotherhamBinsResponseError(RotherhamBinsError):
    """Raised when the API response is invalid."""


@dataclass(frozen=True, slots=True)
class Address:
    """An address returned by the postcode lookup."""

    premise_id: int
    label: str
    postcode: str
    local_authority: str


@dataclass(frozen=True, slots=True)
class Collection:
    """A single upcoming collection."""

    bin_type: str
    collection_date: date

    @property
    def colour(self) -> str:
        """Return the normalized bin colour/type."""
        return self.bin_type.removesuffix(" BIN").strip().title()


def _clean(value: Any) -> str:
    """Normalize API strings, including embedded line breaks."""
    return " ".join(str(value or "").split())


def _address_label(item: dict[str, Any]) -> str:
    """Build a useful selectable label from the API address fields."""
    parts = [
        _clean(item.get("Address1")),
        _clean(item.get("Address2")),
        _clean(item.get("Street")),
        _clean(item.get("Locality")),
        _clean(item.get("Town")),
        _clean(item.get("Postcode")),
    ]
    return ", ".join(part for part in parts if part)


def parse_addresses(payload: Any) -> list[Address]:
    """Parse the postcode lookup response."""
    if not isinstance(payload, list):
        raise RotherhamBinsResponseError("Address response was not a list")

    addresses: list[Address] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        try:
            premise_id = int(item["PremiseID"])
        except (KeyError, TypeError, ValueError) as err:
            raise RotherhamBinsResponseError("Address has no valid premise ID") from err
        addresses.append(
            Address(
                premise_id=premise_id,
                label=_address_label(item),
                postcode=_clean(item.get("Postcode")),
                local_authority=_clean(item.get("LocalAuthority")) or LOCAL_AUTHORITY,
            )
        )
    return addresses


def parse_collections(payload: Any) -> list[Collection]:
    """Parse and sort the collection response, ignoring invalid rows."""
    if not isinstance(payload, list):
        raise RotherhamBinsResponseError("Collection response was not a list")

    collections: list[Collection] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        bin_type = _clean(item.get("BinType")).upper()
        date_value = _clean(item.get("CollectionDate"))
        if not bin_type or not date_value:
            continue
        try:
            collection_date = date.fromisoformat(date_value[:10])
        except ValueError:
            continue
        collections.append(Collection(bin_type=bin_type, collection_date=collection_date))
    return sorted(collections, key=lambda item: item.collection_date)


class RotherhamBinsApi:
    """Small async client for the undocumented Rotherham endpoint."""

    def __init__(self, session: ClientSession, base_url: str = API_BASE_URL) -> None:
        self._session = session
        self._base_url = base_url.rstrip("/")

    async def _get_json(self, path: str, **params: str | int) -> Any:
        try:
            async with self._session.get(f"{self._base_url}/{path}", params=params) as response:
                response.raise_for_status()
                return await response.json()
        except (ClientError, ClientResponseError, ValueError) as err:
            raise RotherhamBinsConnectionError(str(err)) from err

    async def get_addresses(self, postcode: str) -> list[Address]:
        """Look up addresses for a postcode."""
        return parse_addresses(await self._get_json("getaddress", postcode=postcode))

    async def get_collections(self, premise_id: int) -> list[Collection]:
        """Get upcoming collections for a premise."""
        payload = await self._get_json(
            "getcollections",
            premisesid=premise_id,
            localauthority=LOCAL_AUTHORITY,
        )
        return parse_collections(payload)
