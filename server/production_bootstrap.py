from __future__ import annotations

"""Production API bootstrap.

The stable product assembly registers the QA routes. Keep the legacy admin
login overlay disabled. For normal Back Office use, replace only the QA GET
page so it never offers a repair action that would fail without an admin
session. The protected repair POST remains unchanged server-side.

The Mobile V1 consolidated release candidate is installed as an isolated
front-end decorator on the dedicated /app/yipman-v1/ renderer. Existing live
Ordering, Price, True Stock, Data Center, and API behavior remain canonical.
"""

from api_entry_production import app
from qa_review_only_v501 import install_qa_review_only_v501
from yipman_mobile_v1_consolidated_rc import install_mobile_v1_consolidated_rc

install_qa_review_only_v501(app)
install_mobile_v1_consolidated_rc(app)
