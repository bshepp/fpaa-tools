# PIKA HAT hardware reference

Okika **OTC2310K04-PIKA** Raspberry Pi HAT: 4× Anadigm **AN231E04** dpASP,
daisy-chained, driven over SPI from the Pi's GPIO header.

```
Raspberry Pi
    | SPI (GPIO 10/11/8) @ 32 MHz
AN231E04 x4  (daisy-chained on the PIKA HAT)
    | analog I/O
sensors / outputs
```

- **20 CABs per chip** (configurable analog blocks) → 80 across the chain
- **4 I/O cells per chip** (16 total), each configurable as input or output
- **16 MHz** on-board analog clock (40 MHz alternative available)
- CAB resources: op-amps, capacitors, switches, comparators

## GPIO pin map

Direction is from the **host (Raspberry Pi)** perspective. This map is taken from
Okika's `spitest.py` reference, not inferred.

| Signal | GPIO | Dir | Purpose |
|--------|------|-----|---------|
| CE0 | 8 | OUT | SPI chip select — held **LOW for the whole session** (`no_cs=True`) |
| RESET_B | 26 | OUT | FPAA reset; drive LOW to reset, HIGH to release |
| ACTIVATE | 24 | IN | Open-drain; FPAA holds LOW until the last chip in the chain is primary-configured |
| CFGFLG_B | 23 | IN | Open-drain; configuration flag, active LOW |
| ERR_B | 25 | IN | Open-drain; FPAA drives LOW on a configuration error |
| LCL_ACLK_EN | 14 | OUT | Drive HIGH to enable the on-board 16 MHz oscillator |
| ACLK_SEL0 | 5 | OUT | Clock select bit 0 |
| ACLK_SEL1 | 6 | OUT | Clock select bit 1 |
| FPAA0_IO5P / IO5N | 16 / 17 | — | FPAA0 I/O cell 5 |
| FPAA1_IO5P / IO5N | 18 / 19 | — | FPAA1 I/O cell 5 |
| FPAA2_IO5P / IO5N | 20 / 21 | — | FPAA2 I/O cell 5 |
| FPAA3_IO5P / IO5N | 12 / 13 | — | FPAA3 I/O cell 5 |

### Clock select (ACLK_SEL[1:0])

| Value | Source |
|-------|--------|
| `00` | Local 16 MHz oscillator (default) |
| `01` | J11 reference from a stacked PIKA |
| `10` | External via TP1 |
| `11` | GPIO4 GPCLK0 |

## Configuration sequence

- Reset is a **RESET_B pulse** — 20 ms low, 100 ms high. (Not an ERR_B wiggle.)
- SPI: **32 MHz, mode 0, MSB-first**.
- The on-board 16 MHz oscillator is enabled at init (`LCL_ACLK_EN` high).
- CE0 is held low manually across the entire primary-configuration burst, per
  ANU002 timing. This is why the `spi0-0cs` overlay is mandatory (below).

## Raspberry Pi 5 requirements

`/boot/firmware/config.txt` must contain **both**:

```
dtparam=spi=on        # binds RP1 SPI0 to header GPIO 9/10/11 (MISO/MOSI/SCLK)
dtoverlay=spi0-0cs    # zero hardware chip-selects, freeing GPIO 8 (CE0) for the
                      # driver to hold low across the whole config burst
```

The Imager's "enable SPI" toggle adds neither. Without them GPIO 9/10/11 remain
floating inputs and SPI activity never reaches the chips.

**The failure mode is misleading.** `ERR_B` stuck low after configuration reads,
per the PIKA Quick Start, as *"ACLK not reaching the FPAAs"* — but ACLK is
typically fine. The missing signal is **SCLK**.

### Other Pi 5 notes

- **SPI writes are chunked to ≤64 bytes per `xfer2`** to work around an open Pi 5
  DMA timeout bug ([raspberrypi/linux#6020](https://github.com/raspberrypi/linux/issues/6020)).
- The driver uses **SPI bus 0 only** (`/dev/spidev0.0`). On a Pi 5 a second node,
  `/dev/spidev10.0`, may exist: that is the BCM2712 SoC's own SPI controller, wired to the
  **boot EEPROM** — not the header's SPI0 renumbered. The driver refuses it, and raises a
  clear error if `spidev0.0` is absent instead of trying another bus. (Raspberry Pi OS ships
  `dtoverlay=nospi10` under `[pi5]` in recent images for the same reason.)
- **`import RPi.GPIO` is served by `rpi-lgpio`**, a drop-in replacement that routes to
  lgpio and works on every Pi. Raspberry Pi OS ships it as `python3-rpi-lgpio`, and it
  reports `RPi.GPIO.VERSION == "0.7.2"`. That version string is a compatibility label:
  the original RPi.GPIO stops at 0.7.1 on PyPI and does not work on a Pi 5. (Before
  0.5.2 this project asked pip for `RPi.GPIO>=0.7.2`, which no index can satisfy.)

## Measurement notes

Settling time after reconfiguration is roughly **100 µs**.

For timing-sensitive capture use **`GpiodBackend`** (kernel edge timestamps).
`PollBackend` timestamps every pin from a single clock read per loop iteration,
placing all channels on a common grid — which fabricates cross-channel
correlation. Never use it to measure a relationship *between* channels.

Keep high-rate signals in their own `gpiod` request. A pin emitting ~240k edges/s
will flood the shared kernel event buffer and silently drop edges from the pins
you care about.

Two more limits, measured on the bench (Pi 5, kernel 6.12, 2026-07-21):

- **The kernel clamps each line request's edge-event buffer to ~1024 events**,
  regardless of the `event_buffer_size` requested. Sustained loss-free capture
  therefore ends around 100–200k edges/s, and GPIO frequency checks are only
  trustworthy up to **~150 kHz per pin**. The 4osc reference config's 80 and
  150 kHz channels verify exactly; its 277 and 493 kHz channels show edge
  activity but need a scope for frequency confirmation.
- **Analog outputs read through a digital GPIO produce threshold chatter** —
  bursts of extra edges at each level crossing. Estimate frequency from the
  **median rise-to-rise period**; the mean edge rate lies in both directions
  (up under chatter, down under dropped events).

## Analog gotchas

- FPAAs are sensitive to power-supply noise.
- A solid ground plane matters for precision.
- Temperature drift affects capacitor values.
- Practical precision: capacitor matching ~0.1% (≈10 bits); op-amp offset ~1 mV;
  usable weight precision ~8 bits; output precision ~10 bits.
