import dbus
import dbus.exceptions
import dbus.mainloop.glib
import dbus.service
import threading
import struct
import numpy as np
import cv2
import mediapipe as mp

from gi.repository import GLib as GObject
from .gatt import Service, Characteristic, Descriptor

BLUEZ_SERVICE_NAME = 'org.bluez'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
DBUS_OM_IFACE =      'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE =    'org.freedesktop.DBus.Properties'

GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE =    'org.bluez.GattCharacteristic1'
GATT_DESC_IFACE =    'org.bluez.GattDescriptor1'


class HandGestureMouseService(Service):
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
            0x16, 0x01, 0x80,              #         Logical Minimum (0)
            0x26, 0xff, 0x7f,              #         Logical Maximum (10,000)
            0x66, 0x00, 0x00,              #         UNIT(None)
            0x75, 0x10,                    #         Report Size (10)
            0x95, 0x02,                    #         Report Count (2)
            0x81, 0x02,                    #         Input(Data, Variable, Relative); 3 position bytes (X,Y,Wheel)
            0xc0,                          #   END_COLLECTION
            0xc0                           # END_COLLECTION
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


class RepChrc(Characteristic):
    """
    HID Report.
    """

    REP_UUID = '2a4d'

    def __init__(self, bus, index, service):
        Characteristic.__init__(self, bus, index, self.REP_UUID, ['secure-read', 'notify'], service)
        self.add_descriptor(RepDescriptor(bus, 0, self))
        self.notifying = False
        # y, x, s
        self.value = [dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(0x00)]
        self.cap = cv2.VideoCapture(0)
        mp_hands = mp.solutions.hands
        self.history = np.array([], dtype=np.uint8)
        self.max_history_count = 60
        self.hands_detector = mp_hands.Hands(model_complexity=0, max_num_hands=1,
                                             min_detection_confidence=0.5, min_tracking_confidence=0.5)
        GObject.timeout_add(50, self.notify_report)

    def notify_report(self):
        if not self.notifying:
            return True

        success, image = self.cap.read()

        if not success:
            print('Ignoring empty camera frame')
            return True

        image.flags.writeable = False
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        detection_result = self.hands_detector.process(image)

        if not detection_result.multi_hand_landmarks:
            self.history = np.array([], dtype=np.uint8)
            return True

        detection_hand = detection_result.multi_hand_landmarks[0]
        landmark = detection_hand.landmark
        button = 0
        x = max(int(127 * (1.0 - landmark[8].x)), 0)
        y = max(int(127 * landmark[8].y), 0)

        dx, dy = landmark[4].x - landmark[8].x, landmark[4].y - landmark[8].y
        self.history = np.append(self.history, 1 if dy < 0.1 else 0)[-self.max_history_count:]
        grad = self.history[1:] - self.history[:-1]

        if self.history.size == self.max_history_count:
            state_on_at, state_off_at, on_off_count = 0, 0, 0
            for i in range(grad.size):
                if grad[i] == 1:
                    state_on_at = i
                    on_off_count += 1
                elif grad[i] == -1:
                    state_off_at = i
                    on_off_count += 1

                if (state_off_at - state_on_at < 10) and on_off_count == 2:
                    button = 1
                    self.history = np.array([], dtype=np.uint8)



        # 0 ~ 127 normalized to 0 ~ 1
        self.value = [dbus.Byte(button), dbus.Byte(0x00), dbus.Byte(x), dbus.Byte(0x00), dbus.Byte(y)]
        self.PropertiesChanged('org.bluez.GattCharacteristic1', {
            'Value': self.value
        }, [])

        self.value = [dbus.Byte(0x00), dbus.Byte(0x00), dbus.Byte(x), dbus.Byte(0), dbus.Byte(y)]
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
