# evo-sm8550-fixes

Interim fixes for running MaSieS4Fun's SteamOS ARM (SM8550) test image on an **AYANEO Pocket EVO**.
Everything here was verified on real hardware (EVO Retro Power edition).

## Status (2026-10-15)

Verified after a cold reboot on `steamos-AYANEO-TEST-2`: display, touch, built-in pad (all buttons, sticks,
analog triggers, D-pad), the 4 extra buttons (Steam / QAM / L4 / R4 / R5 via InputPlumber), Wi-Fi, desktop
orientation. The Renesas module and the InputPlumber profile load automatically at boot.

`SteamOS-ARM-SM8550 v1.1.1` (kernel `7.2.9-edge-sm8550`) already keeps `splash_region@b8000000` in the EVO DTB
(identical to the fix), but still lacks the Renesas module, the extra-button DTB nodes, the InputPlumber profile
and the desktop orientation fix. The workflow builds the module for both 7.2.8 and 7.2.9; `patch_kernel_evo.py`
keeps an existing identical splash node and only adds the button nodes.

## Findings

| Symptom | Root cause | Fix | Where |
|---|---|---|---|
| Panel stays black after the Snapdragon logo | `dtb-chain/sanitize.sh` strips `reserved-memory/splash_region@b8000000` from the EVO DTB | keep the node (`reg = <0x0 0xb8000000 0x0 0x2b00000>`, `no-map`) | `dts/pocket-evo-fixes.dtsi` |
| Built-in pad does nothing | pad sits behind the Renesas uPD720201 PCIe xHCI (1912:0014); kernel has `# CONFIG_USB_XHCI_PCI_RENESAS is not set` | `xhci-pci-renesas.ko` (built by this repo) / `CONFIG_USB_XHCI_PCI_RENESAS=m` | `.github/workflows/build-xhci-renesas.yml` |
| 4 extra buttons do nothing | they are TLMM GPIO keys (not on the pad); the EVO DTB only has volume-up in gpio-keys | `gpio-keys-pocket-evo` node + pull-up pinctrl, values from the stock Android DT | `dts/pocket-evo-fixes.dtsi` |
| Extra buttons not usable in Steam | no InputPlumber profile for the EVO | composite device -> virtual Steam Deck (deck-uhid) | `inputplumber/` |
| Desktop mode upside down | `sm8550-display.conf` lists the EVO as `right\|Rotated270` | `left\|Rotated90` (DTS rotation = 270, like Odin 2 Portal) | `image-config/sm8550-display.conf.patch` |

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
sudo install -D -m644 xhci-pci-renesas.ko /lib/modules/$(uname -r)/updates/xhci-pci-renesas.ko
sudo depmod -a $(uname -r)

# InputPlumber profile
sudo install -m644 inputplumber/devices.d/03-ayaneo-pocket-evo.yaml /etc/inputplumber/devices.d/
sudo install -m644 inputplumber/capability_maps.d/ayaneo_evo.yaml /etc/inputplumber/capability_maps.d/
sudo systemctl restart inputplumber
```

### DTB (splash region + extra buttons)

The DTB changes go into the EVO DTB of the image's `KERNEL` file on the FAT boot partition
(Android boot image v0, gzip kernel + appended DTBs). `tools/patch_kernel_evo.py` does this without a kernel tree:

```sh
pip install fdt
cp KERNEL KERNEL.orig                       # keep the original
python3 tools/patch_kernel_evo.py KERNEL.orig KERNEL
```

It finds the single DTB whose model is `AYANEO Pocket EVO`, adds the same nodes as `dts/pocket-evo-fixes.dtsi`
(an existing splash node is kept only if it matches the verified one),
copies everything else byte-for-byte and rewrites the header size/SHA1. It refuses an already patched DTB.
On TEST-2 the output is byte-identical to the KERNEL tested on hardware.

### Desktop orientation

Apply `image-config/sm8550-display.conf.patch` to `/usr/share/steamos-odin/devices/sm8550-display.conf`
(one line; game mode is unaffected). Keep a copy of the original file.

### Rollback

Remove the module and InputPlumber files, `depmod -a`, restart InputPlumber,
put back `KERNEL.orig` and the original `sm8550-display.conf`.

## What the workflow builds

`.github/workflows/build-xhci-renesas.yml` builds only `xhci-pci-renesas.ko` for the image kernels
`7.2.8-edge-sm8550` (TEST-2) and `7.2.9-edge-sm8550` (v1.1.1) (vanilla kernel.org source + the image's own IKCONFIG, `USB_XHCI_PCI_RENESAS=m`,
gcc 15.2.0-16ubuntu1 like the image). The job fails unless vermagic is exactly
`<kver>-edge-sm8550 SMP preempt mod_unload aarch64`. Firmware `renesas_usb_fw.mem` is already in the image.
