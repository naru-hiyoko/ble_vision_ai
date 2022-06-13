# DIY BLE Central on Bluez HID over GATT

Nowadays, someone asked me to create app of hand gesture PC controls on bluetooth.
I firstly look at [bluez dbus api](https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/),
but I can't get what `advertisement`, `service`, `characterisitics`, `descriptors` means.
Fortunately [This post](https://punchthrough.com/creating-a-ble-peripheral-with-bluez/) clalified me these words and I decided to try modifying `test service` in [example-gatt-server](https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/test/example-gatt-client).
On the other hand, we should be familiar with `bluetoothctl` beforehand to avoid struggle to use dbus-python api.
To see gatt server works, you can use GattBrowser([android](https://play.google.com/store/apps/details?id=com.renesas.ble.gattbrowser&hl=en&gl=US)/[ios](https://apps.apple.com/jp/app/gattbrowser/id1163057977)) except for HID services.
Specifically, ios won't let you get HID services directlly, it may be restricted by secutiry terms.

After you fully understand gatt, read the HID examples in [References](#References)

* video

[![](https://img.youtube.com/vi/LZKFgrFjOiY/0.jpg)](https://www.youtube.com/watch?v=LZKFgrFjOiY)


## Pre-Requirements

* Linux
* bluez5.x
* python3.x

check `/etc/bluetooth/main.conf` and set `ControllerMode` to `le`.

## References

[Bluez HID Over GATT](https://gist.github.com/HeadHodge/2d3dc6dc2dce03cf82f61d8231e88144)
[MicroPythonBLEHID](https://github.com/Heerkog/MicroPythonBLEHID/blob/master/hid_services.py)
[Mouse move to absolute coordinates](https://github.com/csash7/mbed-BLE-Mouse/issues/1)
[Capacitive Touch Screen Emulation](https://github.com/NicoHood/HID/issues/123)
