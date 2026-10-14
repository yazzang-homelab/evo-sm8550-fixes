# evo-sm8550-fixes

Interim fixes for running MaSieS4Fun's SteamOS ARM (SM8550) test image on an **AYANEO Pocket EVO**.
Everything here was verified on real hardware (EVO Retro Power edition).

## Findings

| Symptom | Root cause | Fix | Where |
|---|---|---|---|
| Panel stays black after the Snapdragon logo | `dtb-chain/sanitize.sh` strips `reserved-memory/splash_region@b8000000` from the EVO DTB | keep the node (`reg = <0x0 0xb8000000 0x0 0x2b00000>`, `no-map`) | `dts/pocket-evo-fixes.dtsi` |
| Built-in pad does nothing | pad sits behind the Renesas uPD720201 PCIe xHCI (1912:0014); kernel has `# CONFIG_USB_XHCI_PCI_RENESAS is not set` | `xhci-pci-renesas.ko` (built by this repo) / `CONFIG_USB_XHCI_PCI_RENESAS=m` | `.github/workflows/build-xhci-renesas.yml` |
| 4 extra buttons do nothing | they are TLMM GPIO keys (not on the pad); the EVO DTB only has volume-up in gpio-keys | `gpio-keys-pocket-evo` node + pull-up pinctrl, values from the stock Android DT | `dts/pocket-evo-fixes.dtsi` |
| Extra buttons not usable in Steam | no InputPlumber profile for the EVO | composite device -> virtual Steam Deck (deck-uhid) | `inputplumber/` |
| Desktop mode upside down | `sm8550-display.conf` lists the EVO as `right\|Rotated270` | `left\|Rotated90` (DTS rotation = 270, like Odin 2 Portal) | image config |

## Button layout (InputPlumber -> Steam Deck)

| EVO | Steam Deck |
|---|---|
| A / B / X / Y, L1 / R1, L2 / R2 (analog), L3 / R3, Select / Start, sticks, D-pad | same positions |
| Home | Steam (Guide) |
| right-side AYANEO button | Quick Access |
| right-side lower button | R5 |
| left inner trigger button | L4 |
| right inner trigger button | R4 |

## Install (temporary, until an official build includes it)

```sh
# module (artifact of the workflow)
sudo install -D -m644 xhci-pci-renesas.ko /lib/modules/7.2.8-edge-sm8550/updates/xhci-pci-renesas.ko
sudo depmod -a 7.2.8-edge-sm8550

# InputPlumber profile
sudo install -m644 inputplumber/devices.d/03-ayaneo-pocket-evo.yaml /etc/inputplumber/devices.d/
sudo install -m644 inputplumber/capability_maps.d/ayaneo_evo.yaml /etc/inputplumber/capability_maps.d/
sudo systemctl restart inputplumber
```

The DTB changes go into the EVO DTB (slot 12) of the image's `KERNEL` (Android boot image v0 with appended DTBs).

Rollback: remove the files above, `depmod -a`, restart InputPlumber, and restore the original `KERNEL`.

## What the workflow builds

`.github/workflows/build-xhci-renesas.yml` builds only `xhci-pci-renesas.ko` for the image kernel
`7.2.8-edge-sm8550` (vanilla kernel.org 7.2.8 + the image's own IKCONFIG, `USB_XHCI_PCI_RENESAS=m`,
gcc 15.2.0-16ubuntu1 like the image). The job fails unless vermagic is exactly
`7.2.8-edge-sm8550 SMP preempt mod_unload aarch64`. Firmware `renesas_usb_fw.mem` is already in the image.
