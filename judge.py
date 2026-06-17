#!/usr/bin/env python3
"""
FUSION JUDGE — Multi-model synthesis via DeepSeek API.
See SKILL.md for full documentation.
Usage: echo "question" | python3 judge.py
"""
import sys, os, json, time, argparse, textwrap, urllib.request, re

def _load_api_key():
    config_path = os.path.expanduser("~/.hermes/config.yaml")
    try:
        with open(config_path) as f:
            for line in f:
                m = re.match(r'\s*api_key_env:\s*(sk-\S{30,})', line)
                if m:
                    return m.group(1)
    except:
        pass
    key = os.environ.get("DEEPSEEK_API_KEY", "")
    if key and len(key) > 20 and "..." not in key:
        return key
    return ""

API_KEY = _load_api_key()
API_URL = "https://api.deepseek.com/v1/chat/completions"

PANELISTS = [
    {"name": "Researcher", "emoji": "🔬", "system": "You are a thorough first-principles researcher. Break problems down to fundamentals. Cite reasoning chains. Consider academic and empirical evidence. Surface assumptions explicitly.", "temperature": 0.3},
    {"name": "Engineer", "emoji": "⚙️", "system": "You are a pragmatic senior engineer. Focus on what actually works in production. Give actionable, concrete answers. Call out hype vs reality. Consider cost, maintenance, and real-world constraints.", "temperature": 0.5},
    {"name": "Creative", "emoji": "💡", "system": "You are a creative lateral thinker. Consider unconventional angles, edge cases, and non-obvious connections. Question the premise if needed. Surface what others might miss.", "temperature": 0.9},
]

JUDGE_SYSTEM = """You are a SYNTHESIS JUDGE. You receive {n} independent answers to the same question from different perspectives. Your job: 1. CONSENSUS — What do all agree on? 2. CONTRADICTIONS — Where do they disagree? 3. UNIQUE INSIGHTS — What did only ONE catch? 4. BLIND SPOTS — What did NOBODY consider? 5. SYNTHESIS — Final fused answer better than any individual."""

C = {"R": "\033[91m", "G": "\033[92m", "Y": "\033[93m", "B": "\033[94m", "M": "\033[95m", "C": "\033[96m", "W": "\033[97m", "D": "\033[90m", "X": "\033[0m", "Bo": "\033[1m"}

def call_deepseek(system_prompt, user_prompt, temperature=0.7, max_tokens=2000):
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    body = {"model": "deepseek-chat", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "temperature": temperature, "max_tokens": max_tokens, "stream": False}
    req = urllib.request.Request(API_URL, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]

def panel_phase(question, num_panelists=3):
    panelists = PANELISTS[:num_panelists]
    outputs = []
    for p in panelists:
        sys.stderr.write(f"  {p['emoji']} {p['name']} reasoning...")
        sys.stderr.flush()
        t0 = time.time()
        try:
            answer = call_deepseek(p["system"], question, p["temperature"])
            sys.stderr.write(f" done ({time.time()-t0:.1f}s)\n")
            outputs.append({"name": p["name"], "emoji": p["emoji"], "answer": answer})
        except Exception as e:
            sys.stderr.write(f" FAILED: {e}\n")
            outputs.append({"name": p["name"], "emoji": p["emoji"], "answer": f"[ERROR: {e}]"})
    return outputs

def judge_phase(question, panel_outputs):
    panel_text = ""
    for i, p in enumerate(panel_outputs):
        panel_text += f"\n{'─'*50}\nPANELIST {i+1}: {p['emoji']} {p['name']}\n{'─'*50}\n{p['answer']}\n"
    judge_prompt = f"QUESTION: {question}\n{panel_text}\n{'─'*50}\nNow synthesize following the 5-step framework."
    return call_deepseek(JUDGE_SYSTEM.replace("{n}", str(len(panel_outputs))), judge_prompt, temperature=0.2, max_tokens=3000)

def format_output(question, panel_outputs, synthesis, show_panel=False):
    w = 80
    try: w = os.get_terminal_size().columns
    except: pass
    w = max(60, w)
    out = [f"{C['Bo']}{C['C']}{'═'*w}{C['X']}", f"{C['Bo']}{C['Y']}  ⚖ JUDGE — Question{C['X']}", f"  {textwrap.fill(question, width=w-4)}", f"{C['Bo']}{C['C']}{'═'*w}{C['X']}"]
    if show_panel:
        out.append(f"\n{C['Bo']}{C['D']}── PANEL OUTPUTS ──{C['X']}")
        for p in panel_outputs:
            out.append(f"\n{C['Bo']}{p['emoji']} {p['name']}{C['X']}")
            out.append(f"{C['D']}{textwrap.fill(p['answer'][:400], width=w-2)}{C['X']}")
        out.append(f"\n{C['Bo']}{C['D']}{'─'*w}{C['X']}")
    out.append(f"\n{C['Bo']}{C['M']}  🧠 SYNTHESIS{C['X']}")
    out.append(f"{C['Bo']}{C['M']}{'─'*w}{C['X']}")
    out.append(textwrap.fill(synthesis, width=w-2))
    out.append(f"\n{C['Bo']}{C['C']}{'═'*w}{C['X']}")
    out.append(f"{C['D']}Panel: {', '.join(p['name'] for p in panel_outputs)} | Judge: DeepSeek | {len(synthesis)} chars{C['X']}")
    return "\n".join(out)

def main():
    parser = argparse.ArgumentParser(description="Fusion-style multi-model JUDGE")
    parser.add_argument("question", nargs="*", help="Question (or pipe via stdin)")
    parser.add_argument("--panel", "-p", type=int, default=3)
    parser.add_argument("--show-panel", "-v", action="store_true")
    parser.add_argument("--judge-only", "-j", action="store_true")
    args = parser.parse_args()
    if args.question: question = " ".join(args.question)
    elif not sys.stdin.isatty(): question = sys.stdin.read().strip()
    else: print("Usage: echo 'question' | python3 judge.py  OR  python3 judge.py 'question'"); sys.exit(1)
    if not API_KEY: print(f"{C['R']}No API key found. Set DEEPSEEK_API_KEY or add api_key_env to ~/.hermes/config.yaml{C['X']}"); sys.exit(1)
    num_panelists = min(args.panel, len(PANELISTS))
    if args.judge_only:
        panel_outputs = [{"name": "Input", "emoji": "📥", "answer": question}]
    else:
        sys.stderr.write(f"\n{C['Bo']}{C['C']}⚖ JUDGE — {num_panelists} panelists → 1 synthesis{C['X']}\n")
        sys.stderr.write(f"{C['D']}Q: {question[:80]}{'...' if len(question)>80 else ''}{C['X']}\n\n")
        panel_outputs = panel_phase(question, num_panelists)
        sys.stderr.write(f"\n{C['Bo']}{C['M']}🧠 Judge synthesizing...{C['X']}")
        sys.stderr.flush()
    t0 = time.time()
    synthesis = judge_phase(question, panel_outputs)
    sys.stderr.write(f" done ({time.time()-t0:.1f}s)\n\n")
    print(format_output(question, panel_outputs, synthesis, show_panel=args.show_panel))
    total_chars = sum(len(p["answer"]) for p in panel_outputs) + len(synthesis)
    sys.stderr.write(f"{C['D']}~{total_chars} chars | ~${total_chars/4*0.28/1_000_000:.4f} est{C['X']}\n")

if __name__ == "__main__":
    main()
