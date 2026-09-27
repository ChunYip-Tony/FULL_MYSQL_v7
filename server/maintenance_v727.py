from __future__ import annotations

import json

from db import db_conn, test_database
from manual_overrides import apply_manual_upc_overrides, apply_manual_upc_retirements
from product_identity_audit import audit_product_identity

VERSION = "7.0.27-authority-refresh"
VALID_F291_UPC = "81223402610"
RETIRED_F291_UPC = "26510500000"


def main() -> int:
    print(json.dumps({
        "version": VERSION,
        "database": test_database(),
        "mode": "TARGETED_MANUAL_AUTHORITY_REFRESH_NO_QC_REBUILD",
    }, indent=2, default=str), flush=True)

    with db_conn() as conn:
        cur = conn.cursor(dictionary=True)
        try:
            before = audit_product_identity(cur)
            overrides = apply_manual_upc_overrides(cur)
            retirements = apply_manual_upc_retirements(cur)

            if overrides.get("held"):
                raise RuntimeError(
                    "Manual authority refresh held one or more overrides: "
                    + json.dumps(overrides["held"], default=str)
                )

            after = audit_product_identity(cur)

            cur.execute(
                """SELECT ean_upc,article_number,main_article_number,
                          selling_uom,base_uom,base_qty_per_selling_unit,
                          quick_check_status,blocking_reason
                   FROM quick_check_current
                   WHERE ean_upc=%s
                   LIMIT 1""",
                (VALID_F291_UPC,),
            )
            valid = cur.fetchone()

            cur.execute(
                """SELECT COUNT(*) AS c
                   FROM quick_check_current
                   WHERE ean_upc=%s""",
                (RETIRED_F291_UPC,),
            )
            retired_qc_count = int((cur.fetchone() or {}).get("c") or 0)

            f291_ok = bool(
                valid
                and str(valid.get("selling_uom") or "").upper() == "PACK"
                and str(valid.get("base_uom") or "").upper() == "EA"
                and str(valid.get("base_qty_per_selling_unit")) in {
                    "1", "1.0", "1.00", "1.000000000000"
                }
                and retired_qc_count == 0
                and not any(
                    x.get("code") == "UPC_CURRENT_UOM_CONFLICT"
                    and str(x.get("ean_upc")) == VALID_F291_UPC
                    for x in after.get("blockers", [])
                )
            )
            if not f291_ok:
                raise RuntimeError(
                    "Family 291 authority verification failed: "
                    + json.dumps({
                        "valid": valid,
                        "retired_quick_check_rows": retired_qc_count,
                        "after_blockers": after.get("blockers", []),
                    }, default=str)
                )

            conn.commit()
            print(json.dumps({
                "status": "COMMITTED",
                "before_summary": before.get("summary"),
                "manual_overrides": overrides,
                "manual_retirements": retirements,
                "after_summary": after.get("summary"),
                "family291_valid_quick_check": valid,
                "family291_retired_quick_check_rows": retired_qc_count,
                "family291_authority_pass": f291_ok,
            }, indent=2, default=str), flush=True)
            return 0
        except Exception:
            conn.rollback()
            raise
        finally:
            cur.close()


if __name__ == "__main__":
    raise SystemExit(main())
