"""
Creative tasks module for AdCP operations.
Provides high-level functions for creative format listing and previewing.
"""

from typing import List, Dict, Any, Optional

try:
    from mcp_client import MCPClient
    from utils.logger import get_logger
except ImportError:
    from .mcp_client import MCPClient
    from .utils.logger import get_logger

logger = get_logger()


class CreativeTasks:
    """High-level interface for Creative Agent tasks."""
    
    def __init__(self, agent_url: str):
        """
        Initialize Creative Tasks.
        
        Args:
            agent_url: Base URL of the Creative Agent
        """
        self.agent_url = agent_url
        self.client = MCPClient(agent_url=agent_url)
    
    def get_creative_formats(self) -> List[Dict[str, Any]]:
        """
        Get all available creative formats.
        
        Returns:
            List of format dictionaries with FormatID
        """
        try:
            logger.log_info("Fetching creative formats...")
            formats = self.client.list_creative_formats()
            logger.log_info(f"Retrieved {len(formats)} creative formats")
            return formats
        except Exception as e:
            logger.log_error(f"Error getting creative formats: {str(e)}")
            raise
    
    def get_creative_preview(self, format_id: str) -> Dict[str, Any]:
        """
        Get preview for a creative format.
        
        Args:
            format_id: FormatID to preview
            
        Returns:
            Preview data dictionary
        """
        try:
            logger.log_info(f"Fetching preview for FormatID: {format_id}")
            preview = self.client.preview_creative(format_id)
            logger.log_info("Preview retrieved successfully")
            return preview
        except Exception as e:
            logger.log_error(f"Error getting creative preview: {str(e)}")
            raise


# Alternative: Direct fetch from S3 for formats (if MCP is not available)
def fetch_formats_from_s3() -> List[Dict[str, Any]]:
    """
    Fallback: Fetch formats directly from S3.
    
    Returns:
        List of format dictionaries
    """
    import requests
    
    formats_url = "https://adzymic-exercise.s3.ap-southeast-1.amazonaws.com/adcp/specs/formats.json"
    
    try:
        response = requests.get(formats_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Transform to expected format
        formats = []
        for item in data.get("formats", []):
            format_item = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "type": item.get("type", ""),
                "FormatID": item.get("id", "")  # Will be combined with agent_url in UI
            }
            formats.append(format_item)
        
        return formats
    except Exception as e:
        logger.log_error(f"Error fetching formats from S3: {str(e)}")
        return []

