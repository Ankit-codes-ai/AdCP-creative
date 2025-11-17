"""
MCP Client for communicating with AdCP Creative Agent.
Handles MCP protocol requests and responses with async status polling.
"""

import json
import time
import uuid
from typing import Dict, Any, Optional, List
import requests

try:
    from utils.logger import get_logger
except ImportError:
    from .utils.logger import get_logger

logger = get_logger()


class MCPClient:
    """Client for MCP protocol communication with Creative Agent."""

    def __init__(
        self,
        agent_url: str,
        max_retries: int = 30,
        retry_delay: float = 2.0,
        timeout: int = 300
    ):
        """
        Initialize MCP client.

        Args:
            agent_url: Base URL of the Creative Agent
            max_retries: Maximum times to poll before giving up
            retry_delay: Seconds to wait between polls
            timeout: Maximum total waiting time
        """
        self.agent_url = agent_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.session = requests.Session()

    def _generate_context_id(self) -> str:
        """Generate unique context ID for async tool calls."""
        return str(uuid.uuid4())

    def _make_mcp_request(
        self,
        tool_name: str,
        context_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generic MCP POST request to invoke a tool.

        Returns:
            Response JSON dict

        Raises:
            Exception if network or HTTP error occurs
        """

        request_body = {
            "tool_name": tool_name,
            "context_id": context_id,
            "input": input_data
        }

        try:
            endpoint = f"{self.agent_url}/mcp/tools"
            logger.log_info(f"Making MCP request to {endpoint}")

            response = self.session.post(
                endpoint,
                json=request_body,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            result = response.json()

            logger.log_mcp_call(
                tool_name=tool_name,
                context_id=context_id,
                request_body=request_body,
                response_status=result.get("status", "unknown"),
                response_data=result
            )

            return result

        except requests.exceptions.RequestException as e:
            error_msg = f"MCP request failed: {str(e)}"

            logger.log_mcp_call(
                tool_name=tool_name,
                context_id=context_id,
                request_body=request_body,
                response_status="failed",
                error=error_msg
            )

            raise Exception(error_msg) from e

    # -------------------------------------------------------------------------
    # NEW POLLING FUNCTION — CLEAN, SIMPLE, COMMENTED, INDENT FIXED
    # -------------------------------------------------------------------------
    def _poll_until_complete(
        self,
        tool_name: str,
        context_id: str,
        initial_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Poll the operation_url returned by the agent until the task completes.

        Args:
            tool_name: The tool being executed
            context_id: The unique async operation identifier
            initial_response: First response returned by MCP

        Returns:
            Final completed JSON response

        Raises:
            Exception if failed or timed out
        """

        # Extract operation URL (Render-safe)
        operation_url = initial_response.get("operation_url")
        if not operation_url:
            raise Exception("No operation_url returned by agent")

        status = initial_response.get("status", "unknown")

        # If immediately completed
        if status == "completed":
            return initial_response

        if status == "failed":
            raise Exception(initial_response.get("error", "Operation failed"))

        logger.log_info(f"Starting polling at {operation_url}")

        start_time = time.time()

        # Poll until finished or timeout
        while True:

            # Check global timeout
            if time.time() - start_time > self.timeout:
                raise Exception("Operation timed out")

            time.sleep(self.retry_delay)

            try:
                # Poll by GET request
                response = self.session.get(operation_url, timeout=30)
                response.raise_for_status()
                data = response.json()

                logger.log_info(
                    f"Poll result: status={data.get('status')} "
                    f"context_id={context_id}"
                )

                if data.get("status") == "completed":
                    return data

                if data.get("status") == "failed":
                    raise Exception(data.get("error", "Operation failed"))

            except Exception as e:
                # Do NOT crash—continue polling gracefully
                logger.log_warning(f"Polling error: {str(e)}")
                continue

    # -------------------------------------------------------------------------

    def call_tool(
        self,
        tool_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Call an MCP tool and handle async polling.

        Returns:
            Final tool result dictionary
        """
        context_id = self._generate_context_id()
        input_data = input_data or {}

        # Initial call
        response = self._make_mcp_request(
            tool_name=tool_name,
            context_id=context_id,
            input_data=input_data
        )

        # Poll if async
        if wait_for_completion:
            status = response.get("status", "unknown")
            if status in ["queued", "in_progress"]:
                response = self._poll_until_complete(
                    tool_name, context_id, response
                )

        return response

    # -------------------------------------------------------------------------

    def list_creative_formats(self) -> List[Dict[str, Any]]:
        """Fetch all creative formats via MCP."""
        try:
            response = self.call_tool("list_creative_formats", {}, True)

            if response.get("status") == "completed":
                formats = response.get("result", {}).get("formats", [])
                for f in formats:
                    f["FormatID"] = f"{self.agent_url}/{f.get('id', '')}"
                return formats

            raise Exception("Listing formats failed")

        except Exception as e:
            logger.log_error(f"Error listing creative formats: {str(e)}")
            raise

    def preview_creative(self, format_id: str) -> Dict[str, Any]]:
        """Fetch preview for a given creative format."""
        try:
            response = self.call_tool(
                "preview_creative",
                {"format_id": format_id},
                True
            )

            if response.get("status") == "completed":
                return response.get("result", {})

            raise Exception("Preview call failed")

        except Exception as e:
            logger.log_error(f"Error previewing creative: {str(e)}")
            raise
