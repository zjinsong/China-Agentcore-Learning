"""专家 Agent:A2A 协议(JSON-RPC 2.0 + Agent Card)。

对应第 4 章的 A2A 协议契约:
  - 监听根路径 /
  - Agent Card 在 /.well-known/agent-card.json
  - 请求体是 JSON-RPC 2.0,method = message/send

真实部署到 AgentCore Runtime 时端口是 9000、协议声明 serverProtocol="A2A",
入站用 SigV4。这里用标准库 HTTP server 本地跑,便于理解协议结构。
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from harness import CATALOG
from tools import REGISTRY

NAME = sys.argv[1] if len(sys.argv) > 1 else "monitoring"
CONFIG = CATALOG["experts"][NAME]
CAPS = {c["id"]: c for c in CONFIG["capabilities"]}


def agent_card():
    """A2A 的自我描述:别的 Agent 靠它知道你能干什么。"""
    return {
        "protocolVersion": "0.3.0",
        "name": NAME,
        "description": CONFIG["description"],
        "version": "1.0.0",
        "preferredTransport": "JSONRPC",
        "capabilities": {"streaming": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["application/json"],
        "skills": [
            {"id": c["id"], "name": c["id"], "description": c["description"],
             "tags": [c["tool"]]}
            for c in CONFIG["capabilities"]
        ],
        "securitySchemes": {"awsIam": {"type": "http", "scheme": "AWS4-HMAC-SHA256"}},
    }


def execute(params):
    """执行一个能力,返回证据。能力 id 不认就拒绝 —— 不猜、不兜底。"""
    message = params.get("message", {})
    meta = message.get("metadata", {})
    cap = CAPS.get(meta.get("capability"))
    if cap is None:
        raise ValueError(f"{NAME} 没有能力 {meta.get('capability')}")

    args = {"region": meta.get("region", CATALOG["region"])}
    args.update(meta.get("dependency_input", {}))
    data = REGISTRY[cap["tool"]](**args)

    missing = [o for o in cap["outputs"] if o not in data]
    if missing:
        raise ValueError(f"能力 {cap['id']} 未产出声明的交付项: {missing}")

    return {
        "expert": NAME,
        "capability": cap["id"],
        "tool": cap["tool"],
        "data": data,
        "text": "\n".join(p.get("text", "") for p in message.get("parts", [])),
    }


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/.well-known/agent-card.json":
            self._send(agent_card())
        elif self.path == "/ping":
            self._send({"status": "Healthy"})
        else:
            self._send({"error": "not found"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            request = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._send({"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": "Parse error"}}, 400)
            return

        request_id = request.get("id")
        if request.get("method") != "message/send":
            self._send({"jsonrpc": "2.0", "id": request_id,
                        "error": {"code": -32601, "message": "Method not found"}})
            return
        try:
            self._send({"jsonrpc": "2.0", "id": request_id,
                        "result": execute(request.get("params", {}))})
        except Exception as error:                      # noqa: BLE001 - 返回给调用方而不是崩掉服务
            self._send({"jsonrpc": "2.0", "id": request_id,
                        "error": {"code": -32000, "message": str(error)}})

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    port = CONFIG["port"]
    print(f"[{NAME}] A2A 服务监听 :{port} (card: /.well-known/agent-card.json)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
