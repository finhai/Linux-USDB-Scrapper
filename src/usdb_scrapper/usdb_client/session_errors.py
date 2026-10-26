"""Shared transport/content errors, independent of session implementations."""


class UsdbError(Exception):
    """Base for sanitized client errors safe to show without response content."""


class ContentDecodeError(UsdbError):
    """A response cannot be decoded or its TXT payload is ambiguous."""
