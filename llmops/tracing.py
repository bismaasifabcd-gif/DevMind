"""
tracing.py
──────────
Phoenix tracing — runs as a SEPARATE process.
The FastAPI server only sends spans to it via OTLP.

Set ENABLE_TRACING=true in .env only when Phoenix is actually running.
Default is false to avoid the OTel exporter blocking the agent for minutes
when Phoenix is down.
"""
import os


def setup_tracing():
    if os.getenv("ENABLE_TRACING", "false").lower() != "true":
        print("[tracing] disabled — set ENABLE_TRACING=true when Phoenix is running")
        return None

    try:
        from phoenix.otel import register
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import SimpleSpanProcessor

        # Use a short timeout so a dead Phoenix never blocks the agent
        exporter = OTLPSpanExporter(
            endpoint="http://localhost:6006/v1/traces",
            timeout=3,   # 3s max — never block the agent
        )

        tracer_provider = register(project_name="swe-agent")
        # Replace the default processor with one that won't retry forever
        tracer_provider.add_span_processor(SimpleSpanProcessor(exporter))

        LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
        print("[tracing] Phoenix connected at http://localhost:6006")
        return tracer_provider
    except Exception as e:
        print(f"[tracing] Could not connect to Phoenix (is it running?): {e}")
        return None
