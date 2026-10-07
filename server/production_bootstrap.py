from __future__ import annotations

"""Production API bootstrap.

The stable product assembly registers the QA routes. Keep the legacy admin
login overlay disabled. For normal Back Office use, replace only the QA GET
page so it never offers a repair action that would fail without an admin
session. The protected repair POST remains unchanged server-side.

The consolidated Mobile V1 release candidate is exposed only at the dedicated
preview path /app/yipman-v1-rc/. The official /app/yipman-v1/ renderer remains
unchanged until live RC validation is complete.
"""

from api_entry_production import app
from qa_review_only_v501 import install_qa_review_only_v501
from yipman_mobile_v1_rc_route import install_mobile_v1_rc_route

install_qa_review_only_v501(app)
install_mobile_v1_rc_route(app)
