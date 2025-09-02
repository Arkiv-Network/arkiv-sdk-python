"""Utility methods."""

import logging
from typing import TypeVar

import rlp

from .types import (
    Annotation,
    GolemBaseTransaction,
)

logger = logging.getLogger(__name__)
"""@private"""


def rlp_encode_transaction(tx: GolemBaseTransaction) -> bytes:
    """Encode a Golem Base transaction in RLP."""
    # TODO: use new generic syntax once we can bump to python 3.12 or higher
    T = TypeVar("T")

    def format_annotation(annotation: Annotation[T]) -> tuple[str, T]:
        return (annotation.key, annotation.value)

    # Turn the transaction into a simple list of basic types that can be
    # RLP encoded
    payload = [
        # Create
        list(
            map(
                lambda el: [
                    el.btl,
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
                    el.btl,
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
                    el.number_of_blocks,
                ],
                tx.extensions,
            )
        ),
    ]
    logger.debug("Payload before RLP encoding: %s", payload)
    encoded: bytes = rlp.encode(payload)
    logger.debug("Encoded  payload: %s", encoded)
    return encoded
