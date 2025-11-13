"""Tests for ArkivModule utility methods."""

import logging

from arkiv import Arkiv

logger = logging.getLogger(__name__)


class TestToSeconds:
    """Test cases for to_seconds time conversion method."""

    def test_to_seconds_from_seconds(self, arkiv_client_http: Arkiv):
        """Test conversion from seconds."""
        result = arkiv_client_http.arkiv.to_seconds(seconds=120)
        assert result == 120

    def test_to_seconds_from_minutes(self, arkiv_client_http: Arkiv):
        """Test conversion from minutes to seconds."""
        # 2 minutes = 120 seconds
        result = arkiv_client_http.arkiv.to_seconds(minutes=2)
        assert result == 120

    def test_to_seconds_from_hours(self, arkiv_client_http: Arkiv):
        """Test conversion from hours to seconds."""
        # 1 hour = 3600 seconds
        result = arkiv_client_http.arkiv.to_seconds(hours=1)
        assert result == 3600

    def test_to_seconds_from_days(self, arkiv_client_http: Arkiv):
        """Test conversion from days to seconds."""
        # 1 day = 86400 seconds
        result = arkiv_client_http.arkiv.to_seconds(days=1)
        assert result == 86400

    def test_to_seconds_mixed_units(self, arkiv_client_http: Arkiv):
        """Test conversion with mixed time units."""
        # 1 day + 2 hours + 30 minutes + 60 seconds
        # = 86400 + 7200 + 1800 + 60 = 95460 seconds
        result = arkiv_client_http.arkiv.to_seconds(
            days=1, hours=2, minutes=30, seconds=60
        )
        assert result == 95460

    def test_to_seconds_default_values(self, arkiv_client_http: Arkiv):
        """Test with all default values (should return 0)."""
        result = arkiv_client_http.arkiv.to_seconds()
        assert result == 0


class TestToBlocks:
    """Test cases for to_blocks time conversion method."""

    def test_to_blocks_from_seconds(self, arkiv_client_http: Arkiv):
        """Test conversion from seconds to blocks."""
        # With 2 second block time, 120 seconds = 60 blocks
        result = arkiv_client_http.arkiv.to_blocks(seconds=120)
        assert result == 60

    def test_to_blocks_from_minutes(self, arkiv_client_http: Arkiv):
        """Test conversion from minutes to blocks."""
        # 2 minutes = 120 seconds = 60 blocks
        result = arkiv_client_http.arkiv.to_blocks(minutes=2)
        assert result == 60

    def test_to_blocks_from_hours(self, arkiv_client_http: Arkiv):
        """Test conversion from hours to blocks."""
        # 1 hour = 3600 seconds = 1800 blocks
        result = arkiv_client_http.arkiv.to_blocks(hours=1)
        assert result == 1800

    def test_to_blocks_from_days(self, arkiv_client_http: Arkiv):
        """Test conversion from days to blocks."""
        # 1 day = 86400 seconds = 43200 blocks
        result = arkiv_client_http.arkiv.to_blocks(days=1)
        assert result == 43200

    def test_to_blocks_mixed_units(self, arkiv_client_http: Arkiv):
        """Test conversion with mixed time units."""
        # 1 day + 2 hours + 30 minutes + 60 seconds
        # = 86400 + 7200 + 1800 + 60 = 95460 seconds = 47730 blocks
        result = arkiv_client_http.arkiv.to_blocks(
            days=1, hours=2, minutes=30, seconds=60
        )
        assert result == 47730

    def test_to_blocks_default_values(self, arkiv_client_http: Arkiv):
        """Test with all default values (should return 0)."""
        result = arkiv_client_http.arkiv.to_blocks()
        assert result == 0

    def test_to_blocks_rounding_down(self, arkiv_client_http: Arkiv):
        """Test that partial blocks are rounded down."""
        # 125 seconds with 2 second blocks = 62.5 blocks, should round to 62
        result = arkiv_client_http.arkiv.to_blocks(seconds=125)
        assert result == 62
