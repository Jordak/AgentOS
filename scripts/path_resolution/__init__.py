"""Public path-resolution interfaces for trusted AgentOS scripts."""

__all__ = [
    "ManagedPathProblem",
    "managed_path_problem",
    "managed_path_problem_text",
]


def __getattr__(name: str):
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from . import managed

    return getattr(managed, name)
