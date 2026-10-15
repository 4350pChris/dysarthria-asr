import logging


def test_health_access_logs(initialized_db) -> None:
    from src.app import configure_logging

    configure_logging()
    configure_logging()
    logger = logging.getLogger("uvicorn.access")
    for method, path, status, expected in [
        ("GET", "/api/health", 200, False),
        ("GET", "/api/health?probe=1", 200, False),
        ("GET", "/api/health", 503, True),
        ("POST", "/api/health", 200, True),
        ("GET", "/api/health/other", 200, True),
        ("GET", "/api/transcribe", 200, True),
    ]:
        record = logger.makeRecord(
            logger.name, logging.INFO, __file__, 0,
            '%s - "%s %s HTTP/%s" %d',
            ("127.0.0.1:1234", method, path, "1.1", status), None,
        )
        assert bool(logger.filter(record)) is expected

    record = logger.makeRecord(
        logger.name, logging.INFO, __file__, 0, "Other message", (), None,
    )
    assert logger.filter(record)
