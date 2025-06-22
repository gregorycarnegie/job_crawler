#!/usr/bin/env python3

import asyncio
import json
import logging
import sys
from typing import Any

from param_job_agent import ParamJobAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("param-job-agent")


class JSONRPCServer:
    def __init__(self) -> None:
        self.agent = ParamJobAgent()

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method")
        req_id = request.get("id")
        if method == "tools/call":
            params = request.get("params", {})
            name = params.get("name")
            arguments = params.get("arguments", {})
            if name == "set_profile":
                self.agent.set_user_profile(arguments)
                result = {"status": "ok"}
            elif name == "search_fintech_jobs":
                limit = int(arguments.get("limit", 20))
                jobs = await self.agent.search_fintech_jobs(limit)
                result = [job.__dict__ for job in jobs]
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": "Unknown tool"},
                }
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        elif method == "tools/list":
            tools = [
                {"name": "set_profile"},
                {"name": "search_fintech_jobs"},
                {"name": "get_job_details"},
            ]
            return {"jsonrpc": "2.0", "id": req_id, "result": tools}
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": "Method not found"},
            }

    async def serve(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            try:
                request = json.loads(line)
            except json.JSONDecodeError:
                continue
            response = await self.handle_request(request)
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


async def main() -> None:
    server = JSONRPCServer()
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())

