from pydantic import BaseModel


class TelemetryConfig(BaseModel):
    disabled: bool = False
    otel_receiver_endpoint: str = "https://app.simbricks.io/telemetry/v1/traces"
    service_name: str = "simbricks-client"
