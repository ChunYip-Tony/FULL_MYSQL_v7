from __future__ import annotations

"""Production API bootstrap.

Keeps api_entry_production as the stable product assembly, then installs small
runtime route repairs that must apply after the stable app has registered its
routes.
"""

from api_entry_production import app
from qa_auth_flow_v494 import install_qa_auth_flow_v494

install_qa_auth_flow_v494(app)
