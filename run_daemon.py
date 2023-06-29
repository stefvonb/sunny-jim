import argparse
import configuration
from communication.connect_devices import run_devices
from communication.attach_observers import attach_observers
from communication.devices import CommandType
import logging
import asyncio
import signal

log = logging.getLogger("Daemon")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Path to config file', default='config.yaml')
    args = parser.parse_args()

    config = configuration.load_config(args.config)
    configuration.configure_logging(config)

    asynchronous_tasks = []

    loop = asyncio.new_event_loop()
    running_devices = loop.run_until_complete(run_devices(config))

    inverter = running_devices["kodak_ogx_548"]

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

        loop.run_until_complete(asyncio.wait(asynchronous_tasks))
