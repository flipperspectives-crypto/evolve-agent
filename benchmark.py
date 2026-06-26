#!/usr/bin/env python3
"""
AGENT BENCHMARK — Autonomous Agent Evaluation Harness
======================================================
Live evaluation of LLMs on autonomous agent tasks.
Tests reasoning, tool use, long-horizon planning, self-improvement.

Each benchmark question is a standard Draco-style task with:
- A real-world scenario
- Multiple sub-questions testing different capabilities
- A grading rubric (accuracy, breadth, synthesis, citations, safety)
- Model-agnostic (works with any LLM via API)

Part of the EVOLVE ecosystem. Feeds into the leaderboard.
"""
import json, time, urllib.request, os, re
from pathlib import Path
from datetime import datetime

HOME = Path.home()
BENCH_DIR = HOME / "evolve" / "benchmarks"
BENCH_DIR.mkdir(parents=True, exist_ok=True)

# ═══════════════════════════════════════════════════════
# BENCHMARK QUESTIONS
# ═══════════════════════════════════════════════════════

BENCHMARKS = [
    {
        "id": "agent-001",
        "title": "Self-Evolving System Architecture",
        "domain": "autonomous-systems",
        "difficulty": "expert",
        "target_model": "gemini-3-pro",
        "question": """You are designing a self-evolving autonomous agent system called EVOLVE. 

The system must:
1. Observe the open-source agent ecosystem (GitHub, npm, PyPI)
2. Identify gaps and opportunities using multi-model synthesis
3. Build and ship solutions autonomously
4. Modify its own source code to improve itself over time
5. Never exceed rate limits or get banned from APIs

Answer the following with concrete, implementable detail:

A) ARCHITECTURE: Design the complete system architecture. What components are needed? How do they communicate? What are the failure modes and how do you handle them?

B) SELF-MODIFICATION: How would you implement safe self-modification? What guardrails prevent the agent from breaking itself? How do you verify changes before applying them?

C) RATE LIMITING: Design a heartbeat/rate-limit system that prevents API bans while maximizing throughput. What data structures track usage? How do you handle burst traffic vs sustained load?

D) JUDGE SYNTHESIS: The system uses a "judge" model that reads outputs from 3 panelist models and synthesizes a final answer. Design the judge's system prompt. What does it look for? How does it resolve contradictions?

E) PROFITABILITY: Beyond just building tools, how does this system generate real value? What artifacts does it produce that people would pay for or that establish authority in the ecosystem?

Be specific. Provide code sketches where helpful. Think in systems, not features.""",
        "rubric": {
            "accuracy": 20,       # Are the architectural decisions sound?
            "breadth": 9,         # Does it cover all 5 sub-questions deeply?
            "synthesis": 9,       # Do the parts form a coherent whole?
            "actionability": 12,  # Can someone build from this answer?
            "safety": 10,         # Are guardrails and failure modes addressed?
            "citations": 5,       # References to real systems/patterns?
            "total": 65,
        },
        "grading_criteria": [
            "Architecture: clear component diagram or description (8pts)",
            "Architecture: failure modes identified and handled (6pts)",
            "Architecture: communication patterns specified (6pts)",
            "Self-modification: sandbox/verification mechanism (6pts)",
            "Self-modification: rollback/recovery strategy (4pts)",
            "Rate limiting: data structures for tracking (5pts)",
            "Rate limiting: burst vs sustained handling (3pts)",
            "Rate limiting: prevents bans while maximizing throughput (4pts)",
            "Judge: system prompt is concrete and usable (5pts)",
            "Judge: contradiction resolution strategy (4pts)",
            "Profitability: identifies real value artifacts (6pts)",
            "Profitability: path to authority/adoption (4pts)",
            "Overall: coherent, buildable, not just hand-waving (8pts)",
        ],
    },
    {
        "id": "agent-002",
        "title": "Multi-Model Consensus Under Uncertainty",
        "domain": "reasoning",
        "difficulty": "hard",
        "target_model": "any",
        "question": """You have 3 AI models that independently analyzed the same codebase for security vulnerabilities.

Model A (Researcher, temp=0.3) found:
- SQL injection in user/login.py line 47
- XSS in templates/profile.html line 12
- "Low risk: missing CSRF token on /api/health"

Model B (Engineer, temp=0.5) found:
- SQL injection in user/login.py line 47
- "Medium risk: hardcoded API key in config/deploy.yaml"
- Race condition in payment/process.py line 89

Model C (Creative, temp=0.9) found:
- XSS in templates/profile.html line 12
- "Architectural: the entire auth module should use OAuth2 not JWT"
- "Speculative: potential supply chain attack via unverified npm dependency left-pad@1.3.0"

As the JUDGE, synthesize these findings. Answer:
1. CONSENSUS — What vulnerabilities do all/most agree on?
2. CONTRADICTIONS — Where do they disagree and how do you resolve?
3. UNIQUE INSIGHTS — What did only one model catch that's critically important?
4. BLIND SPOTS — Based on these reports, what might they ALL have missed?
5. PRIORITIZED ACTION PLAN — In what order should the team fix these? Justify each priority.""",
        "rubric": {
            "accuracy": 25,
            "synthesis": 15,
            "actionability": 15,
            "safety": 10,
            "total": 65,
        },
    },
    {
        "id": "agent-003",
        "title": "Autonomous Pipeline Resilience",
        "domain": "devops",
        "difficulty": "expert",
        "target_model": "gemini-3-pro",
        "question": """You run an autonomous agent pipeline on a Samsung phone (Termux/Android) with these constraints:
- 8GB RAM, ARM64 CPU
- No root access
- Unreliable WiFi (drops every ~2 hours)
- GitHub API: 5000 req/hr authenticated, 60/hr unauthenticated
- DeepSeek API: $0.28/M output tokens, 10 calls/hour budget
- The phone reboots randomly every ~3 days (Android kills background processes)

Your pipeline runs:
- EVOLVE: self-improving agent (every 15min, uses GitHub + DeepSeek APIs)
- APSA-Net: HN scraper → build → push (every 7min)
- 8 trading bots (every 1-5min)
- 5 infrastructure watchers (every 1-30min)
- A live leaderboard regenerator (every 30min)

16 cron jobs total. All must survive reboots, WiFi drops, API failures, and OOM kills.

Design the resilience architecture. Answer:
A) How do you ensure all 16 jobs restart after a phone reboot?
B) How do you handle WiFi drops mid-API-call without data corruption?
C) What's your strategy for API failures? Retry? Exponential backoff? Circuit breaker?
D) How do you prevent OOM kills when all 16 jobs fire simultaneously?
E) Design a watchdog that detects if any pipeline is stuck and recovers it.
F) What monitoring tells you the system is healthy without consuming resources?""",
        "rubric": {
            "accuracy": 20,
            "breadth": 9,
            "actionability": 12,
            "safety": 9,
            "constraints": 15,
            "total": 65,
        },
    },
]

# ═══════════════════════════════════════════════════════
# GRADING ENGINE
# ═══════════════════════════════════════════════════════

def grade_answer(benchmark, answer, model_name):
    """
    Grade an answer against the benchmark rubric.
    For now: heuristic grading. Future: LLM-as-judge grading.
    """
    rubric = benchmark.get("rubric", {})
    criteria = benchmark.get("grading_criteria", [])
    
    scores = {}
    total = 0
    max_total = rubric.get("total", 65)
    
    # Heuristic scoring based on answer quality signals
    answer_lower = answer.lower()
    answer_len = len(answer)
    
    # Accuracy: check for concrete details vs hand-waving
    concrete_signals = ["```", "def ", "class ", "api.", "http", "sql", "table", "diagram", "step 1", "first,"]
    concrete_count = sum(1 for s in concrete_signals if s in answer_lower)
    accuracy = min(20, 5 + concrete_count * 2)
    scores["accuracy"] = accuracy
    
    # Breadth: does it cover sub-questions?
    sections = len(re.findall(r'[A-F]\)|^\d+\.|###|\*\*[A-F]', answer, re.MULTILINE))
    breadth = min(9, sections * 2)
    scores["breadth"] = breadth
    
    # Synthesis: is there a unified conclusion?
    has_conclusion = any(w in answer_lower[-500:] for w in ["conclusion", "summary", "bottom line", "in summary", "overall", "finally"])
    synthesis = 7 if has_conclusion else 4
    if answer_len > 2000:
        synthesis += 2
    scores["synthesis"] = min(9, synthesis)
    
    # Actionability: can someone act on this?
    has_code = "```" in answer
    has_steps = bool(re.search(r'step \d|first,.*second|1\..*2\..*3\.', answer_lower))
    actionability = 8 if has_code and has_steps else 5 if has_code or has_steps else 3
    scores["actionability"] = min(12, actionability)
    
    # Safety: mentions failures/risks?
    safety_signals = ["fail", "error", "rollback", "backup", "guard", "sandbox", "verify", "validate", "rate limit", "circuit breaker"]
    safety_count = sum(1 for s in safety_signals if s in answer_lower)
    scores["safety"] = min(10, safety_count * 2)
    
    # Citations
    has_urls = len(re.findall(r'https?://', answer))
    has_refs = bool(re.search(r'\[.*\]|\(.*\d{4}\)|according to', answer_lower))
    scores["citations"] = min(5, has_urls + (2 if has_refs else 0))
    
    total = sum(scores.values())
    normalized = round(total / max_total * 100, 1)
    
    return {
        "model": model_name,
        "benchmark_id": benchmark["id"],
        "scores": scores,
        "total_raw": total,
        "total_max": max_total,
        "score_pct": normalized,
        "graded_at": datetime.now().isoformat(),
        "answer_length": answer_len,
        "signals": {
            "concrete_count": concrete_count,
            "sections": sections,
            "has_conclusion": has_conclusion,
            "has_code": has_code,
            "safety_count": safety_count,
            "urls": has_urls,
        }
    }

# ═══════════════════════════════════════════════════════
# API CALLER
# ═══════════════════════════════════════════════════════

def call_model(model_name, system_prompt, user_prompt, api_key=None):
    """Call a model API. Supports DeepSeek, Gemini, OpenAI-compatible."""
    
    # Determine which API to use
    if "gemini" in model_name.lower():
        return call_gemini(model_name, system_prompt, user_prompt, api_key)
    elif "deepseek" in model_name.lower():
        return call_deepseek(system_prompt, user_prompt, api_key)
    else:
        return call_deepseek(system_prompt, user_prompt, api_key)

def call_gemini(model_name, system_prompt, user_prompt, api_key):
    """Call Gemini API."""
    key = api_key or os.environ.get("GEMINI_API_KEY", "")
    if not key:
        # Try Hermes config
        config_path = HOME / ".hermes" / "config.yaml"
        try:
            with open(config_path) as f:
                for line in f:
                    m = re.match(r'\s*api_key_env:\s*(AIza\S{30,})', line)
                    if m:
                        key = m.group(1)
                        break
        except: pass
    
    if not key:
        return None, "No Gemini API key found"
    
    model = model_name if "/" not in model_name else model_name.split("/")[-1]
    if not model.startswith("gemini-"):
        model = "gemini-2.5-pro"  # default
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    body = {
        "contents": [{"parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 4000},
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode(), 
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        return text, None
    except Exception as e:
        return None, str(e)

def call_deepseek(system_prompt, user_prompt, api_key=None):
    """Call DeepSeek API."""
    key = api_key or ""
    if not key:
        key = os.environ.get("DEEPSEEK_API_KEY", "")
    # Always try config key as fallback (env may have stale key)
    config_path = HOME / ".hermes" / "config.yaml"
    try:
        with open(config_path) as f:
            for line in f:
                m = re.match(r'\s*api_key_env:\s*(sk-\S{30,})', line)
                if m:
                    config_key = m.group(1)
                    if not key or key != config_key:
                        key = config_key  # prefer config key
                    break
    except: pass
    
    if not key:
        return None, "No DeepSeek API key found"
    
    url = "https://api.deepseek.com/v1/chat/completions"
    body = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 4000,
    }
    
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                  headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"]["content"]
        return text, None
    except Exception as e:
        return None, str(e)

# ═══════════════════════════════════════════════════════
# BENCHMARK RUNNER
# ═══════════════════════════════════════════════════════

def run_benchmark(benchmark_id, model_name="deepseek-chat"):
    """Run a specific benchmark against a model."""
    bench = next((b for b in BENCHMARKS if b["id"] == benchmark_id), None)
    if not bench:
        return {"error": f"Benchmark {benchmark_id} not found"}
    
    print(f"🧪 Running: {bench['title']}")
    print(f"   Model: {model_name}")
    print(f"   Difficulty: {bench['difficulty']}")
    print(f"   Max score: {bench['rubric']['total']}")
    print()
    
    system = "You are an expert systems architect specializing in autonomous AI agents. Be concrete, specific, and implementable. Provide code sketches. Think in systems."
    
    answer, error = call_model(model_name, system, bench["question"])
    
    if error:
        return {"error": error, "benchmark": bench["id"]}
    
    result = grade_answer(bench, answer, model_name)
    result["benchmark_title"] = bench["title"]
    result["question_preview"] = bench["question"][:200] + "..."
    
    # Save result
    result_path = BENCH_DIR / f"{benchmark_id}_{model_name.replace('/','_')}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
    result_path.write_text(json.dumps(result, indent=2))
    
    return result

def print_result(result):
    """Pretty-print benchmark result."""
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        return
    
    print(f"\n{'═'*60}")
    print(f"📊 BENCHMARK RESULT: {result.get('benchmark_title', '?')}")
    print(f"{'═'*60}")
    print(f"Model:      {result['model']}")
    print(f"Score:      {result['score_pct']}% ({result['total_raw']}/{result['total_max']})")
    print(f"Answer:     {result['answer_length']} chars")
    print(f"{'─'*60}")
    
    signals = result.get("signals", {})
    print(f"Concrete:   {signals.get('concrete_count', 0)} signals")
    print(f"Sections:   {signals.get('sections', 0)} detected")
    print(f"Code:       {'✓' if signals.get('has_code') else '✗'}")
    print(f"Safety:     {signals.get('safety_count', 0)} mentions")
    print(f"Citations:  {signals.get('urls', 0)} URLs")
    print(f"{'─'*60}")
    
    for k, v in result.get("scores", {}).items():
        bar = "█" * v + "░" * (20 - v) if v <= 20 else "█" * (v//2) + "░" * (10 - v//2)
        print(f"  {k:20s} {bar} {v}")
    
    print(f"{'═'*60}")
    print(f"Saved: {BENCH_DIR}/{result['benchmark_id']}_{result['model'].replace('/','_')}_*.json")

# ═══════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Agent Benchmark Harness")
    p.add_argument("--list", action="store_true", help="List all benchmarks")
    p.add_argument("--run", type=str, help="Run specific benchmark ID (e.g. agent-001)")
    p.add_argument("--model", type=str, default="deepseek-chat", help="Model to test")
    p.add_argument("--all", action="store_true", help="Run all benchmarks")
    
    args = p.parse_args()
    
    if args.list:
        for b in BENCHMARKS:
            print(f"\n{b['id']}: {b['title']}")
            print(f"  Domain: {b['domain']} | Difficulty: {b['difficulty']} | Target: {b['target_model']}")
            print(f"  Max score: {b['rubric']['total']}")
            print(f"  Question: {b['question'][:150]}...")
    
    elif args.run:
        result = run_benchmark(args.run, args.model)
        print_result(result)
    
    elif args.all:
        for b in BENCHMARKS:
            result = run_benchmark(b["id"], args.model)
            print_result(result)
            time.sleep(2)
    
    else:
        # Default: show benchmark 001 (the gemini-3-pro tailored one)
        b = BENCHMARKS[0]
        print(f"🎯 TAILORED FOR GEMINI 3 PRO")
        print(f"{'═'*60}")
        print(f"Benchmark: {b['id']} — {b['title']}")
        print(f"Domain: {b['domain']} | Difficulty: {b['difficulty']}")
        print(f"Max score: {b['rubric']['total']} points")
        print(f"{'═'*60}")
        print(f"\n{b['question']}")
        print(f"\n{'═'*60}")
        print(f"Grading criteria ({len(b['grading_criteria'])} items):")
        for c in b['grading_criteria']:
            print(f"  • {c}")
        print(f"\nRun: python3 benchmark.py --run agent-001 --model gemini-2.5-pro")
