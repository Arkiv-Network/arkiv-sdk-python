"""Python SDK for Arkiv networks."""

from importlib.metadata import PackageNotFoundError, version

from .account import NamedAccount
from .client import Arkiv, AsyncArkiv
from .events import EventFilter
from .events_async import AsyncEventFilter
from .node import ArkivNode
from .query import QueryIterator
from .types import (
    CreateEvent,
    DeleteEvent,
    ExtendEvent,
    TransactionReceipt,
    UpdateEvent,
)

try:
    __version__ = version("arkiv-sdk")
except PackageNotFoundError:
    # Package is not installed (e.g., development without editable install)
    __version__ = "dev"

__all__ = [
    "Arkiv",
    "ArkivNode",
    "AsyncArkiv",
    "AsyncEventFilter",
    "CreateEvent",
    "DeleteEvent",
    "EventFilter",
    "ExtendEvent",
    "NamedAccount",
    "QueryIterator",
    "TransactionReceipt",
    "UpdateEvent",
]
