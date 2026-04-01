import os
import json
import anthropic
from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)

# Allow all origins including file:// (null origin) for local HTML use
CORS(app, origins="*", supports_credentials=False)

client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))

@app.route("/", methods=["GET"])
def health():
    return {"status": "PropScope backend running"}, 200

@app.route("/v1/messages", methods=["POST", "OPTIONS"])
def proxy():
    # Handle CORS preflight
    if request.method == "OPTIONS":
        response = Response("", status=200)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        return response

    body = request.get_json()
    if not body:
        return {"error": "Invalid JSON"}, 400

    # Force correct model
    body["model"] = "claude-sonnet-4-6"

    # Cap tokens
    if not body.get("max_tokens") or body["max_tokens"] > 8000:
        body["max_tokens"] = 8000

    # Only include tools and tool_choice if tools are actually provided
    tools = body.get("tools", [])
    tool_choice = body.get("tool_choice", {"type": "auto"}) if tools else None

    def generate():
        try:
            kwargs = {
                "model": body["model"],
                "max_tokens": body["max_tokens"],
                "system": body.get("system", ""),
                "messages": body["messages"],
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            with client.messages.stream(**kwargs) as stream:
                message = stream.get_final_message()

            content_blocks = []
            for block in message.content:
                if block.type == "text":
                    content_blocks.append({"type": "text", "text": block.text})
                elif block.type == "tool_use":
                    content_blocks.append({
                        "type": "tool_use",
                        "name": block.name,
                        "input": block.input
                    })
                elif block.type == "tool_result":
                    content_blocks.append({
                        "type": "tool_result",
                        "content": block.content
                    })

            result = json.dumps({
                "id": message.id,
                "type": "message",
                "role": "assistant",
                "content": content_blocks,
                "model": message.model,
                "stop_reason": message.stop_reason,
                "usage": {
                    "input_tokens": message.usage.input_tokens,
                    "output_tokens": message.usage.output_tokens,
                }
            })
            yield result

        except anthropic.APIStatusError as e:
            yield json.dumps({"error": {"type": "api_error", "message": str(e)}})
        except Exception as e:
            yield json.dumps({"error": {"type": "server_error", "message": str(e)}})

    response = Response(
        stream_with_context(generate()),
        content_type="application/json"
    )
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
