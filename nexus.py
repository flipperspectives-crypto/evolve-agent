#!/usr/bin/env python3
"""
NEXUS — Unified autonomous fleet coordinator
=============================================
Connects APSA-Net (HN observer) + EVOLVE (GitHub gap hunter)
Both feed each other. One unified state.

Runs: python3 nexus.py --sync
"""
import json, time, subprocess, sys
from pathlib import Path
from datetime import datetime

HOME = Path.home()
NEXUS_STATE = HOME / "nexus_state.json"
APSA_STATE = HOME / "apsa_projects" / "pipeline_state.json"
EVOLVE_STATE = HOME / "evolve" / "state.json"

def load_json(path):
    try: return json.loads(path.read_text())
    except: return {}

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, default=str))

def sync():
    """Pull state from both pipelines, merge, show unified dashboard."""
    apsa = load_json(APSA_STATE)
    evolve = load_json(EVOLVE_STATE)
    
    # Count APSA projects
    apsa_builds = list((HOME / "apsa-builds").glob("*"))
    apsa_count = len([d for d in apsa_builds if d.is_dir() and not d.name.startswith(".")])
    
    # Count lines
    apsa_lines = 0
    for d in apsa_builds:
        if d.is_dir() and not d.name.startswith("."):
            for py in d.glob("**/*.py"):
                try: apsa_lines += len(py.read_text().splitlines())
                except: pass
    
    evolve_lines = 0
    for py in (HOME / "evolve").glob("**/*.py"):
        try: evolve_lines += len(py.read_text().splitlines())
        except: pass
    
    total_lines = apsa_lines + evolve_lines
    
    nexus = {
        "updated": datetime.now().isoformat(),
        "total_projects": apsa_count + 1,  # +1 for EVOLVE itself
        "total_lines": total_lines,
        "apasa_net": {
            "projects": apsa_count,
            "lines": apsa_lines,
            "schedule": "every 7min",
            "source": "Hacker News",
            "repo": "apsa-builds",
            "last_run": apsa.get("last_run", "?"),
        },
        "evolve": {
            "projects": 1,
            "lines": evolve_lines,
            "schedule": "every 15min",
            "source": "GitHub agent ecosystem",
            "repo": "evolve-agent",
            "generation": evolve.get("generation", 1),
            "decisions": len(evolve.get("decisions", [])),
            "shipped": evolve.get("repos_shipped", 0),
            "mutations": evolve.get("mutations_applied", 0),
        },
        "other_autonomous": {
            "trading": ["wallet-guardian (5m)", "giga-trader (1m)", "perp-tracker (1m)", 
                       "jup-tracker (1m)", "position-tracker (1m)", "airdrop-hunter (6h)",
                       "sol-miner (4h)", "income-watch (1h)"],
            "infra": ["slime-watchdog (1m)", "ma-radar (30m)", "daily-digest (8am)",
                     "bird-report (7am)", "listener-summary (9pm)"],
        }
    }
    
    save_json(NEXUS_STATE, nexus)
    return nexus

def dashboard():
    nexus = load_json(NEXUS_STATE)
    if not nexus:
        nexus = sync()
    
    a = nexus["apasa_net"]
    e = nexus["evolve"]
    o = nexus["other_autonomous"]
    
    print(f"""
╔══════════════════════════════════════════════════════════╗
║              ⚡ NEXUS — Autonomous Fleet                 ║
╠══════════════════════════════════════════════════════════╣
║  Total projects: {nexus['total_projects']:<3}   Total lines: {nexus['total_lines']:<6}                    ║
║  Updated: {nexus['updated'][:19]}                            ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  🔭 APSA-NET (HN Observer)                               ║
║     Projects: {a['projects']:<3}   Lines: {a['lines']:<6}   Schedule: {a['schedule']:<12}     ║
║     Source: Hacker News → builds what people want         ║
║     Repo: apsa-builds                                     ║
║                                                          ║
║  ⚛ EVOLVE (GitHub Gap Hunter)                            ║
║     Generation: {e['generation']:<3}  Decisions: {e['decisions']:<3}  Shipped: {e['shipped']:<2}               ║
║     Lines: {e['lines']:<6}   Mutations: {e['mutations']:<2}   Schedule: {e['schedule']:<12}     ║
║     Source: GitHub → builds what's missing                ║
║     Repo: evolve-agent                                    ║
║                                                          ║
╠══════════════════════════════════════════════════════════╣
║  💰 Trading ({len(o['trading'])} bots): {o['trading'][0]:<35s}║
║           {o['trading'][1]:<40s}║
║           {o['trading'][2]:<40s}║
║  🔧 Infra ({len(o['infra'])} watchers): {o['infra'][0]:<36s}║
║           {o['infra'][1]:<38s}║
╚══════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    if "--sync" in sys.argv:
        sync()
        dashboard()
    else:
        dashboard()
