# Feux de Foret for Home Assistant

<p align="center">
  <img src="custom_components/feuxdeforet_fr/brand/logo.png" alt="Feux de Foret" width="420">
</p>

Unofficial Home Assistant custom integration for wildfire data exposed by [feuxdeforet.fr](https://feuxdeforet.fr), powered by [`pyfeuxdeforet-fr`](https://github.com/jul-fls/pyfeuxdeforet-fr).

The integration is designed for dashboards and automations:

- national fire counters: current, 24h, 7d, 30d, current year;
- national risk-zone counters by vigilance level;
- one fire-count sensor per French region;
- one fire-count sensor per department;
- one dynamic `geo_location` entity per mapped fire;
- rich attributes on fire locations, including status, state, URL, department and region slugs;
- HACS-compatible repository layout.

## Installation

### HACS custom repository

1. Open HACS.
2. Go to `Integrations`.
3. Add this repository as a custom repository:

```text
https://github.com/jul-fls/ha-feuxdeforet-fr
```

4. Category: `Integration`.
5. Install `Feux de Foret`.
6. Restart Home Assistant.
7. Add the integration from `Settings > Devices & services`.

### Manual

Copy this folder:

```text
custom_components/feuxdeforet_fr
```

into your Home Assistant config:

```text
config/custom_components/feuxdeforet_fr
```

Then restart Home Assistant.

## Entities

### National sensors

The integration creates:

- `sensor.feux_de_foret_current_fires`
- `sensor.feux_de_foret_fires_over_24h`
- `sensor.feux_de_foret_fires_over_7_days`
- `sensor.feux_de_foret_fires_over_30_days`
- `sensor.feux_de_foret_fires_this_year`
- `sensor.feux_de_foret_weak_risk_zones`
- `sensor.feux_de_foret_moderate_risk_zones`
- `sensor.feux_de_foret_high_risk_zones`
- `sensor.feux_de_foret_very_high_risk_zones`
- `sensor.feux_de_foret_extreme_risk_zones`
- `sensor.feux_de_foret_mapped_fires`

Entity IDs may vary depending on your Home Assistant naming rules.

### Region and department sensors

For each known region and department, a sensor exposes:

- state: active mapped fire count;
- attributes:
  - `total_mapped_fires`;
  - `active_fires`;
  - `by_status`;
  - source URL.

Empty department sensors are marked as diagnostic so they do not overwhelm primary dashboards.

### Dynamic fire locations

Every mapped fire becomes a `geo_location` entity with:

- latitude;
- longitude;
- fire ID;
- status;
- state;
- source URL;
- department slug;
- region slug;
- raw `properties` from the GeoJSON payload.

These entities can be displayed on a map and used in automations.

## Dashboard examples

### Overview

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Feux de Foret
    entities:
      - sensor.feux_de_foret_current_fires
      - sensor.feux_de_foret_fires_over_24h
      - sensor.feux_de_foret_fires_over_7_days
      - sensor.feux_de_foret_fires_over_30_days
      - sensor.feux_de_foret_fires_this_year
      - sensor.feux_de_foret_mapped_fires
  - type: grid
    columns: 2
    square: false
    cards:
      - type: tile
        entity: sensor.feux_de_foret_high_risk_zones
      - type: tile
        entity: sensor.feux_de_foret_very_high_risk_zones
      - type: tile
        entity: sensor.feux_de_foret_extreme_risk_zones
```

### Fire map

The built-in map card can display geo-location sources:

```yaml
type: map
title: Feux en France
geo_location_sources:
  - feuxdeforet_fr
hours_to_show: 24
default_zoom: 6
```

### Regional focus

```yaml
type: entities
title: Feux par région
entities:
  - sensor.auvergne_rhone_alpes_fires
  - sensor.bourgogne_franche_comte_fires
  - sensor.bretagne_fires
  - sensor.centre_val_de_loire_fires
  - sensor.corse_fires
  - sensor.grand_est_fires
  - sensor.hauts_de_france_fires
  - sensor.ile_de_france_fires
  - sensor.normandie_fires
  - sensor.nouvelle_aquitaine_fires
  - sensor.occitanie_fires
  - sensor.pays_de_la_loire_fires
  - sensor.provence_alpes_cote_d_azur_fires
```

## Automation ideas

### Alert when a department has an active fire

```yaml
alias: Alerte feu dans le Var
triggers:
  - trigger: numeric_state
    entity_id: sensor.var_fires
    above: 0
actions:
  - action: notify.mobile_app_phone
    data:
      title: Feu détecté dans le Var
      message: "{{ states('sensor.var_fires') }} feu(x) actif(s) cartographié(s)."
```

### Alert when a fire geo-location is near home

Home Assistant can use geo-location entities with zones. Create a zone around your house, then use a geo-location trigger:

```yaml
alias: Feu proche de la maison
triggers:
  - trigger: geo_location
    source: feuxdeforet_fr
    zone: zone.home
    event: enter
actions:
  - action: notify.mobile_app_phone
    data:
      title: Feu proche
      message: >-
        {{ trigger.entity_id }} est dans la zone maison.
```

For an arbitrary radius in kilometers, create a Home Assistant zone with that radius and use the same trigger.

## Options

The integration options let you tune:

- polling interval;
- region sensors on/off;
- department sensors on/off;
- dynamic fire geo-location entities on/off;
- GeoJSON `last_update` parameter;
- GeoJSON `x-fdf-nonce` header value.

## Development

```bash
python -m pip install -r requirements_test.txt
pytest -q --cov
ruff check .
```

## Notes

This integration is unofficial and is not affiliated with feuxdeforet.fr.

The GeoJSON endpoint currently works with:

```http
x-fdf-nonce: 0
Referer: https://feuxdeforet.fr/fdf/cartographie/
Accept: application/geo+json, application/json
```

If feuxdeforet.fr changes its frontend/proxy behavior, update the integration or the library client accordingly.
