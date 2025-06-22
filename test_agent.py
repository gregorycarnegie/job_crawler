#!/usr/bin/env python3

import asyncio
import json
import sys
from typing import Dict, Any

class MCPClient:
    def __init__(self):
        self.process = None
        self.request_id = 1

    async def start_agent(self):
        """Start the MCP agent process"""
        self.process = await asyncio.create_subprocess_exec(
            sys.executable, 'param_agent.py',
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

    async def send_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request to the MCP agent"""
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        self.request_id += 1

        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # Read response
        response_line = await self.process.stdout.readline()
        if response_line:
            return json.loads(response_line.decode())
        return {}

    async def test_profile_and_search(self):
        """Test setting profile and searching for jobs"""
        print("🚀 Starting Param Job Agent Test...")

        await self.start_agent()

        # Test 1: Set profile
        print("\n📋 Setting user profile...")
        profile_response = await self.send_request("tools/call", {
            "name": "set_profile",
            "arguments": {
                "skills": ["Python", "Django", "React", "PostgreSQL", "AWS"],
                "experience": ["web development", "API design", "fintech systems", "payment processing"],
                "qualifications": ["Computer Science degree", "AWS certified developer"],
                "min_salary": 55000
            }
        })
        print(f"Profile Response: {profile_response}")

        # Test 2: Search for jobs
        print("\n🔍 Searching for fintech jobs...")
        search_response = await self.send_request("tools/call", {
            "name": "search_fintech_jobs",
            "arguments": {
                "limit": 5
            }
        })
        print(f"Search Response: {search_response}")

        # Cleanup
        self.process.terminate()
        await self.process.wait()
        print("\n✅ Test completed!")

async def main():
    client = MCPClient()
    await client.test_profile_and_search()

if __name__ == "__main__":
    asyncio.run(main())