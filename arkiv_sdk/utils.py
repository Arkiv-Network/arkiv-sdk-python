"""Utility methods."""

import logging
import math
from typing import TypeVar

import rlp

from .types import (
    Annotation,
    ArkivTransaction,
)

logger = logging.getLogger(__name__)
"""@private"""


def rlp_encode_transaction(tx: ArkivTransaction, chain_cadence: int) -> bytes:
    """Encode an Arkiv transaction in RLP."""
    # TODO: use new generic syntax once we can bump to python 3.12 or higher
    T = TypeVar("T")

    def format_annotation(annotation: Annotation[T]) -> tuple[str, T]:
        return (annotation.key, annotation.value)

    def getBTL(blocks: int | None, seconds: int | None) -> int:
        if not blocks and not seconds:
            raise Exception("You cannot define BTL and expiresIn at the same time")
        if seconds:
            return math.ceil(seconds / chain_cadence)
        if blocks:
            return blocks
        raise Exception("You need to define either BTL or expiresIn")

    # Turn the transaction into a simple list of basic types that can be
    # RLP encoded
    payload = [
        # Create
        list(
            map(
                lambda el: [
                    getBTL(el.btl, el.expires_in),
                    el.data,
                    list(map(format_annotation, el.string_annotations)),
                    list(map(format_annotation, el.numeric_annotations)),
                ],
                tx.creates,
            )
        ),
        # Update
        list(
            map(
                lambda el: [
                    el.entity_key.generic_bytes,
                    getBTL(el.btl, el.expires_in),
                    el.data,
                    list(map(format_annotation, el.string_annotations)),
                    list(map(format_annotation, el.numeric_annotations)),
                ],
                tx.updates,
            )
        ),
        # Delete
        list(
            map(
                lambda el: el.entity_key.generic_bytes,
                tx.deletes,
            )
        ),
        # Extend
        list(
            map(
                lambda el: [
                    el.entity_key.generic_bytes,
                    getBTL(el.number_of_blocks, el.number_of_seconds),
                ],
                tx.extensions,
            )
        ),
    ]
    logger.debug("Payload before RLP encoding: %s", payload)
    encoded: bytes = rlp.encode(payload)
    logger.debug("Encoded  payload: %s", encoded)
    return encoded
