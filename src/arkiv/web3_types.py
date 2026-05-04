"""Small Web3 typing aliases used across sync/async code."""

from __future__ import annotations

from typing import TypeAlias

from web3.contract import AsyncContract, Contract

ContractLike: TypeAlias = Contract | AsyncContract
