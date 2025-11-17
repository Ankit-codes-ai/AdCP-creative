"""
Logging utility for AdCP Agentic Platform.
Logs all MCP calls with tool_name, context_id, request body, response status, and timestamps.
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class AdCPLogger:
    """Logger for AdCP MCP operations."""
    
    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize the logger.
        
        Args:
            log_file: Optional path to log file. If None, logs to 'adcp_platform.log'
        """
        self.log_file = log_file or "adcp_platform.log"
        self.logger = logging.getLogger("adcp_platform")
        self.logger.setLevel(logging.INFO)
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers = []
        
        # File handler
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def log_mcp_call(
        self,
        tool_name: str,
        context_id: str,
        request_body: Dict[str, Any],
        response_status: str,
        response_data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        Log an MCP call with all relevant information.
        
        Args:
            tool_name: Name of the MCP tool being called
            context_id: Context ID for the request
            request_body: Full request body
            response_status: Status from response
            response_data: Optional response data
            error: Optional error message
        """
        timestamp = datetime.now().isoformat()
        
        log_entry = {
            "timestamp": timestamp,
            "tool_name": tool_name,
            "context_id": context_id,
            "request_body": request_body,
            "response_status": response_status,
            "response_data": response_data,
            "error": error
        }
        
        log_message = f"""
=== MCP Call Log ===
Timestamp: {timestamp}
Tool Name: {tool_name}
Context ID: {context_id}
Request Body: {json.dumps(request_body, indent=2)}
Response Status: {response_status}
"""
        
        if response_data:
            log_message += f"Response Data: {json.dumps(response_data, indent=2)}\n"
        
        if error:
            log_message += f"Error: {error}\n"
            self.logger.error(log_message)
        else:
            self.logger.info(log_message)
    
    def log_info(self, message: str):
        """Log an info message."""
        self.logger.info(message)
    
    def log_error(self, message: str):
        """Log an error message."""
        self.logger.error(message)
    
    def log_warning(self, message: str):
        """Log a warning message."""
        self.logger.warning(message)


# Global logger instance
_logger_instance: Optional[AdCPLogger] = None


def get_logger(log_file: Optional[str] = None) -> AdCPLogger:
    """Get or create the global logger instance."""
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = AdCPLogger(log_file)
    return _logger_instance

