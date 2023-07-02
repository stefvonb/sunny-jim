import device_daemon
import logging
import asyncio
import argparse
import configuration
import uvicorn
from fastapi import FastAPI
import signal
from web_interface import endpoints


if __name__ == '__main__':
    web_app = FastAPI()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Path to config file', default='config.yaml')
    args = parser.parse_args()

    config = configuration.load_config(args.config)
    configuration.configure_logging(config)

    log = logging.getLogger("Sunny Jim")

    loop = asyncio.new_event_loop()

    uvicorn_config = uvicorn.Config(app=web_app, port=config["web_interface"]["port"], log_level="info", host=config["web_interface"]["host"], loop=loop)
    uvicorn_server = uvicorn.Server(config=uvicorn_config)
    server_task = asyncio.ensure_future(uvicorn_server.serve(), loop=loop)

    daemon = device_daemon.DeviceDaemon(config, loop)
    daemon_task = asyncio.ensure_future(daemon.run(), loop=loop)

    endpoints.register_device_endpoints(web_app, daemon)

    @web_app.on_event("shutdown")
    async def shutdown_event():
        await daemon.stop(signal.SIGTERM)

    @web_app.on_event("startup")
    async def startup_event():
        logger = logging.getLogger("uvicorn")
        console_formatter = configuration.get_formatter()
        logger.handlers[0].formatter = console_formatter

    try:
        loop.run_until_complete(asyncio.gather(daemon_task, server_task))
    except Exception as e:
        log.error(f"Exception in main loop: {e}")
    