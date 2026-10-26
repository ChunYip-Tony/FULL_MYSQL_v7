# Bounded Seafood source cutover

The separate, time-limited `/v1/migration/sites/cutover` credential permits a fixed plan, prepare, freeze, verify, frozen snapshot, commit, and pre-commit rollback. No caller SQL, schema name, account name, or destination is accepted. The committed startup mode remains NORMAL in this change.

The plan pins the current database and the four reviewed business writer identities, retains exact original grants, checks global account/role/proxy/event/definer and cross-database foreign-key paths, and rejects drift. A verified DigitalOcean hostname, CA configuration, and encrypted session are required. The exact system `root` identity remains unchanged: DigitalOcean documents that customers cannot use it, at https://docs.digitalocean.com/products/databases/mysql/details/limits/. This is a managed-provider policy classification, not a claim that the account has no privileges.

Before preparation the Sites coordinator must retain and read back the canonical plan in private storage. Preparation creates a new schema-scoped restore controller and tests partial revoke plus exact grant restoration on a new locked disposable account. It does not revoke any business account privileges.

Freeze requires the matching isolated startup gate, no other ordinary SQL sessions, the tested restore path, and exact account inventory. Only write/DDL privileges in the current Seafood database are partially revoked; reads and other databases stay unchanged. The new controller holds the narrowly scoped restoration privileges and writes the cutover receipt. A fresh application connection must reject zero-row business writes. Frozen exports include matching before/after freeze proof and the existing table checksums.

Rollback restores the exact original grants using the independent controller, then the committed startup mode can return to NORMAL. After the coordinator records COMMITTED, automatic rollback is refused: native writes require reconciliation before any return to the old source. No existing accounts or source data are deleted. The control table is excluded from source exports.

Validation: run `python -m unittest discover -s tests -v`. Live prepare additionally verifies the actual managed server's revoke/restore behavior before the freeze is attempted.
