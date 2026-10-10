from fastapi import FastAPI

app = FastAPI(
    title="PropertyScout API",
    description="Property intelligence and market analytics for the UAE.",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
def health_check() -> dict[str, str]:
    """Report whether the PropertyScout API is running."""
    return {
        "status": "healthy",
        "service": "PropertyScout API",
    }
