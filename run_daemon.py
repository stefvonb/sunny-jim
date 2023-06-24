import argparse
import configuration
from communication.connect_devices import run_devices
from communication.attach_observers import attach_observers
import logging
import asyncio

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

    if len(running_devices) == 0:
        log.error("No devices running!")

    else:
        observer_tasks = attach_observers(running_devices, config)
        asynchronous_tasks.extend(observer_tasks)
        asynchronous_tasks.extend([device.run() for device in running_devices.values()])

        try:
            loop.run_until_complete(asyncio.wait(asynchronous_tasks))
        except KeyboardInterrupt:
            log.info("Keyboard interrupt received, stopping devices...")
            for device in running_devices.values():
                device.stop()
        finally:
            # TODO: Still not sure why the loop doesn't close properly
            loop.close()
