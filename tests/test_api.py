"""Tests for the Rotherham Bins API parser."""

from datetime import date

from custom_components.rotherham_bins.api import (
    parse_addresses,
    parse_collections,
)
from custom_components.rotherham_bins.config_flow import _migrated_object_id


def test_migrated_entity_object_ids_are_stable() -> None:
    assert _migrated_object_id("123_next", "123") == "rotherham_bins_next_collection"
    assert _migrated_object_id("123_black_bin", "123") == "rotherham_bins_black_collection"
    assert _migrated_object_id("123_pink_bin", "123") == "rotherham_bins_pink_collection"
    assert _migrated_object_id("123_green_bin", "123") == "rotherham_bins_green_collection"
    assert _migrated_object_id("456_black_bin", "123") is None


def test_parse_addresses_normalizes_fields() -> None:
    addresses = parse_addresses(
        [
            {
                "PremiseID": 999999,
                "Address1": "TEST PROPERTY",
                "Address2": "1",
                "Street": "EXAMPLE STREET",
                "Locality": "ROTHERHAM",
                "Town": "ROTHERHAM",
                "Postcode": "S60\n1AE",
                "LocalAuthority": "Rotherham",
            }
        ]
    )

    assert addresses[0].premise_id == 999999
    assert addresses[0].label == (
        "TEST PROPERTY, 1, EXAMPLE STREET, ROTHERHAM, "
        "ROTHERHAM, S60 1AE"
    )
    assert addresses[0].postcode == "S60 1AE"


def test_parse_collections_sorts_and_normalizes_bin_types() -> None:
    collections = parse_collections(
        [
            {"BinType": " PINK\nBIN ", "CollectionDate": "2026-10-07"},
            {"BinType": "BLACK BIN", "CollectionDate": "2026-09-16"},
            {"BinType": "GREEN BI\n", "CollectionDate": "2026-09-30"},
            {"BinType": "bad", "CollectionDate": "not-a-date"},
        ]
    )

    assert [(item.bin_type, item.collection_date) for item in collections] == [
        ("BLACK BIN", date(2026, 9, 16)),
        ("GREEN BI", date(2026, 9, 30)),
        ("PINK BIN", date(2026, 10, 7)),
    ]
    assert collections[1].colour == "Green Bi"


def test_parse_collections_rejects_non_list() -> None:
    try:
        parse_collections({})
    except Exception as error:
        assert str(error) == "Collection response was not a list"
    else:
        raise AssertionError("Expected invalid collection payload to fail")
