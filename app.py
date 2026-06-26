import asyncio
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from loguru import logger

from config import Config
from orchestrator import handle_user_message

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/health", methods=["GET"])
def health():
    return jsonify(
        {
            "status": "ok",
            "service": "Hybrid Flask RAG MCP Chatbot"
        }
    )


@app.route("/api/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json(force=True)

        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify(
                {
                    "success": False,
                    "error": "Message is required."
                }
            ), 400

        result = asyncio.run(handle_user_message(user_message))

        return jsonify(
            {
                "success": True,
                "answer": result["answer"],
                "intent": result["intent"],
                "used_tools": result["used_tools"],
                "sources": result["sources"]
            }
        )

    except Exception as e:
        logger.exception("Chat API failed")

        return jsonify(
            {
                "success": False,
                "error": "Chat processing failed.",
                "details": str(e)
            }
        ), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
