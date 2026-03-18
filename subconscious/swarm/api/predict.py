"""
Quick-predict API endpoint.
Accepts a scenario, searches the knowledge graph for context,
and returns an LLM-synthesized prediction.
"""

import traceback
from flask import request, jsonify

from . import predict_bp
from ..config import Config
from ..utils.logger import get_logger
from ..utils.llm_client import LLMClient

logger = get_logger('mirofish.api.predict')


@predict_bp.route('/', methods=['POST'])
def predict():
    """
    Quick-predict a scenario using the knowledge graph.

    Request body:
        {
            "scenario": "What happens if ...",
            "graph_id": "mirofish_abc123" (optional)
        }

    Returns:
        {
            "success": true,
            "prediction": "Based on the knowledge graph ...",
            "context_facts": ["fact1", "fact2", ...]
        }
    """
    try:
        data = request.get_json()
        if not data or not data.get('scenario'):
            return jsonify({
                "success": False,
                "error": "Missing 'scenario' field"
            }), 400

        scenario = data['scenario']
        graph_id = data.get('graph_id', '')

        context_facts = []

        # If a graph_id is provided, search for relevant context
        if graph_id:
            try:
                from ..services.zep_tools import ZepToolsService
                tools = ZepToolsService()
                search_result = tools.search_graph(
                    graph_id=graph_id,
                    query=scenario,
                    limit=15,
                    scope="edges"
                )
                context_facts = search_result.facts
            except Exception as e:
                logger.warning(f"Graph search failed for prediction: {e}")

        # Build the prediction prompt
        context_block = ""
        if context_facts:
            facts_text = "\n".join(f"- {f}" for f in context_facts[:20])
            context_block = f"\n\nRelevant knowledge from the graph:\n{facts_text}"

        llm = LLMClient()
        prediction = llm.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are Mirai's Subconscious — a predictive analysis engine. "
                        "Given a scenario and optional context facts from a knowledge graph, "
                        "predict the most likely outcomes. Be concise, analytical, and "
                        "identify risks, opportunities, and recommended actions."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Scenario: {scenario}{context_block}\n\nPredict the outcomes.",
                },
            ],
            temperature=0.4,
            max_tokens=1000,
        )

        return jsonify({
            "success": True,
            "prediction": prediction,
            "context_facts": context_facts,
        })

    except Exception as e:
        logger.error(f"Prediction failed: {e}\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
