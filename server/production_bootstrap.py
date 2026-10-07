from __future__ import annotations

"""Production API bootstrap.

The stable product assembly registers the QA routes. Keep the legacy admin
login overlay disabled. For normal Back Office use, replace only the QA GET
page so it never offers a repair action that would fail without an admin
session. The protected repair POST remains unchanged server-side.
"""

from api_entry_production import app
from qa_review_only_v501 import install_qa_review_only_v501

install_qa_review_only_v501(app)
