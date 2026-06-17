#!/usr/bin/env python3
"""EVOLVE MCP Server — Expose agent leaderboard via Model Context Protocol."""
import json, sys
from pathlib import Path

LEADERBOARD = Path.home() / "evolve" / "leaderboard_data.json"

def handle_request(request):
    method = request.get("method", "")
    
    if method == "tools/list":
        return {"tools": [
            {"name": "agent_leaderboard", "description": "Get the live autonomous agent leaderboard — top repos ranked by activity, health, momentum"},
            {"name": "agent_search", "description": "Search for a specific agent/repo in the leaderboard"},
            {"name": "ecosystem_stats", "description": "Get ecosystem-wide stats: categories, stars, trends"},
        ]}
    
    elif method == "tools/call":
        tool = request.get("params", {}).get("name", "")
        
        if not LEADERBOARD.exists():
            return {"content": [{"type": "text", "text": "Leaderboard data not available yet"}]}
        
        data = json.loads(LEADERBOARD.read_text())
        
        if tool == "ecosystem_stats":
            cats = data.get("categories", {})
            return {"content": [{"type": "text", "text": json.dumps({
                "total_repos": data.get("count", 0),
                "total_stars": data.get("total_stars", 0),
                "categories": cats,
                "self_evolving_count": cats.get("Self-Evolving", 0),
            }, indent=2)}]}
        
        elif tool == "agent_leaderboard":
            repos = list(data.get("repos", {}).values())
            repos.sort(key=lambda x: x.get("score", 0), reverse=True)
            top = [{"name": r["name"], "stars": r["stars"], "score": r.get("score",0), "category": r["category"]} for r in repos[:10]]
            return {"content": [{"type": "text", "text": json.dumps(top, indent=2)}]}
        
        elif tool == "agent_search":
            query = request.get("params", {}).get("arguments", {}).get("query", "").lower()
            repos = data.get("repos", {})
            matches = [{"name": n, "stars": r["stars"], "desc": r["desc"][:100]} 
                      for n, r in repos.items() if query in n.lower() or query in r.get("desc","").lower()][:10]
            return {"content": [{"type": "text", "text": json.dumps(matches, indent=2)}]}
    
    return {"error": "Unknown method"}

if __name__ == "__main__":
    # Simple stdin/stdout MCP protocol
    for line in sys.stdin:
        try:
            req = json.loads(line)
            resp = handle_request(req)
            print(json.dumps(resp), flush=True)
        except: pass
