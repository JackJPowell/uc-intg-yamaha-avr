# Yamaha AVR integration for Remote Two/3

This integration is based on the [pyamaha](https://github.com/rsc-dev/pyamaha) library and uses the
[uc-integration-api](https://github.com/aitatoi/integration-python-library) to communicate with the Remote Two/3.

A [media player entity](https://github.com/unfoldedcircle/core-api/blob/main/doc/entities/entity_media_player.md)
is exposed to the Remote Two/3. A [Remote](https://github.com/unfoldedcircle/core-api/blob/main/doc/entities/entity_remote.md) is also created.

Supported versions:
- Network enabled Yamaha Receiver

Supported attributes:
- State (on, off, unknown)
- Source List

Supported commands:
- Turn on & off (device will be put into standby)
- Volume up / down
- Mute toggle
- Directional pad navigation and select
- Context menu
- Standard Key Commands


### Network

- The Yamaha AVR device must be on the same network subnet as the Remote. 
- When using DHCP: a static IP address reservation for the Yamaha AVR device(s) is recommended.

### Yamaha AVR device

- A Yamaha AVR that is network enabled is required to use the integration. Please refer to the yamaha library #TODO for additional information on supported models. 

## Usage

### Docker
```
docker run -d \
  --name Yamaha \
  --network host \
  -v $(pwd)/<local_directory>:/config \
  --restart unless-stopped \
  -e UC_INTEGRATION_HTTP_PORT=9090 \
  ghcr.io/jackjpowell/uc-intg-yamaha-avr:latest
```

### Docker Compose

```
  yamaha:
    container_name: Yamaha
    image: ghcr.io/jackjpowell/uc-intg-yamaha-avr:latest
    network_mode: host
    volumes:
      - ./<local_directory>:/config
    environment:
      - UC_INTEGRATION_HTTP_PORT=9090
    restart: unless-stopped
```

### Install on Remote

- Download tar.gz file from Releases section of this repository
- Upload the file to the remove via the integrations tab (Requires Remote Beta)

### Setup (For Development)

- Requires Python 3.11
- Install required libraries:  
  (using a [virtual environment](https://docs.python.org/3/library/venv.html) is highly recommended)
```shell
pip3 install -r requirements.txt
```

For running a separate integration driver on your network for Remote Two/3, the configuration in file
[driver.json](driver.json) needs to be changed:

- Change `name` to easily identify the driver for discovery & setup  with Remote Two/3 or the web-configurator.
- Optionally add a `"port": 8090` field for the WebSocket server listening port.
    - Default port: `9090`
    - This is also overrideable with environment variable `UC_INTEGRATION_HTTP_PORT`

### Run

```shell
UC_CONFIG_HOME=./ python3 intg-yamaha-avr/driver.py
```

See available [environment variables](https://github.com/unfoldedcircle/integration-python-library#environment-variables)
in the Python integration library to control certain runtime features like listening interface and configuration directory.

The configuration file is loaded & saved from the path specified in the environment variable `UC_CONFIG_HOME`.
Otherwise, the `HOME` path is used or the working directory as fallback.

The client name prefix used for pairing can be set in ENV variable `UC_CLIENT_NAME`. The hostname is used by default.

## Versioning

We use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags and releases in this repository](https://github.com/jackjpowell/uc-intg-yamaha-avr/releases).

## Changelog

The major changes found in each new release are listed in the [changelog](CHANGELOG.md)
and under the GitHub [releases](https://github.com/jackjpowell/uc-intg-yamaha-avr/releases).

## Contributions

Please read the [contribution guidelines](CONTRIBUTING.md) before opening a pull request.

## License

This project is licensed under the [**Mozilla Public License 2.0**](https://choosealicense.com/licenses/mpl-2.0/).
See the [LICENSE](LICENSE) file for details.
