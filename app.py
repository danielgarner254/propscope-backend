import os
import json
import anthropic
from flask import Flask, request, Response, stream_with_context
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))

@app.route("/", methods=["GET"])
def health():
    return {"status": "PropScope backend running"}, 200

@app.route("/v1/messages", methods=["POST", "OPTIONS"])
def proxy():
    if request.method == "OPTIONS":
        return {}, 200

    body = request.get_json()
    if not body:
        return {"error": "Invalid JSON"}, 400

    body["model"] = "claude-sonnet-4-6"

    if body.get("max_tokens", 0) > 8000:
        body["max_tokens"] = 8000

    def generate():
        with client.messages.stream(
            model=body["model"],
            max_tokens=body["max_tokens"],
            system=body.get("system", ""),
            tools=body.get("tools", []),
            tool_choice=body.get("tool_choice", {"type": "auto"}),
            messages=body["messages"],
        ) as stream:
            message = stream.get_final_message()

        yield json.dumps({
            "id": message.id,
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": block.type, "text": block.text}
                if block.type == "text"
                else {"type": block.type, "name": block.name, "input": block.input}
                for block in message.content
            ],
            "model": message.model,
            "stop_reason": message.stop_reason,
            "usage": {
                "input_tokens": message.usage.input_tokens,
                "output_tokens": message.usage.output_tokens,
            }
        })

    return Response(
        stream_with_context(generate()),
        content_type="application/json"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
