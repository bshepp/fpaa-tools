# AnadigmDesigner2 COM Automation

AD2 registers a COM automation server (`AnadigmDesigner2.Application`) that allows
circuits to be built, parameterized, and exported **without the GUI**. Verified
2026-07-03 against the Okika AD2 build installed at
`C:\Program Files (x86)\Anadigm\AnadigmDesigner2` (32-bit).

Anadigm's own reference for the object model ships with the installer:
`AnadigmDesigner2\Circuits\Build Example Circuit.vbs`.

## Quick start (PowerShell)

```powershell
$ad2 = New-Object -ComObject 'AnadigmDesigner2.Application'   # launches hidden
try {
    $chip = $ad2.Workspace.Chips.Add(9, "MyChip")             # 9 = AN231E04
    $cam  = $chip.Cams.Add('AnadigmApex\GainInv', [Type]::Missing, 8, 5)
    $cam.Parameters('G').Value = 2
    $cam.Contacts('Out').ConnectWire('OutputCell1\In')        # names per chip family
    $ad2.Document.SaveAs('C:\path\my_circuit.ad2')
    $chip.WriteConfigData('C:\path\my_circuit.ahf', 0)        # fmt 0 = AHF-style
} finally {
    $ad2.Quit(0)                                              # 0 = don't save
}
```

## Chip type enum (`Workspace.Chips.Add(type, name)`)

| type | family | part |
|------|--------|------|
| 0–8 | 0 (Vortex) | ANx20 / ANx21 variants (AN120/121/122/127, AN220/221/222/227) |
| 9–12 | 1 (Apex) | AN131E04 / AN134E04 / **AN231E04** / AN234E04 family |
| 13+ | — | crashes the COM server (RPC_E_SERVERFAULT) — do not use |

**AN231E04 = type 9**, verified by opening the shipped
`Circuits\AN231 Examples\Gain_of_2.ad2` and reading `chip.ChipType`.
Apex CAM library string: `AnadigmApex\<CamName>` (e.g. `AnadigmApex\GainInv`,
matching `Libraries\AnadigmApex\*.cam`).

## Object model (as discovered via `Get-Member`)

- **Application**: `Workspace`, `Document`, `Visible`, `Activate()`, `Quit(saveFlag)`
- **Workspace**: `Chips`, `Cams`, `Clear()`
- **Document**: `Open(path)`, `OpenNew()`, `Save()`, `SaveAs(path)`,
  `RevertToSaved()`, `CreateCppPrototype(dir, bool)`, `WriteAlgorithmicFiles(dir)`
- **Chip**: `Cams`, `IOCells`, `Clocks`, `Name`, `ChipType`, `ChipFamily`,
  `DeviceID`, `LoadOrder`, `PowerMode`, `Pullups`, `Resources`,
  `WriteConfigData(path, fmt)`, `DownloadToBoard(...)`, `Delete()`
- **CAM**: `Parameters(name).Value`, `Options(name).Choices(label).Selected`,
  `Clocks("Clock A").ChipClock`, `Contacts(name).ConnectWire(target)`, `Lut`,
  `CamType`, `Name`, `Notes`, `Delete()`
- **IOCell**: same option/parameter/contact pattern as CAMs
  (e.g. `chip.IOCells("InputCell1").Options("mode").Choices("Output").Selected = $true`)

COM errors are informative: wrong argument counts throw
"Cannot find an overload", invalid CAM/chip combinations throw
"CAM X is not compatible with chip Y".

## `WriteConfigData(path, fmt)` formats

| fmt | output |
|-----|--------|
| 0 | **AHF-compatible**: ASCII hex, one byte per line, 5-NULL preamble + 0xD5 frame. Parses with `fpaa.config.load_ahf_bytes()` / streams with `FPAAChain.send_bytes()` unchanged. |
| 1 | hex-per-line variant without a 0xD5 primary frame (purpose TBD) |
| 2 | Motorola S-record of the same frame |
| 3 | S-record of different (unidentified) data |

Export is **per chip** — for the 4-chip PIKA chain, export each chip and
concatenate the streams in chain order (extra NULL padding between frames is
ignored by the config state machine, which idles until SYNC 0xD5).

## `CreateCppPrototype(dir, bool)` — the reconfiguration reference

Generates `CCode/ApiCode.c|h` and `CCode/CAMCode.c|h` containing:

- `an_GetPrimaryConfigData(chip, &count)` — primary bitstream as C array
- `an_apiReconfigInfo` / per-chip `ReconfigBuffer` — runtime update machinery
- Per-CAM runtime setters, e.g. `an_setGainInv(an_CAM cam, double G)` —
  **the capacitor-ratio → config-bytes math needed to implement runtime
  weight updates in the Python driver** (port target or per-circuit codegen)

Known quirk: the `dir` argument suffered backslash-mangling when called with a
deep path from PowerShell — use a short, simple output directory.

## Why this matters for this repo

The full circuit → silicon pipeline is scriptable end-to-end on Windows:
author circuit via COM → `WriteConfigData(…, 0)` → validate with
`fpaa.config` → scp to the Pi → `FPAAChain.send_bytes()`. No GUI sessions
required for the `09-fpaa-characterization` study's circuit iterations.
