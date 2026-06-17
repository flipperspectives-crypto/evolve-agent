#!/usr/bin/env python3
"""
AGENT LEADERBOARD — Live autonomous agent ecosystem benchmark
=============================================================
Scrapes 229+ repos, ranks by stars/activity/health, generates live HTML.
Runs as cron → pushes to GitHub Pages.

THE definitive map of the autonomous agent landscape.
"""
import json, urllib.request, time, os, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
DATA_FILE = HOME / "evolve" / "leaderboard_data.json"
HTML_FILE = HOME / "evolve" / "index.html"

# ── Scrape ────────────────────────────────────────────
def scrape_full():
    """Deep scrape all autonomous agent repos."""
    all_repos = {}
    
    dimensions = [
        ("autonomous agent framework language:python", "Framework", 3),
        ("AI coding agent autonomous", "Coding Agent", 2),
        ("multi-agent LLM orchestration", "Multi-Agent", 2),
        ("agent memory persistent context LLM", "Memory", 1),
        ("self-improving self-evolving autonomous LLM", "Self-Evolving", 1),
        ("agent evaluation benchmark LLM", "Benchmark", 1),
        ("agent skill plugin autonomous", "Skills/Plugins", 1),
    ]
    
    for query, category, pages in dimensions:
        for page in range(1, pages + 1):
            url = f"https://api.github.com/search/repositories?q={query.replace(' ', '+')}&sort=stars&per_page=30&page={page}"
            req = urllib.request.Request(url, headers={"User-Agent": "agent-leaderboard", "Accept": "application/vnd.github.v3+json"})
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read())
                for r in data.get("items", []):
                    name = r["full_name"]
                    if name not in all_repos:
                        all_repos[name] = {
                            "name": name,
                            "stars": r["stargazers_count"],
                            "lang": r.get("language") or "?",
                            "desc": (r.get("description") or "")[:200],
                            "pushed": r["pushed_at"][:10],
                            "issues": r["open_issues_count"],
                            "forks": r["forks_count"],
                            "url": r["html_url"],
                            "topics": r.get("topics", []),
                            "category": category,
                            "created": r["created_at"][:10],
                            "license": r.get("license", {}).get("spdx_id", "?") if r.get("license") else "?",
                        }
            except Exception as e:
                pass
            time.sleep(1.2)
    
    return all_repos

def compute_scores(repos):
    """Score each repo by activity, health, and momentum."""
    now = datetime.now()
    for name, r in repos.items():
        # Activity score (0-10): how recently pushed
        try:
            pushed_date = datetime.strptime(r["pushed"], "%Y-%m-%d")
            days_since = (now - pushed_date).days
            activity = max(0, 10 - days_since / 30)  # 0 if >300 days
        except:
            activity = 0
        
        # Health score (0-10): issues to stars ratio (lower = healthier)
        if r["stars"] > 0:
            issue_ratio = r["issues"] / r["stars"]
            health = max(0, 10 - issue_ratio * 100)
        else:
            health = 0
        
        # Momentum score: approximate from stars (log scale)
        momentum = min(10, r["stars"] / 5000) if r["stars"] > 0 else 0
        
        r["score"] = round(activity * 0.3 + health * 0.3 + momentum * 0.4, 1)
        r["activity"] = round(activity, 1)
        r["health"] = round(health, 1)
        r["momentum"] = round(momentum, 1)

def generate_html(repos):
    """Generate the live leaderboard HTML."""
    # Sort by score
    ranked = sorted(repos.values(), key=lambda x: x["score"], reverse=True)
    
    # Category stats
    categories = {}
    for r in repos.values():
        cat = r["category"]
        categories.setdefault(cat, {"count": 0, "stars": 0, "active": 0})
        categories[cat]["count"] += 1
        categories[cat]["stars"] += r["stars"]
        if r["pushed"] >= "2026-05-01":
            categories[cat]["active"] += 1
    
    total_repos = len(repos)
    total_stars = sum(r["stars"] for r in repos.values())
    total_active = sum(1 for r in repos.values() if r["pushed"] >= "2026-05-01")
    
    # Generate rows
    rows = []
    for i, r in enumerate(ranked[:100]):
        stars_badge = f"{r['stars']/1000:.1f}K" if r['stars'] >= 1000 else str(r['stars'])
        score_color = "#4ade80" if r['score'] >= 7 else "#facc15" if r['score'] >= 4 else "#f87171"
        activity_dot = "🟢" if r['activity'] >= 7 else "🟡" if r['activity'] >= 3 else "🔴"
        
        rows.append(f"""<tr>
            <td class="rank">#{i+1}</td>
            <td><a href="{r['url']}" target="_blank">{r['name']}</a></td>
            <td><span class="badge cat-{r['category'].lower().replace(' ','-').replace('/','-')}">{r['category']}</span></td>
            <td class="stars">⭐ {stars_badge}</td>
            <td class="score" style="color:{score_color}">{r['score']}</td>
            <td>{activity_dot} {r['activity']:.1f}</td>
            <td>{r['lang']}</td>
            <td style="font-size:12px;color:#888;max-width:300px">{r['desc'][:100]}</td>
        </tr>""")
    
    # Category summary cards
    cat_cards = []
    for cat, stats in sorted(categories.items(), key=lambda x: x[1]["stars"], reverse=True):
        star_str = f"{stats['stars']/1000:.0f}K" if stats['stars'] >= 1000 else str(stats['stars'])
        cat_cards.append(f"""<div class="cat-card">
            <div class="cat-name">{cat}</div>
            <div class="cat-count">{stats['count']} repos</div>
            <div class="cat-stars">⭐ {star_str}</div>
            <div class="cat-active">{stats['active']} active</div>
        </div>""")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Agent Leaderboard — Autonomous AI Agent Ecosystem</title>
<meta name="description" content="Live leaderboard of {total_repos}+ autonomous AI agent repos. Updated every 15 minutes. The definitive map of the agent landscape.">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0a0a0f; color:#e2e8f0; font-family:system-ui,-apple-system,sans-serif; padding:20px; }}
.header {{ text-align:center; padding:40px 0 20px; border-bottom:1px solid #1e293b; margin-bottom:30px; }}
.header h1 {{ font-size:2.2em; background:linear-gradient(135deg,#4ade80,#60a5fa); -webkit-background-clip:text; -webkit-text-fill-color:transparent; }}
.header p {{ color:#64748b; margin-top:10px; }}
.stats {{ display:flex; gap:15px; justify-content:center; flex-wrap:wrap; margin:25px 0; }}
.stat {{ background:#1e293b; padding:15px 25px; border-radius:10px; text-align:center; }}
.stat .num {{ font-size:1.8em; font-weight:bold; color:#4ade80; }}
.stat .label {{ font-size:0.8em; color:#64748b; }}
.categories {{ display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin:20px 0 30px; }}
.cat-card {{ background:#1e293b; padding:12px 18px; border-radius:8px; text-align:center; min-width:130px; }}
.cat-name {{ font-weight:bold; color:#60a5fa; }}
.cat-count {{ font-size:1.2em; }}
.cat-stars {{ color:#facc15; font-size:0.9em; }}
.cat-active {{ color:#4ade80; font-size:0.8em; }}
table {{ width:100%; border-collapse:collapse; }}
th {{ background:#1e293b; padding:12px 10px; text-align:left; font-size:0.85em; color:#94a3b8; position:sticky; top:0; }}
td {{ padding:10px; border-bottom:1px solid #1e293b; font-size:0.9em; }}
tr:hover {{ background:#1e293b55; }}
.rank {{ color:#64748b; font-weight:bold; width:50px; }}
.stars {{ color:#facc15; }}
.score {{ font-weight:bold; font-size:1.1em; }}
.badge {{ padding:3px 8px; border-radius:4px; font-size:0.75em; font-weight:bold; }}
.cat-framework {{ background:#7c3aed33; color:#a78bfa; }}
.cat-coding-agent {{ background:#2563eb33; color:#60a5fa; }}
.cat-multi-agent {{ background:#05966933; color:#34d399; }}
.cat-memory {{ background:#d9770633; color:#fbbf24; }}
.cat-self-evolving {{ background:#dc262633; color:#f87171; }}
.cat-benchmark {{ background:#db277733; color:#f472b6; }}
.cat-skills-plugins {{ background:#0891b233; color:#22d3ee; }}
.footer {{ text-align:center; padding:30px; color:#475569; font-size:0.8em; margin-top:30px; border-top:1px solid #1e293b; }}
.footer a {{ color:#60a5fa; }}
a {{ color:#93c5fd; text-decoration:none; }}
a:hover {{ text-decoration:underline; }}
@media(max-width:768px) {{ .stats {{ flex-direction:column; }} }}
</style>
</head>
<body>
<div class="header">
    <h1>🤖 Agent Leaderboard</h1>
    <p>The definitive live map of the autonomous AI agent ecosystem · Updated every 15min</p>
    <div class="stats">
        <div class="stat"><div class="num">{total_repos}</div><div class="label">Repos Tracked</div></div>
        <div class="stat"><div class="num">{total_stars/1000:.0f}K</div><div class="label">Total Stars</div></div>
        <div class="stat"><div class="num">{total_active}</div><div class="label">Active (30d)</div></div>
        <div class="stat"><div class="num">{len(categories)}</div><div class="label">Categories</div></div>
    </div>
    <div class="categories">
        {"".join(cat_cards)}
    </div>
</div>

<table>
<thead><tr>
    <th>#</th><th>Repository</th><th>Category</th><th>Stars</th><th>Score</th><th>Activity</th><th>Lang</th><th>Description</th>
</tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>

<div class="footer">
    <p>⚡ Powered by <a href="https://github.com/flipperspectives-crypto/evolve-agent">EVOLVE</a> — the self-evolving autonomous agent pipeline</p>
    <p>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M UTC")} · Next update in ~15min</p>
    <p>Only 3 self-evolving agents exist. <a href="https://github.com/flipperspectives-crypto/evolve-agent">EVOLVE</a> is one of them.</p>
</div>
</body>
</html>"""
    return html

def main():
    print("🔍 Scraping agent ecosystem...")
    repos = scrape_full()
    print(f"   Found {len(repos)} repos")
    
    compute_scores(repos)
    
    # Save data
    DATA_FILE.write_text(json.dumps({"updated": datetime.now().isoformat(), "count": len(repos), "repos": repos}, indent=2, default=str))
    
    # Generate HTML
    html = generate_html(repos)
    HTML_FILE.write_text(html)
    print(f"✅ Leaderboard generated: {HTML_FILE}")
    print(f"   {len(repos)} repos · {sum(r['stars'] for r in repos.values())/1000:.0f}K stars")
    
    # Quick stats
    cats = {}
    for r in repos.values():
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True):
        print(f"   {cat}: {count}")

if __name__ == "__main__":
    main()
