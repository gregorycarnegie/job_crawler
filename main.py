#!/usr/bin/env python3

import asyncio
import logging
from typing import Any

import aiohttp
import mcp.server.stdio
from bs4 import BeautifulSoup
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.types import Tool, TextContent, CallToolResult

from param_job_agent import ParamJobAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("param-job-agent")


# MCP Server setup
app = Server("param-fintech-jobs")
job_agent = ParamJobAgent()

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools"""
    return [
        Tool(
            name="set_profile",
            description="Set your professional profile (skills, experience, qualifications)",
            inputSchema={
                "type": "object",
                "properties": {
                    "skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Your technical and professional skills"
                    },
                    "experience": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Your work experience areas"
                    },
                    "qualifications": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Your qualifications and certifications"
                    },
                    "min_salary": {
                        "type": "number",
                        "description": "Minimum salary requirement in GBP",
                        "default": 50000
                    }
                }
            }
        ),
        Tool(
            name="search_fintech_jobs",
            description="Search for fintech job opportunities matching your profile",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "number",
                        "description": "Maximum number of jobs to return",
                        "default": 20
                    }
                }
            }
        ),
        Tool(
            name="get_job_details",
            description="Get detailed information about a specific job",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL of the job posting"
                    }
                },
                "required": ["url"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Handle tool calls"""
    try:
        if name == "set_profile":
            job_agent.set_user_profile(arguments)
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text="Profile updated successfully! Ready to search for fintech opportunities."
                    )
                ]
            )

        elif name == "search_fintech_jobs":
            limit = arguments.get("limit", 20)
            jobs = await job_agent.search_fintech_jobs(limit)

            if not jobs:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="No fintech jobs found matching your criteria. Try updating your profile or check back later."
                        )
                    ]
                )

            jobs_text = []
            for job in jobs:
                job_info = f"""**{job.title}** at {job.company}
📍 Location: {job.location}
💰 Salary: {job.salary or 'Not specified'}
🎯 Match Score: {job.match_score:.1f}/100
🔗 Source: {job.source}
🌐 URL: {job.url}
📝 Description: {job.description[:200]}{'...' if len(job.description) > 200 else ''}
"""
                jobs_text.append(job_info)

            result_text = f"Found {len(jobs)} fintech job opportunities:\n\n" + "\n---\n\n".join(jobs_text)

            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=result_text
                    )
                ]
            )

        elif name == "get_job_details":
            url = arguments.get("url")
            if not url:
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="URL is required to fetch job details"
                        )
                    ],
                    isError=True
                )

            async with aiohttp.ClientSession() as session:
                html = await job_agent.fetch_page(session, url)
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    # Extract main content
                    content = soup.get_text()[:2000]
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Job Details from {url}:\n\n{content}..."
                            )
                        ]
                    )
                else:
                    return CallToolResult(
                        content=[
                            TextContent(
                                type="text",
                                text=f"Unable to fetch job details from {url}"
                            )
                        ],
                        isError=True
                    )
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=f"Unknown tool: {name}"
                    )
                ],
                isError=True
            )

    except Exception as e:
        logger.error(f"Error in tool {name}: {e}")
        return CallToolResult(
            content=[
                TextContent(
                    type="text",
                    text=f"Error: {str(e)}"
                )
            ],
            isError=True
        )

async def main():
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="param-fintech-jobs",
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())