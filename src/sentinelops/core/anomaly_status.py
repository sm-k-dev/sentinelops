from typing import Final

ANOMALY_STATUS_OPEN: Final[str] = "open"
ANOMALY_STATUS_ACK: Final[str] = "acknowledged"
ANOMALY_STATUS_RESOLVED: Final[str] = "resolved"

ANOMALY_STATUSES: Final[set[str]] = {
    ANOMALY_STATUS_OPEN,
    ANOMALY_STATUS_ACK,
    ANOMALY_STATUS_RESOLVED,
}
