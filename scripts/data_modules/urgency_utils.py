def coerce_urgency(value, default=0.0):
    """Normalize urgency to float. Never raises.

    Handles: int/float, numeric strings (\"100\", \"3.14\"),
    natural language (\"high\"/\"medium\"/\"low\", case-insensitive),
    None, empty string, bool, and unparseable values.
    String mapping aligns with config.foreshadowing_urgency_score_*.
    """
    if value is None:
        return float(default)
    if isinstance(value, bool):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return float(default)
        try:
            return float(stripped)
        except ValueError:
            label = stripped.lower()
            if label in ("high", "紧急"):
                return 100.0
            if label in ("medium", "一般"):
                return 60.0
            if label in ("low", "远期"):
                return 20.0
    return float(default)
