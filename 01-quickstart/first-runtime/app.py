"""Minimal AgentCore-compatible learning example. No credentials or AWS calls."""
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()


@app.entrypoint
def handler(event, context):
    prompt = str(event.get("prompt", ""))[:500]
    return {"answer": f"Received: {prompt}", "mode": "learning-example"}


if __name__ == "__main__":
    app.run()
