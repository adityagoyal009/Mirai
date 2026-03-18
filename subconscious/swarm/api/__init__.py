"""
API route module
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
predict_bp = Blueprint('predict', __name__)
bi_bp = Blueprint('bi', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import predict  # noqa: E402, F401
from . import business_intel  # noqa: E402, F401

