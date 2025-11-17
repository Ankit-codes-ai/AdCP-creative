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
            max_retries: Maximum number of retries for async operations
            retry_delay: Delay between retries in seconds
            timeout: Maximum time to wait for completion in seconds
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
        
        Args:
            tool_name: Name of the MCP tool to call
            context_id: Context ID for the request
            input_data: Input data for the tool
            
        Returns:
            Response dictionary from the agent
            
        Raises:
            Exception: If request fails
        """
        request_body = {
            "tool_name": tool_name,
            "context_id": context_id,
            "input": input_data
        }
        
        try:
            # MCP endpoint is typically at /mcp/tools or /tools
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
        Poll for completion of async operation.
        
        Args:
            tool_name: Name of the tool
            context_id: Context ID
            initial_response: Initial response from the agent
            
        Returns:
            Final response when completed
            
        Raises:
            Exception: If operation fails or times out
        """
        status = initial_response.get("status", "unknown")
        
        # If already completed, return immediately
        if status == "completed":
            return initial_response
        
        # If failed, raise exception
        if status == "failed":
            error_msg = initial_response.get("error", "Operation failed")
            raise Exception(f"Operation failed: {error_msg}")
        
        # Poll for completion
        start_time = time.time()
        retry_count = 0
        last_response = initial_response
        
        while retry_count < self.max_retries:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > self.timeout:
                raise Exception(f"Operation timed out after {self.timeout} seconds")
            
            # Wait before next poll
            time.sleep(self.retry_delay)
            
            # Poll for status
            try:
                poll_input = {"context_id": context_id}
                response = self._make_mcp_request(
                    tool_name=f"{tool_name}_status",
                    context_id=context_id,
                    input_data=poll_input
                )
                
                status = response.get("status", "unknown")
                last_response = response
                
                logger.log_info(f"Poll {retry_count + 1}: Status = {status}")
                
                if status == "completed":
                    return response
                elif status == "failed":
                    error_msg = response.get("error", "Operation failed")
                    raise Exception(f"Operation failed: {error_msg}")
                
                retry_count += 1
                
            except Exception as e:
                # If polling fails, try to use the last known response
                logger.log_warning(f"Poll failed: {str(e)}")
                retry_count += 1
                continue
        
        # If we exhausted retries, return last response or raise
        if status in ["queued", "in_progress"]:
            raise Exception(f"Operation did not complete after {self.max_retries} retries")
        
        return last_response
    
    def call_tool(
        self,
        tool_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        wait_for_completion: bool = True
    ) -> Dict[str, Any]:
        """
        Call an MCP tool and optionally wait for completion.
        
        Args:
            tool_name: Name of the MCP tool
            input_data: Input data for the tool
            wait_for_completion: Whether to poll until completion
            
        Returns:
            Response dictionary
        """
        context_id = self._generate_context_id()
        input_data = input_data or {}
        
        # Make initial request
        response = self._make_mcp_request(
            tool_name=tool_name,
            context_id=context_id,
            input_data=input_data
        )
        
        # If async and we should wait, poll until complete
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
        
        Returns:
            List of format dictionaries with FormatID
        """
        try:
            response = self.call_tool(
                tool_name="list_creative_formats",
                input_data={},
                wait_for_completion=True
            )
            
            if response.get("status") == "completed":
                formats = response.get("result", {}).get("formats", [])
                
                # Add FormatID to each format (FormatID = agent_url + id)
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
        
        Args:
            format_id: FormatID to preview
            
        Returns:
            Preview data dictionary
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

