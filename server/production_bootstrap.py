from __future__ import annotations

"""Production API bootstrap.

The stable product assembly already registers the QA review route. Do not
install the legacy v494 inline admin-login overlay; QA review should open
cleanly from Yipman Back Office without asking the store user for a second
Admin ID/password.

Server-side authorization for protected QA write actions remains owned by the
canonical QA repair route.
"""

from api_entry_production import app
