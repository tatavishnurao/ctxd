class StorageError(RuntimeError):
    """Base error for an unavailable or invalid persistence operation."""


class StorageUnavailableError(StorageError):
    """The configured persistence backend could not be reached."""


class StorageDataError(StorageError):
    """Persisted data does not satisfy the current domain model."""


class RetrievalTimeoutError(StorageError):
    """A lexical query exceeded the configured database timeout."""


class MigrationRequiredError(StorageError):
    """The database schema has not been migrated to the required revision."""
