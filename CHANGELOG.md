# Yamaha Integration for Unfolded Circle Remote — Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

## v1.2.3 - 2026-03-24

### Added
- **Surround Decoder Type** and **Auro-Matic Preset** select entities restored — backed by new `set_surr_decoder_type` and `set_auro_matic_preset` methods added to pyamaha

### Changed
- Navigation-only option values (`prev`, `next`, `toggle`) are now filtered out of all select option lists at connection time, so only directly settable values are presented
- `Auro-3D Listening Mode` select removed — those programs are redundant with entries already present in the Sound Program list
- `Tone Control Mode` select removed — requires additional bass/treble arguments incompatible with a single-option select

---

## v1.2.2 - 2026-03-11

### Fixed

- Corrected a bug where select entity would trigger connection timeouts

---

## v1.2.0 - 2026-03-09

### Added
- **Select entities** — 5 new select entities exposed per receiver, each backed by real option lists fetched from the receiver's features API at connection time. Selects not supported by a given receiver are omitted automatically:
  - **Sound Program** — choose from all supported surround/DSP modes (e.g. Munich, Vienna, Standard, Straight, etc.)
  - **Surround Decoder Type** — Auto, Dolby Surround, DTS Neural:X, Auro-3D, etc.
  - **Link Control** — Speed, Standard, Stability
  - **Link Audio Delay** — Audio Sync, Balanced, Lip Sync
  - **Auro-Matic Preset** — Small, Medium, Large, Movie, Speech, etc.

---


## v0.1.0 - 2025-01-22

### Added
- First release. Control Yamaha clients on your local network from your Unfolded Circle Remote.
