-- Additive MySQL 8.4 schema. Apply explicitly before enabling any Site cutover.
-- Department identity is part of every primary/foreign key.
CREATE TABLE IF NOT EXISTS finder_department_state (
  department VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  source_revision VARCHAR(128) NOT NULL,
  payload LONGBLOB NOT NULL,
  byte_count BIGINT UNSIGNED NOT NULL,
  record_counts JSON NOT NULL,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (department, sha256),
  CHECK (department IN ('meat','produce')),
  CHECK (byte_count > 0 AND byte_count <= 16777216)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS finder_department_head (
  department VARCHAR(16) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  sha256 CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NULL,
  generation BIGINT UNSIGNED NOT NULL DEFAULT 0,
  updated_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  PRIMARY KEY (department),
  FOREIGN KEY (department, sha256) REFERENCES finder_department_state(department, sha256),
  CHECK (department IN ('meat','produce'))
) ENGINE=InnoDB;

-- Exact source bytes remain immutable. SQL users can inspect the full current
-- JSON document without discarding source metadata, corrections or unknown keys.
CREATE OR REPLACE VIEW finder_department_current AS
SELECT h.department,h.generation,s.sha256,s.source_revision,s.record_counts,
       CAST(CONVERT(s.payload USING utf8mb4) AS JSON) AS document,h.updated_at
FROM finder_department_head h JOIN finder_department_state s
ON s.department=h.department AND s.sha256=h.sha256;

CREATE OR REPLACE VIEW finder_upc_profiles AS
SELECT d.department,d.source_revision,p.ordinal,p.upc,p.article,p.item_name,p.profile
FROM finder_department_current d JOIN JSON_TABLE(d.document,'$.items[*]' COLUMNS (
  ordinal FOR ORDINALITY,
  upc VARCHAR(64) PATH '$.upc' NULL ON EMPTY ERROR ON ERROR,
  article VARCHAR(64) PATH '$.article' NULL ON EMPTY ERROR ON ERROR,
  item_name VARCHAR(512) PATH '$.name' NULL ON EMPTY ERROR ON ERROR,
  profile JSON PATH '$'
)) AS p ON TRUE;

-- POS and family movements deliberately remain separate evidence collections.
CREATE OR REPLACE VIEW finder_pos_records AS
SELECT d.department,d.source_revision,p.ordinal,p.upc,p.source_date,p.record
FROM finder_department_current d JOIN JSON_TABLE(d.document,'$.posEvents[*]' COLUMNS (
  ordinal FOR ORDINALITY,
  upc VARCHAR(64) PATH '$.upc' NULL ON EMPTY ERROR ON ERROR,
  source_date VARCHAR(32) PATH '$.date' NULL ON EMPTY ERROR ON ERROR,
  record JSON PATH '$'
)) AS p ON TRUE;

CREATE OR REPLACE VIEW finder_family_movements AS
SELECT d.department,d.source_revision,m.ordinal,m.article,m.source_date,m.record
FROM finder_department_current d JOIN JSON_TABLE(d.document,'$.movements[*]' COLUMNS (
  ordinal FOR ORDINALITY,
  article VARCHAR(64) PATH '$.article' NULL ON EMPTY ERROR ON ERROR,
  source_date VARCHAR(32) PATH '$.date' NULL ON EMPTY ERROR ON ERROR,
  record JSON PATH '$'
)) AS m ON TRUE;
