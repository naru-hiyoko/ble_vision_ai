import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service

import struct
import array
import sys
import time

from gi.repository import GLib as GObject
from random import randint
from errors import InvalidArgsException, NotPermittedException, InvalidValueLengthException, FailedException
from gatt import Service, Characteristic, Descriptor

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


#name="Human Interface Device" sourceId="org.bluetooth.service.human_interface_device" type="primary" uuid="1812"
class KeyboardService(Service):
    SERVICE_UUID = '1812'

    def __init__(self, bus, index):
        Service.__init__(self, bus, index, self.SERVICE_UUID, True)

        self.protocolMode = ProtocolModeCharacteristic(bus, 0, self)
        self.hidInfo = HIDInfoCharacteristic(bus, 1, self)
        self.controlPoint = ControlPointCharacteristic(bus, 2, self)
        self.reportMap = ReportMapCharacteristic(bus, 3, self)
        self.report1 = Report1Characteristic(bus, 4, self)
        self.report2 = Report2Characteristic(bus, 5, self)

        self.add_characteristic(self.protocolMode)
        self.add_characteristic(self.hidInfo)
        self.add_characteristic(self.controlPoint)
        self.add_characteristic(self.reportMap)
        self.add_characteristic(self.report1)
        self.add_characteristic(self.report2)

#name="Protocol Mode" sourceId="org.bluetooth.characteristic.protocol_mode" uuid="2A4E"
class ProtocolModeCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = '2A4E'

    def __init__(self, bus, index, service):

        Characteristic.__init__(
                self, bus, index,
                self.CHARACTERISTIC_UUID,
                ["read", "write-without-response"],
                service)

        '''
        <Field name="Protocol Mode Value">
        <Requirement>Mandatory</Requirement>
        <Format>uint8</Format>
        <Enumerations>
        <Enumeration key="0" value="Boot Protocol Mode"/>
        <Enumeration key="1" value="Report Protocol Mode"/>
        <ReservedForFutureUse start="2" end="255"/>
        </Enumerations>
        '''

        #self.value = dbus.Array([1], signature=dbus.Signature('y'))
        self.parent = service
        self.value = dbus.Array(bytearray.fromhex('01'), signature=dbus.Signature('y'))
        print(f'***ProtocolMode value***: {self.value}')

    def ReadValue(self, options):
        print(f'Read ProtocolMode: {self.value}')
        return self.value

    def WriteValue(self, value, options):
        print(f'Write ProtocolMode {value}')
        self.value = value


#id="hid_information" name="HID Information" sourceId="org.bluetooth.characteristic.hid_information" uuid="2A4A"
class HIDInfoCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = '2A4A'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.CHARACTERISTIC_UUID,
                ['read'],
                service)

        '''
        <Field name="bcdHID">
            <InformativeText>16-bit unsigned integer representing version number of base USB HID Specification implemented by HID Device</InformativeText>
            <Requirement>Mandatory</Requirement>
            <Format>uint16</Format>
        </Field>

        <Field name="bCountryCode">
            <InformativeText>Identifies which country the hardware is localized for. Most hardware is not localized and thus this value would be zero (0).</InformativeText>
            <Requirement>Mandatory</Requirement>
            <Format>8bit</Format>
        </Field>

        <Field name="Flags">
            <Requirement>Mandatory</Requirement>
            <Format>8bit</Format>
            <BitField>
                <Bit index="0" size="1" name="RemoteWake">
                <Enumerations>
                    <Enumeration key="0" value="The device is not designed to be capable of providing wake-up signal to a HID host"/>
                    <Enumeration key="1" value="The device is designed to be capable of providing wake-up signal to a HID host"/>
                </Enumerations>
                </Bit>

                <Bit index="1" size="1" name="NormallyConnectable">
                <Enumerations>
                    <Enumeration key="0" value="The device is not normally connectable"/>
                    <Enumeration key="1" value="The device is normally connectable"/>
                </Enumerations>
                </Bit>

                <ReservedForFutureUse index="2" size="6"/>
            </BitField>
        </Field>
        '''

        self.value = dbus.Array(bytearray.fromhex('01110002'), signature=dbus.Signature('y'))
        print(f'***HIDInformation value***: {self.value}')

    def ReadValue(self, options):
        print(f'Read HIDInformation: {self.value}')
        return self.value

#sourceId="org.bluetooth.characteristic.hid_control_point" uuid="2A4C"
class ControlPointCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = '2A4C'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.CHARACTERISTIC_UUID,
                ["write-without-response"],
                service)

        self.value = dbus.Array(bytearray.fromhex('00'), signature=dbus.Signature('y'))
        print(f'***ControlPoint value***: {self.value}')

    def WriteValue(self, value, options):
        print(f'Write ControlPoint {value}')
        self.value = value


#sourceId="org.bluetooth.characteristic.report_map" uuid="2A4B"
class ReportMapCharacteristic(Characteristic):

    CHARACTERISTIC_UUID = '2A4B'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.CHARACTERISTIC_UUID,
                ['read'],
                service)
        '''
        <Field name="Report Map Value">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Repeated>true</Repeated>
        </Field>

        HID Report Descriptors https://www.usb.org/sites/default/files/documents/hid1_11.pdf
        HID Report Parser https://eleccelerator.com/usbdescreqparser/
        '''

        ##############################################################################################
        # This Report Descriptor defines 2 Input Reports
        # ReportMap designed by HeadHodge
        #
        # <Report Layouts>
        #   <Report>
        #       <ReportId>1</ReportId>
        #       <Description>HID Keyboard Input</Description>
        #       <Example>KeyCode capital 'M' = [dbus.Byte(0x02), dbus.Byte(0x10)]</Example>
        #       <Field>
        #           <Name>Keyboard Modifier</Name>
        #           <Size>uint8</Size>
        #           <Format>
        #               <Bit0>Left CTRL Key Pressed</Bit0>
        #               <Bit1>Left SHIFT Key Pressed</Bit1>
        #               <Bit2>Left ALT Key Pressed</Bit2>
        #               <Bit3>Left CMD(Window) Key Pressed</Bit3>
        #               <Bit4>Right CTRL Key Pressed</Bit4>
        #               <Bit5>Right SHIFT Key Pressed</Bit5>
        #               <Bit6>Right ALT Key Pressed</Bit6>
        #               <Bit7>Right CMD(Window) Key Pressed</Bit7>
        #           </Format>
        #       </Field>
        #       <Field>
        #           <Name>Keyboard Input KeyCode</Name>
        #           <Size>uint8</Size>
        #       </Field>
        #   </Report>
        #   <Report>
        #       <ReportId>2</ReportId>
        #       <Description>HID Consumer Input</Description>
        #       <Example>KeyCode 'VolumeUp' = [dbus.Byte(0xe9), dbus.Byte(0x00)]</Example>
        #       <Field>
        #           <Name>Consumer Input KeyCode</Name>
        #           <Size>uint16</Size>
        #       </Field>
        #   </Report>
        # </Report Layouts>
        ##############################################################################################

        #USB HID Report Descriptor
        self.value = dbus.Array(bytearray.fromhex('05010906a1018501050719e029e71500250175019508810295017508150025650507190029658100c0050C0901A101850275109501150126ff0719012Aff078100C0'))
        print(f'***ReportMap value***: {self.value}')

    def ReadValue(self, options):
        print(f'Read ReportMap: {self.value}')
        return self.value


#id="report" name="Report" sourceId="org.bluetooth.characteristic.report" uuid="2A4D"
class Report1Characteristic(Characteristic):

    CHARACTERISTIC_UUID = '2A4D'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.CHARACTERISTIC_UUID,
                ['secure-read', 'notify'],
                service)

        '''
        <Field name="Report Value">
        <Requirement>Mandatory</Requirement>
        <Format>uint8</Format>
        <Repeated>true</Repeated>
        </Field>

        Use standard key codes: https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
        '''

        self.add_descriptor(Report1ReferenceDescriptor(bus, 1, self))

        self.value = [dbus.Byte(0x00),dbus.Byte(0x00)]
        print(f'***Report value***: {self.value}')

    def send(self):

        #send keyCode: 'M'
        print(f'***send keyCode: "M"***');
        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': [dbus.Byte(0x02),dbus.Byte(0x10)] }, [])
        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': [dbus.Byte(0x00),dbus.Byte(0x00)] }, [])
        print(f'***sent***')
        return True

    def ReadValue(self, options):
        print(f'Read Report: {self.value}')
        return self.value

    def WriteValue(self, value, options):
        print(f'Write Report {self.value}')
        self.value = value

    def StartNotify(self):
        print(f'Start Start Report Keyboard Input')
        GObject.timeout_add(10000, self.send)

    def StopNotify(self):
        print(f'Stop Report Keyboard Input')


#type="org.bluetooth.descriptor.report_reference" uuid="2908"
class Report1ReferenceDescriptor(Descriptor):

    DESCRIPTOR_UUID = '2908'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.DESCRIPTOR_UUID,
                ['read'],
                characteristic)

        '''
        <Field name="Report ID">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>0</Minimum>
            <Maximum>255</Maximum>
        </Field>

        <Field name="Report Type">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>1</Minimum>
            <Maximum>3</Maximum>
            <Enumerations>
                <Enumeration value="Input Report" key="1"/>
                <Enumeration value="Output report" key="2"/>
                <Enumeration value="Feature Report" key="3"/>
                <ReservedForFutureUse start="4" end="255"/>
                <ReservedForFutureUse1 start1="0" end1="0"/>
            </Enumerations>
        </Field>
        '''

        # This report uses ReportId 1 as defined in the ReportMap characteristic
        self.value = dbus.Array(bytearray.fromhex('0101'), signature=dbus.Signature('y'))
        print(f'***ReportReference***: {self.value}')

    def ReadValue(self, options):
        print(f'Read ReportReference: {self.value}')
        return self.value


#id="report" name="Report" sourceId="org.bluetooth.characteristic.report" uuid="2A4D"
class Report2Characteristic(Characteristic):

    CHARACTERISTIC_UUID = '2A4D'

    def __init__(self, bus, index, service):
        Characteristic.__init__(
                self, bus, index,
                self.CHARACTERISTIC_UUID,
                ['secure-read', 'notify'],
                service)

        '''
        <Field name="Report Value">
        <Requirement>Mandatory</Requirement>
        <Format>uint8</Format>
        <Repeated>true</Repeated>
        </Field>

        Use standard key codes: https://www.usb.org/sites/default/files/documents/hut1_12v2.pdf
        '''

        self.add_descriptor(Report2ReferenceDescriptor(bus, 1, self))

        self.value = [dbus.Byte(0x00),dbus.Byte(0x00)]
        print(f'***Report value***: {self.value}')

    def send(self):

        #send keyCode: 'VolumeUp'
        print(f'***send keyCode: "VolumeUp"***');
        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': [dbus.Byte(0xe9), dbus.Byte(0x00)] }, [])
        self.PropertiesChanged(GATT_CHRC_IFACE, { 'Value': [dbus.Byte(0x00), dbus.Byte(0x00)] }, [])
        print(f'***sent***')
        return True

    def ReadValue(self, options):
        print(f'Read Report: {self.value}')
        return self.value

    def WriteValue(self, value, options):
        print(f'Write Report {self.value}')
        self.value = value

    def StartNotify(self):
        print(f'Start Report Consumer Input')
        GObject.timeout_add(15000, self.send)

    def StopNotify(self):
        print(f'Stop Start Report Consumer Input')


#type="org.bluetooth.descriptor.report_reference" uuid="2908"
class Report2ReferenceDescriptor(Descriptor):

    DESCRIPTOR_UUID = '2908'

    def __init__(self, bus, index, characteristic):
        Descriptor.__init__(
                self, bus, index,
                self.DESCRIPTOR_UUID,
                ['read'],
                characteristic)

        '''
        <Field name="Report ID">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>0</Minimum>
            <Maximum>255</Maximum>
        </Field>

        <Field name="Report Type">
            <Requirement>Mandatory</Requirement>
            <Format>uint8</Format>
            <Minimum>1</Minimum>
            <Maximum>3</Maximum>
            <Enumerations>
                <Enumeration value="Input Report" key="1"/>
                <Enumeration value="Output report" key="2"/>
                <Enumeration value="Feature Report" key="3"/>
                <ReservedForFutureUse start="4" end="255"/>
                <ReservedForFutureUse1 start1="0" end1="0"/>
            </Enumerations>
        </Field>
        '''

        # This report uses ReportId 2 as defined in the ReportMap characteristic
        self.value = dbus.Array(bytearray.fromhex('0201'), signature=dbus.Signature('y'))
        print(f'***ReportReference***: {self.value}')

    def ReadValue(self, options):
        print(f'Read ReportReference: {self.value}')
        return self.value
