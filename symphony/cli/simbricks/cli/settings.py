from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from simbricks.client.settings import ClientSettings
from simbricks.telemetry.config import TelemetryConfig
from simbricks.client import (
    simb_client as client_simb_client,
    SimBricksClient,
    ns_client as client_ns_client,
    NSClient,
    rg_client as client_rg_client,
    ResourceGroupClient,
    runner_client as client_runner_client,
    RunnerClient,
)

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


async def ns_client() -> NSClient:
    base_url = cli_settings().client.base_url
    ns_path = cli_settings().client.namespace
    client = await client_ns_client(base_url, ns_path)
    return client


async def runner_client(runner_id: str) -> RunnerClient:
    namespace_client = await ns_client()
    client = await client_runner_client(runner_id, namespace_client)
    return client


async def rg_client() -> ResourceGroupClient:
    namespace_client = await ns_client()
    client = await client_rg_client(namespace_client)
    return client


async def simb_client() -> SimBricksClient:
    namespace_client = await ns_client()
    client = await client_simb_client(namespace_client)
    return client
