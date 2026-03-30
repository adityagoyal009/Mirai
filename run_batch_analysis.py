#!/usr/bin/env python3
"""
Batch Analysis Runner — sends startups to Mirai one at a time via WebSocket.
Waits for each to complete before starting the next.
Logs all inputs and report URLs.
"""

import asyncio
import json
import time
import sys
import os
import websockets

WS_URL = "ws://127.0.0.1:5000/ws/swarm"
INPUTS_FILE = os.path.join(os.path.dirname(__file__), "batch_analysis_inputs.json")
RESULTS_LOG = os.path.join(os.path.dirname(__file__), "batch_analysis_results.json")
EXEC_SUMMARIES_DIR = "/home/aditya/Downloads/Executive Summaries-20260328T022012Z-3-001/Executive Summaries"

# Gap between runs to let NVIDIA RPM cool down
GAP_SECONDS = 120


def load_exec_summary(filename: str) -> str:
    """Load full text from .docx file."""
    import docx
    path = os.path.join(EXEC_SUMMARIES_DIR, filename)
    doc = docx.Document(path)
    return '\n'.join(p.text for p in doc.paragraphs if p.text.strip())


async def run_single_analysis(startup: dict, index: int, total: int) -> dict:
    """Run a single startup analysis via WebSocket and wait for completion."""
    company = startup["company"]
    print(f"\n{'='*60}")
    print(f"[{index+1}/{total}] Starting analysis: {company}")
    print(f"{'='*60}")

    # Load full exec summary text
    exec_text = load_exec_summary(startup["exec_summary_file"])

    # Build the startAnalysis message matching the WebSocket handler format
    # Handler expects structuredFields as a nested dict (websocket.py:152)
    competitors_raw = startup.get("competitors", "")
    competitors_list = [c.strip() for c in competitors_raw.split(",")] if competitors_raw else []

    msg = {
        "type": "startAnalysis",
        "agentCount": 50,
        "depth": "deep",
        "execSummary": exec_text,
        "structuredFields": {
            "company": startup.get("company", ""),
            "industry": startup.get("industry", ""),
            "product": startup.get("product", ""),
            "target_market": startup.get("ask", ""),
            "business_model": startup.get("revenue_model", ""),
            "stage": startup.get("stage", ""),
            "traction": startup.get("traction", ""),
            "ask": startup.get("ask", ""),
            "key_differentiators": [startup.get("moat", "")],
            "website_url": startup.get("website", ""),
            "year_founded": startup.get("founded", ""),
            "location": startup.get("location", ""),
            "revenue": startup.get("revenue_stage", ""),
            "known_competitors": competitors_list,
            "funding": startup.get("funding", ""),
            "team": startup.get("team", ""),
            "pricing": startup.get("pricing", ""),
        },
    }

    report_url = None
    final_score = None
    verdict = None
    start_time = time.time()

    try:
        async with websockets.connect(WS_URL, ping_interval=30, ping_timeout=60,
                                       close_timeout=10, max_size=10_000_000) as ws:
            # Send the analysis request
            await ws.send(json.dumps(msg))
            print(f"  [{company}] Analysis request sent")

            # Listen for events until we get the report
            while True:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=1800)  # 30 min max
                    event = json.loads(raw)
                    etype = event.get("type", "")

                    if etype == "researchComplete":
                        facts = event.get("factsCount", 0)
                        sources = event.get("sourcesCount", 0)
                        print(f"  [{company}] Research complete: {facts} facts, {sources} sources")

                    elif etype == "councilComplete":
                        score = event.get("compositeScore", 0)
                        v = event.get("verdict", "")
                        print(f"  [{company}] Council complete: {score}/10 ({v})")

                    elif etype == "swarmStarted":
                        agents = event.get("totalAgents", 0)
                        print(f"  [{company}] Swarm started: {agents} agents")

                    elif etype == "swarmProgress":
                        done = event.get("agentsCompleted", 0)
                        total_agents = event.get("totalAgents", 0)
                        pos = event.get("positivePct", 0)
                        print(f"  [{company}] Swarm: {done}/{total_agents} agents ({pos}% positive)")

                    elif etype == "swarmComplete":
                        print(f"  [{company}] Swarm complete")

                    elif etype == "analysisComplete":
                        final_score = event.get("compositeScore", 0)
                        verdict = event.get("verdict", "")
                        report_url = event.get("reportUrl", "")
                        elapsed = time.time() - start_time
                        print(f"  [{company}] DONE: {final_score}/10 ({verdict}) in {elapsed:.0f}s")
                        if report_url:
                            print(f"  [{company}] Report: https://vclabs.org{report_url}")
                        break

                    elif etype == "error":
                        error_msg = event.get("message", "Unknown error")
                        print(f"  [{company}] ERROR: {error_msg}")
                        break

                except asyncio.TimeoutError:
                    elapsed = time.time() - start_time
                    print(f"  [{company}] TIMEOUT after {elapsed:.0f}s")
                    break

    except Exception as e:
        print(f"  [{company}] CONNECTION ERROR: {e}")

    elapsed = time.time() - start_time
    return {
        "company": company,
        "score": final_score,
        "verdict": verdict,
        "report_url": f"https://vclabs.org{report_url}" if report_url else None,
        "elapsed_seconds": round(elapsed, 1),
        "input": {k: v for k, v in startup.items() if k != "exec_summary_file"},
    }


async def main():
    with open(INPUTS_FILE) as f:
        startups = json.load(f)

    total = len(startups)
    print(f"Batch Analysis Runner — {total} startups queued")
    print(f"Gap between runs: {GAP_SECONDS}s")
    print(f"Estimated total time: ~{total * 28 + (total-1) * GAP_SECONDS // 60} minutes\n")

    results = []

    for i, startup in enumerate(startups):
        result = await run_single_analysis(startup, i, total)
        results.append(result)

        # Save progress after each run
        with open(RESULTS_LOG, "w") as f:
            json.dump(results, f, indent=2, default=str)

        if i < total - 1:
            print(f"\n  Waiting {GAP_SECONDS}s before next analysis (NVIDIA RPM cooldown)...")
            await asyncio.sleep(GAP_SECONDS)

    # Final summary
    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE — {len(results)} startups analyzed")
    print(f"{'='*60}")
    for r in results:
        status = f"{r['score']}/10 ({r['verdict']})" if r['score'] else "FAILED"
        print(f"  {r['company']}: {status} [{r['elapsed_seconds']}s]")
        if r['report_url']:
            print(f"    Report: {r['report_url']}")
    print(f"\nResults saved to: {RESULTS_LOG}")
    print(f"Inputs saved to: {INPUTS_FILE}")


if __name__ == "__main__":
    asyncio.run(main())
