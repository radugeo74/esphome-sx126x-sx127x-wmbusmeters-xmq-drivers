"""T1 proprietary XMQ primary meters; no wmbus_meter or shadow probe."""
import json
from pathlib import Path
from .generate_drivers import generate_driver_header
from .profile_validation import approved_families, validate_driver_family

# Generate before ESPHome resource discovery copies *.h sources to build dir.
generate_driver_header(Path(__file__).resolve().parent)
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.components.wmbus_radio import RadioComponent
from esphome.components.esp32 import add_idf_sdkconfig_option
from esphome.const import CONF_ID

DEPENDENCIES = ["wmbus_radio"]
AUTO_LOAD = ["sensor"]
MULTI_CONF = True
CODEOWNERS = ["@radugeo74"]
ns = cg.esphome_ns.namespace("xmq_meter")
Meter = ns.class_("Meter", cg.Component)
FIELDS = ("current_hca", "previous_hca", "temp_room_c", "temp_radiator_c",
          "target_m3", "total_m3", "rssi_dbm")
CONF_RADIO_ID = "radio_id"
CONF_METER_ID = "meter_id"
CONF_FAMILY = "family"
CONF_DRIVER = "driver"
APPROVED_FAMILIES = approved_families(Path(__file__).resolve().parent)
VALIDATED_DRIVERS = tuple(APPROVED_FAMILIES)

def _validate_meter_profile(config):
    try:
        return validate_driver_family(config, APPROVED_FAMILIES)
    except ValueError as exc:
        raise cv.Invalid(str(exc)) from exc


CONFIG_SCHEMA = cv.All(cv.Schema({
    cv.GenerateID(): cv.declare_id(Meter),
    cv.Required(CONF_RADIO_ID): cv.use_id(RadioComponent),
    cv.Required(CONF_METER_ID): cv.hex_int,
    cv.Required(CONF_FAMILY): cv.one_of("heat", "water", lower=True),
    cv.Optional(CONF_DRIVER, default="auto"): cv.one_of("auto", *VALIDATED_DRIVERS, lower=True),
    **{cv.Optional(name): sensor.sensor_schema(accuracy_decimals=1)
       for name in FIELDS},
}).extend(cv.COMPONENT_SCHEMA), _validate_meter_profile)


async def to_code(config):
    # Regenerate if a single .xmq source was updated in the component cache.
    generate_driver_header(Path(__file__).resolve().parent)
    add_idf_sdkconfig_option("CONFIG_COMPILER_CXX_EXCEPTIONS", True)
    cg.add_build_flag("-DXMQ_STANDALONE_ONLY=1")
    var = cg.new_Pvariable(config[CONF_ID])
    cg.add(var.set_meter(config[CONF_METER_ID], config[CONF_FAMILY] == "heat"))
    cg.add(var.set_driver(config[CONF_DRIVER]))
    radio = await cg.get_variable(config[CONF_RADIO_ID])
    cg.add(var.set_radio(radio))
    for name in FIELDS:
        if name in config:
            s = await sensor.new_sensor(config[name])
            cg.add(var.add_sensor(name, s))
    await cg.register_component(var, config)
