import subprocess
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from gi.repository import GLib as GObject
from .gatt import Service, Characteristic

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


class BatteryService(Service):
    """
    Fake Battery service that emulates a draining battery.

    """
    BATTERY_UUID = '180f'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.BATTERY_UUID, True)
        self.add_characteristic(BatteryLevelCharacteristic(bus, 0, self))


class BatteryLevelCharacteristic(Characteristic):
    """
    Fake Battery Level characteristic. The battery level is drained by 2 points
    every 5 seconds.

    """
    BATTERY_LVL_UUID = '2a19'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
            self, bus, index,
            self.BATTERY_LVL_UUID,
            ['read', 'notify'],
            service)

        self.notifying = False
        self.battery_lvl = 100
        GObject.timeout_add(5000, self.notify_battery_level)

    def notify_battery_level(self):
        proc = subprocess.run(
            ['upower', '-i', '/org/freedesktop/UPower/devices/battery_BAT1'],
            capture_output=True
        )

        if proc.returncode == 0:
            fields_list = [
                [v.strip() for v in l.split(':')]
                for l in proc.stdout.decode('utf-8').split('\n')
            ]
            # FIXME: Error occurs when a item length is not `2`.
            fields_dict = {
                item[0]: item[1] for item in fields_list if len(item) == 2
            }
            if 'percentage' in fields_dict:
                self.battery_lvl = int(fields_dict['percentage'].replace('%', ''))
            else:
                self.battery_lvl = 100
        else:
            self.battery_lvl = 100

        if self.notifying:
            payload = {'Value': [dbus.Byte(self.battery_lvl)]}
            self.PropertiesChanged(GATT_CHRC_IFACE, payload, [])

        return True

    def ReadValue(self, options):
        print('Battery Level read: ' + repr(self.battery_lvl))
        return [dbus.Byte(self.battery_lvl)]

    def StartNotify(self):
        if self.notifying:
            return

        self.notifying = True
        self.notify_battery_level()

    def StopNotify(self):
        if not self.notifying:
            return

        self.notifying = False
