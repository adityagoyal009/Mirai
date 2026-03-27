"""
WebSocket handler for real-time swarm prediction visualization.
Called from app.py (FastAPI). Thread-safe broadcast via queue.
"""

import json
import queue
import threading
import time
import traceback

from ..utils.logger import get_logger
from ..services.swarm_predictor import SwarmPredictor

logger = get_logger('mirofish.api.ws')

# Each connected client gets a message queue
_client_queues: list = []
_clients_lock = threading.Lock()


def broadcast(msg: dict):
    """Thread-safe broadcast — pushes to all client queues."""
    data = json.dumps(msg)
    with _clients_lock:
        for q in _client_queues:
            try:
                q.put_nowait(data)
            except queue.Full:
                pass


# Legacy Flask init — no longer used. WebSocket handled by FastAPI in app.py.


def swarm_ws(ws):
    """WebSocket endpoint for swarm prediction streaming."""
    from ..services.analytics import analytics
    client_queue = queue.Queue(maxsize=5000)
    with _clients_lock:
        _client_queues.append(client_queue)
    logger.info("[WS] Client connected")
    analytics.track_connection()

    # Sender thread: reads from queue, sends to WebSocket
    stop_event = threading.Event()

    def sender():
        while not stop_event.is_set():
            try:
                data = client_queue.get(timeout=0.5)
                try:
                    ws.send(data)
                except Exception:
                    break
            except queue.Empty:
                continue

    sender_thread = threading.Thread(target=sender, daemon=True)
    sender_thread.start()

    try:
        while True:
            raw = ws.receive(timeout=30)
            if raw is None:
                # Keepalive — client still connected but no message
                continue

            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                client_queue.put(json.dumps({"type": "error", "error": "Invalid JSON"}))
                continue

            if msg.get("type") == "ping":
                client_queue.put(json.dumps({"type": "pong"}))
                continue
            elif msg.get("type") == "startAnalysis":
                _handle_full_analysis(msg)
            elif msg.get("type") == "chatWithAgent":
                _handle_agent_chat(msg)
            elif msg.get("type") == "startSwarm":
                _handle_start_swarm(msg)
            elif msg.get("type") == "saveLayout":
                logger.info("[WS] Layout save received")
            else:
                client_queue.put(json.dumps({
                    "type": "error",
                    "error": f"Unknown message type: {msg.get('type')}"
                }))

    except Exception as e:
        if "timed out" not in str(e).lower():
            logger.warning(f"[WS] Client error: {e}")
    finally:
        stop_event.set()
        with _clients_lock:
            if client_queue in _client_queues:
                _client_queues.remove(client_queue)
        logger.info("[WS] Client disconnected")


def _handle_full_analysis(msg: dict):
    """Handle startAnalysis — run full BI pipeline with streaming events."""
    exec_summary = msg.get("execSummary", "")
    depth = msg.get("depth", "deep")
    agent_count = msg.get("agentCount", 100)
    stage = msg.get("stage", "")  # Explicit stage from frontend (Idea/Pre-seed/Seed/Series A/B/C/Growth/Pre-IPO)

    if not exec_summary:
        broadcast({"type": "error", "error": "Missing execSummary"})
        return

    if len(exec_summary) > 50000:
        exec_summary = exec_summary[:50000]
        logger.warning(f"[WS] exec_summary truncated from {len(msg.get('execSummary', ''))} to 50000 chars")

    # 50 or 100 agents; 0 disables swarm
    valid_counts = [0, 50, 100]
    if agent_count not in valid_counts:
        agent_count = 100

    logger.info(f"[WS] Starting full analysis: depth={depth}, agents={agent_count}")
    _analysis_start_time = time.time()

    def run_analysis():
        warnings = []  # Collects degradation warnings for analysisComplete payload
        try:
            from ..services.business_intel import BusinessIntelEngine
            from ..services.swarm_predictor import SwarmPredictor
            from ..utils.audit_log import AuditLog

            bi = BusinessIntelEngine()

            # ── Start audit log ──
            from ..config import Config
            _council_models = Config.get_council_models()
            _swarm_models = Config.get_swarm_models()
            audit = AuditLog.start_run(
                company="(extracting...)",
                industry="",
                agent_count=agent_count,
                council_models=[m['label'] for m in _council_models],
                swarm_models=[m['label'] for m in _swarm_models],
            )

            # ── Phase 1: Research (dual-model agentic) ──
            broadcast({"type": "researchStarted"})
            _ext_t0 = time.time()

            # Use structured fields from frontend when available (skips lossy LLM extraction)
            structured = msg.get("structuredFields")
            if structured and isinstance(structured, dict) and structured.get("company"):
                from ..services.business_intel import ExtractionResult
                extraction = ExtractionResult(
                    company=structured.get("company", ""),
                    industry=structured.get("industry", ""),
                    product=structured.get("product", ""),
                    target_market=structured.get("target_market", ""),
                    business_model=structured.get("business_model", ""),
                    stage=structured.get("stage", ""),
                    traction=structured.get("traction", ""),
                    ask=structured.get("ask", ""),
                    claims=structured.get("claims", []),
                    key_differentiators=structured.get("key_differentiators", []),
                    website_url=structured.get("website_url", ""),
                    year_founded=structured.get("year_founded", ""),
                    location=structured.get("location", ""),
                    revenue=structured.get("revenue", ""),
                    known_competitors=structured.get("known_competitors", []),
                    funding=structured.get("funding", ""),
                    team=structured.get("team", ""),
                    pricing=structured.get("pricing", ""),
                )
                extraction = bi._compute_data_quality(extraction)
                logger.info(f"[WS] Using structured fields from frontend (skipping LLM extraction) — "
                           f"company={extraction.company}, data_quality={extraction.data_quality}")
            else:
                # Fallback: LLM extraction (for PDF upload path or old clients)
                extraction = bi.extract_and_validate(exec_summary)

            audit._data["company"] = getattr(extraction, 'company', '')
            audit._data["industry"] = getattr(extraction, 'industry', '')
            audit.log_step("extraction",
                          model="structured_passthrough" if structured else "claude-opus-4-6",
                          prompt=exec_summary[:500],
                          parsed=extraction.to_dict() if hasattr(extraction, 'to_dict') else {},
                          latency_s=time.time() - _ext_t0,
                          metadata={"data_quality": getattr(extraction, 'data_quality', 0),
                                    "fields_present": getattr(extraction, 'fields_present', []),
                                    "fields_missing": getattr(extraction, 'fields_missing', []),
                                    "source": "structured_fields" if structured else "llm_extraction"})

            from ..services.analytics import analytics as _analytics
            _analytics.track_analysis_start(
                company=getattr(extraction, 'company', ''),
                industry=getattr(extraction, 'industry', ''),
                agent_count=agent_count,
            )

            # ── Start council blind scoring in parallel with research ──
            # _predict_blind only needs exec_summary (no research), so it can run concurrently
            _blind_scores = [None]  # mutable container for thread result
            _blind_thread = None
            use_council = depth == "deep"
            if use_council:
                from ..config import Config as _cfg
                _council_models_for_blind = _cfg.get_council_models()
                if _council_models_for_blind and len(_council_models_for_blind) > 1:
                    def _run_blind_scoring():
                        try:
                            from ..utils.llm_client import LLMClient
                            results = {}
                            from concurrent.futures import ThreadPoolExecutor, as_completed as _ac
                            with ThreadPoolExecutor(max_workers=len(_council_models_for_blind)) as _pool:
                                def _blind_one(mcfg):
                                    _llm = LLMClient(model=mcfg["model"])
                                    return mcfg["label"], bi._predict_blind(exec_summary, _llm, stage=stage)
                                futs = [_pool.submit(_blind_one, m) for m in _council_models_for_blind]
                                for f in _ac(futs):
                                    try:
                                        lbl, scores = f.result()
                                        results[lbl] = scores
                                    except Exception:
                                        pass
                            _blind_scores[0] = results
                            logger.info(f"[WS] Blind scoring complete: {len(results)} models (parallel with research)")
                        except Exception as e:
                            logger.warning(f"[WS] Blind scoring parallel thread failed: {e}")

                    _blind_thread = threading.Thread(target=_run_blind_scoring, daemon=True)
                    _blind_thread.start()
                    logger.info("[WS] Blind scoring started in parallel with research")

            # Check research cache
            research = None
            research_failed = False
            cache = None
            cache_key = None
            try:
                from ..services.research_cache import ResearchCache
                cache = ResearchCache()
                cache_key = cache.make_key(
                    getattr(extraction, 'company', ''),
                    getattr(extraction, 'industry', ''),
                )
                cached = cache.get(cache_key)
                if cached and isinstance(cached, dict) and 'summary' in cached:
                    logger.info(f"[WS] Cache HIT — skipping research")
                    broadcast({"type": "researchProgress", "round": 0, "status": "Using cached research..."})
                    research = cached
            except Exception as e:
                logger.error(f"[WS] Cache check failed (non-fatal): {e}\n{traceback.format_exc()}")

            # Run research if no cache — Gemini primary, OpenClaw fallback
            if research is None:
                def on_progress(round_num, status):
                    broadcast({"type": "researchProgress", "round": round_num, "status": status})

                _research_company = getattr(extraction, 'company', '')
                _research_industry = getattr(extraction, 'industry', '')
                _research_product = getattr(extraction, 'product', '')
                _research_target = getattr(extraction, 'target_market', '')
                _research_website = getattr(extraction, 'website_url', '')
                _research_competitors = ', '.join(getattr(extraction, 'known_competitors', []) or [])

                # PRIMARY: Gemini grounded research (fast, no gateway dependency)
                try:
                    from ..services.gemini_researcher import GeminiResearcher
                    broadcast({"type": "researchProgress", "round": 0, "status": "Web research via Gemini..."})

                    gemini = GeminiResearcher()
                    research = gemini.research(
                        company=_research_company,
                        industry=_research_industry,
                        product=_research_product,
                        target_market=_research_target,
                        website_url=_research_website,
                        known_competitors=_research_competitors,
                        on_progress=on_progress,
                    )

                    logger.info(f"[WS] Gemini research done: {len(research.get('facts', []))} facts, "
                               f"{len(research.get('competitors', []))} competitors, "
                               f"{len(research.get('sources', []))} sources")
                except Exception as gemini_err:
                    logger.warning(f"[WS] Gemini research failed, trying OpenClaw fallback: {gemini_err}")
                    broadcast({"type": "researchProgress", "round": 0, "status": "Gemini failed, trying OpenClaw..."})

                    # FALLBACK: OpenClaw agentic research
                    try:
                        from ..services.agentic_researcher import AgenticResearcher
                        import dataclasses

                        agentic = AgenticResearcher()
                        findings = agentic.research(
                            company=_research_company,
                            industry=_research_industry,
                            product=_research_product,
                            target_market=_research_target,
                            website_url=_research_website,
                            known_competitors=_research_competitors,
                            on_progress=on_progress,
                        )
                        research = dataclasses.asdict(findings) if dataclasses.is_dataclass(findings) else (findings if isinstance(findings, dict) else {})
                        logger.info(f"[WS] OpenClaw research done: {len(research.get('facts', []))} facts")
                    except Exception as openclaw_err:
                        logger.error(f"[WS] Both Gemini and OpenClaw failed — STOPPING pipeline: "
                                    f"Gemini: {gemini_err} | OpenClaw: {openclaw_err}\n{traceback.format_exc()}")
                        broadcast({
                            "type": "error",
                            "error": f"Research failed (both Gemini and OpenClaw). Analysis aborted.",
                            "phase": "research",
                            "fatal": True,
                        })
                        return

                # Cache for future use
                if cache and cache_key and research and research.get('summary'):
                    cache.put(cache_key, research)

            broadcast({
                "type": "researchComplete",
                "findings": len(research.get('facts', [])),
                "competitors": len(research.get('competitors', [])),
                "summary": (research.get('summary', '') or '')[:500],
                "sources": len(research.get('sources', [])),
                "citedFactsCount": len(research.get('cited_facts', [])),
            })

            # Wait for blind scoring thread if it was started
            if _blind_thread is not None:
                _blind_thread.join(timeout=30)
                if _blind_scores[0]:
                    logger.info(f"[WS] Blind scores ready from parallel thread: {len(_blind_scores[0])} models")

            # ── Phase 2: Council ──
            from ..config import Config
            council_models = Config.get_council_models()
            model_labels = [m.get('label', m.get('model', '?')) for m in council_models] if council_models else ['Primary LLM']
            broadcast({
                "type": "councilStarted",
                "modelCount": len(model_labels),
                "models": model_labels,
            })

            use_council = depth == "deep" and len(council_models) > 1
            prediction = bi.predict(
                exec_summary, research, use_council=use_council, stage=stage,
                blind_scores_cache=_blind_scores[0],
            )

            dims = []
            if hasattr(prediction, 'dimensions'):
                dims = [{"name": d.name, "score": d.score} for d in prediction.dimensions]
            elif isinstance(prediction, dict):
                dims = prediction.get('dimensions', [])

            contested = []
            if hasattr(prediction, 'contested_dimensions'):
                contested = prediction.contested_dimensions or []
            elif isinstance(prediction, dict):
                contested = prediction.get('contested_dimensions', [])

            p_score = prediction.overall_score if hasattr(prediction, 'overall_score') else prediction.get('overall_score', 0)
            p_verdict = prediction.verdict if hasattr(prediction, 'verdict') else prediction.get('verdict', '?')
            p_confidence = prediction.confidence if hasattr(prediction, 'confidence') else prediction.get('confidence', 0)

            broadcast({
                "type": "councilComplete",
                "overall": p_score,
                "verdict": p_verdict,
                "confidence": p_confidence,
                "dimensions": dims,
                "contestedDimensions": contested,
                "models": model_labels,
                "factVerification": {
                    "verified": prediction.fact_check.get("verified_count", 0),
                    "contradicted": prediction.fact_check.get("contradicted_count", 0),
                    "unverified": prediction.fact_check.get("unverified_count", 0),
                    "trustScore": prediction.fact_check.get("trust_score", 0),
                } if (hasattr(prediction, 'fact_check') and prediction.fact_check) else None,
            })

            # ── Phase 2b: Swarm (with enriched context) ──
            swarm_result = None
            if agent_count > 0:
                # Build enriched context from research only (no council scores — swarm must evaluate independently)
                research_summary = (research.get('summary', '') or str(research))[:3000]
                competitors_str = ', '.join(
                    (c if isinstance(c, str) else c.get('name', str(c)))
                    for c in (research.get('competitors', []) or [])[:5]
                )

                # Build cited facts block for swarm context
                cited_facts_block = ""
                _cited = research.get('cited_facts', []) or []
                if _cited:
                    cited_lines = []
                    for cf in _cited[:10]:
                        src = cf.get('source_domain', '')
                        text = cf.get('text', '')[:150]
                        if src and src != 'multi-model synthesis':
                            cited_lines.append(f"- {text} [source: {src}]")
                        else:
                            cited_lines.append(f"- {text}")
                    if cited_lines:
                        cited_facts_block = f"\nKEY FACTS (sourced):\n" + "\n".join(cited_lines) + "\n"

                enriched_context = (
                    f"RESEARCH FINDINGS:\n{research_summary}\n"
                    f"Competitors: {competitors_str}\n"
                    f"{cited_facts_block}\n"
                    f"Given this research, evaluate this startup independently from your unique perspective."
                )

                agents_completed = [0]
                total_positive = [0]
                total_negative = [0]
                total_confidence = [0.0]

                broadcast({
                    "type": "swarmStarted",
                    "totalAgents": agent_count,
                    "execSummary": exec_summary[:200],
                })

                def on_agent_start(agent_id, persona_name, model_label, zone="wildcard"):
                    broadcast({
                        "type": "agentSpawned",
                        "id": agent_id,
                        "persona": persona_name,
                        "model": model_label,
                        "zone": zone,
                    })
                    broadcast({"type": "agentActive", "id": agent_id, "activity": "evaluating"})

                def on_agent_complete(agent):
                    agents_completed[0] += 1
                    if agent.vote == "positive":
                        total_positive[0] += 1
                    else:
                        total_negative[0] += 1
                    total_confidence[0] += float(getattr(agent, 'confidence', 0) or 0)
                    broadcast({
                        "type": "agentVoted",
                        "id": agent.agent_id,
                        "vote": agent.vote,
                        "overall": agent.overall,
                        "scores": agent.scores,
                        "confidence": agent.confidence,
                        "reasoning": agent.reasoning[:150],
                    })
                    if agents_completed[0] % 5 == 0 or agents_completed[0] == agent_count:
                        total = agents_completed[0]
                        broadcast({
                            "type": "swarmProgress",
                            "agentsCompleted": total,
                            "totalAgents": agent_count,
                            "positivePct": round(total_positive[0] / max(total, 1) * 100, 1),
                            "negativePct": round(total_negative[0] / max(total, 1) * 100, 1),
                            "avgConfidence": round(total_confidence[0] / max(total, 1), 3),
                        })

                swarm = SwarmPredictor()

                def on_deliberation_start():
                    broadcast({"type": "deliberationStarted", "rounds": 2})

                swarm_result = swarm.predict(
                    exec_summary=exec_summary,
                    research_context=enriched_context,
                    agent_count=agent_count,
                    on_agent_complete=on_agent_complete,
                    on_agent_start=on_agent_start,
                    on_deliberation_start=on_deliberation_start,
                    industry=extraction.industry if hasattr(extraction, 'industry') else '',
                    product=extraction.product if hasattr(extraction, 'product') else '',
                    stage=stage or (extraction.stage if hasattr(extraction, 'stage') else ''),
                )

                raw = swarm_result.to_dict()
                broadcast({
                    "type": "swarmComplete",
                    "result": {
                        "totalAgents": raw.get("total_agents", 0),
                        "requestedAgents": raw.get("requested_agents", raw.get("total_agents", 0)),
                        "verdict": raw.get("verdict", "Unknown"),
                        "avg_scores": raw.get("avg_scores", {}),
                        "median_overall": raw.get("median_overall", 0),
                        "std_overall": raw.get("std_overall", 0),
                        "score_distribution": raw.get("score_distribution", {}),
                        "positivePct": raw.get("positive_pct", 0),
                        "negativePct": raw.get("negative_pct", 0),
                        "avgConfidence": raw.get("avg_confidence", 0),
                        "keyThemesPositive": raw.get("key_themes_positive", []),
                        "keyThemesNegative": raw.get("key_themes_negative", []),
                        "contestedThemes": raw.get("contested_themes", []),
                        "modelsUsed": raw.get("models_used", []),
                        "executionTimeSeconds": raw.get("execution_time_seconds", 0),
                        "divergence": raw.get("divergence"),
                        "deliberation": raw.get("deliberation"),
                    },
                })

            # ── Phase 3: Plan ──
            broadcast({"type": "planStarted"})
            plan_dict = {}
            try:
                plan = bi.plan(exec_summary, research, prediction)
                plan_dict = plan.to_dict() if hasattr(plan, 'to_dict') else (plan if isinstance(plan, dict) else {})
                broadcast({
                    "type": "planComplete",
                    "risks": plan_dict.get("risks", [])[:5],
                    "moves": plan_dict.get("next_moves", plan_dict.get("moves", []))[:5],
                })
            except Exception as e:
                logger.error(f"[WS] Plan phase failed: {e}\n{traceback.format_exc()}")
                warnings.append(f"Plan phase failed: {e}")
                broadcast({
                    "type": "planFailed",
                    "reason": str(e),
                    "message": "Risk assessment and strategic recommendations unavailable due to a planning error.",
                })
                broadcast({"type": "planComplete", "risks": [], "moves": [], "failed": True})

            # ── Phase 4: OASIS Market Simulation (optional) ──
            oasis_result = {}
            simulate_market = msg.get("simulateMarket", False)
            if simulate_market:
                try:
                    broadcast({"type": "oasisStarted", "rounds": 6})
                    from ..services.oasis_simulator import OasisSimulator
                    oasis = OasisSimulator()

                    def on_round(result):
                        broadcast({
                            "type": "oasisRound",
                            "month": result["month"],
                            "event": result["event"],
                            "sentimentPct": result["sentiment_pct"],
                            "change": result["sentiment_change"],
                            "quote": result["key_quote"],
                            "confidenceLow": result.get("confidence_low", 0),
                            "confidenceHigh": result.get("confidence_high", 100),
                        })

                    # Pass swarm agents to OASIS so it can select real panelists
                    # instead of using hardcoded roles
                    oasis_swarm_agents = None
                    if swarm_result and hasattr(swarm_result, 'agent_results'):
                        oasis_swarm_agents = swarm_result.agent_results

                    oasis_result = oasis.simulate(
                        exec_summary=exec_summary,
                        research_context=research_summary[:500] if 'research_summary' in dir() else '',
                        council_verdict=f"{p_score:.1f}/10 - {p_verdict}",
                        on_round_complete=on_round,
                        swarm_agents=oasis_swarm_agents,
                        stage=stage or (extraction.stage if hasattr(extraction, 'stage') else ''),
                    )
                    broadcast({
                        "type": "oasisComplete",
                        "trajectory": oasis_result.get("trajectory", "stable"),
                        "startSentiment": oasis_result.get("start_sentiment", 50),
                        "endSentiment": oasis_result.get("final_sentiment", oasis_result.get("end_sentiment", 50)),
                        "timeline": oasis_result.get("timeline", []),
                        "uncertaintyBand": oasis_result.get("uncertainty_band", {}),
                    })
                    logger.info(f"[WS] OASIS complete: {oasis_result.get('trajectory')}")
                except Exception as e:
                    logger.error(f"[WS] OASIS simulation failed: {e}\n{traceback.format_exc()}")
                    warnings.append(f"OASIS market simulation failed: {e}")
                    broadcast({
                        "type": "oasisFailed",
                        "reason": str(e),
                        "message": "OASIS market simulation unavailable for this analysis.",
                    })

            # ── Build data dicts for report + analysisComplete ──
            research_dict = {}
            try:
                research_dict = {
                    "summary": research.get('summary', '') or '',
                    "competitors": [
                        (c if isinstance(c, str) else c.get('name', str(c)) if isinstance(c, dict) else str(c))
                        for c in (research.get('competitors', []) or [])
                    ][:10],
                    "trends": (research.get('trends', []) or [])[:5],
                    "context_facts": (research.get('context_facts', research.get('facts', [])) or [])[:10],
                    "cited_facts": (research.get('cited_facts', []) or [])[:15],
                }
            except Exception:
                pass

            swarm_dict = {}
            final_verdict = p_verdict
            final_confidence = p_confidence
            if agent_count > 0:
                try:
                    raw_swarm = swarm_result.to_dict()
                    swarm_dict = {
                        "total_agents": raw_swarm.get("total_agents", 0),
                        "positive_pct": raw_swarm.get("positive_pct", 0),
                        "negative_pct": raw_swarm.get("negative_pct", 0),
                        "sample_agents": raw_swarm.get("sample_agents", []),
                        "key_themes_positive": raw_swarm.get("key_themes_positive", []),
                        "key_themes_negative": raw_swarm.get("key_themes_negative", []),
                        "divergence": raw_swarm.get("divergence"),
                        "deliberation": raw_swarm.get("deliberation"),
                        "verdict": raw_swarm.get("verdict"),
                        "avg_confidence": raw_swarm.get("avg_confidence"),
                    }
                    # Confidence-weighted verdict blend (replaces conservative-wins rule)
                    swarm_verdict = raw_swarm.get("verdict", p_verdict)
                    swarm_confidence = raw_swarm.get("avg_confidence", p_confidence)
                    _verdict_score = {"Strong Miss": 1, "Likely Miss": 2, "Mixed Signal": 3,
                                      "Uncertain": 3, "Likely Hit": 4, "Strong Hit": 5}
                    _council_s = _verdict_score.get(p_verdict, 3)
                    _swarm_s = _verdict_score.get(swarm_verdict, 3)
                    _cw = max(p_confidence, 0.1)
                    _sw = max(swarm_confidence, 0.1)
                    _blended = (_council_s * _cw + _swarm_s * _sw) / (_cw + _sw)
                    if _blended >= 4.5:     final_verdict = "Strong Hit"
                    elif _blended >= 3.5:   final_verdict = "Likely Hit"
                    elif _blended >= 2.5:   final_verdict = "Mixed Signal"
                    elif _blended >= 1.5:   final_verdict = "Likely Miss"
                    else:                    final_verdict = "Strong Miss"
                    # Confidence-weighted confidence (matches verdict blend formula)
                    final_confidence = round((_cw * p_confidence + _sw * swarm_confidence) / (_cw + _sw), 2)
                    logger.info(f"[WS] Verdict blend: council={p_verdict}({_cw:.2f}), swarm={swarm_verdict}({_sw:.2f}) -> blended={_blended:.2f} -> {final_verdict} (confidence {final_confidence})")
                    # Surface explicit warning when council and swarm strongly disagree
                    if abs(_council_s - _swarm_s) >= 3:
                        _disagree_msg = (
                            f"Council ({p_verdict}) and Swarm ({swarm_verdict}) strongly disagree. "
                            f"Final verdict '{final_verdict}' is a confidence-weighted blend — review both perspectives."
                        )
                        warnings.append(_disagree_msg)
                        broadcast({
                            "type": "verdictDisagreement",
                            "council_verdict": p_verdict,
                            "swarm_verdict": swarm_verdict,
                            "final_verdict": final_verdict,
                            "message": _disagree_msg,
                        })
                        logger.warning(f"[WS] {_disagree_msg}")
                    audit.log_verdict_blend(
                        council_verdict=p_verdict, council_confidence=p_confidence,
                        swarm_verdict=swarm_verdict, swarm_confidence=swarm_confidence,
                        blended_score=round(_blended, 2), final_verdict=final_verdict,
                        final_confidence=final_confidence,
                    )
                except Exception as e:
                    logger.error(f"[WS] Swarm dict extraction failed — verdict blend unavailable, using council-only: {e}\n{traceback.format_exc()}")
                    warnings.append(f"Swarm result extraction failed: {e}. Final verdict is council-only (not blended).")
                    swarm_dict = {"extraction_failed": True, "error": str(e)}
                    broadcast({
                        "type": "swarmDegradation",
                        "reason": str(e),
                        "message": "Swarm result extraction failed — final verdict uses council scores only.",
                    })

            # ── OASIS trajectory adjustment (confidence-gated) ──
            if simulate_market and 'oasis_result' in dir() and oasis_result:
                try:
                    trajectory = oasis_result.get('trajectory', 'stable')
                    # OASIS override only applies when council+swarm confidence is LOW (< 0.7)
                    _oasis_confidence_low = final_confidence < 0.7
                    # Always surface trajectory data to user (never suppress)
                    if trajectory in ('declining', 'improving') and trajectory != 'stable':
                        broadcast({
                            "type": "oasisTrajectoryWarning",
                            "trajectory": trajectory,
                            "message": f"OASIS projects {trajectory} trajectory — monitor closely.",
                            "confidence": final_confidence,
                            "verdict_before_oasis": final_verdict,
                        })

                    if trajectory == 'declining' and final_verdict in ('Likely Hit', 'Strong Hit'):
                        if _oasis_confidence_low:
                            # Require at least 2 consecutive declining rounds
                            timeline = oasis_result.get('timeline', [])
                            _consecutive_declines = 0
                            _max_consecutive = 0
                            for _r in timeline:
                                if _r.get('sentiment_change', 0) < 0:
                                    _consecutive_declines += 1
                                    _max_consecutive = max(_max_consecutive, _consecutive_declines)
                                else:
                                    _consecutive_declines = 0
                            if _max_consecutive >= 2:
                                final_verdict = 'Mixed Signal'
                                logger.info(
                                    f"[WS] OASIS trajectory 'declining' downgraded verdict to Mixed Signal "
                                    f"(confidence={final_confidence:.2f} < 0.7, {_max_consecutive} consecutive declining rounds)"
                                )
                            else:
                                logger.info(
                                    f"[WS] OASIS 'declining' — {_max_consecutive} consecutive decline(s) "
                                    f"(need >= 2 for verdict override); trajectory warning surfaced to user"
                                )
                        else:
                            logger.info(
                                f"[WS] OASIS 'declining' — confidence={final_confidence:.2f} >= 0.7; "
                                f"verdict not overridden but trajectory warning surfaced to user"
                            )
                    elif trajectory == 'improving' and final_verdict in ('Likely Miss', 'Mixed Signal'):
                        if _oasis_confidence_low:
                            _upgrade = {"Likely Miss": "Mixed Signal", "Mixed Signal": "Likely Hit"}
                            final_verdict = _upgrade.get(final_verdict, final_verdict)
                            logger.info(f"[WS] OASIS trajectory 'improving' upgraded verdict to {final_verdict}")
                        else:
                            logger.info(
                                f"[WS] OASIS 'improving' — confidence={final_confidence:.2f} >= 0.7; "
                                f"verdict not overridden but trajectory warning surfaced to user"
                            )
                except Exception as e:
                    logger.warning(f"[WS] OASIS verdict adjustment failed: {e}")

            # ── Report Enhancements: Score Forecast, Exec Rewrite, Similar Funded ──
            enhancements = {}
            try:
                from ..services.report_enhancements import (
                    generate_score_forecast, rewrite_exec_summary, find_similar_funded
                )
                _stage = stage or (extraction.stage if hasattr(extraction, 'stage') else '')
                _industry = extraction.industry if hasattr(extraction, 'industry') else ''

                # Top fixes + investor matches come from swarm result
                _top_fixes = raw_swarm.get("top_fixes") if agent_count > 0 and 'raw_swarm' in dir() else None
                _investor_matches = raw_swarm.get("investor_matches") if agent_count > 0 and 'raw_swarm' in dir() else None

                if _top_fixes:
                    enhancements["top_fixes"] = _top_fixes
                    # Score forecast per fix
                    _current_scores = {d['name']: d['score'] for d in dims} if dims else {}
                    forecast = generate_score_forecast(_top_fixes, _current_scores, p_score, _stage)
                    if forecast:
                        enhancements["score_forecast"] = forecast

                    # Rewritten exec summary
                    rewritten = rewrite_exec_summary(exec_summary, _top_fixes, _stage)
                    if rewritten:
                        enhancements["rewritten_exec_summary"] = rewritten

                if _investor_matches:
                    enhancements["investor_matches"] = _investor_matches

                # Similar funded startups from 231K database
                similar = find_similar_funded(_industry, _stage)
                if similar:
                    enhancements["similar_funded"] = similar

                if enhancements:
                    broadcast({"type": "enhancementsComplete", "enhancements": enhancements})
                    logger.info(f"[WS] Report enhancements complete: {list(enhancements.keys())}")
            except Exception as e:
                logger.error(f"[WS] Report enhancements failed: {e}\n{traceback.format_exc()}")
                warnings.append(f"Report enhancements failed (score forecast, exec rewrite, similar funded unavailable): {e}")
                broadcast({
                    "type": "enhancementsDegraded",
                    "reason": str(e),
                    "message": "Premium report features (score forecast, exec rewrite, similar startups) unavailable.",
                })

            # ── ReACT Report Agent: generate professional report sections ──
            report_sections = {}
            try:
                broadcast({"type": "narrativeStarted"})
                from ..services.report_agent import ReportAgent

                report_data = {
                    "prediction": {
                        "verdict": final_verdict,
                        "composite_score": p_score,
                        "confidence": final_confidence,
                        "dimensions": dims,
                        "contested_dimensions": contested,
                        "council_models": model_labels,
                        "council_verdict": p_verdict,
                        "swarm_verdict": swarm_dict.get("verdict", p_verdict),
                    },
                    "research": research_dict,
                    "swarm": swarm_dict,
                    "plan": plan_dict,
                    "extraction": {
                        "company": extraction.company if hasattr(extraction, 'company') else '',
                        "industry": extraction.industry if hasattr(extraction, 'industry') else '',
                        "product": extraction.product if hasattr(extraction, 'product') else '',
                        "target_market": extraction.target_market if hasattr(extraction, 'target_market') else '',
                        "business_model": extraction.business_model if hasattr(extraction, 'business_model') else '',
                        "stage": extraction.stage if hasattr(extraction, 'stage') else '',
                        "traction": extraction.traction if hasattr(extraction, 'traction') else '',
                        "ask": extraction.ask if hasattr(extraction, 'ask') else '',
                    },
                }

                agent = ReportAgent()
                report_sections = agent.generate_report(report_data)
                logger.info(f"[WS] ReACT report generated: {len(report_sections)} sections")
            except Exception as e:
                logger.error(f"[WS] ReportAgent FAILED — PDF will have empty narrative sections: {e}\n{traceback.format_exc()}")
                warnings.append(f"ReportAgent failed: all 6 narrative sections are empty. PDF content is severely degraded. Error: {e}")
                broadcast({
                    "type": "reportAgentFailed",
                    "reason": str(e),
                    "message": "Report narrative generation failed — PDF sections will be empty. Download may not reflect full analysis.",
                })

            # Convert sections to narrative string for backward compatibility
            narrative = "\n\n".join(
                f"{title}\n{content}" for title, content in report_sections.items()
            ) if report_sections else ""

            # Compute blended score (numeric) for analysisComplete
            _verdict_to_score = {"Strong Miss": 1, "Likely Miss": 2, "Mixed Signal": 3,
                                  "Uncertain": 3, "Likely Hit": 4, "Strong Hit": 5}
            _score_to_numeric = {1: 2.0, 2: 4.0, 3: 5.5, 4: 7.5, 5: 9.5}
            _final_verdict_ordinal = _verdict_to_score.get(final_verdict, 3)
            blended_score = _score_to_numeric.get(_final_verdict_ordinal, p_score)

            # ── Final: Full result for PDF export ──
            broadcast({
                "type": "analysisComplete",
                "fullResult": {
                    "prediction": {
                        "verdict": final_verdict,
                        "composite_score": blended_score,
                        "confidence": final_confidence,
                        "council_verdict": p_verdict,
                        "council_score": p_score,
                        "council_confidence": p_confidence,
                        "dimensions": dims,
                        "contested_dimensions": contested,
                        "council_models": model_labels,
                        "model_scores": prediction.model_scores if hasattr(prediction, 'model_scores') else {},
                    },
                    "research": research_dict,
                    "research_failed": research_failed,
                    "swarm": swarm_dict,
                    "plan": plan_dict,
                    "extraction": {
                        "company": getattr(extraction, 'company', ''),
                        "industry": getattr(extraction, 'industry', ''),
                        "product": getattr(extraction, 'product', ''),
                        "target_market": getattr(extraction, 'target_market', ''),
                        "business_model": getattr(extraction, 'business_model', ''),
                        "stage": getattr(extraction, 'stage', ''),
                        "traction": getattr(extraction, 'traction', ''),
                        "ask": getattr(extraction, 'ask', ''),
                        "website_url": getattr(extraction, 'website_url', ''),
                        "year_founded": getattr(extraction, 'year_founded', ''),
                        "location": getattr(extraction, 'location', ''),
                        "revenue": getattr(extraction, 'revenue', ''),
                        "team": getattr(extraction, 'team', ''),
                        "funding": getattr(extraction, 'funding_raised', '') or getattr(extraction, 'ask', ''),
                        "competitive_advantage": getattr(extraction, 'competitive_advantage', ''),
                        "known_competitors": getattr(extraction, 'known_competitors', []),
                    },
                    "oasis": oasis_result if oasis_result else {},
                    "data_quality": getattr(extraction, 'data_quality', 0),
                    "data_sources": ["Brave Search", "Council", "Swarm", "LLM", "OASIS"] if oasis_result else ["Brave Search", "Council", "Swarm", "LLM"],
                    "narrative": narrative,
                    "report_sections": report_sections,
                    "enhancements": enhancements if enhancements else {},
                    "warnings": warnings,
                },
            })

            if warnings:
                logger.warning(f"[WS] Analysis completed with {len(warnings)} degradation warning(s): {warnings}")
            logger.info(f"[WS] Full analysis complete: {p_verdict} ({p_score:.1f}/10)")

            # ── Write audit log ──
            try:
                audit.log_council_reconciliation(
                    reconciled_scores={d['name']: d['score'] for d in dims},
                    contested=contested,
                    chairman_notes="",
                    model_scores=prediction.model_scores if hasattr(prediction, 'model_scores') else {},
                )
                audit_path = audit.end_run(verdict=final_verdict, score=p_score, confidence=final_confidence)
                logger.info(f"[WS] Audit log written: {audit_path}")
            except Exception as ae:
                logger.warning(f"[WS] Audit log failed (non-fatal): {ae}")

            try:
                from ..services.analytics import analytics as _analytics
                _analytics.track_analysis_complete(
                    company=extraction.company if hasattr(extraction, 'company') else '',
                    score=p_score,
                    verdict=final_verdict,
                    duration_s=time.time() - _analysis_start_time,
                    agent_count=agent_count,
                )
            except Exception as _analytics_err:
                logger.debug(f"[WS] Analytics tracking failed (non-fatal): {_analytics_err}")

            # Generate HTML report (skip PDF rendering — user views HTML in new tab)
            try:
                from ..services.llm_report_generator import generate_llm_report, _html_cache
                from datetime import datetime
                import os as _os

                full_analysis = {
                    "prediction": {
                        "verdict": final_verdict,
                        "composite_score": p_score,
                        "confidence": final_confidence,
                        "dimensions": dims,
                        "contested_dimensions": contested,
                        "council_models": model_labels,
                        "model_scores": prediction.model_scores if hasattr(prediction, 'model_scores') else {},
                    },
                    "research": research_dict,
                    "swarm": swarm_dict,
                    "plan": plan_dict,
                    "extraction": {
                        "company": getattr(extraction, 'company', ''),
                        "industry": getattr(extraction, 'industry', ''),
                        "product": getattr(extraction, 'product', ''),
                        "target_market": getattr(extraction, 'target_market', ''),
                        "business_model": getattr(extraction, 'business_model', ''),
                        "stage": getattr(extraction, 'stage', ''),
                        "traction": getattr(extraction, 'traction', ''),
                        "website_url": getattr(extraction, 'website_url', ''),
                        "location": getattr(extraction, 'location', ''),
                        "revenue": getattr(extraction, 'revenue', ''),
                        "team": getattr(extraction, 'team', ''),
                        "funding": getattr(extraction, 'funding_raised', '') or getattr(extraction, 'ask', ''),
                        "known_competitors": getattr(extraction, 'known_competitors', []),
                    },
                    "data_quality": getattr(extraction, 'data_quality', 0),
                    "oasis": oasis_result if oasis_result else {},
                    "narrative": narrative if 'narrative' in dir() else '',
                    "report_sections": report_sections,
                }

                company_name = extraction.company if hasattr(extraction, 'company') else 'unknown'
                safe_name = ''.join(c if c.isalnum() or c in '-_ ' else '' for c in company_name).strip().replace(' ', '-').lower()
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_dir = _os.path.expanduser("~/.mirai/reports")
                _os.makedirs(archive_dir, exist_ok=True)

                # Generate HTML report (no PDF rendering needed)
                broadcast({"type": "reportGenerating"})
                html_report = generate_llm_report(full_analysis)

                # Cache for instant retrieval via /api/bi/report/html/{report_id}
                report_id = f"{safe_name}_{ts}"
                _html_cache[report_id] = html_report
                broadcast({"type": "reportReady", "reportId": report_id})

                # Save raw analysis JSON (keep history, skip PDF)
                json_path = _os.path.join(archive_dir, f"{ts}_{safe_name}.json")
                with open(json_path, 'w') as f:
                    json.dump(full_analysis, f, default=str, ensure_ascii=False)

                # Also save HTML report to disk
                html_path = _os.path.join(archive_dir, f"{ts}_{safe_name}.html")
                with open(html_path, 'w') as f:
                    f.write(html_report)

                logger.info(f"[WS] Report generated and cached: {report_id} ({len(html_report)} chars)")
            except Exception as archive_err:
                logger.error(f"[WS] Report generation failed: {archive_err}\n{traceback.format_exc()}")
                broadcast({
                    "type": "reportFailed",
                    "reason": str(archive_err),
                    "message": "Report generation failed. The analysis is complete but the report could not be generated.",
                })

        except Exception as e:
            logger.error(f"[WS] Full analysis failed: {e}\n{traceback.format_exc()}")
            broadcast({"type": "error", "error": str(e)})

    thread = threading.Thread(target=run_analysis, daemon=True)
    thread.start()


def _handle_agent_chat(msg: dict):
    """Handle chatWithAgent — let user ask follow-up questions to a specific agent."""
    agent_id = msg.get("agentId")
    user_message = msg.get("message", "")
    persona = msg.get("persona", "")
    zone = msg.get("zone", "")
    previous_vote = msg.get("previousVote", "")
    previous_reasoning = msg.get("previousReasoning", "")
    analysis_context = msg.get("analysisContext", "")

    if not user_message:
        broadcast({"type": "agentChatResponse", "agentId": agent_id, "error": "Empty message"})
        return

    def run_chat():
        try:
            from ..utils.llm_client import LLMClient
            llm = LLMClient()

            prompt = (
                f"You are: {persona}\n"
                f"Zone: {zone}\n\n"
                f"You previously evaluated a startup and voted: {previous_vote}\n"
                f"Your reasoning was: {previous_reasoning}\n\n"
                f"Analysis context: {analysis_context[:500]}\n\n"
                f"The user is now asking you a follow-up question. Stay in character as this persona. "
                f"Be specific and reference your previous assessment.\n\n"
                f"User: {user_message}\n\n"
                f"Your response:"
            )

            response = llm.chat([{"role": "user", "content": prompt}], max_tokens=500)
            broadcast({
                "type": "agentChatResponse",
                "agentId": agent_id,
                "response": response.strip() if response else "I couldn't formulate a response.",
            })
        except Exception as e:
            logger.error(f"[WS] Agent chat failed: {e}")
            broadcast({"type": "agentChatResponse", "agentId": agent_id, "error": str(e)})

    threading.Thread(target=run_chat, daemon=True).start()


def _handle_start_swarm(msg: dict):
    """Handle a startSwarm request — run prediction with streaming callbacks."""
    exec_summary = msg.get("execSummary", "")
    agent_count = msg.get("agentCount", 100)

    if not exec_summary:
        broadcast({"type": "error", "error": "Missing execSummary"})
        return

    valid_counts = [10, 25, 50, 100, 250, 500, 1000]
    if agent_count not in valid_counts:
        agent_count = min(valid_counts, key=lambda x: abs(x - agent_count))

    logger.info(f"[WS] Starting swarm: {agent_count} agents")
    broadcast({
        "type": "swarmStarted",
        "totalAgents": agent_count,
        "execSummary": exec_summary[:200],
    })

    agents_completed = [0]
    total_positive = [0]
    total_negative = [0]
    total_confidence = [0.0]

    # Track zone info from persona data
    agent_zones = {}

    def on_agent_start(agent_id, persona_name, model_label, zone="wildcard"):
        agent_zones[agent_id] = zone
        broadcast({
            "type": "agentSpawned",
            "id": agent_id,
            "persona": persona_name,
            "model": model_label,
            "zone": zone,
        })
        broadcast({
            "type": "agentActive",
            "id": agent_id,
            "activity": "evaluating",
        })

    def on_agent_complete(agent):
        agents_completed[0] += 1
        if agent.vote == "positive":
            total_positive[0] += 1
        else:
            total_negative[0] += 1
        total_confidence[0] += float(getattr(agent, 'confidence', 0) or 0)

        broadcast({
            "type": "agentVoted",
            "id": agent.agent_id,
            "vote": agent.vote,
            "overall": agent.overall,
            "scores": agent.scores,
            "confidence": agent.confidence,
            "reasoning": agent.reasoning[:150],
        })

        if agents_completed[0] % 5 == 0 or agents_completed[0] == agent_count:
            total = agents_completed[0]
            broadcast({
                "type": "swarmProgress",
                "agentsCompleted": total,
                "totalAgents": agent_count,
                "positivePct": round(total_positive[0] / max(total, 1) * 100, 1),
                "negativePct": round(total_negative[0] / max(total, 1) * 100, 1),
                "avgConfidence": round(total_confidence[0] / max(total, 1), 3),
            })

    def run_swarm():
        try:
            swarm = SwarmPredictor()
            research_context = f"Executive Summary Analysis:\n{exec_summary}"

            result = swarm.predict(
                exec_summary=exec_summary,
                research_context=research_context,
                agent_count=agent_count,
                on_agent_complete=on_agent_complete,
                on_agent_start=on_agent_start,
                stage=msg.get('stage', ''),
            )

            raw = result.to_dict()
            # Convert snake_case to camelCase for dashboard compatibility
            broadcast({
                "type": "swarmComplete",
                "result": {
                    "totalAgents": raw.get("total_agents", 0),
                    "requestedAgents": raw.get("requested_agents", raw.get("total_agents", 0)),
                    "verdict": raw.get("verdict", "Unknown"),
                    "avg_scores": raw.get("avg_scores", {}),
                    "median_overall": raw.get("median_overall", 0),
                    "std_overall": raw.get("std_overall", 0),
                    "score_distribution": raw.get("score_distribution", {}),
                    "positivePct": raw.get("positive_pct", 0),
                    "negativePct": raw.get("negative_pct", 0),
                    "avgConfidence": raw.get("avg_confidence", 0),
                    "keyThemesPositive": raw.get("key_themes_positive", []),
                    "keyThemesNegative": raw.get("key_themes_negative", []),
                    "contestedThemes": raw.get("contested_themes", []),
                    "modelsUsed": raw.get("models_used", []),
                    "executionTimeSeconds": raw.get("execution_time_seconds", 0),
                    "divergence": raw.get("divergence"),
                    "deliberation": raw.get("deliberation"),
                },
            })
            logger.info(f"[WS] Swarm complete: {result.positive_pct}% positive")

        except Exception as e:
            logger.error(f"[WS] Swarm failed: {e}\n{traceback.format_exc()}")
            broadcast({"type": "error", "error": str(e)})

    thread = threading.Thread(target=run_swarm, daemon=True)
    thread.start()
