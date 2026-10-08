from __future__ import annotations

"""Production API bootstrap.

The stable product assembly registers the QA routes. Keep the legacy admin
login overlay disabled. For normal Back Office use, replace only the QA GET
page so it never offers a repair action that would fail without an admin
session. The protected repair POST remains unchanged server-side.

Yipman Mobile V1 remains the only official mobile channel. V494 adds a shared
primary-decision drill-down (why, evidence, calculation/source, limitations)
without creating a new product route. The existing RC route remains available
for consolidated-release validation.
"""

from api_entry_v494 import app
from qa_review_only_v501 import install_qa_review_only_v501
from yipman_mobile_v1_rc_route import install_mobile_v1_rc_route

install_qa_review_only_v501(app)
install_mobile_v1_rc_route(app)
