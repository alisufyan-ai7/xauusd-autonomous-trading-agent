"""Fail-closed exception hierarchy for the production candidate."""


class AgentError(RuntimeError):
    """Base class for errors that must stop or quarantine processing."""


class ValidationError(AgentError, ValueError):
    """Input cannot be represented without ambiguity or loss."""


class IntegrityError(AgentError):
    """Persisted state failed an integrity invariant."""


class LeaseError(AgentError):
    """The caller does not hold a valid single-writer lease."""


class ConcurrentWriteError(LeaseError):
    """A compare-and-swap operation lost a race."""


class CapabilityError(AgentError):
    """A forbidden capability was requested."""
