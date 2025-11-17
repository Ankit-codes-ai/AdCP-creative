# mock_agent.py - Simulated MCP backend for Render deployment
from flask import Flask, request, jsonify
import uuid
import os

app = Flask(__name__)
state = {}

# The public Render URL (important!)
BASE_URL = os.environ.get("RENDER_URL", "https://adcp-creative.onrender.com")


# -----------------------------------------
# 1. DISCOVER TOOLS (REQUIRED BY MCP)
# -----------------------------------------
@app.route("/mcp/tools", methods=["GET"])
def list_tools():
    """Return available MCP tools"""
    return jsonify({
        "tools": [
            {"name": "list_creative_formats"},
            {"name": "preview_creative"}
        ]
    })


# -----------------------------------------
# 2. INVOKE TOOL (POST /mcp/tools)
# -----------------------------------------
@app.route("/mcp/tools", methods=["POST"])
def tools_root():
    payload = request.get_json(force=True)
    tool = payload.get("tool_name")
    context_id = payload.get("context_id") or str(uuid.uuid4())
    inp = payload.get("input", {})

    # First step → queued
    if context_id not in state:
        state[context_id] = {"step": 0, "tool": tool, "input": inp}

        return jsonify({
            "status": "queued",
            "operation_url": f"{BASE_URL}/mcp/tools/{context_id}",
            "context_id": context_id
        })

    # Progress workflow
    s = state[context_id]

    if s["step"] == 0:
        s["step"] = 1
        return jsonify({
            "status": "in_progress",
            "operation_url": f"{BASE_URL}/mcp/tools/{context_id}",
            "context_id": context_id
        })

    elif s["step"] == 1:
        s["step"] = 2

        if s["tool"] == "list_creative_formats":
            return jsonify({
                "status": "completed",
                "result": {
                    "formats": [
                        {"id": "banner_300x250", "name": "300x250 Banner"},
                        {"id": "story_vertical", "name": "Vertical Story Ad"}
                    ]
                }
            })

        elif s["tool"] == "preview_creative":
            fmt = s["input"].get("format_id", "unknown")
            return jsonify({
                "status": "completed",
                "result": {
                    "preview_url": f"mock://preview/{fmt}.png",
                    "format_id": fmt
                }
            })

        else:
            return jsonify({"status": "completed", "result": {}})

    else:
        return jsonify({"status": "completed", "result": {}})


# -----------------------------------------
# 3. POLLING ENDPOINT
# -----------------------------------------
@app.route("/mcp/tools/<context_id>", methods=["GET"])
def tools_poll(context_id):
    s = state.get(context_id)
    if not s:
        return jsonify({"status": "failed", "error": "no such context"}), 404

    # Step 0 → queued
    if s["step"] == 0:
        s["step"] = 1
        return jsonify({
            "status": "queued",
            "operation_url": f"{BASE_URL}/mcp/tools/{context_id}"
        })

    # Step 1 → in progress
    elif s["step"] == 1:
        s["step"] = 2
        return jsonify({
            "status": "in_progress",
            "operation_url": f"{BASE_URL}/mcp/tools/{context_id}"
        })

    # Step 2 → completed
    else:
        if s["tool"] == "list_creative_formats":
            return jsonify({
                "status": "completed",
                "result": {
                    "formats": [
                        {"id": "banner_300x250", "name": "300x250 Banner"},
                        {"id": "story_vertical", "name": "Vertical Story Ad"}
                    ]
                }
            })

        elif s["tool"] == "preview_creative":
            fmt = s["input"].get("format_id", "unknown")
            return jsonify({
                "status": "completed",
                "result": {
                    "preview_url": f"mock://preview/{fmt}.png",
                    "format_id": fmt
                }
            })

        return jsonify({"status": "completed", "result": {}})


# -----------------------------------------
# RUN SERVER
# -----------------------------------------
if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=PORT)
