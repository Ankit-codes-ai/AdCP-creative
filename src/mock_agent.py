# mock_agent.py - local simulated MCP backend
from flask import Flask, request, jsonify
import uuid

app = Flask(__name__)
state = {}


@app.route("/mcp", methods=["POST"])
def mcp():
    payload = request.get_json(force=True)
    tool = payload.get("tool_name")
    context_id = payload.get("context_id") or str(uuid.uuid4())
    inp = payload.get("input", {})

    if context_id not in state:
        state[context_id] = {"step": 0, "tool": tool, "input": inp}
        return jsonify({
            "status": "queued",
            "operation_url": f"http://127.0.0.1:8000/mcp/tools/{context_id}",
            "context_id": context_id
        })

    s = state[context_id]

    if s["step"] == 0:
        s["step"] = 1
        return jsonify({
            "status":
            "in_progress",
            "operation_url":
            f"http://127.0.0.1:8000/mcp/tools/{context_id}"
        })

    elif s["step"] == 1:
        s["step"] = 2
        if s["tool"] == "list_creative_formats":
            return jsonify({
                "status": "completed",
                "result": {
                    "formats": [{
                        "id": "banner_300x250",
                        "name": "300x250 Banner"
                    }, {
                        "id": "story_vertical",
                        "name": "Vertical Story Ad"
                    }]
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


@app.route("/ops/<context_id>", methods=["GET"])
def ops(context_id):
    s = state.get(context_id)
    if not s:
        return jsonify({"status": "failed", "error": "no such context"}), 404

    if s["step"] == 0:
        s["step"] = 1
        return jsonify({
            "status":
            "queued",
            "operation_url":
            f"http://127.0.0.1:8000/mcp/tools/{context_id}"
        })

    elif s["step"] == 1:
        s["step"] = 2
        return jsonify({
            "status":
            "in_progress",
            "operation_url":
            f"http://127.0.0.1:8000/mcp/tools/{context_id}"
        })

    else:
        if s["tool"] == "list_creative_formats":
            return jsonify({
                "status": "completed",
                "result": {
                    "formats": [{
                        "id": "banner_300x250",
                        "name": "300x250 Banner"
                    }, {
                        "id": "story_vertical",
                        "name": "Vertical Story Ad"
                    }]
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


# -------------------------------------------------------
# ADD THESE REQUIRED ENDPOINTS FOR REAL MCP COMPATIBILITY
# -------------------------------------------------------


@app.route("/mcp/tools", methods=["POST"])
def tools_root():
    """Required MCP endpoint: POST /mcp/tools"""
    return mcp()


@app.route("/mcp/tools/<context_id>", methods=["GET"])
def tools_poll(context_id):
    """Required MCP endpoint: GET /mcp/tools/<context_id>"""
    return ops(context_id)


# -------------------------------------------------------

if __name__ == "__main__":
    import os
    PORT = int(os.environ.get("PORT", "8000"))
    app.run(host="0.0.0.0", port=PORT)
