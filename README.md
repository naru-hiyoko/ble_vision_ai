# DIY Peripherals on Bluez HID over GATT

Nowadays, someone asked me to create app of hand gesture PC controls on bluetooth.
I firstly look at [bluez dbus api](https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/),
but I can't get what `advertisement`, `service`, `characterisitics`, `descriptors` means.
[This post](https://punchthrough.com/creating-a-ble-peripheral-with-bluez/) clalify me these words and I decided to try modifying `test service` in [example-gatt-server](https://git.kernel.org/pub/scm/bluetooth/bluez.git/tree/test/example-gatt-client).
However, to avoid struggle to use dbus-python we should be familiar with `bluetoothctl` beforehand.
Once example codes work, you can try/see published services with GattBrowser([android](https://play.google.com/store/apps/details?id=com.renesas.ble.gattbrowser&hl=en&gl=US)/[ios](https://apps.apple.com/jp/app/gattbrowser/id1163057977))

After you fully understand gatt, read the HID examples in [References](#References)

## Pre-Requirements

* bluez5.x
* python3.x

check `/etc/bluetooth/main.conf` and set `ControllerMode` to `le`.

## References

[Bluez HID Over GATT](https://gist.github.com/HeadHodge/2d3dc6dc2dce03cf82f61d8231e88144)
[MicroPythonBLEHID](https://github.com/Heerkog/MicroPythonBLEHID/blob/master/hid_services.py)
[Mouse move to absolute coordinates](https://github.com/csash7/mbed-BLE-Mouse/issues/1)
[Capacitive Touch Screen Emulation](https://github.com/NicoHood/HID/issues/123)
