from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass
class ThemeConfig:
    background_color: str = "#1a1a2e"
    card_gradient_start: str = "#16213e"
    card_gradient_end: str = "#0f3460"
    accent_color: str = "#e94560"
    text_color: str = "#e0e0e0"
    font_family: str = "Segoe UI"
    font_size: int = 12
    logo_path: str = "images/logo.png"


class ThemeLoader:
    """Read theme.json and return a ThemeConfig.

    On any error (missing file, invalid JSON, wrong types, etc.)
    returns a ThemeConfig with all default values — never raises.
    """

    def load(self, config_path: str) -> ThemeConfig:
        try:
            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return ThemeConfig()
            return ThemeConfig(
                background_color=data.get("background_color", ThemeConfig.background_color),
                card_gradient_start=data.get("card_gradient_start", ThemeConfig.card_gradient_start),
                card_gradient_end=data.get("card_gradient_end", ThemeConfig.card_gradient_end),
                accent_color=data.get("accent_color", ThemeConfig.accent_color),
                text_color=data.get("text_color", ThemeConfig.text_color),
                font_family=data.get("font_family", ThemeConfig.font_family),
                font_size=data.get("font_size", ThemeConfig.font_size),
                logo_path=data.get("logo_path", ThemeConfig.logo_path),
            )
        except Exception:
            return ThemeConfig()

    def to_dict(self, config: ThemeConfig) -> dict:
        """Serialize a ThemeConfig to a plain dict (for round-trip testing)."""
        return asdict(config)
