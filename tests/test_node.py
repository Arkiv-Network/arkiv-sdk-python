"""Tests for Arkiv node connection and basic functionality."""

import asyncio
import json
import logging

import pytest
import requests

from arkiv.node import ArkivNode

logger = logging.getLogger(__name__)


class TestArkivNodeConnections:
    """Test basic node connectivity - works for both containerized and external nodes."""

    def test_node_connection_http(self, arkiv_node: ArkivNode) -> None:
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

    def test_node_connection_ws(self, arkiv_node: ArkivNode) -> None:
        """Check if the Arkiv node WebSocket endpoint is available and responsive."""
        # Try to import websockets, skip test if not available
        try:
            import websockets
        except ImportError:
            pytest.skip("websockets package not available")

        async def test_ws_connection() -> dict[str, object]:
            """Test WebSocket connection and send a JSON-RPC request."""
            async with websockets.connect(
                arkiv_node.ws_url, open_timeout=5
            ) as websocket:
                # Send a JSON-RPC request over WebSocket
                request = {
                    "jsonrpc": "2.0",
                    "method": "eth_chainId",
                    "params": [],
                    "id": 1,
                }

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
        assert response.get("id") == 1, (
            "WebSocket response should have matching request id"
        )

        logger.info(f"WebSocket connection successful: {arkiv_node.ws_url}")
        logger.info(f"Chain ID response: {response.get('result', 'N/A')}")


class TestContainerizedNode:
    """Tests specific to containerized (local Docker) nodes."""

    def test_node_container_properties(self, arkiv_container: ArkivNode) -> None:
        """Test that containerized nodes expose container properties."""
        # Should have access to container
        assert arkiv_container.container is not None
        assert arkiv_container.http_port > 0
        assert arkiv_container.ws_port > 0

    def test_node_container_stop_start(self, arkiv_container: ArkivNode) -> None:
        """Test that containerized nodes can be stopped and started."""
        # Should be running initially
        assert arkiv_container.is_running

        # Stop the node
        arkiv_container.stop()
        assert not arkiv_container.is_running
        with pytest.raises(
            RuntimeError,
            match=r"Node is not running\. Call start\(\) first or use context manager\.",
        ):
            _ = arkiv_container.http_url

        with pytest.raises(
            RuntimeError,
            match=r"Node is not running\. Call start\(\) first or use context manager\.",
        ):
            _ = arkiv_container.ws_url

        with pytest.raises(
            RuntimeError,
            match=r"Node is not running\. Call start\(\) first or use context manager\.",
        ):
            _ = arkiv_container.http_port

        with pytest.raises(
            RuntimeError,
            match=r"Node is not running\. Call start\(\) first or use context manager\.",
        ):
            _ = arkiv_container.ws_port

        # Stop a 2nd time should be no-op
        arkiv_container.stop()
        assert not arkiv_container.is_running

        # Start the node again
        arkiv_container.start()
        assert arkiv_container.is_running
        assert arkiv_container.http_port > 0
        assert arkiv_container.ws_port > 0

        # Start a 2nd time should be no-op
        arkiv_container.start()
        assert arkiv_container.is_running
        assert arkiv_container.http_port > 0
        assert arkiv_container.ws_port > 0

    def test_node_container_arkiv_help_command(
        self, arkiv_container: ArkivNode
    ) -> None:
        """Check if the Arkiv node help command is available via container CLI."""
        help_command = ["golembase", "account", "help"]
        exit_code, output = arkiv_container.container.exec(help_command)

        assert exit_code == 0, f"Help command should succeed, got exit code {exit_code}"
        assert b"help" in output.lower() or b"usage" in output.lower(), (
            "Help output should contain help or usage information"
        )

        logger.info(
            f"Account help command: {help_command}, exit_code: {exit_code}, output:\n{output.decode()}"
        )

    def test_node_container_fund_account(self, arkiv_container: ArkivNode) -> None:
        """Test that fund_account works for containerized nodes."""
        from arkiv.account import NamedAccount

        # Create a test account
        account = NamedAccount.create("test_fund")

        # Should be able to fund it
        arkiv_container.fund_account(account)

        # No exception means success
        logger.info(f"Successfully funded account {account.name}")

    def test_node_container_context_manager(self, arkiv_container: ArkivNode) -> None:
        """Test that containerized nodes work with context managers."""
        # arkiv_container fixture already uses context manager, just verify it's running
        assert arkiv_container.is_running
        assert not arkiv_container.is_external


class TestExternalNode:
    """Tests specific to external (remote) nodes - uses Kaolin testnet."""

    def test_node_external_urls(self, arkiv_testnet: ArkivNode) -> None:
        """Test that external nodes have proper URLs configured."""

        # Should have URLs
        assert arkiv_testnet.http_url.startswith("http")
        assert arkiv_testnet.ws_url.startswith("ws")

        logger.info(f"External node HTTP URL: {arkiv_testnet.http_url}")
        logger.info(f"External node WS URL: {arkiv_testnet.ws_url}")

    def test_node_external_no_container(self, arkiv_testnet: ArkivNode) -> None:
        """Test that external nodes raise errors when accessing container properties."""

        # Should raise error when accessing container
        with pytest.raises(RuntimeError, match="External nodes do not have containers"):
            _ = arkiv_testnet.container

        # Should raise error when accessing ports
        with pytest.raises(
            RuntimeError, match="External nodes do not expose port information"
        ):
            _ = arkiv_testnet.http_port

        with pytest.raises(
            RuntimeError, match="External nodes do not expose port information"
        ):
            _ = arkiv_testnet.ws_port

    def test_node_external_cannot_start(self, arkiv_testnet: ArkivNode) -> None:
        """Test that external nodes cannot be started."""

        with pytest.raises(RuntimeError, match="Cannot start external node"):
            arkiv_testnet.start()

    def test_node_external_cannot_stop(self, arkiv_testnet: ArkivNode) -> None:
        """Test that external nodes cannot be stopped."""

        with pytest.raises(RuntimeError, match="Cannot stop external node"):
            arkiv_testnet.stop()

    def test_node_external_cannot_fund(self, arkiv_testnet: ArkivNode) -> None:
        """Test that external nodes cannot fund accounts."""

        from arkiv.account import NamedAccount

        account = NamedAccount.create("test_external")

        with pytest.raises(RuntimeError, match="Cannot fund account on external node"):
            arkiv_testnet.fund_account(account)

    def test_node_external_context_manager(self, arkiv_testnet: ArkivNode) -> None:
        """Test that external nodes work safely with context managers."""

        # Should work without errors (no-op)
        with arkiv_testnet as node:
            assert node.is_running
            assert node.http_url == arkiv_testnet.http_url

        # Node should still be running after context exit
        assert arkiv_testnet.is_running

    def test_node_external_is_external(self, arkiv_testnet: ArkivNode) -> None:
        """Verify that external nodes are properly identified."""

        assert arkiv_testnet.is_external
