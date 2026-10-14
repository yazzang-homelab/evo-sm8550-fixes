# evo-sm8550-fixes

Interim fixes for running MaSieS4Fun's SteamOS ARM (SM8550) test image on an **AYANEO Pocket EVO**.

## Background (findings)

| Symptom | Root cause | Fix |
|---|---|---|
| Panel stays black after the Snapdragon logo | `dtb-chain/sanitize.sh` strips `reserved-memory/splash_region@b8000000` from the EVO DTB | keep the node (`reg = <0x0 0xb8000000 0x0 0x2b00000>`, `no-map`) |
| Built-in controls do nothing | gamepad sits behind the Renesas uPD720201 PCIe xHCI (1912:0014); kernel has `# CONFIG_USB_XHCI_PCI_RENESAS is not set` | build `xhci-pci-renesas.ko` (this repo) + uPD720201 nodes from the current EVO DTS |
| Desktop mode upside down | `sm8550-display.conf` lists the EVO as `right\|Rotated270` | `left\|Rotated90` (DTS rotation = 270, like Odin 2 Portal) |

## What this repo builds

`.github/workflows/build-xhci-renesas.yml` builds only `xhci-pci-renesas.ko` for the image kernel
`7.2.8-edge-sm8550` (vanilla kernel.org 7.2.8 + the image's own IKCONFIG, `USB_XHCI_PCI_RENESAS=m`).
The job fails unless vermagic is exactly `7.2.8-edge-sm8550 SMP preempt mod_unload aarch64`.

Install on the device (temporary, until an official build includes it):

```sh
sudo install -D -m644 xhci-pci-renesas.ko /lib/modules/7.2.8-edge-sm8550/updates/xhci-pci-renesas.ko
sudo depmod -a 7.2.8-edge-sm8550
sudo modprobe xhci-pci-renesas
```

Rollback: delete the file and run `depmod -a` again. Firmware `renesas_usb_fw.mem` is already in the image.
