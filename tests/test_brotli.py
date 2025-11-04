"""Tests for Brotli compression/decompression.

Installation:
    uv add brotli
"""

import json
import logging

import brotli

logger = logging.getLogger(__name__)


def log_compression_ratio(label: str, original: bytes, compressed: bytes) -> None:
    """Log compression ratio with test label."""
    ratio = len(compressed) / len(original)
    logger.info(f"{label}: {len(original)} -> {len(compressed)} bytes ({ratio:.2%})")


def test_brotli_basic_compression():
    """Test basic compression and decompression."""
    original = b"Hello, World! This is a test string for Brotli compression."

    # Compress
    compressed = brotli.compress(original)

    # Decompress
    decompressed = brotli.decompress(compressed)

    # Verify
    assert decompressed == original
    assert len(compressed) < len(original)

    log_compression_ratio("test_brotli_basic_compression", original, compressed)


def test_brotli_compression_quality_levels():
    """Test different compression quality levels (0-11)."""
    original = b"The quick brown fox jumps over the lazy dog. " * 100

    results = {}
    for quality in [0, 5, 9, 11]:  # 0=fastest, 11=best compression
        compressed = brotli.compress(original, quality=quality)
        decompressed = brotli.decompress(compressed)

        assert decompressed == original
        results[quality] = len(compressed)

        log_compression_ratio(
            f"test_brotli_compression_quality_levels[quality={quality}]",
            original,
            compressed,
        )

    # All quality levels should work and produce valid output
    # Note: Higher quality doesn't always mean smaller size for all data
    assert all(size > 0 for size in results.values())
    assert len(results) == 4


def test_brotli_large_data():
    """Test compression of larger data."""
    # Simulate JSON-like data
    original = (
        b'{"key": "value", "data": [1, 2, 3, 4, 5], "nested": {"a": 1, "b": 2}}' * 1000
    )

    compressed = brotli.compress(original, quality=6)
    decompressed = brotli.decompress(compressed)

    assert decompressed == original
    assert len(compressed) < len(original)

    log_compression_ratio("test_brotli_large_data", original, compressed)


def test_brotli_empty_data():
    """Test compression of empty data."""
    original = b""

    compressed = brotli.compress(original)
    decompressed = brotli.decompress(compressed)

    assert decompressed == original


def test_brotli_binary_data():
    """Test compression of binary data."""
    # Binary data (less compressible than text)
    original = bytes(range(256)) * 10

    compressed = brotli.compress(original)
    decompressed = brotli.decompress(compressed)

    assert decompressed == original

    log_compression_ratio("test_brotli_binary_data", original, compressed)


def test_brotli_highly_compressible():
    """Test highly compressible data (repetitive)."""
    original = b"A" * 10000

    compressed = brotli.compress(original, quality=11)
    decompressed = brotli.decompress(compressed)

    assert decompressed == original
    # Should achieve very high compression ratio
    assert len(compressed) < len(original) * 0.01  # Less than 1% of original

    log_compression_ratio("test_brotli_highly_compressible", original, compressed)


def test_brotli_roundtrip_with_different_qualities():
    """Test roundtrip compression/decompression with different quality levels."""
    original = b"Test data for roundtrip with various quality settings." * 50

    for quality in range(0, 12):  # 0 to 11
        compressed = brotli.compress(original, quality=quality)
        decompressed = brotli.decompress(compressed)
        assert decompressed == original


def test_brotli_compression_ratio():
    """Test that compression actually reduces size for compressible data."""
    original = b"This is a highly repetitive string. " * 100

    compressed = brotli.compress(original)

    # Should achieve significant compression
    assert len(compressed) < len(original) * 0.5  # At least 50% reduction

    log_compression_ratio("test_brotli_compression_ratio", original, compressed)


def test_brotli_json_compression():
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

    # Compress with good quality
    compressed = brotli.compress(original, quality=9)
    decompressed = brotli.decompress(compressed)

    # Verify correctness
    assert decompressed == original

    # Calculate compression ratio
    compression_ratio = len(compressed) / len(original)

    log_compression_ratio("test_brotli_json_compression", original, compressed)

    # JSON should compress very well (lots of repetitive structure)
    assert compression_ratio < 0.2  # At least 80% reduction
    assert len(compressed) < len(original)
