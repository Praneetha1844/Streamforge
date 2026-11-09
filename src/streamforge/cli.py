"""Command-line interface: ``streamforge generate|run|replay|quality|migrate|serve``."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
import threading
from collections.abc import Sequence
from datetime import timedelta

from pydantic import ValidationError

from streamforge import __version__
from streamforge.bootstrap import App, build_app, build_stores
from streamforge.config import Settings
from streamforge.domain import QueueError, RejectReason
from streamforge.generator import generate_events
from streamforge.logging_setup import configure_logging
from streamforge.migrate import apply_migrations
from streamforge.pipeline import replay, utc_now
from streamforge.quality import evaluate, load_rules

log = logging.getLogger("streamforge.cli")


def build_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(prog="streamforge", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="write synthetic events as JSON lines")
    gen.add_argument("--count", type=int, default=100)
    gen.add_argument("--seed", type=int, default=1)
    gen.add_argument("--invalid-ratio", type=float, default=0.0)
    gen.add_argument("--out", help="output file (default: stdout)")

    run = sub.add_parser("run", help="process messages from the queue")
    run.add_argument("--follow", action="store_true", help="keep polling instead of exiting")
    run.add_argument(
        "--demo", type=int, default=0, metavar="N", help="publish N demo events per cycle"
    )
    run.add_argument("--seed", type=int, default=1, help="base seed for demo events")
    run.add_argument("--poll-interval", type=float, help="seconds between empty polls")
    run.add_argument("--no-metrics-server", action="store_true")

    rep = sub.add_parser("replay", help="re-publish dead letters to the queue")
    rep.add_argument("--reason", choices=[r.value for r in RejectReason])
    rep.add_argument("--limit", type=int, default=1000)

    qual = sub.add_parser("quality", help="evaluate data-quality rules on stored events")
    qual.add_argument("--limit", type=int, default=10000)

    sub.add_parser("migrate", help="apply pending SQL migrations")
    sub.add_parser("serve", help="run the read API")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point. Return the process exit code."""
    args = build_parser().parse_args(argv)
    if args.command == "generate":
        return _generate(args)
    try:
        settings = Settings()
    except ValidationError as exc:
        print(f"invalid configuration: {exc}", file=sys.stderr)
        return 2
    configure_logging(settings.log_level)
    handlers = {
        "run": _run,
        "replay": _replay,
        "quality": _quality,
        "migrate": _migrate,
        "serve": _serve,
    }
    return handlers[args.command](args, settings)


def _generate(args: argparse.Namespace) -> int:
    events = generate_events(args.count, args.seed, invalid_ratio=args.invalid_ratio)
    out = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout  # noqa: SIM115
    try:
        for event in events:
            out.write(json.dumps(event) + "\n")
    finally:
        if args.out:
            out.close()
    return 0


def _publish_demo(app: App, count: int, seed: int) -> None:
    # Start in the past so generated timestamps never lie in the future.
    start = utc_now() - timedelta(seconds=count * 7 + 5)
    for event in generate_events(count, seed, start=start, invalid_ratio=0.05):
        app.queue.publish(json.dumps(event).encode("utf-8"))


def _run(args: argparse.Namespace, settings: Settings) -> int:
    from prometheus_client import start_http_server

    app = build_app(settings)
    if not args.no_metrics_server:
        start_http_server(settings.metrics_port, registry=app.metrics.registry)
    poll = args.poll_interval or settings.poll_interval_seconds
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())

    cycle = 0
    while not stop.is_set():
        if args.demo and (args.follow or cycle == 0):
            _publish_demo(app, args.demo, args.seed + cycle)
        cycle += 1
        try:
            result = app.processor.process_batch(settings.batch_size)
        except QueueError:
            log.exception("queue error, backing off")
            stop.wait(poll)
            continue
        if result.total:
            log.info(
                "batch done",
                extra={
                    "processed": result.processed,
                    "duplicates": result.duplicates,
                    "dead_lettered": result.dead_lettered,
                    "retried": result.retried,
                },
            )
        elif args.follow:
            stop.wait(poll)
        else:
            break
    return 0


def _replay(args: argparse.Namespace, settings: Settings) -> int:
    app = build_app(settings)
    reasons = [RejectReason(args.reason)] if args.reason else None
    count = replay(app.dead_letters, app.queue, reasons, args.limit)
    print(json.dumps({"replayed": count}))
    return 0


def _quality(args: argparse.Namespace, settings: Settings) -> int:
    store, _ = build_stores(settings)
    rules = load_rules(settings.rules_path)
    records = [record.as_dict() for record in store.list_events(None, args.limit)]
    report = evaluate(rules, records, utc_now())
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.passed else 1


def _migrate(_: argparse.Namespace, settings: Settings) -> int:
    if settings.database_url is None:
        print("SF_DATABASE_URL is required to migrate", file=sys.stderr)
        return 2
    applied = apply_migrations(settings.database_url.get_secret_value(), settings.migrations_dir)
    print(json.dumps({"applied": applied}))
    return 0


def _serve(_: argparse.Namespace, settings: Settings) -> int:
    import uvicorn

    uvicorn.run(
        "streamforge.api:app_from_env",
        factory=True,
        host=settings.api_host,
        port=settings.api_port,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
