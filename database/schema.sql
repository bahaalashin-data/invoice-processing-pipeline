
--Schema SQL for the Automated Invoice Processing Pipeline
-- Table: email_processing_log
CREATE TABLE IF NOT EXISTS email_processing_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email_id      TEXT,
    message_id    TEXT UNIQUE,
    sender        TEXT,
    subject       TEXT,
    status        TEXT,
    reason        TEXT,
    processed_at  TEXT
);

-- Table: invoice_data
CREATE TABLE IF NOT EXISTS invoice_data (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id        TEXT,
    source_batch      TEXT,
    invoice_no        TEXT NOT NULL,
    invoice_date      TEXT NOT NULL,
    customer_name     TEXT NOT NULL,
    product_category  TEXT,
    product_name      TEXT,
    quantity          REAL,
    unit_price        REAL,
    total_amount      REAL,
    country           TEXT,
    created_date      TEXT,
    record_status TEXT NOT NULL DEFAULT 'VALID',
    rejection_reason TEXT,
    UNIQUE (invoice_no, product_name, quantity, unit_price),
    FOREIGN KEY (message_id) REFERENCES email_processing_log (message_id) ON DELETE CASCADE
);

-- Helpful indexes for the dashboard's analytics queries
CREATE INDEX IF NOT EXISTS idx_invoice_date ON invoice_data (invoice_date);
CREATE INDEX IF NOT EXISTS idx_customer_name ON invoice_data (customer_name);
CREATE INDEX IF NOT EXISTS idx_product_category ON invoice_data (product_category);


-- Table: pipeline_runs
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    duration_sec    REAL,
    status          TEXT NOT NULL DEFAULT 'RUNNING',   -- RUNNING | COMPLETED | FAILED
    email_subject   TEXT,
    zip_filename    TEXT,
    invoices_found  INTEGER DEFAULT 0,
    invoices_loaded INTEGER DEFAULT 0,
    error_message   TEXT
);

-- Table: pipeline_activity_log
CREATE TABLE IF NOT EXISTS pipeline_activity_log (
    log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      INTEGER,
    timestamp   TEXT NOT NULL,
    step_name   TEXT NOT NULL,     -- e.g. "Email Received", "ZIP Downloaded"
    status      TEXT NOT NULL,     -- SUCCESS | FAILED | INFO
    message     TEXT,
    FOREIGN KEY (run_id) REFERENCES pipeline_runs (run_id)
);

CREATE TABLE IF NOT EXISTS rejected_records (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no       TEXT,
    message_id       TEXT,
    source_batch     TEXT,
    customer_name    TEXT,
    product_name     TEXT,
    source_file      TEXT,
    rejection_reason TEXT NOT NULL,
    created_at       TEXT NOT NULL,

    UNIQUE (invoice_no,rejection_reason)
);