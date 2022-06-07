import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from gi.repository import GLib as GObject
from gatt import Service, Characteristic, Descriptor

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


class RelativeMouseService(Service):
    """
    Fake HID Mouse that simulates a mouse controls behaviour.

    """
    HID_UUID = '1812'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HID_UUID, primary=True)
        self.add_characteristic(InfoChrc(bus, 0, self))
        self.add_characteristic(InputRepMapChrc(bus, 1, self))
        self.add_characteristic(CtrlPntChrc(bus, 2, self))
        self.add_characteristic(RepChrc(bus, 3, self))
        self.add_characteristic(ProtoModeChrc(bus, 4, self))


class InfoChrc(Characteristic):
    """
    HID Information.
    """

    INFO_UUID = '2a4a'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.INFO_UUID, ['read'], service)
        self.value = dbus.Array(bytearray.fromhex('01010002'), signature=dbus.Signature('y'))

    def ReadValue(self, options):
        # HID info: ver=1.1, country=0, flags=normal
        print('HID Information Chrc called')
        return self.value


class InputRepMapChrc(Characteristic):
    """
    HID input report map.
    """

    REP_MAP_UUID = '2a4b'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.REP_MAP_UUID, ['read'], service)

    def ReadValue(self, options):
        print('HID Input Report Map Chrc called')
        hex_list = [
            # Report Description: describes what we communicate
            0x05, 0x01,                    # USAGE_PAGE (Generic Desktop)
            0x09, 0x02,                    # USAGE (Mouse)
            0xa1, 0x01,                    # COLLECTION (Application)
            0x85, 0x01,                    #   REPORT_ID (1)
            0x09, 0x01,                    #   USAGE (Pointer)
            0xa1, 0x00,                    #   COLLECTION (Physical)
            0x05, 0x09,                    #         Usage Page (Buttons)
            0x19, 0x01,                    #         Usage Minimum (1)
            0x29, 0x03,                    #         Usage Maximum (3)
            0x15, 0x00,                    #         Logical Minimum (0)
            0x25, 0x01,                    #         Logical Maximum (1)
            0x95, 0x03,                    #         Report Count (3)
            0x75, 0x01,                    #         Report Size (1)
            0x81, 0x02,                    #         Input(Data, Variable, Absolute); 3 button bits
            0x95, 0x01,                    #         Report Count(1)
            0x75, 0x05,                    #         Report Size(5)
            0x81, 0x03,                    #         Input(Constant);                 5 bit padding
            0x05, 0x01,                    #         Usage Page (Generic Desktop)
            0x09, 0x30,                    #         Usage (X)
            0x09, 0x31,                    #         Usage (Y)
            0x09, 0x38,                    #         Usage (Wheel)
            0x15, 0x81,                    #         Logical Minimum (-127)
            0x25, 0x7F,                    #         Logical Maximum (127)
            0x75, 0x08,                    #         Report Size (8)
            0x95, 0x03,                    #         Report Count (3)
            0x81, 0x06,                    #         Input(Data, Variable, Relative); 3 position bytes (X,Y,Wheel)
            0xc0,                          #   END_COLLECTION
            0xc0                           # END_COLLECTION
        ]

        hex_string = ''.join(['{:02x}'.format(b) for b in hex_list])
        print(hex_string)
        return dbus.Array(bytearray.fromhex(hex_string))


class CtrlPntChrc(Characteristic):
    """
    HID Control Point.
    """

    CTRL_PNT_UUID = '2a4c'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.CTRL_PNT_UUID, ['write-without-response'], service)
        self.value = dbus.Array(bytearray.fromhex('00'), signature=dbus.Signature('y'))

    def WriteValue(self, value, options):
        self.value = value


class RepChrc(Characteristic):
    """
    HID Report.
    """

    REP_UUID = '2a4d'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.REP_UUID, ['secure-read', 'notify'], service)
        self.add_descriptor(RepDescriptor(bus, 0, self))
        self.notifying = False
        # w, y, x, s
        self.value = [dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(0x10), dbus.Byte(0x00)]
        GObject.timeout_add(5000, self.notify_report)

    def notify_report(self):
        if not self.notifying:
            return True

        print('Sent')
        self.PropertiesChanged('org.bluez.GattCharacteristic1', {
            'Value': self.value
        }, [])

        return True

    def ReadValue(self, options):
        print('Read Report Chrc')
        return self.value

    def WriteValue(self, value, options):
        print(f'Write Report {self.value}')
        self.value = value

    def StartNotify(self):
        print('Start Report Chrc Notification')
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False


class RepDescriptor(Descriptor):
    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index,
                            '2908', ['read'],
                            characteristic)

    def ReadValue(self, options):
        print('Read Rep Descriptor')
        # HID reference: id=1, type=input
        return dbus.Array(bytearray.fromhex('0101'), signature=dbus.Signature('y'))


class ProtoModeChrc(Characteristic):
    """
    HID protocol mode.
    """

    PROTO_MODE_UUID = '2a4e'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.PROTO_MODE_UUID, ['read', 'write-without-response'], service)
        self.parent = service
        self.value = dbus.Array(bytearray.fromhex('01'), signature=dbus.Signature('y'))

    def ReadValue(self, options):
        # HID protocol mode: report
        return self.value

    def WriteValue(self, value, options):
        self.value = value
