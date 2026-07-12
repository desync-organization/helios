import asyncio

import uvicorn

from helios.api import create_app
from helios.config import Settings
from helios.runtime import HeliosRuntime


async def run() -> None:
    settings = Settings()
    runtime = HeliosRuntime(settings)
    app = create_app(runtime)
    server = uvicorn.Server(uvicorn.Config(app, host=settings.helios_api_host,
                                          port=settings.helios_api_port, log_level="info"))
    poller = asyncio.create_task(runtime.serve(), name="helios-poller")
    try:
        await server.serve()
    finally:
        runtime.stop()
        poller.cancel()
        await asyncio.gather(poller, return_exceptions=True)


def cli() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    cli()

