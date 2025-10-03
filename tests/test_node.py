"""Tests for Arkiv node connection and basic functionality."""

import asyncio
import json
import logging

import pytest
import requests

from arkiv.node import ArkivNode

logger = logging.getLogger(__name__)


def test_node_connection_http(arkiv_node: ArkivNode) -> None:
    """Check if the Arkiv node is available and responsive via JSON-RPC."""
    # Use JSON-RPC call - works for both dev and production nodes
    rpc_payload = {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}

    response = requests.post(
        arkiv_node.http_url,
        json=rpc_payload,
        headers={"Content-Type": "application/json"},
        timeout=10,
    )

    assert response.status_code == 200, (
        f"Arkiv node should respond with 200 OK, got {response.status_code}"
    )

    # Verify it's a proper JSON-RPC response
    json_response = response.json()
    assert "result" in json_response or "error" in json_response, (
        "Response should contain either 'result' or 'error' field"
    )
    assert json_response.get("jsonrpc") == "2.0", (
        "Response should have jsonrpc version 2.0"
    )

    logger.info(f"HTTP connection successful: {arkiv_node.http_url}")
    logger.info(f"Request response: {json_response}")


def test_node_connection_ws(arkiv_node: ArkivNode) -> None:
    """Check if the Arkiv node WebSocket endpoint is available and responsive."""
    # Try to import websockets, skip test if not available
    try:
        import websockets
    except ImportError:
        pytest.skip("websockets package not available")

    async def test_ws_connection() -> dict[str, object]:
        """Test WebSocket connection and send a JSON-RPC request."""
        async with websockets.connect(arkiv_node.ws_url, open_timeout=5) as websocket:
            # Send a JSON-RPC request over WebSocket
            request = {"jsonrpc": "2.0", "method": "eth_chainId", "params": [], "id": 1}

            await websocket.send(json.dumps(request))
            response = await websocket.recv()

            return json.loads(response)  # type: ignore[no-any-return]

    # Run the async test
    response = asyncio.run(test_ws_connection())
    logger.info(f"WebSocket response: {response}")

    # Verify the WebSocket JSON-RPC response
    assert "result" in response or "error" in response, (
        "WebSocket response should contain either 'result' or 'error' field"
    )
    assert response.get("jsonrpc") == "2.0", (
        "WebSocket response should have jsonrpc version 2.0"
    )
    assert response.get("id") == 1, "WebSocket response should have matching request id"

    logger.info(f"WebSocket connection successful: {arkiv_node.ws_url}")
    logger.info(f"Chain ID response: {response.get('result', 'N/A')}")


def test_node_arkiv_help(arkiv_node: ArkivNode) -> None:
    """Check if the Arkiv node help command is available and responsive."""
    if arkiv_node.is_external():
        pytest.skip("Skipping help command test for external nodes")

    help_command = ["golembase", "account", "help"]
    exit_code, output = arkiv_node.container.exec(help_command)
    logger.info(
        f"Account help command: {help_command}, exit_code: {exit_code}, output:\n{output.decode()}"
    )
