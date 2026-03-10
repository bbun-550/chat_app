import os

# Set OPENCLAW_ROUTER_ENABLED=true to activate intent-based routing.
ROUTER_ENABLED: bool = os.getenv("OPENCLAW_ROUTER_ENABLED", "false").lower() == "true"

# Minimum confidence score (0.0–1.0) to dispatch to a non-chat tool.
ROUTER_THRESHOLD: float = float(os.getenv("OPENCLAW_ROUTER_THRESHOLD", "0.7"))

# Absolute path to the Obsidian vault for the obsidian intent handler.
OBSIDIAN_VAULT_PATH: str = os.getenv("OBSIDIAN_VAULT_PATH", "")
