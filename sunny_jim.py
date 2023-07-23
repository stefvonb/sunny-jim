import device_daemon
import logging
import asyncio
import argparse
import configuration
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import signal
from web_interface import endpoints
from data_management.data_interface import DataInterface


if __name__ == '__main__':
    web_app = FastAPI()

    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Path to config file', default='config.yaml')
    args = parser.parse_args()

    config = configuration.load_config(args.config)
    configuration.configure_logging(config)

    log = logging.getLogger("Sunny Jim")

    loop = asyncio.new_event_loop()

    uvicorn_config = uvicorn.Config(app=web_app, port=config["web_interface"]["port"], log_level="info", host="0.0.0.0", loop=loop)
    uvicorn_server = uvicorn.Server(config=uvicorn_config)
    server_task = asyncio.ensure_future(uvicorn_server.serve(), loop=loop)

    daemon = device_daemon.DeviceDaemon(config, loop)
    daemon_task = asyncio.ensure_future(daemon.run(), loop=loop)

    web_app.mount("/static", StaticFiles(directory="web_interface/static"), name="static")
    templates = Jinja2Templates(directory="web_interface/templates")
    endpoints.register_template_endpoints(web_app, templates, config)

    endpoints.register_device_endpoints(web_app, daemon)

    data_interface = DataInterface.create_from_config(config)
    endpoints.register_data_endpoints(web_app, data_interface, daemon)

    web_app.add_middleware(
        CORSMiddleware,
        allow_origins=config["web_interface"]["allowed_origins"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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
    
