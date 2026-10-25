from __future__ import annotations

"""Production API bootstrap.

Yipman Mobile V1 is the only official mobile channel. V504 promotes the
consolidated operational renderer to /app/yipman-v1/: Stock Flow-only home,
regular/promotion ordering, REG/TPR lifecycle review, Quick Check and causal
primary-decision evidence. The RC route remains only for diagnostic comparison.

App Ready adds an atomic precomputed snapshot serving layer. Upload/publish
workers build the next snapshot before promotion; Mobile/Desktop readers keep
using the previous complete snapshot until the replacement is APP_READY.
"""

import api as _api
from api_entry_v504 import app
from qa_review_only_v501 import install_qa_review_only_v501
from yipman_mobile_v1_rc_route import install_mobile_v1_rc_route
from yipman_app_ready_api import install_app_ready_api, request_app_ready_rebuild
from yipman_app_ready_ingest_hook import install_app_ready_ingest_hook
from yipman_app_ready_true_stock_hook import install_app_ready_true_stock_hook
from yipman_mobile_v1_app_ready_fastpath import install_app_ready_fastpath

install_qa_review_only_v501(app)
install_mobile_v1_rc_route(app)
install_app_ready_fastpath(app)
install_app_ready_api(app)
install_app_ready_ingest_hook(app, _api, request_app_ready_rebuild)
install_app_ready_true_stock_hook(app, _api, request_app_ready_rebuild)


# Shared inventory card evidence; both existing desktop URLs retain their identity.
from inventory_sales import install_inventory_sales
install_inventory_sales(app, _api)

from inventory_family_catalog import install_family_catalog
install_family_catalog(app)


# Final display branding runs after the official mobile renderer composition.
from fishfinder_brand import install_fishfinder_brand
install_fishfinder_brand(_api)

# Keep health and AI status responsive when interactive requests arrive in bursts.
from request_capacity import RequestCapacityMiddleware
app.add_middleware(RequestCapacityMiddleware)

# Bounded-memory, consistent historical export for the Sites migration.
from sites_migration_export import install_sites_migration_export
install_sites_migration_export(app)

# Disabled until schema, credentials, and complete source readback are verified.
from finder_department_store import install_department_store
install_department_store(app)

