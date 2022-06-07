import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import struct

from .gatt import Service, Characteristic

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


def string_pack(in_str):
    return struct.pack(str(len(in_str)) + 's', in_str.encode('UTF-8'))


class DeviceInfoService(Service):
    """
    Device Information Service.

    """
    UUID = '180a'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.UUID, True)
        self.add_characteristic(ModelNumberChrc(bus, 0, self))
        self.add_characteristic(SerialNumberChrc(bus, 1, self))
        self.add_characteristic(FwChrc(bus, 2, self))
        self.add_characteristic(HwChrc(bus, 3, self))
        self.add_characteristic(SwChrc(bus, 4, self))
        self.add_characteristic(MfChrc(bus, 5, self))
        self.add_characteristic(PnpChrc(bus, 6, self))


class ModelNumberChrc(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a24', ['read'], service)
        self.value = dbus.Array('smartRemotes'.encode(), signature=dbus.Signature('y'))

    def ReadValue(self, options):
        return self.value


class SerialNumberChrc(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a25', ['read'], service)

    def ReadValue(self, options):
        return string_pack('0000-0000-0000-0000')


class FwChrc(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a26', ['read'], service)

    def ReadValue(self, options):
        return string_pack('0000-0000-0000-0000')


class HwChrc(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a27', ['read'], service)

    def ReadValue(self, options):
        return string_pack('0000-0000-0000-0000')


class SwChrc(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a28', ['read'], service)
        self.value = dbus.Array('version 1.0.0'.encode(), signature=dbus.Signature('y'))

    def ReadValue(self, options):
        return self.value


class MfChrc(Characteristic):
    # Manifacture Name
    # Vendor Characteristics
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a29', ['read'], service)
        self.value = dbus.Array('HodgeCode'.encode(), signature=dbus.Signature('y'))

    def ReadValue(self, options):
        return self.value


class PnpChrc(Characteristic):
    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, '2a50', ['read'], service)

    def ReadValue(self, options):
        pnp_manufacturer_source = 0x01     # Bluetooth uuid list
        pnp_manufacturer_uuid = 0xFE61     # 0xFEB2 for Microsoft, 0xFE61 for Logitech, 0xFD65 for Razer
        pnp_product_id = 0x01              # ID 1
        pnp_product_version = 0x0123       # Version 1.2.3
        return struct.pack("<BHHH", pnp_manufacturer_source, pnp_manufacturer_uuid, pnp_product_id, pnp_product_version)
