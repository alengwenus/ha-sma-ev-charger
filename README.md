# SMA EV Charger integration for Home Assistant

Home Assistant (https://www.home-assistant.io) Integration Component

This custom component integrates the SMA EV Charger into Home Assistant.

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

## Installation

### HACS - Home Assistant Community Store _(recommended)_

This method needs to have HACS installed correctly. For more info on HACS refer to [here](https://hacs.xyz/).

#### Automatically with _My Home Assistant_

Click on the following button to have the SMA EV Charger integration added automatically to HACS. Once the installation is done, go on with the [Configuration](#configuration) below.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=alengwenus&repository=ha-sma-ev-charger&category=integration)

#### Manually in HACS

If _My Home Assistant_ does not work for you, you might consider installing the SMA EV Charger integration manually using HACS. For this you need to add a custom repository following the instructions [here](https://hacs.xyz/docs/faq/custom_repositories/).

When asked, use the custom repository link `https://github.com/alengwenus/ha-sma-ev-charger`

Select the category type `integration`

Once the repository is downloaded click the INSTALL button (still in HACS). Go on with the [Configuration](#configuration) below.

### Manual installation

You probably **do not** want to do this! Use one of the HACS methods above unless you know what you are doing and have a good reason as to why you are installing manually

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`)
1. If you do not have a `custom_components` directory there, you need to create it
1. In the `custom_components` directory create a new folder called `smaev`
1. Download _all_ the files from the `custom_components/smaev/` directory in this repository
1. Place the files you downloaded in the new directory you created
1. _Restart HA to load the new integration_
1. Go on with the [Configuration](#configuration) below

### Configuration

1. [Click Here](https://my.home-assistant.io/redirect/config_flow_start/?domain=smaev) to directly add a `SMA EV Charger` integration **or**<br/>
   a. In Home Assistant, go to Settings -> [Integrations](https://my.home-assistant.io/redirect/integrations/)<br/>
   b. Click `+ Add Integrations` and select `SMA EV Charger`<br/>
1. Enter your SMA EV Charger network address and your credentials (as defined in the wallbox web-ui)
1. Change the SSL setting to your needs (e.g. if you access the wallbox through a proxy)
1. Click `Submit`

[<img src="https://github.com/alengwenus/ha-sma-ev-charger/blob/main/.github/screenshots/install.png" width="300">](https://github.com/alengwenus/ha-sma-ev-charger/blob/main/.github/screenshots/install.png)

After successful installation all entities are automatically added to Home Assistant. You may then add them to your dashboards as you like.
