from requests import Session
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from simbricks.client.auth import simbricks_requests_auth
from .config import TelemetryConfig


def setup_telemetry(config: TelemetryConfig) -> None:
    """Enables the collection of OTEL data for SimBricks.

    User can opt out from this by setting 'disabled' in the 'TelemetryConfig' to
    True or by setting the TELEMETRY_DISABLED environment variable to True.

    Telemetry is collected by default by the runner and the cli.
    """
    assert config

    print("==============================================================")
    if config.disabled:
        print("SimBricks Telemetry Collection disabled.")
        print("==============================================================")
        return

    print("SimBricks Telemetry Collection enabled.")
    print(
        "If you want to disable this, set 'disabled' in the 'TelemetryConfig'\n"
        "to True or set the TELEMETRY_DISABLED environment variable to True."
    )
    print("==============================================================")
    
    assert not config.disabled

    resource = Resource(attributes={"service.name": config.service_name})

    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    custom_session = Session()
    sb_auth = simbricks_requests_auth()
    custom_session.auth = sb_auth

    # Use our custom exporter that knows how to talk to __token_provider
    exporter = OTLPSpanExporter(endpoint=config.otel_receiver_endpoint, session=custom_session)

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Automatically trace the custom httpx_client you pass to AuthenticatedClient
    HTTPXClientInstrumentor().instrument()
