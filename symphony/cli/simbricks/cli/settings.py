from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from simbricks.client.settings import ClientSettings
from simbricks.telemetry.config import TelemetryConfig


class CliSettings(BaseSettings):
    client: ClientSettings = ClientSettings()
    telemetry: TelemetryConfig = TelemetryConfig()

    model_config = SettingsConfigDict(
        env_prefix="",
        env_nested_delimiter="_",
    )


@lru_cache
def cli_settings() -> CliSettings:
    return CliSettings(_env_file="simbricks-cli.env", _env_file_encoding="utf-8")
