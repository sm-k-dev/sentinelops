def anomaly_to_slack_text(anomaly) -> str:
    lines = [
        "🚨 *SentinelOps Anomaly Detected*",
        f"*Rule:* {anomaly.rule_code}",
        f"*Severity:* {anomaly.severity}",
        f"*Status:* {anomaly.status}",
    ]

    if anomaly.window_start and anomaly.window_end:
        lines.append(
            f"*Window:* {anomaly.window_start} ~ {anomaly.window_end}"
        )

    if anomaly.evidence:
        lines.append(f"*Evidence:* `{anomaly.evidence}`")

    return "\n".join(lines)
