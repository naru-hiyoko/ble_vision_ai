import array
import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

from gi.repository import GLib as GObject
from .errors import NotPermittedException
from .gatt import Service, Characteristic, Descriptor

mainloop = None

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


class TestService(Service):
    """
    Dummy test service that provides characteristics and descriptors that
    exercise various API functionality.

    """
    TEST_SVC_UUID = '12345678-1234-5678-1234-56789abcdef0'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.TEST_SVC_UUID, True)
        self.add_characteristic(TestCharacteristic(bus, 0, self))
        self.add_characteristic(TestEncryptCharacteristic(bus, 1, self))
        self.add_characteristic(TestSecureCharacteristic(bus, 2, self))
        self.add_characteristic(TestNotificationCharacteristic(bus, 3, self))


class TestCharacteristic(Characteristic):
    """
    Dummy test characteristic. Allows writing arbitrary bytes to its value, and
    contains "extended properties", as well as a test descriptor.

    """
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef1'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.TEST_CHRC_UUID,
                                ['read', 'write', 'writable-auxiliaries'],
                                service)
        self.value = []
        self.add_descriptor(TestDescriptor(bus, 0, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print('TestCharacteristic Read: ' + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print('TestCharacteristic Write: ' + repr(value))
        self.value = value


class TestDescriptor(Descriptor):
    """
    Dummy test descriptor. Returns a static value.

    """
    TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef2'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index,
                            self.TEST_DESC_UUID,
                            ['read', 'write'],
                            characteristic)

    def ReadValue(self, options):
        return [
            dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
        ]


class CharacteristicUserDescriptionDescriptor(Descriptor):
    """
    Writable CUD descriptor.

    """
    CUD_UUID = '2901'

    def __init__(self, bus, index, characteristic):
        self.writable = 'writable-auxiliaries' in characteristic.flags
        self.value = array.array('B', b'This is a characteristic for testing')
        self.value = self.value.tolist()
        Descriptor.__init__(self, bus, index,
                            self.CUD_UUID,
                            ['read', 'write'],
                            characteristic)

    def ReadValue(self, options):
        return self.value

    def WriteValue(self, value, options):
        if not self.writable:
            raise NotPermittedException()
        self.value = value


class TestEncryptCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring encryption.

    """
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef3'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index,
                                self.TEST_CHRC_UUID,
                                ['encrypt-read', 'encrypt-write'],
                                service)

        self.value = []
        self.add_descriptor(TestEncryptDescriptor(bus, 0, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print('TestEncryptCharacteristic Read: ' + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print('TestEncryptCharacteristic Write: ' + repr(value))
        self.value = value


class TestEncryptDescriptor(Descriptor):
    """
    Dummy test descriptor requiring encryption. Returns a static value.

    """
    TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef4'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index,
                            self.TEST_DESC_UUID,
                            ['encrypt-read', 'encrypt-write'],
                            characteristic)

    def ReadValue(self, options):
        return [
            dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
        ]


class TestSecureCharacteristic(Characteristic):
    """
    Dummy test characteristic requiring secure connection.

    """
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef5'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index,
                                self.TEST_CHRC_UUID,
                                ['secure-read', 'secure-write'],
                                service)
        self.value = []
        self.add_descriptor(TestSecureDescriptor(bus, 0, self))
        self.add_descriptor(CharacteristicUserDescriptionDescriptor(bus, 1, self))

    def ReadValue(self, options):
        print('TestSecureCharacteristic Read: ' + repr(self.value))
        return self.value

    def WriteValue(self, value, options):
        print('TestSecureCharacteristic Write: ' + repr(value))
        self.value = value


class TestSecureDescriptor(Descriptor):
    """
    Dummy test descriptor requiring secure connection. Returns a static value.

    """
    TEST_DESC_UUID = '12345678-1234-5678-1234-56789abcdef6'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index,
                            self.TEST_DESC_UUID,
                            ['secure-read', 'secure-write'],
                            characteristic)

    def ReadValue(self, options):
        return [
            dbus.Byte('T'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')
        ]


class TestNotificationCharacteristic(Characteristic):
    TEST_CHRC_UUID = '12345678-1234-5678-1234-56789abcdef7'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index,
                                self.TEST_CHRC_UUID,
                                ['read', 'notify'],
                                service)
        self.value = 1
        self.add_descriptor(TestNotificationDescriptor(bus, 0, self))
        self.notifying = False
        GObject.timeout_add(1000, self.notify_report)

    def notify_report(self):
        if self.notifying:
            self.value += 1
            self.PropertiesChanged('org.bluez.GattCharacteristic1', {'Value': [dbus.Byte(self.value)]}, [])
        else:
            pass

        return True

    def ReadValue(self, options):
        print('TestCharacteristic Read')
        # return [dbus.Byte(self.value)]
        return [0x01, 0x02]

    def StartNotify(self):
        if self.notifying:
            print('Already notifying, nothing to do')
            return

        self.notifying = True

    def StopNotify(self):
        if not self.notifying:
            print('Not notifying, nothing to do')
            return

        self.notifying = False


class TestNotificationDescriptor(Descriptor):
    """
    Dummy test descriptor. Returns a static value.

    """
    TEST_DESC_UUID = '2901'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(self, bus, index,
                            self.TEST_DESC_UUID,
                            ['read', 'write'],
                            characteristic)

    def ReadValue(self, options):
        return [dbus.Byte('H'), dbus.Byte('e'), dbus.Byte('s'), dbus.Byte('t')]
