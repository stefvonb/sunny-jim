import device_daemon
import functools
import logging
import asyncio
import argparse
import configuration
import uvicorn
from fastapi import FastAPI
import signal

shared_devices = {}
web_app = FastAPI()

@web_app.get("/")
async def root():
    return shared_devices


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Path to config file', default='config.yaml')
    args = parser.parse_args()

    config = configuration.load_config(args.config)
    configuration.configure_logging(config)

    log = logging.getLogger("Sunny Jim")

    loop = asyncio.new_event_loop()

    uvicorn_config = uvicorn.Config(app=web_app, port=8000, log_level="info", host="0.0.0.0", loop=loop)
    uvicorn_server = uvicorn.Server(config=uvicorn_config)
    server_task = asyncio.ensure_future(uvicorn_server.serve(), loop=loop)

    daemon = device_daemon.DeviceDaemon(config, loop, shared_devices)
    daemon_task = asyncio.ensure_future(daemon.run(), loop=loop)

    @web_app.on_event("shutdown")
    async def shutdown_event():
        await daemon.stop(signal.SIGTERM)

    try:
        loop.run_until_complete(asyncio.gather(daemon_task, server_task))
    except Exception as e:
        log.error(f"Exception in main loop: {e}")
    