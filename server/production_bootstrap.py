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
