# Backwards-compatibility shim.
# The canonical implementation lives in swm_common.logger.
from swm_common.logger import configure_logging, get_logger

__all__ = ["configure_logging", "get_logger"]
