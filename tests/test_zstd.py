"""Tests for Zstandard (zstd) compression/decompression.

Installation:
    uv add zstd
"""

import json
import logging

import zstd

logger = logging.getLogger(__name__)


def log_compression_ratio(label: str, original: bytes, compressed: bytes) -> None:
    """Log compression ratio with test label."""
    ratio = len(compressed) / len(original)
    logger.info(f"{label}: {len(original)} -> {len(compressed)} bytes ({ratio:.2%})")


def test_zstd_basic_compression():
    """Test basic compression and decompression."""
    original = b"Hello, World! This is a test string for Zstandard compression."

    # Compress
    compressed = zstd.compress(original)

    # Decompress
    decompressed = zstd.decompress(compressed)

    # Verify
    assert decompressed == original
    # Note: Very small data may not compress well due to overhead

    log_compression_ratio("test_zstd_basic_compression", original, compressed)


def test_zstd_compression_quality_levels():
    """Test different compression quality levels (1-22)."""
    original = b"The quick brown fox jumps over the lazy dog. " * 100

    results = {}
    for level in [1, 5, 10, 15, 22]:  # Sample of zstd levels (1=fastest, 22=best)
        compressed = zstd.compress(original, level)
        decompressed = zstd.decompress(compressed)

        assert decompressed == original
        results[level] = len(compressed)

        log_compression_ratio(
            f"test_zstd_compression_quality_levels[level={level}]",
            original,
            compressed,
        )

    # All quality levels should work and produce valid output
    # Note: Higher level doesn't always mean smaller size for all data
    assert all(size > 0 for size in results.values())
    assert len(results) == 5


def test_zstd_large_data():
    """Test compression of larger data."""
    # Simulate JSON-like data
    original = (
        b'{"key": "value", "data": [1, 2, 3, 4, 5], "nested": {"a": 1, "b": 2}}' * 1000
    )

    compressed = zstd.compress(original, 6)
    decompressed = zstd.decompress(compressed)

    assert decompressed == original
    assert len(compressed) < len(original)

    log_compression_ratio("test_zstd_large_data", original, compressed)


def test_zstd_empty_data():
    """Test compression of empty data."""
    original = b""

    compressed = zstd.compress(original)
    decompressed = zstd.decompress(compressed)

    assert decompressed == original


def test_zstd_binary_data():
    """Test compression of binary data."""
    # Binary data (less compressible than text)
    original = bytes(range(256)) * 10

    compressed = zstd.compress(original)
    decompressed = zstd.decompress(compressed)

    assert decompressed == original

    log_compression_ratio("test_zstd_binary_data", original, compressed)


def test_zstd_highly_compressible():
    """Test highly compressible data (repetitive)."""
    original = b"A" * 10000

    compressed = zstd.compress(original, 22)
    decompressed = zstd.decompress(compressed)

    assert decompressed == original
    # Should achieve very high compression ratio
    assert len(compressed) < len(original) * 0.01  # Less than 1% of original

    log_compression_ratio("test_zstd_highly_compressible", original, compressed)


def test_zstd_roundtrip_with_different_levels():
    """Test roundtrip compression/decompression with different compression levels."""
    original = b"Test data for roundtrip with various level settings." * 50

    for level in range(1, 23):  # 1 to 22
        compressed = zstd.compress(original, level)
        decompressed = zstd.decompress(compressed)
        assert decompressed == original


def test_zstd_compression_ratio():
    """Test that compression actually reduces size for compressible data."""
    original = b"This is a highly repetitive string. " * 100

    compressed = zstd.compress(original)

    # Should achieve significant compression
    assert len(compressed) < len(original) * 0.5  # At least 50% reduction

    log_compression_ratio("test_zstd_compression_ratio", original, compressed)


def test_zstd_json_compression():
    """Test compression ratio for medium-sized JSON data."""
    # Create a realistic JSON structure
    data = {
        "users": [
            {
                "id": i,
                "name": f"User {i}",
                "email": f"user{i}@example.com",
                "age": 20 + (i % 50),
                "active": i % 2 == 0,
                "tags": ["python", "javascript", "rust", "go"],
                "metadata": {
                    "created_at": "2025-11-04T00:00:00Z",
                    "updated_at": "2025-11-04T12:00:00Z",
                    "permissions": ["read", "write", "execute"],
                },
            }
            for i in range(100)
        ],
        "total": 100,
        "page": 1,
        "per_page": 100,
    }

    # Convert to JSON string and encode to bytes
    json_str = json.dumps(data, indent=2)
    original = json_str.encode("utf-8")

    # Compress with good level
    compressed = zstd.compress(original, 10)
    decompressed = zstd.decompress(compressed)

    # Verify correctness
    assert decompressed == original

    # Calculate compression ratio
    compression_ratio = len(compressed) / len(original)

    log_compression_ratio("test_zstd_json_compression", original, compressed)

    # JSON should compress very well (lots of repetitive structure)
    assert compression_ratio < 0.2  # At least 80% reduction
    assert len(compressed) < len(original)
