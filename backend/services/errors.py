"""Boundary error types so upstream/location failures map to HTTP codes."""


class LocationError(Exception):
    """Origin/destination could not be resolved (client error -> 400)."""


class UpstreamError(Exception):
    """An external service (routing, LLM) failed (-> 502)."""
