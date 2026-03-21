"""
Business Intelligence API endpoints.
Full pipeline: exec_summary → research → predict → plan.
"""

import traceback
from flask import request, jsonify

from . import bi_bp
from ..utils.logger import get_logger
from ..services.business_intel import BusinessIntelEngine, EXEC_SUMMARY_TEMPLATE

logger = get_logger('mirofish.api.bi')


@bi_bp.route('/template', methods=['GET'])
def template():
    """
    Returns the recommended exec summary template and an example.
    Use this to guide users on what information to provide.
    """
    return jsonify({
        "success": True,
        "template": EXEC_SUMMARY_TEMPLATE["template"],
        "example": EXEC_SUMMARY_TEMPLATE["example"],
        "fields": EXEC_SUMMARY_TEMPLATE["fields"],
    })


@bi_bp.route('/validate', methods=['POST'])
def validate():
    """
    Validate an exec summary without running the full analysis.
    Returns data quality score and what fields are missing/vague.

    Request body:
        {"exec_summary": "..."}
    """
    try:
        data = request.get_json()
        if not data or not data.get('exec_summary'):
            return jsonify({"success": False, "error": "Missing 'exec_summary' field"}), 400

        engine = BusinessIntelEngine()
        result = engine.extract_and_validate(data['exec_summary'])

        return jsonify({
            "success": True,
            "data_quality": result.data_quality,
            "fields_present": result.fields_present,
            "fields_missing": result.fields_missing,
            "fields_vague": result.fields_vague,
            "extraction": {
                "company": result.company,
                "industry": result.industry,
                "product": result.product,
                "target_market": result.target_market,
                "business_model": result.business_model,
                "stage": result.stage,
                "traction": result.traction,
                "ask": result.ask,
            },
            "ready_for_analysis": len([
                f for f in ["company", "industry", "product"]
                if f in result.fields_missing
            ]) == 0,
        })

    except Exception as e:
        logger.error(f"BI validate failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@bi_bp.route('/analyze', methods=['POST'])
def analyze():
    """
    Full BI pipeline: extract → validate → research → predict → plan.

    Request body:
        {
            "exec_summary": "We are building...",
            "research_depth": "quick|standard|deep"   (optional, default: standard)
            "swarm_count": 0|50|100|250|500|1000       (optional, default: 0)
        }

    Returns:
        - If critical fields missing: status=needs_more_info with template + guidance
        - If sufficient: status=complete with full analysis + data_quality score
        - If swarm_count > 0: includes swarm prediction with agent consensus
    """
    try:
        data = request.get_json()
        if not data or not data.get('exec_summary'):
            return jsonify({"success": False, "error": "Missing 'exec_summary' field"}), 400

        exec_summary = data['exec_summary']
        depth = data.get('research_depth', 'standard')
        if depth not in ('quick', 'standard', 'deep'):
            depth = 'standard'

        swarm_count = data.get('swarm_count', 0)
        try:
            swarm_count = int(swarm_count)
        except (TypeError, ValueError):
            swarm_count = 0
        if swarm_count not in (0, 50, 100, 250, 500, 1000):
            swarm_count = 0

        engine = BusinessIntelEngine()
        result = engine.analyze(exec_summary, depth=depth, swarm_count=swarm_count)

        if result.get("status") == "needs_more_info":
            return jsonify({"success": False, **result}), 422

        return jsonify({"success": True, "analysis": result})

    except Exception as e:
        logger.error(f"BI analysis failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@bi_bp.route('/research', methods=['POST'])
def research_only():
    """
    Research phase only.

    Request body:
        {
            "exec_summary": "...",
            "research_depth": "quick|standard|deep"
        }
    """
    try:
        data = request.get_json()
        if not data or not data.get('exec_summary'):
            return jsonify({"success": False, "error": "Missing 'exec_summary' field"}), 400

        depth = data.get('research_depth', 'standard')
        if depth not in ('quick', 'standard', 'deep'):
            depth = 'standard'

        engine = BusinessIntelEngine()
        report = engine.research(data['exec_summary'], depth=depth)

        return jsonify({"success": True, "research": report.to_dict()})

    except Exception as e:
        logger.error(f"BI research failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@bi_bp.route('/predict', methods=['POST'])
def predict_only():
    """
    Predict phase only (requires research data).

    Request body:
        {
            "exec_summary": "...",
            "research": { ... ResearchReport dict ... }
        }
    """
    try:
        data = request.get_json()
        if not data or not data.get('exec_summary') or not data.get('research'):
            return jsonify({
                "success": False,
                "error": "Missing 'exec_summary' or 'research' field"
            }), 400

        from ..services.business_intel import ResearchReport
        r = data['research']
        report = ResearchReport(
            company=r.get('company', ''),
            industry=r.get('industry', ''),
            product=r.get('product', ''),
            market_data=r.get('market_data', []),
            competitors=r.get('competitors', []),
            news=r.get('news', []),
            trends=r.get('trends', []),
            sentiment=r.get('sentiment', 'neutral'),
            context_facts=r.get('context_facts', []),
            browser_queries=r.get('browser_queries', []),
        )

        engine = BusinessIntelEngine()
        prediction = engine.predict(data['exec_summary'], report)

        return jsonify({"success": True, "prediction": prediction.to_dict()})

    except Exception as e:
        logger.error(f"BI predict failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500


@bi_bp.route('/history', methods=['GET'])
def history():
    """
    Retrieve past BI analyses from ChromaDB.

    Query params:
        limit (int, default 20)
    """
    try:
        limit = request.args.get('limit', 20, type=int)
        engine = BusinessIntelEngine()
        results = engine.get_history(limit=limit)
        return jsonify({"success": True, "analyses": results})

    except Exception as e:
        logger.error(f"BI history failed: {e}\n{traceback.format_exc()}")
        return jsonify({"success": False, "error": str(e)}), 500
