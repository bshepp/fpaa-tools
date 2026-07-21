# fpaa-tools

Python tooling for **Anadigm AN231E04** field-programmable analog arrays on the
**Okika OTC2310K04-PIKA** Raspberry Pi HAT (4 chips, daisy-chained over SPI).

Configure the chain from `.ahf` files, reconfigure parameters at runtime in ~1 ms
without a reset, and measure what the analog side actually does.

```python
from fpaa import FPAAChain

with FPAAChain() as chain:                          # auto-detects the SPI bus
    ok = chain.configure_from_ahf("circuit.ahf")    # reset + stream + verify
    print(f"active={chain.activate_status} err_clear={chain.err_status}")
```

## Read this first if you are on a Raspberry Pi 5

**`/boot/firmware/config.txt` must contain BOTH of these lines:**

```
dtparam=spi=on        # binds RP1 SPI0 to header GPIO 9/10/11 (MISO/MOSI/SCLK)
dtoverlay=spi0-0cs    # declares zero hardware chip-selects, freeing GPIO 8 (CE0)
                      # so the driver can hold it low across the whole primary
                      # configuration burst, as ANU002 timing requires
```

The Raspberry Pi Imager's "enable SPI" toggle adds **neither**. Without them,
GPIO 9/10/11 stay floating inputs and SPI never reaches the chips.

The symptom is actively misleading: `ERR_B` sits low after configuration, which
the PIKA Quick Start attributes to *"ACLK not reaching the FPAAs."* The ACLK is
usually fine — **SCLK is the missing signal.** This cost us a day; it should
cost you nothing.

Two more Pi 5 notes baked into the driver:

- **SPI writes are chunked to ≤64 bytes per `xfer2`**, working around an open Pi 5
  DMA timeout bug ([raspberrypi/linux#6020](https://github.com/raspberrypi/linux/issues/6020)).
  This is deliberate — don't "simplify" it back to a single transfer.
- The driver **auto-detects the SPI bus** (`/dev/spidev0.0` on a Pi 4 or a
  correctly-configured Pi 5; `/dev/spidev10.0` on a Pi 5 with the wrong overlay).

## Install

**On a Raspberry Pi (drives real hardware):**

```bash
git clone https://github.com/bshepp/fpaa-tools
cd fpaa-tools
pip install -e ".[hardware]"   # pulls spidev, RPi.GPIO, gpiod (Pi-only wheels)
```

**On any host (no Pi, no hardware)** — the pure-logic layers (AHF parsing, reconfig
diffing, measurement analysis) install and test anywhere:

```bash
pip install -e ".[dev]"        # numpy + pytest only
pytest                         # 64 tests, no hardware needed
```

> `requirements.txt` is the **Pi runtime** dependency set and expects Pi-only wheels
> (`spidev`, `RPi.GPIO`); it will not install on a non-Pi host. Use the extras above.

## What's here

### Chain configuration

```python
from fpaa import load_ahf_bytes, split_ahf_by_chip

data = load_ahf_bytes("circuit.ahf")        # raw byte stream
for cfg in split_ahf_by_chip(data):         # per-chip frames
    print(f"chip {cfg.chip_id:02X}: {cfg.total_bytes} B, {len(cfg.blocks)} blocks")
```

### Runtime reconfiguration (~1 ms, no reset)

`fpaa.reconfig` builds AN231E04 update frames directly. The trick is that you
need no parameter→address math: export two same-layout configurations from
AnadigmDesigner2 that differ in one parameter, diff them, and send the result.
The chain stays live.

```python
from fpaa import make_update_from_configs

upd = make_update_from_configs(frame_before, frame_after)   # ~15 bytes
chain.send_update(upd)                                      # ~1 ms, no reset
```

Validated on hardware: ~1 ms per update, versus ~180 ms for a full reconfigure.

### Measurement (`fpaa.measure`)

Edge capture, channel analysis, entropy, dynamics, and synchronization metrics.

**Use `GpiodBackend` for anything timing-sensitive.** It uses kernel edge
timestamps. `PollBackend` reads the clock once per loop iteration and stamps
*every* pin with that same value — which snaps independent channels onto a
common sampling grid and **manufactures correlation between them**. We measured
a phase-locking value of 0.435 that way; the honest number was 0.068. If you are
measuring a correlation *between channels*, `PollBackend` will lie to you.

Also keep high-rate signals out of a shared `gpiod` request: a pin emitting
~240k edges/s floods the kernel event buffer and silently drops ~1.3% of the
other pins' edges.

### Headless circuit generation

AnadigmDesigner2 is fully scriptable over COM — no GUI needed. You can build
circuits, set CAM parameters, wire contacts, and export AHF-compatible hex that
this library streams unchanged. See **[docs/AD2_COM_AUTOMATION.md](docs/AD2_COM_AUTOMATION.md)**.

The essentials: `Workspace.Chips.Add(9, name)` — chip type **9** is the AN231E04;
the CAM library string is `AnadigmApex\<CamName>`; and `chip.WriteConfigData(path, 0)`
(format 0) exports per-chip hex that `fpaa.config` parses directly.

## Hardware reference

Pin map, clock-select modes, and the Pi 5 SPI requirements:
**[docs/PIKA_HARDWARE.md](docs/PIKA_HARDWARE.md)**.

## Scope, honestly

- `fpaa.neural` is **capacity modeling only** — it estimates what fits (CABs,
  weights, precision). It does **not** synthesize bitstreams. Circuit design
  happens in AnadigmDesigner2; see the COM automation above.
- The Pi 5 findings come from one bench (Pi 5 / Debian Trixie / PIKA HAT).
  They are reported as measured, not as universal truths.
- Tested against the PIKA HAT. The QuadApex/USB-serial path is not supported here.

## Credit

The GPIO pin map and the primary-configuration sequence were derived from Okika's
own [`pikapy`](https://github.com/okikajre) reference (`spitest.py`), which is
released under MIT-0. This library is licensed **MIT No Attribution** to match it —
take it, use it, no credit required.

## License

MIT No Attribution. See [LICENSE](LICENSE).
