import argparse
import configuration
from communication.connect_devices import run_devices
from communication.attach_observers import attach_observers
import logging
import asyncio
import signal

log = logging.getLogger("Device Daemon")

class DeviceDaemon:
    def __init__(self, config: dict, loop: asyncio.AbstractEventLoop, running_devices: dict = None):
        self.config = config
        self.loop = loop
        self.stop_functions = []

        if running_devices is None:
            self.running_devices = {}
        else:
            self.running_devices = running_devices

    async def run(self):
        asynchronous_tasks = []

        self.running_devices = await run_devices(self.config)

        if len(self.running_devices) == 0:
            log.error("No devices running!")

        else:
            observer_tasks, self.stop_functions = attach_observers(self.running_devices, self.config)
            asynchronous_tasks.extend(observer_tasks)
            asynchronous_tasks.extend([device.run() for device in self.running_devices.values()])

            await asyncio.gather(*asynchronous_tasks)

    async def stop(self, signal_type):
        log.info(f"Shutting down due to signal {signal_type}...")
        for device in self.running_devices.values():
            device.stop()

        for stop_function in self.stop_functions:
            await stop_function()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help='Path to config file', default='config.yaml')
    args = parser.parse_args()

    config = configuration.load_config(args.config)
    configuration.configure_logging(config)

    log.info("Starting daemon...")
    loop = asyncio.new_event_loop()

    daemon = DeviceDaemon(config, loop)

    # Add handling for signals
    for signal_type in [signal.SIGINT, signal.SIGTERM, signal.SIGHUP]:
        loop.add_signal_handler(signal_type, lambda: asyncio.ensure_future(daemon.stop(signal_type), loop=loop))

    loop.run_until_complete(daemon.run())
    