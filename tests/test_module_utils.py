"""Tests for ArkivModule utility methods."""

import logging
from unittest.mock import MagicMock

import pytest

from arkiv.module import ArkivModule
from arkiv.module_async import AsyncArkivModule

logger = logging.getLogger(__name__)


class TestToBlocks:
    """Test cases for to_blocks time conversion method."""

    @pytest.fixture
    def mock_module(self):
        """Create a mock ArkivModule for testing."""
        module = MagicMock(spec=ArkivModule)
        # Mock the get_block_timing response
        module.get_block_timing.return_value = {"duration": 2}
        # Bind the actual to_blocks method to our mock
        module.to_blocks = ArkivModule.to_blocks.__get__(module)
        return module

    def test_to_blocks_from_seconds(self, mock_module):
        """Test conversion from seconds to blocks."""
        # With 2 second block time, 120 seconds = 60 blocks
        result = mock_module.to_blocks(seconds=120)
        assert result == 60
        mock_module.get_block_timing.assert_called_once()

    def test_to_blocks_from_minutes(self, mock_module):
        """Test conversion from minutes to blocks."""
        # 2 minutes = 120 seconds = 60 blocks
        result = mock_module.to_blocks(minutes=2)
        assert result == 60

    def test_to_blocks_from_hours(self, mock_module):
        """Test conversion from hours to blocks."""
        # 1 hour = 3600 seconds = 1800 blocks
        result = mock_module.to_blocks(hours=1)
        assert result == 1800

    def test_to_blocks_from_days(self, mock_module):
        """Test conversion from days to blocks."""
        # 1 day = 86400 seconds = 43200 blocks
        result = mock_module.to_blocks(days=1)
        assert result == 43200

    def test_to_blocks_mixed_units(self, mock_module):
        """Test conversion with mixed time units."""
        # 1 day + 2 hours + 30 minutes + 60 seconds
        # = 86400 + 7200 + 1800 + 60 = 95460 seconds = 47730 blocks
        result = mock_module.to_blocks(days=1, hours=2, minutes=30, seconds=60)
        assert result == 47730

    def test_to_blocks_caches_block_duration(self, mock_module):
        """Test that block duration is cached after first call."""
        mock_module.to_blocks(seconds=2)
        mock_module.to_blocks(seconds=4)
        # Should only call get_block_timing once
        assert mock_module.get_block_timing.call_count == 1

    def test_to_blocks_default_values(self, mock_module):
        """Test with all default values (should return 0)."""
        result = mock_module.to_blocks()
        assert result == 0

    def test_to_blocks_rounding_down(self, mock_module):
        """Test that partial blocks are rounded down."""
        # 125 seconds with 2 second blocks = 62.5 blocks, should round to 62
        result = mock_module.to_blocks(seconds=125)
        assert result == 62


class TestToBlocksAsync:
    """Test cases for async to_blocks time conversion method."""

    @pytest.fixture
    async def mock_module_async(self):
        """Create a mock AsyncArkivModule for testing."""
        module = MagicMock(spec=AsyncArkivModule)
        # Mock the async get_block_timing response
        async def mock_get_block_timing():
            return {"duration": 2}

        module.get_block_timing = mock_get_block_timing
        # Bind the actual to_blocks method to our mock
        module.to_blocks = AsyncArkivModule.to_blocks.__get__(module)
        return module

    @pytest.mark.asyncio
    async def test_async_to_blocks_from_seconds(self, mock_module_async):
        """Test async conversion from seconds to blocks."""
        # With 2 second block time, 120 seconds = 60 blocks
        result = await mock_module_async.to_blocks(seconds=120)
        assert result == 60

    @pytest.mark.asyncio
    async def test_async_to_blocks_from_minutes(self, mock_module_async):
        """Test async conversion from minutes to blocks."""
        # 2 minutes = 120 seconds = 60 blocks
        result = await mock_module_async.to_blocks(minutes=2)
        assert result == 60

    @pytest.mark.asyncio
    async def test_async_to_blocks_from_hours(self, mock_module_async):
        """Test async conversion from hours to blocks."""
        # 1 hour = 3600 seconds = 1800 blocks
        result = await mock_module_async.to_blocks(hours=1)
        assert result == 1800

    @pytest.mark.asyncio
    async def test_async_to_blocks_from_days(self, mock_module_async):
        """Test async conversion from days to blocks."""
        # 1 day = 86400 seconds = 43200 blocks
        result = await mock_module_async.to_blocks(days=1)
        assert result == 43200

    @pytest.mark.asyncio
    async def test_async_to_blocks_mixed_units(self, mock_module_async):
        """Test async conversion with mixed time units."""
        # 1 day + 2 hours + 30 minutes + 60 seconds
        # = 86400 + 7200 + 1800 + 60 = 95460 seconds = 47730 blocks
        result = await mock_module_async.to_blocks(
            days=1, hours=2, minutes=30, seconds=60
        )
        assert result == 47730

    @pytest.mark.asyncio
    async def test_async_to_blocks_default_values(self, mock_module_async):
        """Test async with all default values (should return 0)."""
        result = await mock_module_async.to_blocks()
        assert result == 0

    @pytest.mark.asyncio
    async def test_async_to_blocks_rounding_down(self, mock_module_async):
        """Test that partial blocks are rounded down in async version."""
        # 125 seconds with 2 second blocks = 62.5 blocks, should round to 62
        result = await mock_module_async.to_blocks(seconds=125)
        assert result == 62
