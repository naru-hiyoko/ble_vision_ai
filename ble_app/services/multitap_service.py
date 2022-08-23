import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from gi.repository import GLib as GObject
from .gatt import Service, Characteristic, Descriptor

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


class MultitapService(Service):
    HID_UUID = '1812'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.HID_UUID, primary=True)
        self.add_characteristic(InfoChrc(bus, 0, self))
        self.add_characteristic(InputRepMapChrc(bus, 1, self))
        self.add_characteristic(CtrlPntChrc(bus, 2, self))
        self.add_characteristic(ReportChrc(bus, 3, self))
        self.add_characteristic(ProtoModeChrc(bus, 4, self))


class InfoChrc(Characteristic):
    """
    HID Information.
    """

    INFO_UUID = '2a4a'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.INFO_UUID, ['read'], service)
        self.value = dbus.Array(bytearray.fromhex('01020002'), signature=dbus.Signature('y'))

    def ReadValue(self, options):
        # HID info: ver=1.1, country=0, flags=normal
        return self.value


class InputRepMapChrc(Characteristic):
    """
    HID input report map.
    """

    REP_MAP_UUID = '2a4b'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.REP_MAP_UUID, ['read'], service)

    def ReadValue(self, options):
        # https://docs.microsoft.com/en-us/windows-hardware/design/component-guidelines/sample-report-descriptor-for-a-touch-digitizer-device

        hex_list = [
            0x05, 0x0D,                    # USAGE_PAGE(Digitizers)
            0x09, 0x04,                    # USAGE     (Touch Screen)
            0xA1, 0x01,                    # COLLECTION(Application)
            0x85, 0x01,          #   REPORT_ID (Touch)
            # define the maximum amount of fingers that the device supports
            0x09, 0x55,                    #   USAGE (Contact Count Maximum)
            0x25, 0x01,   #   LOGICAL_MAXIMUM (CONTACT_COUNT_MAXIMUM)
            0xB1, 0x02,                    #   FEATURE (Data,Var,Abs)
            # define the actual amount of fingers that are concurrently touching the screen
            0x09, 0x54,                    #   USAGE (Contact count)
            0x95, 0x01,                    #   REPORT_COUNT(1)
            0x75, 0x08,                    #   REPORT_SIZE (8)
            0x81, 0x02,                    #   INPUT (Data,Var,Abs)
            # declare a finger collection
            0x09, 0x22,                    #   USAGE (Finger)
            0xA1, 0x02,                    #   COLLECTION (Logical)
            # declare an identifier for the finger
            0x09, 0x51,                    #     USAGE (Contact Identifier)
            0x75, 0x08,                    #     REPORT_SIZE (8)
            0x95, 0x01,                    #     REPORT_COUNT (1)
            0x81, 0x02,                    #     INPUT (Data,Var,Abs)
            # declare Tip Switch and In Range
            0x09, 0x42,                    #     USAGE (Tip Switch)
            0x09, 0x32,                    #     USAGE (In Range)
            0x15, 0x00,                    #     LOGICAL_MINIMUM (0)
            0x25, 0x01,                    #     LOGICAL_MAXIMUM (1)
            0x75, 0x01,                    #     REPORT_SIZE (1)
            0x95, 0x02,                    #     REPORT_COUNT(2)
            0x81, 0x02,                    #     INPUT (Data,Var,Abs)
            # declare the remaining 6 bits of the first data byte as constant -> the driver will ignore them
            0x95, 0x06,                    #     REPORT_COUNT (6)
            0x81, 0x03,                    #     INPUT (Cnst,Ary,Abs)
            # define absolute X and Y coordinates of 16 bit each (percent values multiplied with 100)
            0x05, 0x01,                    #     USAGE_PAGE (Generic Desktop)
            0x09, 0x30,                    #     Usage (X)
            0x09, 0x31,                    #     Usage (Y)
            0x16, 0x00, 0x00,              #     Logical Minimum (0)
            0x26, 0x10, 0x27,              #     Logical Maximum (10000)
            0x36, 0x00, 0x00,              #     Physical Minimum (0)
            0x46, 0x10, 0x27,              #     Physical Maximum (10000)
            0x66, 0x00, 0x00,              #     UNIT (None)
            0x75, 0x10,                    #     Report Size (16),
            0x95, 0x02,                    #     Report Count (2),
            0x81, 0x02,                    #     Input (Data,Var,Abs)
            0xC0,                          #   END_COLLECTION
            0xC0                           # END_COLLECTION

            # with this declaration a data packet must be sent as:
            # byte 1   -> "contact count"        (always == 1)
            # byte 2   -> "contact identifier"   (any value)
            # byte 3   -> "Tip Switch" state     (bit 0 = Tip Switch up/down, bit 1 = In Range)
            # byte 4,5 -> absolute X coordinate  (0...10000)
            # byte 6,7 -> absolute Y coordinate  (0...10000)
        ]

        hex_string = ''.join(['{:02x}'.format(b) for b in hex_list])
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


class ReportChrc(Characteristic):
    """
    HID Report.
    """

    REP_UUID = '2a4d'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.REP_UUID, ['secure-read', 'notify'], service)
        self.add_descriptor(RepDescriptor(bus, 0, self))
        self.notifying = False
        self.value = []
        GObject.timeout_add(5000, self.notify_report)

    def notify_report(self):
        if not self.notifying:
            return True

        x, y = 1500, 1000

        self.value = [
            dbus.Byte(0x01),
            dbus.Byte(0x01),
            dbus.Byte(0xff),
            dbus.Byte(x & 0x00ff), dbus.Byte((x >> 8) & 0x00ff), # x
            dbus.Byte(y & 0x00ff), dbus.Byte((y >> 8) & 0x00ff), # y
        ]

        self.PropertiesChanged('org.bluez.GattCharacteristic1', {
            'Value': self.value
        }, [])

        self.value = [
            dbus.Byte(0x01),
            dbus.Byte(0x01),
            dbus.Byte(0x00),
            dbus.Byte(x & 0x00ff), dbus.Byte((x >> 8) & 0x00ff), # x
            dbus.Byte(y & 0x00ff), dbus.Byte((y >> 8) & 0x00ff), # y
        ]

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
        Descriptor.__init__(self, bus, index, '2908', ['read'], characteristic)

    def ReadValue(self, options):
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
