"""
London Job Search MCP Agent
===========================

An **MCP (Model‑Context Protocol) server** exposing one tool —
`search_london_jobs`.  Claude (or any other MCP‑capable client) can call this
endpoint to retrieve up‑to‑date job postings located in **London, UK**.

Quick‑start
-----------
```bash
# 1) Install requirements
pip install fastmcp httpx python‑dotenv

# 2) Create an Adzuna developer account (https://developer.adzuna.com/) and
#    export your credentials so the tool can authenticate:
export ADZUNA_APP_ID="your_app_id"
export ADZUNA_APP_KEY="your_app_key"

# 3) Run the MCP server locally (stdio transport)
python london_job_search_agent.py
```

### Claude Desktop integration
1. **Settings → MCP → Add New MCP Server**
2. *Type*: **stdio**
   *Command*: `python`
   *Args*: `path/to/london_job_search_agent.py`
   *Name*: *London Job Search*
3. Save.  Claude will automatically discover the `search_london_jobs` tool.

Example prompt inside Claude:
```
Use the search_london_jobs tool to find five recent "machine learning engineer"
openings and give me a short summary of each.
```

Return format
-------------
`search_london_jobs` returns **List[dict]** where each dict contains:
* `title`          – Job title
* `company`        – Hiring company name
* `location`       – Display location (always a London area)
* `salary_min`     – Lower salary bound (if provided)
* `salary_max`     – Upper salary bound (if provided)
* `contract_type`  – full_time | part_time | contract | etc.
* `url`            – Direct link to the listing on Adzuna
* `description`    – First 160‑character snippet of the description

Security note
-------------
The server only reaches out to **Adzuna's public HTTPS API** and does not touch
local files or the network beyond that request.
"""

from __future__ import annotations

import os
import textwrap
from typing import List, Dict, Any

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load environment variables from a .env file if present (developer convenience)
load_dotenv()

# ---------------------------------------------------------------------------
# Initialise the MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(name="London Job Search Agent")


@mcp.tool(
    name="search_london_jobs",  # Visible name Claude will reference
    description=textwrap.dedent(
        """Search live job vacancies that are **physically located in London, UK**.

        Parameters
        ----------
        query : str
            Free‑text keywords, e.g. "software engineer" or "data scientist".
        max_results : int, optional (default 10, max 50)
            How many postings to return.
        """,
    ),
)
async def search_london_jobs(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """Return a list of current London‑based jobs that match *query*.

    The function queries Adzuna’s REST API (UK endpoint) and extracts the most
    relevant fields for downstream processing within the LLM conversation.
    """

    # ---------------------------------------------------------------------
    # 0) API credentials
    # ---------------------------------------------------------------------
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if app_id is None or app_key is None:
        raise RuntimeError(
            "Please set ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables."
        )

    # ---------------------------------------------------------------------
    # 1) Compose request
    # ---------------------------------------------------------------------
    max_results = min(max(max_results, 1), 50)  # Enforce 1–50 bounds
    endpoint = "https://api.adzuna.com/v1/api/jobs/gb/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": max_results,
        "what": query,
        "where": "London",
        "content-type": "application/json",
        "sort_by": "date",
    }

    # ---------------------------------------------------------------------
    # 2) Fetch data (async HTTP)
    # ---------------------------------------------------------------------
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(endpoint, params=params)
        response.raise_for_status()
        payload = response.json()

    # ---------------------------------------------------------------------
    # 3) Transform into a clean, LLM‑friendly schema
    # ---------------------------------------------------------------------
    jobs: List[Dict[str, Any]] = []
    for item in payload.get("results", []):
        jobs.append(
            {
                "title": item.get("title"),
                "company": item.get("company", {}).get("display_name"),
                "location": item.get("location", {}).get("display_name"),
                "salary_min": item.get("salary_min"),
                "salary_max": item.get("salary_max"),
                "contract_type": item.get("contract_type"),
                "url": item.get("redirect_url"),
                "description": (item.get("description", "")[:160] + "…"),
            }
        )

    return jobs


# ---------------------------------------------------------------------------
# Entry point – run with stdio transport by default
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # `mcp.run()` automatically selects stdio when launched directly and the
    # process is connected to a terminal / Claude Desktop.
    mcp.run()
