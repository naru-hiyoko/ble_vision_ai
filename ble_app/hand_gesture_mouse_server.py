#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later

import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import time

from gi.repository import GLib as GObject
from .services import BatteryService
from .services import DeviceInfoService
from .services import HandGestureMouseService
from .services import RelativeMouseService
from .advertisement import TestAdvertisement
from .agent import Agent

bus = None
mainloop = None


class Application(dbus.service.Object):
    """
    org.bluez.GattApplication1 interface implementation
    """
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)
        self.add_service(BatteryService(bus, 0))
        self.add_service(DeviceInfoService(bus, 1))
        self.add_service(HandGestureMouseService(bus, 2))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method('org.freedesktop.DBus.ObjectManager', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}

        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
                descs = chrc.get_descriptors()
                for desc in descs:
                    response[desc.get_path()] = desc.get_properties()

        return response


def register_app_cb():
    print('GATT application registered')


def register_app_error_cb(error):
    print('Failed to register application: ' + str(error))
    mainloop.quit()


def register_ad_cb():
    print('Advertisement registered')


def register_ad_error_cb(error):
    print(f'Advertisement error {error}')


def main():
    global mainloop
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = GObject.MainLoop()

    global bus
    bus = dbus.SystemBus()

    adapter_obj = bus.get_object('org.bluez', '/org/bluez/hci0')
    service_manager = dbus.Interface(adapter_obj, 'org.bluez.GattManager1')
    app = Application(bus)
    service_manager.RegisterApplication(app.get_path(), {},
                                        reply_handler=register_app_cb,
                                        error_handler=register_app_error_cb)

    time.sleep(1)

    # https://www.kynetics.com/docs/2018/pairing_agents_bluez/#simple-agent
    agent = Agent(bus)
    ag_manager = dbus.Interface(bus.get_object('org.bluez', "/org/bluez"), "org.bluez.AgentManager1")
    ag_manager.RegisterAgent(agent.path, 'DisplayYesNo')  # 'NoInputNoOutput'

    adapter_props_interface = dbus.Interface(adapter_obj, 'org.freedesktop.DBus.Properties')
    adapter_props_interface.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(1))
    adapter_props_interface.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(1))
    adapter_props_interface.Set('org.bluez.Adapter1', 'Alias', dbus.String('AIBot'))

    ad_manager = dbus.Interface(adapter_obj, 'org.bluez.LEAdvertisingManager1')
    test_advertisement = TestAdvertisement(bus, index=0)
    ad_manager.RegisterAdvertisement(test_advertisement.get_path(), {},
                                     reply_handler=register_ad_cb,
                                     error_handler=register_ad_error_cb)
    # ad_manager.UnregisterAdvertisement(advertisement)
    # dbus.service.Object.remove_from_connection(advertisement)

    try:
        mainloop.run()

    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
