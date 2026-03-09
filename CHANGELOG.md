# Yamaha Integration for Unfolded Circle Remote — Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

---

## v1.2.0 - 2026-03-09

### Added
- **Select entities** — 7 new select entities exposed per receiver, each backed by real option lists fetched from the receiver's features API at connection time:
  - **Sound Program** — choose from all supported surround/DSP modes (e.g. Munich, Vienna, Standard, Straight, etc.)
  - **Surround Decoder Type** — Auto, Dolby Surround, DTS Neural:X, Auro-3D, etc.
  - **Link Control** — Speed, Standard, Stability
  - **Link Audio Delay** — Audio Sync, Balanced, Lip Sync
  - **Auro-3D Listening Mode** — Auro-3D, Surround, Native, etc.
  - **Auro-Matic Preset** — Small, Medium, Large, Movie, Speech, etc.
  - **Tone Control Mode** — Manual, Auto, Bypass (availability depends on zone)

---


## v0.1.0 - 2025-01-22

### Added
- First release. Control Yamaha clients on your local network from your Unfolded Circle Remote.
