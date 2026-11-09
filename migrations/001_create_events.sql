CREATE TABLE events (
    event_id       text PRIMARY KEY,
    type           text        NOT NULL,
    source         text        NOT NULL,
    schema_version integer     NOT NULL CHECK (schema_version >= 1),
    occurred_at    timestamptz NOT NULL,
    processed_at   timestamptz NOT NULL,
    payload        jsonb       NOT NULL
);

CREATE INDEX events_type_occurred_at_idx ON events (type, occurred_at DESC);
CREATE INDEX events_occurred_at_idx ON events (occurred_at DESC);
