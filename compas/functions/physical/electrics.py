__author__ = 'Vincenzo Arcidiacono'

import numpy as np
from math import pi
# Power Demand due to Electrics:
def evaluate_power_demand_electrics(bat_int_res, load_elec, alt_eff, current):
    """
    Calculates power demand due to electrics.

    :param bat_int_res:
        Battery internal resistance.
    :type bat_int_res: float

    :param load_elec:
        Electric load power.
    :type load_elec: float

    :param alt_eff:
        Alternator efficiency.
    :type alt_eff: float

    :param current:
        Electric current.
    :type current: float

    :return:
        Power demand due to electrics.
    :rtype: float
    """

    if current >= 0:
        return (bat_int_res * current**2 / 1000 + load_elec) / alt_eff
    return 0

# Current
def evaluate_current(
        is_ener_recup, bat_char_amp_max, alt_char_factor_regen,
        battery_soc, current_no_recup, current_recup):
    """
    --> Positive from alternator
    --> Negative from battery

    Calculates system current.

    :param is_ener_recup:
        Energy recuperation ?.
    :type is_ener_recup: binary

    :param bat_char_amp_max:
        Battery maximum charging current.
    :type bat_char_amp_max: float

    :param alt_char_factor_regen:
        Alternator charging regeneration factor.
    :type alt_char_factor_regen: float

    :param battery_soc:
        Battery SOC.
    :type battery_soc: float

    :param current_no_recup:
        Current with no recuperation.
    :type current_no_recup: float

    :param current_recup:
        Current with recuperation.
    :type current_recup: float

    :return:
        System current.
    :rtype: float
    """

    if is_ener_recup == 0 or battery_soc > 0.99:
        return current_no_recup
    else:
        if current_recup < -1:
            return current_no_recup + bat_char_amp_max * alt_char_factor_regen
        else:
            return current_no_recup - current_recup * bat_char_amp_max * alt_char_factor_regen

def evaluate_current_recup(
        eng_p0fc, battery_eff, alt_eff, alt_power_nom, braking_power):
    """
    Calculates current with recuperation active.

    :param eng_p0fc:
        ???.
    :type eng_p0fc: float

    :param battery_eff:
        Battery efficiency.
    :type battery_eff: float

    :param alt_eff:
        Alternator efficiency.
    :type alt_eff: float

    :param alt_power_nom:
        Alternator power nomimal.
    :type alt_power_nom: float

    :param wheel_power:
        Wheel power.
    :type wheel_power: float

    :param gearbox_efficiency_fixed:
        Fixed gearbox efficiency.
    :type gearbox_efficiency_fixed: float

    :return:
        Current with recuperation active.
    :rtype: float
    """

    if braking_power < eng_p0fc:
        return (braking_power)/(alt_power_nom/(battery_eff*alt_eff))
    return 0

def evaluate_current_no_recup(
        engine_status, next_engine_status, battery_starting_current, battery_soc, previous_battery_soc,
        battery_soc_bal, battery_soc_bal_margin, engine_speed, engine_speed_gen_off, load_elec, alt_volt,
        battery_charging_current_max, alt_char_factor):
    """
    Calculates current with recuperation not active.

    :param engine_status:
        Engine status.
    :type engine_status: binary

    :param next_engine_status:
        Next step's engine status.
    :type next_engine_status: binary

    :param battery_starting_current:
        Battery starting current.
    :type battery_starting_current: float

    :param battery_soc:
        Battery SOC.
    :type battery_soc: float

    :param previous_battery_soc:
        Previous step's battery SOC.
    :type previous_battery_soc: float

    :param battery_soc_bal:
        Battery SOC balance.
    :type battery_soc_bal: float

    :param battery_soc_bal_margin:
        Battery SOC balance margin.
    :type battery_soc_bal_margin: float

    :param engine_speed:
        Engine speed.
    :type engine_speed: float

    :param engine_speed_gen_off:
        Engine speed generator off.
    :type engine_speed_gen_off: float

    :param load_elec:
        Electric power load.
    :type load_elec: float

    :param alt_volt:
        Alternator voltage.
    :type alt_volt: float

    :param battery_charging_current_max:
        Maximum battery charging current.
    :type battery_charging_current_max: float

    :param alt_char_factor:
        Alternator charging factor.
    :type alt_char_factor: float

    :return:
        Current with recuperation not active.
    :rtype: float
    """

    if next_engine_status - engine_status == 1:
        return battery_starting_current
    else:
        if engine_status == 0 or battery_soc > battery_soc_bal + battery_soc_bal_margin or engine_speed < engine_speed_gen_off or battery_soc > 0.99:
            return -load_elec * 1000 / alt_volt
        else:
            if battery_soc < battery_soc_bal - battery_soc_bal_margin and battery_soc - previous_battery_soc < 0:
                return  load_elec * 1000 / alt_volt + battery_charging_current_max
            else:
                if battery_soc < battery_soc_bal + battery_soc_bal_margin and battery_soc - previous_battery_soc > 0:
                    return -load_elec * 1000 / alt_volt + battery_charging_current_max * alt_char_factor
                else:
                    return -load_elec * 1000 / alt_volt

from compas.functions.physical.utils import reject_outliers


def identify_electric_loads(
        alternator_nominal_voltage, battery_currents,
        alternator_powers_demand):
    """
    Identifies vehicle electric load and start/stop demand [kW].

    :param alternator_nominal_voltage:
        Alternator nominal voltage [V].
    :type alternator_nominal_voltage: float

    :param battery_currents:
        Low voltage battery current vector [A].
    :type battery_currents: np.array

    :param alternator_powers_demand:
        Alternator power demand to the engine [kW].
    :type alternator_powers_demand: np.array

    :return:
        Vehicle electric load [kW].
    :rtype: (float, float)
    """

    power = (alternator_nominal_voltage / 1000) * battery_currents
    power += alternator_powers_demand

    vl, s = reject_outliers(power, n=1)

    ssl = np.median((power <= vl - s) | (power >= vl + s)) - vl

    return vl, ssl


def calculate_soc(
        battery_capacity, times, initial_soc, battery_currents):
    """
    Calculates the state of charge of the battery [%].

    :param battery_capacity:
        Battery capacity [Ah].
    :type battery_capacity: float

    :param times:
        Time vector [s].
    :type times: np.array

    :param initial_soc:
        Initial state of charge of the battery [%].
    :type initial_soc: float

    :param battery_currents:
        Low voltage battery current vector [A].
    :type battery_currents: np.array

    :return:
        State of charge of the battery [%].
    :rtype: np.array
    """

    soc = [initial_soc]
    c = battery_capacity * 3600.0

    bc = np.asarray(battery_currents)
    bc = (bc[:-1] + bc[1:]) * np.diff(times) / 2

    for b in bc:
        soc.append(soc[-1] + b / c)

    return np.asarray(soc) * 100.0


def calculate_alternator_powers_demand(
        alternator_nominal_voltage, alternator_currents, alternator_efficiency):
    """
    Calculates the alternator power demand to the engine [kW].

    :param alternator_nominal_voltage:
        Alternator nominal voltage [V].
    :type alternator_nominal_voltage: float

    :param alternator_currents:
        Alternator current vector [A].
    :type alternator_currents: np.array

    :param alternator_efficiency:
        Alternator efficiency [-].
    :type alternator_efficiency: float

    :return:
        Alternator power demand to the engine [kW].
    :rtype: np.array
    """

    c = alternator_nominal_voltage / (1000 * alternator_efficiency)

    return c * alternator_currents


def identify_bers():
    pass