# AdCP Creative Agentic Platform

##1 Overview

This is an agentic platform for interacting with AdCP Creative Agents via the MCP (Model Context Protocol). The application provides a client-side interface for listing creative formats and previewing creative assets. Since AdCP does not provide a real backend for assessment candidates, the project includes a local mock MCP backend that simulates the protocol's asynchronous workflow (queued → in_progress → completed states).

The platform consists of a Streamlit-based UI, an MCP client for protocol communication, high-level creative task abstractions, and utility modules for logging.

## User Preferences

Preferred communication style: Simple, everyday language.

##2 System Architecture

### Frontend Architecture

**Technology**: Streamlit web framework

The UI (`ui_app.py`) provides an interactive interface for:
- Listing available creative formats
- Previewing creative assets
- Configuring the agent URL endpoint

**Design Pattern**: Session state management
- Uses Streamlit's session state to maintain application data across reruns
- Stores formats list, selected format ID, preview data, and agent URL
- Enables stateful interactions without backend session management

### Backend Architecture

**MCP Client Layer** (`mcp_client.py`)
- Implements the MCP protocol for communication with Creative Agents
- Handles asynchronous request/response patterns with polling
- Manages context IDs for operation tracking
- Implements retry logic with configurable max retries, delays, and timeouts
- Uses requests library with session management for HTTP communication


**Task Abstraction Layer** (`creative_tasks.py`)
- Provides high-level interface for creative operations
- Wraps MCP client with domain-specific methods
- Handles format listing and preview retrieval
- Implements error handling and logging



### Mock Backend

**Technology**: Flask REST API (`mock_agent.py`)

Simulates the MCP protocol for local development and testing:
- Maintains in-memory state for operation tracking
- Returns progressive status updates (queued → in_progress → completed)
- Provides mock creative format data

** this mock enables full local testing. The stateful simulation allows the  logic to be properly tested.

### Logging Architecture

**Custom Logger** (`utils/logger.py`)

Implements structured logging for MCP operations:
- Dual output: file (`adcp_platform.log`) and console
- Logs MCP calls with tool names, context IDs, request/response data, and timestamps
- Uses Python's standard logging module with custom formatting



##3. External Dependencies

### Core Dependencies

- **Streamlit** (>=1.28.0): Web UI framework for building the interactive interface
- **Requests** (>=2.31.0): HTTP client library for MCP protocol communication
- **Flask** (>=3.0.0): Lightweight web framework for the mock backend server
- **python-dotenv** (>=1.0.0): Environment configuration management

### Protocol Integration

**MCP (Model Context Protocol)**
- Custom implementation for AdCP Creative Agent communication
- Asynchronous request/response pattern with operation URLs
- Context-based operation tracking
- Status polling mechanism: queued → in_progress → completed

### Data Sources

**S3 Integration** (mentioned in pdf)
- Creative format data fetched from AWS S3
- Base URL: `https://adzymic-exercise.s3.ap-southeast-1.amazonaws.com/adcp`
- Used as alternative/primary data source for creative formats

**Note**: The codebase references `fetch_formats_from_s3` in imports, suggesting S3 is used as the actual data source while the mock backend provides fallback/testing data.

### Runtime Requirements

- Python 3.x environment
- No database dependencies (in-memory state management)
- No authentication/authorization mechanisms currently implemented
- Local development: Flask server on port 8000, Streamlit on default port

##4. How the Workflow Is Structured

1. UI calls:
   - `list_creative_formats`
   - `preview_creative`
2. Creative Agent builds MCP requests and forwards them to the MCP Client.  
3. MCP Client:
   - sends `POST /mcp/tools`
   - handles `queued → in_progress → completed`
   - polls `operation_url` until done  
4. UI displays formats and preview results.

## 5. Design Rationale (Context Handling & Error Recovery)

### Context Handling
- Each MCP request uses a `context_id`.
- New IDs are generated if missing.
- IDs persist during polling.
- Fully aligned with AdCP async specification.

### Error Recovery
- Retries on non-completed states.
- Logs tool name, context_id, status.
- Clean handling for timeouts, 404/405, and malformed responses.
- All main functions include docstrings or comments.

## 6. Running the Platform (Local Instructions)
Step 1: Install dependency
            -pip install flask streamlit requests

Step 2: Start the MCP Backend
            -python mock_agent.py
             Backend runs at: http://127.0.0.1:8000
            
Step 3: Start the UI
            -streamlit run ui_app.py
            Test the agentic platform at:http://localhost:8501
*(Streamlit may choose another available port such as 5000.)*

Step 4:Enter MCP URL inside UI under Creative Agent URL configuration:
            http://127.0.0.1:8000

## 6. Files Included

- ui_app.py — UI  
- creative_tasks.py — Creative Agent logic  
- mcp_client.py — MCP protocol client  
- mock_agent.py — Local MCP backend  
- utils/logger.py — Logging  
- requirements.txt — Dependencies  
- README.md — This document