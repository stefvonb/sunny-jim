import abc


class DeviceObserver(abc.ABC):
    @abc.abstractmethod
    def update(self, device):
        pass


class PrintObserver(DeviceObserver):
    def update(self, device):
        print(device.get_state_dictionary())
