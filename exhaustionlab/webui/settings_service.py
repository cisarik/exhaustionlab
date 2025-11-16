"""
Settings Service - Manages application configuration and user preferences.
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional, Dict, Any
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)


@dataclass
class ExchangeSettings:
    """Exchange connection settings"""

    exchange: str = "binance"
    api_key: str = ""
    api_secret: str = ""
    testnet: bool = True
    default_symbol: str = "ADAEUR"
    default_timeframe: str = "1m"


@dataclass
class LLMSettings:
    """LLM configuration settings"""

    provider: str = "deepseek"  # deepseek, openai, local
    api_url: str = "http://127.0.0.1:1234/v1"
    api_key: str = ""
    model: str = "deepseek-r1-0528-qwen3-8b"
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: int = 120
    enabled: bool = True


@dataclass
class RiskSettings:
    """Default risk management settings"""

    max_position_size: float = 0.02  # 2% of portfolio
    max_daily_loss: float = 0.01  # 1% daily loss
    max_drawdown: float = 0.05  # 5% max drawdown
    max_open_positions: int = 3
    enable_stop_loss: bool = True
    stop_loss_pct: float = 0.02  # 2%
    enable_take_profit: bool = True
    take_profit_pct: float = 0.05  # 5%


@dataclass
class EvolutionSettings:
    """Evolution/backtesting settings"""

    default_generations: int = 5
    default_population: int = 3
    use_llm: bool = True
    use_crawled: bool = True
    backtest_data_days: int = 30
    fitness_metric: str = "sharpe_ratio"  # sharpe_ratio, total_return, win_rate


@dataclass
class UISettings:
    """UI preferences"""

    theme: str = "dark"  # dark, light
    auto_refresh: bool = True
    refresh_interval: int = 2  # seconds
    chart_default_symbol: str = "ADAEUR"
    chart_default_timeframe: str = "1m"
    notifications_enabled: bool = True
    sound_enabled: bool = False


@dataclass
class AppSettings:
    """Complete application settings"""

    exchange: ExchangeSettings
    llm: LLMSettings
    risk: RiskSettings
    evolution: EvolutionSettings
    ui: UISettings

    def to_dict(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Convert to dictionary, optionally masking secrets"""
        data = {
            "exchange": asdict(self.exchange),
            "llm": asdict(self.llm),
            "risk": asdict(self.risk),
            "evolution": asdict(self.evolution),
            "ui": asdict(self.ui),
        }

        if not include_secrets:
            # Mask sensitive data
            if data["exchange"]["api_key"]:
                data["exchange"]["api_key"] = "***MASKED***"
            if data["exchange"]["api_secret"]:
                data["exchange"]["api_secret"] = "***MASKED***"
            if data["llm"]["api_key"]:
                data["llm"]["api_key"] = "***MASKED***"

        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AppSettings":
        """Create from dictionary"""
        return cls(
            exchange=ExchangeSettings(**data.get("exchange", {})),
            llm=LLMSettings(**data.get("llm", {})),
            risk=RiskSettings(**data.get("risk", {})),
            evolution=EvolutionSettings(**data.get("evolution", {})),
            ui=UISettings(**data.get("ui", {})),
        )


class SettingsService:
    """
    Manages application settings with encryption for sensitive data.

    Features:
    - Load/save settings from/to disk
    - Encrypt sensitive data (API keys)
    - Default settings
    - Settings validation
    """

    def __init__(
        self,
        settings_file: Optional[Path] = None,
        encryption_key: Optional[bytes] = None,
    ):
        self.settings_file = (
            settings_file or Path.home() / ".exhaustionlab" / "settings.json"
        )
        self.settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Encryption for sensitive data
        self.encryption_key = encryption_key or self._get_or_create_key()
        self.cipher = Fernet(self.encryption_key)

        # Load or create default settings
        self.settings = self._load_settings()

    def _get_or_create_key(self) -> bytes:
        """Get or create encryption key"""
        key_file = self.settings_file.parent / ".key"

        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            key_file.chmod(0o600)  # Read/write for owner only
            return key

    def _encrypt(self, value: str) -> str:
        """Encrypt a string value"""
        if not value:
            return ""
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, value: str) -> str:
        """Decrypt a string value"""
        if not value:
            return ""
        try:
            return self.cipher.decrypt(value.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt value: {e}")
            return ""

    def _load_settings(self) -> AppSettings:
        """Load settings from disk or create defaults"""
        if self.settings_file.exists():
            try:
                data = json.loads(self.settings_file.read_text())
                settings = AppSettings.from_dict(data)

                # Decrypt sensitive fields
                if (
                    settings.exchange.api_key
                    and settings.exchange.api_key != "***MASKED***"
                ):
                    settings.exchange.api_key = self._decrypt(settings.exchange.api_key)
                if (
                    settings.exchange.api_secret
                    and settings.exchange.api_secret != "***MASKED***"
                ):
                    settings.exchange.api_secret = self._decrypt(
                        settings.exchange.api_secret
                    )
                if settings.llm.api_key and settings.llm.api_key != "***MASKED***":
                    settings.llm.api_key = self._decrypt(settings.llm.api_key)

                logger.info(f"Loaded settings from {self.settings_file}")
                return settings
            except Exception as e:
                logger.error(f"Failed to load settings: {e}, using defaults")

        # Return default settings
        return AppSettings(
            exchange=ExchangeSettings(),
            llm=LLMSettings(),
            risk=RiskSettings(),
            evolution=EvolutionSettings(),
            ui=UISettings(),
        )

    def save_settings(self, settings: Optional[AppSettings] = None) -> bool:
        """Save settings to disk"""
        if settings:
            self.settings = settings

        try:
            # Create a copy for saving with encrypted secrets
            data = asdict(self.settings)

            # Encrypt sensitive fields
            if data["exchange"]["api_key"]:
                data["exchange"]["api_key"] = self._encrypt(data["exchange"]["api_key"])
            if data["exchange"]["api_secret"]:
                data["exchange"]["api_secret"] = self._encrypt(
                    data["exchange"]["api_secret"]
                )
            if data["llm"]["api_key"]:
                data["llm"]["api_key"] = self._encrypt(data["llm"]["api_key"])

            self.settings_file.write_text(json.dumps(data, indent=2))
            logger.info(f"Saved settings to {self.settings_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
            return False

    def get_settings(self, include_secrets: bool = False) -> Dict[str, Any]:
        """Get current settings as dictionary"""
        return self.settings.to_dict(include_secrets=include_secrets)

    def update_settings(self, updates: Dict[str, Any]) -> bool:
        """Update settings with partial updates"""
        try:
            # Update exchange settings
            if "exchange" in updates:
                for key, value in updates["exchange"].items():
                    if hasattr(self.settings.exchange, key):
                        setattr(self.settings.exchange, key, value)

            # Update LLM settings
            if "llm" in updates:
                for key, value in updates["llm"].items():
                    if hasattr(self.settings.llm, key):
                        setattr(self.settings.llm, key, value)

            # Update risk settings
            if "risk" in updates:
                for key, value in updates["risk"].items():
                    if hasattr(self.settings.risk, key):
                        setattr(self.settings.risk, key, value)

            # Update evolution settings
            if "evolution" in updates:
                for key, value in updates["evolution"].items():
                    if hasattr(self.settings.evolution, key):
                        setattr(self.settings.evolution, key, value)

            # Update UI settings
            if "ui" in updates:
                for key, value in updates["ui"].items():
                    if hasattr(self.settings.ui, key):
                        setattr(self.settings.ui, key, value)

            # Save to disk
            return self.save_settings()
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            return False

    def reset_to_defaults(self) -> bool:
        """Reset all settings to defaults"""
        self.settings = AppSettings(
            exchange=ExchangeSettings(),
            llm=LLMSettings(),
            risk=RiskSettings(),
            evolution=EvolutionSettings(),
            ui=UISettings(),
        )
        return self.save_settings()

    def validate_exchange_connection(self) -> tuple[bool, str]:
        """Validate exchange API credentials"""
        # This would actually test the connection
        # For now, just check if credentials are provided
        if not self.settings.exchange.api_key or not self.settings.exchange.api_secret:
            return False, "API key and secret are required"
        return True, "Exchange credentials configured"

    def validate_llm_connection(self) -> tuple[bool, str]:
        """Validate LLM connection"""
        if not self.settings.llm.enabled:
            return True, "LLM disabled"

        if not self.settings.llm.api_url:
            return False, "LLM API URL is required"

        # Could test actual connection here
        return True, "LLM configured"


# Global instance
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """Get or create global settings service instance"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service
