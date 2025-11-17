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
        """
        self.agent_url = agent_url.rstrip('/')
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.session = requests.Session()
    
    def _generate_context_id(self) -> str:
        """Generate a unique context ID."""
        return str(uuid.uuid4())
    
    def _make_mcp_request(
        self,
        tool_name: str,
        context_id: str,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make an MCP request to the Creative Agent.
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
                timeout=30
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

    def _poll_until_complete(
        self,
        tool_name: str,
        context_id: str,
        initial_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Poll the operation_url returned by the agent until completed.
        """

        operation_url = initial_response.get("operation_url")
        if not operation_url:
            raise Exception("No operation_url returned by agent")

        status = initial_response.get("status", "unknown")
        if status == "completed":
            return initial_response
        if status == "failed":
            raise Exception(initial_response.get("error", "Operation failed"))

        start_time = time.time()

        while True:
            if time.time() - start_time > self.timeout:
                raise Exception("Operation timed out")

            time.sleep(self.retry_delay)

            try:
                response = self.session.get(operation_url, timeout=30)
                response.raise_for_status()
                result = response.json()

                logger.log_info(f"Poll: {result.get('status')} at {operation_url}")

                if result.get("status") == "completed":
                    return result

                if result.get("status") == "failed":
                    raise Exception(result.get("error", "Operation failed"))

            except Exception as e:
                logger.log_warning(f"Polling failed: {str(e)}")
                continue

    def call_tool(
        self,
        tool_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Call an MCP tool and optionally wait for completion.
        """
        context_id = self._generate_context_id()
        input_data = input_data or {}
        
        response = self._make_mcp_request(
            tool_name=tool_name,
            context_id=context_id,
            input_data=input_data
        )
        
        if wait_for_completion:
            status = response.get("status", "unknown")
            if status in ["queued", "in_progress"]:
                response = self._poll_until_complete(
                    tool_name=tool_name,
                    context_id=context_id,
                    initial_response=response
                )
        
        return response
    
    def list_creative_formats(self) -> List[Dict[str, Any]]:
        """
        List all available creative formats.
        """
        try:
            response = self.call_tool(
                tool_name="list_creative_formats",
                input_data={},
                wait_for_completion=True
            )
            
            if response.get("status") == "completed":
                formats = response.get("result", {}).get("formats", [])
                
                for format_item in formats:
                    format_id = format_item.get("id", "")
                    format_item["FormatID"] = f"{self.agent_url}/{format_id}"
                
                return formats
            else:
                raise Exception(f"Failed to list formats: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.log_error(f"Error listing creative formats: {str(e)}")
            raise
    
    def preview_creative(self, format_id: str) -> Dict[str, Any]:
        """
        Preview a creative by FormatID.
        """
        try:
            response = self.call_tool(
                tool_name="preview_creative",
                input_data={"format_id": format_id},
                wait_for_completion=True
            )
            
            if response.get("status") == "completed":
                return response.get("result", {})
            else:
                raise Exception(f"Failed to preview creative: {response.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.log_error(f"Error previewing creative: {str(e)}")
            raise
