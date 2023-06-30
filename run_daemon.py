import argparse
import configuration
from communication.connect_devices import run_devices
from communication.attach_observers import attach_observers
import logging
import asyncio
import signal

log = logging.getLogger("Daemon")

async def daemon(config: dict):
    asynchronous_tasks = []

    loop = asyncio.get_event_loop()
    running_devices = await run_devices(config)

    if len(running_devices) == 0:
        log.error("No devices running!")

    else:
        observer_tasks, stop_functions = attach_observers(running_devices, config)
        asynchronous_tasks.extend(observer_tasks)
        asynchronous_tasks.extend([device.run() for device in running_devices.values()])

        async def shutdown(signal_type):
            # This functionality might benefit from some structure
            log.info(f"Shutting down due to signal {signal_type}...")
            for device in running_devices.values():
                device.stop()

            for stop_function in stop_functions:
                await stop_function()

        # Add handling for signals
        for signal_type in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
            loop.add_signal_handler(signal_type, lambda: asyncio.ensure_future(shutdown(signal_type)))

        await asyncio.gather(*asynchronous_tasks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Path to config file', default='config.yaml')
    args = parser.parse_args()

    config = configuration.load_config(args.config)
    configuration.configure_logging(config)

    log.info("Starting daemon...")
    loop = asyncio.new_event_loop()

    loop.run_until_complete(daemon(config))
    