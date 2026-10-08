from __future__ import annotations

"""Production API bootstrap.

Yipman Mobile V1 is the only official mobile channel. V504 promotes the
consolidated operational renderer to /app/yipman-v1/: Stock Flow-only home,
regular/promotion ordering, REG/TPR lifecycle review, Quick Check and causal
primary-decision evidence. The RC route remains only for diagnostic comparison.
"""

from api_entry_v504 import app
from qa_review_only_v501 import install_qa_review_only_v501
from yipman_mobile_v1_rc_route import install_mobile_v1_rc_route

install_qa_review_only_v501(app)
install_mobile_v1_rc_route(app)
