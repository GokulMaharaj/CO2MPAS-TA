# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""
It contains functions that model the basic mechanics of the vehicle.
"""

import schedula as sh
import scipy.interpolate as sci_itp
import pykalman
import numpy as np
from .defaults import dfl


def calculate_velocities(times, obd_velocities):
    """
    Filters the obd velocities [km/h].

    :param times:
        Time vector [s].
    :type times: numpy.array

    :param obd_velocities:
        OBD velocity vector [km/h].
    :type obd_velocities: numpy.array

    :return:
        Velocity vector [km/h].
    :rtype: numpy.array
    """

    dt = float(np.median(np.diff(times)))
    t = np.arange(times[0], times[-1] + dt, dt)
    v = np.interp(t, times, obd_velocities)

    return np.interp(times, t, pykalman.KalmanFilter().em(v).smooth(v)[0].T[0])


def calculate_accelerations(times, velocities):
    """
    Calculates the acceleration from velocity time series [m/s2].

    :param times:
        Time vector [s].
    :type times: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :return:
        Acceleration vector [m/s2].
    :rtype: numpy.array
    """

    Spline = sci_itp.InterpolatedUnivariateSpline
    acc = Spline(times, velocities / 3.6).derivative()(times)
    b = (velocities[:-1] == 0) & (velocities[1:] == velocities[:-1])
    acc[:-1][b] = 0
    if b[-1]:
        acc[-1] = 0
    return acc


def calculate_aerodynamic_resistances(f2, velocities):
    """
    Calculates the aerodynamic resistances of the vehicle [N].

    :param f2:
        As used in the dyno and defined by respective guidelines [N/(km/h)^2].
    :type f2: float

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array | float

    :return:
        Aerodynamic resistance vector [N].
    :rtype: numpy.array | float
    """

    return f2 * velocities**2


def calculate_f2(
        air_density, aerodynamic_drag_coefficient, frontal_area, has_roof_box):
    """
    Calculates the f2 coefficient [N/(km/h)^2].

    :param air_density:
        Air density [kg/m3].
    :type air_density: float

    :param aerodynamic_drag_coefficient:
        Aerodynamic drag coefficient [-].
    :type aerodynamic_drag_coefficient: float

    :param frontal_area:
        Frontal area of the vehicle [m2].
    :type frontal_area: float
    
    :param has_roof_box:
         Has the vehicle a roof box? [-].
    :type has_roof_box: bool

    :return:
        As used in the dyno and defined by respective guidelines [N/(km/h)^2].
    :rtype: float
    """

    c = aerodynamic_drag_coefficient * frontal_area * air_density

    if has_roof_box:
        c *= dfl.functions.calculate_f2.roof_box

    return 0.5 * c / 3.6 ** 2


def calculate_raw_frontal_area_v1(vehicle_mass, vehicle_category):
    """
    Calculates raw frontal area of the vehicle [m2].

    :param vehicle_mass:
        Vehicle mass [kg].
    :type vehicle_mass: float 

    :param vehicle_category: 
        Vehicle category (i.e., A, B, C, D, E, F, S, M, and J).
    :type vehicle_category: str

    :return:
        Raw frontal area of the vehicle [m2].
    :rtype: float
    """
    d = dfl.functions.calculate_raw_frontal_area_v1
    return eval(d.formulas[vehicle_category.upper()])(vehicle_mass)


def calculate_raw_frontal_area(vehicle_height, vehicle_width):
    """
    Calculates raw frontal area of the vehicle [m2].

    :param vehicle_height:
        Vehicle height [m].
    :type vehicle_height: float 

    :param vehicle_width: 
        Vehicle width [m].
    :type vehicle_width: float

    :return:
        Raw frontal area of the vehicle [m2].
    :rtype: float
    """
    return vehicle_height * vehicle_width


def calculate_frontal_area(raw_frontal_area):
    """
    Calculates the vehicle frontal area [m2].

    :param raw_frontal_area:
        Raw frontal area of the vehicle [m2].
    :type raw_frontal_area: float 

    :return:
        Frontal area of the vehicle [m2].
    :rtype: float
    """
    d = dfl.functions.calculate_frontal_area.projection_factor
    return raw_frontal_area * d


def calculate_aerodynamic_drag_coefficient_v1(vehicle_body):
    """
    Calculates the aerodynamic drag coefficient [-].

    :param vehicle_body: 
        Vehicle body (i.e., cabriolet, sedan, hatchback, stationwagon,
        suv/crossover, mpv, coupé, bus, bestelwagen, pick-up).
    :type vehicle_body: str

    :return: 
        Aerodynamic drag coefficient [-].
    :rtype: float
    """
    d = dfl.functions.calculate_aerodynamic_drag_coefficient_v1
    return d.cw[vehicle_body.lower()]


def calculate_aerodynamic_drag_coefficient(vehicle_category):
    """
    Calculates the aerodynamic drag coefficient [-].

    :param vehicle_category: 
        Vehicle category (i.e., A, B, C, D, E, F, S, M, and J).
    :type vehicle_category: str

    :return: 
        Aerodynamic drag coefficient [-].
    :rtype: float
    """
    d = dfl.functions.calculate_aerodynamic_drag_coefficient
    return d.cw[vehicle_category.upper()]


def calculate_rolling_resistance_coeff(tyre_class, tyre_category):
    """
    Calculates the rolling resistance coefficient [-].

    :param tyre_class: 
        Tyre class (i.e., C1, C2, and C3).
    :type tyre_class: str

    :param tyre_category: 
        Tyre category (i.e., A, B, C, D, E, F, and G).
    :type tyre_category: str

    :return: 
        Rolling resistance coefficient [-].
    :rtype: float
    """
    coeff = dfl.functions.calculate_rolling_resistance_coeff.coeff
    return coeff[tyre_class.upper()][tyre_category.upper()]


def calculate_f1(f2):
    """
    Calculates the f1 road load [N/(km/h)].

    :param f2:
        As used in the dyno and defined by respective guidelines [N/(km/h)^2].
    :type f2: float

    :return: 
        Defined by dyno procedure [N/(km/h)].
    :rtype: float
    """

    q, m = dfl.functions.calculate_f1.qm
    return m * f2 + q


def calculate_angle_slopes(times, angle_slope):
    """
    Returns the angle slope vector [rad].

    :param times:
        Time vector [s].
    :type times: numpy.array

    :param angle_slope:
         Angle slope [rad].
    :type angle_slope: float

    :return:
        Angle slope vector [rad].
    :rtype: numpy.array
    """

    return np.ones_like(times, dtype=float) * angle_slope


def calculate_rolling_resistance(f0, angle_slopes):
    """
    Calculates rolling resistance [N].

    :param f0:
        Rolling resistance force [N] when angle_slope == 0.
    :type f0: float

    :param angle_slopes:
        Angle slope vector [rad].
    :type angle_slopes: numpy.array

    :return:
        Rolling resistance force [N].
    :rtype: numpy.array
    """

    return f0 * np.cos(angle_slopes)


def calculate_f0(vehicle_mass, rolling_resistance_coeff):
    """
    Calculates rolling resistance [N].

    :param vehicle_mass:
        Vehicle mass [kg].
    :type vehicle_mass: float

    :param rolling_resistance_coeff:
        Rolling resistance coefficient [-].
    :type rolling_resistance_coeff: float

    :return:
        Rolling resistance force [N] when angle_slope == 0.
    :rtype: float
    """

    return vehicle_mass * 9.81 * rolling_resistance_coeff


def calculate_velocity_resistances(f1, velocities):
    """
    Calculates forces function of velocity [N].

    :param f1:
        Defined by dyno procedure [N/(km/h)].
    :type f1: float

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array | float

    :return:
        Forces function of velocity [N].
    :rtype: numpy.array | float
    """

    return f1 * velocities


def calculate_climbing_force(vehicle_mass, angle_slopes):
    """
    Calculates the vehicle climbing resistance [N].

    :param vehicle_mass:
        Vehicle mass [kg].
    :type vehicle_mass: float

    :param angle_slopes:
        Angle slope vector [rad].
    :type angle_slopes: numpy.array

    :return:
        Vehicle climbing resistance [N].
    :rtype: numpy.array
    """

    return vehicle_mass * 9.81 * np.sin(angle_slopes)


def calculate_rotational_inertia_forces(
        vehicle_mass, inertial_factor, accelerations):
    """
    Calculate rotational inertia forces [N].

    :param vehicle_mass:
        Vehicle mass [kg].
    :type vehicle_mass: float

    :param inertial_factor:
        Factor that considers the rotational inertia [%].
    :type inertial_factor: float

    :param accelerations:
        Acceleration vector [m/s2].
    :type accelerations: numpy.array | float

    :return:
        Rotational inertia forces [N].
    :rtype: numpy.array | float
    """

    return vehicle_mass * inertial_factor * accelerations / 100


def select_default_n_dyno_axes(cycle_type):
    """
    Selects the default number of dyno axes[-].

    :param cycle_type:
        Cycle type (WLTP or NEDC).
    :type cycle_type: str

    :return:
        Number of dyno axes [-].
    :rtype: int
    """
    par = dfl.functions.select_default_n_dyno_axes
    return par.DYNO_AXES.get(cycle_type.upper(), 2)


def select_inertial_factor(n_dyno_axes):
    """
    Selects the inertia factor [%] according to the number of dyno axes.

    :param n_dyno_axes:
        Number of dyno axes [-].
    :type n_dyno_axes: int

    :return:
        Factor that considers the rotational inertia [%].
    :rtype: float
    """

    return 1.5 * n_dyno_axes


# noinspection PyPep8Naming
def calculate_motive_forces(
        vehicle_mass, accelerations, climbing_force, aerodynamic_resistances,
        rolling_resistance, velocity_resistances, rotational_inertia_forces):
    """
    Calculate motive forces [N].

    :param vehicle_mass:
        Vehicle mass [kg].
    :type vehicle_mass: float

    :param accelerations:
        Acceleration vector [m/s2].
    :type accelerations: numpy.array | float

    :param climbing_force:
        Vehicle climbing resistance [N].
    :type climbing_force: float | numpy.array

    :param rolling_resistance:
        Rolling resistance force [N].
    :type rolling_resistance: float | numpy.array

    :param aerodynamic_resistances:
        Aerodynamic resistance vector [N].
    :type aerodynamic_resistances: numpy.array | float

    :param velocity_resistances:
        Forces function of velocity [N].
    :type velocity_resistances: numpy.array | float

    :param rotational_inertia_forces:
        Rotational inertia forces [N].
    :type rotational_inertia_forces: numpy.array | float

    :return:
        Motive forces [N].
    :rtype: numpy.array | float
    """

    # namespace shortcuts
    Frr = rolling_resistance
    Faero = aerodynamic_resistances
    Fclimb = climbing_force
    Fvel = velocity_resistances
    Finertia = rotational_inertia_forces

    return vehicle_mass * accelerations + Fclimb + Frr + Faero + Fvel + Finertia


def calculate_motive_powers(motive_forces, velocities):
    """
    Calculates motive power [kW].

    :param motive_forces:
        Motive forces [N].
    :type motive_forces: numpy.array | float

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array | float

    :return:
        Motive power [kW].
    :rtype: numpy.array | float
    """

    return motive_forces * velocities / 3600


def apply_f0_correction(f0_uncorrected, correct_f0):
    """
    Corrects the rolling resistance force [N] if a different preconditioning
    cycle was used for WLTP (WLTP precon) and NEDC (NEDC precon).

    :param f0_uncorrected:
        Uncorrected rolling resistance force [N] when angle_slope == 0.
    :type f0_uncorrected: float

    :param correct_f0:
        A different preconditioning cycle was used for WLTP and NEDC?
    :type correct_f0: bool

    :return:
        Rolling resistance force [N] when angle_slope == 0.
    :rtype: float
    """

    if correct_f0:
        return f0_uncorrected - 6.0
    return f0_uncorrected


def vehicle():
    """
    Defines the vehicle model.

    .. dispatcher:: d

        >>> d = vehicle()

    :return:
        The vehicle model.
    :rtype: schedula.Dispatcher
    """

    d = sh.Dispatcher(
        name='Vehicle free body diagram',
        description='Calculates forces and power acting on the vehicle.'
    )

    d.add_function(
        function=calculate_velocities,
        inputs=['times', 'obd_velocities'],
        outputs=['velocities']
    )

    d.add_function(
        function=calculate_accelerations,
        inputs=['times', 'velocities'],
        outputs=['accelerations']
    )

    d.add_function(
        function=calculate_aerodynamic_resistances,
        inputs=['f2', 'velocities'],
        outputs=['aerodynamic_resistances']
    )

    d.add_function(
        function=calculate_raw_frontal_area,
        inputs=['vehicle_height', 'vehicle_width'],
        outputs=['raw_frontal_area']
    )

    d.add_function(
        function=calculate_raw_frontal_area_v1,
        inputs=['vehicle_mass', 'vehicle_category'],
        outputs=['raw_frontal_area'],
        weight=5
    )

    d.add_function(
        function=calculate_frontal_area,
        inputs=['raw_frontal_area'],
        outputs=['frontal_area']
    )

    d.add_function(
        function=calculate_aerodynamic_drag_coefficient_v1,
        inputs=['vehicle_body'],
        outputs=['aerodynamic_drag_coefficient']
    )

    d.add_function(
        function=calculate_aerodynamic_drag_coefficient,
        inputs=['vehicle_category'],
        outputs=['aerodynamic_drag_coefficient']
    )

    d.add_data(
        data_id='air_density',
        default_value=dfl.values.air_density,
    )

    d.add_data(
        data_id='has_roof_box',
        default_value=dfl.values.has_roof_box,
    )

    d.add_function(
        function=calculate_f2,
        inputs=['air_density', 'aerodynamic_drag_coefficient', 'frontal_area',
                'has_roof_box'],
        outputs=['f2'],
        weight=5
    )

    d.add_data(
        data_id='tyre_class',
        default_value=dfl.values.tyre_class
    )

    d.add_function(
        function=calculate_rolling_resistance_coeff,
        inputs=['tyre_class', 'tyre_category'],
        outputs=['rolling_resistance_coeff']
    )

    d.add_function(
        function=calculate_f0,
        inputs=['vehicle_mass', 'rolling_resistance_coeff'],
        outputs=['f0'],
        weight=5
    )

    d.add_function(
        function=calculate_f1,
        inputs=['f2'],
        outputs=['f1'],
        weight=5
    )

    d.add_data(
        data_id='angle_slope',
        default_value=dfl.values.angle_slope,
    )

    d.add_function(
        function=calculate_angle_slopes,
        inputs=['times', 'angle_slope'],
        outputs=['angle_slopes']
    )

    d.add_function(
        function=calculate_rolling_resistance,
        inputs=['f0', 'angle_slopes'],
        outputs=['rolling_resistance']
    )

    d.add_function(
        function=calculate_velocity_resistances,
        inputs=['f1', 'velocities'],
        outputs=['velocity_resistances']
    )

    d.add_function(
        function=calculate_climbing_force,
        inputs=['vehicle_mass', 'angle_slopes'],
        outputs=['climbing_force']
    )

    d.add_function(
        function=select_default_n_dyno_axes,
        inputs=['cycle_type'],
        outputs=['n_dyno_axes']
    )

    d.add_function(
        function=select_inertial_factor,
        inputs=['n_dyno_axes'],
        outputs=['inertial_factor']
    )

    d.add_function(
        function=calculate_rotational_inertia_forces,
        inputs=['vehicle_mass', 'inertial_factor', 'accelerations'],
        outputs=['rotational_inertia_forces']
    )

    d.add_function(
        function=calculate_motive_forces,
        inputs=['vehicle_mass', 'accelerations', 'climbing_force',
                'aerodynamic_resistances', 'rolling_resistance',
                'velocity_resistances', 'rotational_inertia_forces'],
        outputs=['motive_forces']
    )

    d.add_function(
        function=calculate_motive_powers,
        inputs=['motive_forces', 'velocities'],
        outputs=['motive_powers']
    )

    d.add_function(
        function_id='grouping',
        function=sh.bypass,
        inputs=['f0', 'f1', 'f2'],
        outputs=['road_loads']
    )

    d.add_data(
        data_id='road_loads',
        description='Cycle road loads [N, N/(km/h), N/(km/h)^2].'
    )

    d.add_function(
        function_id='splitting',
        function=sh.bypass,
        inputs=['road_loads'],
        outputs=['f0', 'f1', 'f2']
    )

    d.add_data(
        data_id='correct_f0',
        default_value=dfl.values.correct_f0
    )

    d.add_function(
        function=apply_f0_correction,
        inputs=['f0_uncorrected', 'correct_f0'],
        outputs=['f0']
    )

    return d
