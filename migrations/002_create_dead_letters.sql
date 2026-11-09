CREATE TABLE dead_letters (
    id        bigserial PRIMARY KEY,
    raw       bytea       NOT NULL,
    reason    text        NOT NULL,
    detail    text        NOT NULL,
    failed_at timestamptz NOT NULL
);

CREATE INDEX dead_letters_reason_idx ON dead_letters (reason, id);
