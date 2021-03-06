# -*- coding: utf-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""
It contains functions that model the basic mechanics of the gear box.
"""

import functools
import math
import scipy.interpolate as sci_itp
import scipy.optimize as sci_opt
import scipy.stats as sci_sta
import sklearn.cluster as sk_clu
import schedula as sh
import co2mpas.utils as co2_utl
import numpy as np
import co2mpas.model.physical.defaults as defaults


def _identify_gear(idle, vsr, stop_vel, plateau_acc, ratio, vel, acc):
    """
    Identifies a gear [-].

    :param idle:
        Engine speed idle median and median + std [RPM].
    :type idle: (float, float)

    :param vsr:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :type vsr: iterable

    :param stop_vel:
        Maximum velocity to consider the vehicle stopped [km/h].
    :type stop_vel: float

    :param plateau_acc:
        Maximum acceleration to be at constant velocity [m/s2].
    :type plateau_acc: float

    :param ratio:
        Vehicle velocity speed ratio [km/(h*RPM)].
    :type ratio: float

    :param vel:
        Vehicle velocity [km/h].
    :type vel: float

    :param acc:
        Vehicle acceleration [m/s2].
    :type acc: float

    :return:
        A gear [-].
    :rtype: int
    """

    if vel <= stop_vel:
        return 0

    m, (gear, vs) = min((abs(v - ratio), (k, v)) for k, v in vsr)

    if acc < 0 and (vel <= idle[0] * vs or abs(vel / idle[1] - ratio) < m):
        return 0

    if gear == 0 and ((vel > stop_vel and acc > 0) or acc > plateau_acc):
        return 1

    return gear


def identify_gears(
        times, velocities, accelerations, engine_speeds_out,
        velocity_speed_ratios, stop_velocity, plateau_acceleration,
        change_gear_window_width, idle_engine_speed):
    """
    Identifies gear time series [-].

    :param times:
        Time vector [s].
    :type times: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :param accelerations:
        Acceleration vector [m/s2].
    :type accelerations: numpy.array

    :param engine_speeds_out:
        Engine speed [RPM].
    :type engine_speeds_out: numpy.array

    :param velocity_speed_ratios:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :type velocity_speed_ratios: dict

    :param stop_velocity:
        Maximum velocity to consider the vehicle stopped [km/h].
    :type stop_velocity: float

    :param plateau_acceleration:
        Maximum acceleration to be at constant velocity [m/s2].
    :type plateau_acceleration: float

    :param change_gear_window_width:
        Time window used to apply gear change filters [s].
    :type change_gear_window_width: float

    :param idle_engine_speed:
        Engine speed idle median and std [RPM].
    :type idle_engine_speed: (float, float)

    :return:
        Gear vector identified [-].
    :rtype: numpy.array
    """

    vsr = [v for v in velocity_speed_ratios.items() if v[0] != 0]

    ratios = velocities / engine_speeds_out

    idle_speed = (idle_engine_speed[0] - idle_engine_speed[1],
                  idle_engine_speed[0] + idle_engine_speed[1])

    ratios[engine_speeds_out < idle_speed[0]] = 0

    id_gear = functools.partial(_identify_gear, idle_speed, vsr, stop_velocity,
                                plateau_acceleration)

    gear = list(map(id_gear, *(ratios, velocities, accelerations)))

    gear = co2_utl.median_filter(times, gear, change_gear_window_width)

    gear = _correct_gear_shifts(times, ratios, gear, velocity_speed_ratios)

    gear = co2_utl.clear_fluctuations(times, gear, change_gear_window_width)

    return gear


def _correct_gear_shifts(
        times, ratios, gears, velocity_speed_ratios, shift_window=4.0):
    from . import calculate_gear_shifts
    shifts = calculate_gear_shifts(gears)
    vsr = np.vectorize(lambda v: velocity_speed_ratios.get(v, 0))
    s = len(gears)

    def err(v, r):
        v = int(v)
        return np.float32(np.mean(np.abs(ratios[slice(v - 1, v + 1, 1)] - r)))

    k = 0
    new_gears = np.zeros_like(gears)
    dt = shift_window / 2
    for i in np.arange(s)[shifts]:
        g = gears[slice(i - 1, i + 1, 1)]
        if g[0] != 0 and g[-1] != 0:
            t = times[i]
            n = max(i - sum(((t - dt) <= times) & (times <= t)), k)
            m = min(i + sum((t <= times) & (times <= (t + dt))), s)
            j = int(sci_opt.brute(err, (slice(n, m, 1),), args=(vsr(g),),
                                  finish=None))
        else:
            j = int(i)

        x = slice(j - 1, j + 1, 1)
        new_gears[x] = g
        new_gears[k:x.start] = g[0]
        k = x.stop

    new_gears[k:] = new_gears[k - 1]

    return new_gears


def _speed_shift(times, speeds):
    speeds = sci_itp.InterpolatedUnivariateSpline(times, speeds, k=1)

    def shift(dt):
        return speeds(times + dt)

    return shift


# not used
def calculate_gear_box_speeds_from_engine_speeds(
        times, velocities, engine_speeds_out, velocity_speed_ratios,
        shift_window=6.0):
    """
    Calculates the gear box speeds applying a constant time shift [RPM, s].

    :param times:
        Time vector [s].
    :type times: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :param engine_speeds_out:
        Engine speed vector [RPM].
    :type engine_speeds_out: numpy.array

    :param velocity_speed_ratios:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :type velocity_speed_ratios: dict

    :param shift_window:
        Maximum dt shift [s].
    :type shift_window: float

    :return:
        - Gear box speed vector [RPM].
        - time shift of engine speeds [s].
    :rtype: (numpy.array, float)
    """

    bins = [-defaults.dfl.INF, 0]
    bins.extend([v for k, v in sorted(velocity_speed_ratios.items()) if k != 0])
    bins.append(defaults.dfl.INF)
    bins = bins[:-1] + np.diff(bins) / 2
    bins[0] = 0

    speeds = _speed_shift(times, engine_speeds_out)

    # noinspection PyUnresolvedReferences
    def error_fun(x):
        s = speeds(x)

        b = s > 0
        ratio = velocities[b] / s[b]

        std = sci_sta.binned_statistic(ratio, ratio, np.std, bins)[0]
        w = sci_sta.binned_statistic(ratio, ratio, 'count', bins)[0]

        return np.float32(sum(std * w))

    dt = shift_window / 2
    shift = sci_opt.brute(error_fun, ranges=(slice(-dt, dt, 0.1),))

    gear_box_speeds = speeds(*shift)
    gear_box_speeds[gear_box_speeds < 0] = 0

    return gear_box_speeds, tuple(shift)


def calculate_gear_box_speeds_in(
        gears, velocities, velocity_speed_ratios, stop_velocity):
    """
    Calculates Gear box speed vector [RPM].

    :param gears:
        Gear vector [-].
    :type gears: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :param velocity_speed_ratios:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :type velocity_speed_ratios: dict

    :param stop_velocity:
        Maximum velocity to consider the vehicle stopped [km/h].
    :type stop_velocity: float

    :return:
        Gear box speed vector [RPM].
    :rtype: numpy.array
    """

    speeds = np.array(velocities, dtype=float, copy=True)
    n = velocities >= stop_velocity
    b = ~n
    for k, r in velocity_speed_ratios.items():
        if r:
            speeds[n & (gears == k)] /= r
        else:
            b |= gears == k

    speeds[b] = 0.0
    return speeds


def calculate_gear_box_speeds_in_v1(
        gears, gear_box_speeds_out, gear_box_ratios):
    """
    Calculates Gear box speed vector [RPM].

    :param gears:
        Gear vector [-].
    :type gears: numpy.array

    :param gear_box_speeds_out:
        Wheel speed vector [RPM].
    :type gear_box_speeds_out: numpy.array

    :param gear_box_ratios:
        Gear box ratios [-].
    :type gear_box_ratios: dict

    :return:
        Gear box speed vector [RPM].
    :rtype: numpy.array
    """

    d = {0: 0.0}

    d.update(gear_box_ratios)

    ratios = np.vectorize(d.get)(gears)

    return gear_box_speeds_out * ratios


def identify_n_gears(gear_box_ratios):
    """
    Identify the number of gears [-].

    :param gear_box_ratios:
        Gear box ratios [-].
    :type gear_box_ratios: dict

    :return:
        Number of gears [-].
    :rtype: int
    """
    return len([k for k in gear_box_ratios if k > 0])


def identify_velocity_speed_ratios(
        n_gears, gear_box_speeds_in, velocities, idle_engine_speed,
        stop_velocity):
    """
    Identifies velocity speed ratios from gear box speed vector [km/(h*RPM)].

    :param n_gears:
        Number of gears [-].
    :type n_gears: int

    :param gear_box_speeds_in:
        Gear box speed vector [RPM].
    :type gear_box_speeds_in: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :param idle_engine_speed:
        Engine speed idle median and std [RPM].
    :type idle_engine_speed: (float, float)

    :param stop_velocity:
        Maximum velocity to consider the vehicle stopped [km/h].
    :type stop_velocity: float

    :return:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :rtype: dict
    """

    idle_speed = idle_engine_speed[0] + idle_engine_speed[1]

    b = (gear_box_speeds_in > idle_speed) & (velocities > stop_velocity)
    x = (velocities[b] / gear_box_speeds_in[b])[:, None]

    ms = sk_clu.KMeans(n_clusters=int(n_gears), copy_x=False, random_state=0)
    ms.fit(x)

    vsr = {k + 1: v for k, v in enumerate(sorted(ms.cluster_centers_[:, 0]))}

    vsr[0] = 0.0

    return vsr


def identify_velocity_speed_ratios_v1(
        gear_box_speeds_in, velocities, idle_engine_speed, stop_velocity):
    """
    Identifies velocity speed ratios from gear box speed vector [km/(h*RPM)].

    :param gear_box_speeds_in:
        Gear box speed vector [RPM].
    :type gear_box_speeds_in: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :param idle_engine_speed:
        Engine speed idle median and std [RPM].
    :type idle_engine_speed: (float, float)

    :param stop_velocity:
        Maximum velocity to consider the vehicle stopped [km/h].
    :type stop_velocity: float

    :return:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :rtype: dict
    """

    idle_speed = idle_engine_speed[0] + idle_engine_speed[1]

    b = (gear_box_speeds_in > idle_speed) & (velocities > stop_velocity)
    x = (velocities[b] / gear_box_speeds_in[b])[:, None]

    bandwidth = sk_clu.estimate_bandwidth(x, quantile=0.2)
    ms = sk_clu.MeanShift(bandwidth=bandwidth, bin_seeding=True)
    ms.fit(x)

    vsr = {k + 1: v for k, v in enumerate(sorted(ms.cluster_centers_[:, 0]))}

    vsr[0] = 0.0

    return vsr


def identify_speed_velocity_ratios(
        gears, velocities, gear_box_speeds_in, stop_velocity):
    """
    Identifies speed velocity ratios from gear vector [h*RPM/km].

    :param gears:
        Gear vector [-].
    :type gears: numpy.array

    :param velocities:
        Velocity vector [km/h].
    :type velocities: numpy.array

    :param gear_box_speeds_in:
        Gear box speed vector [RPM].
    :type gear_box_speeds_in: numpy.array

    :param stop_velocity:
        Maximum velocity to consider the vehicle stopped [km/h].
    :type stop_velocity: float

    :return:
        Speed velocity ratios of the gear box [h*RPM/km].
    :rtype: dict
    """

    ratios = gear_box_speeds_in / velocities

    ratios[velocities < stop_velocity] = 0

    svr = {k: co2_utl.reject_outliers(ratios[gears == k])[0]
           for k in range(1, int(max(gears)) + 1)
           if k in gears}
    svr[0] = defaults.dfl.INF

    return svr


def calculate_gear_box_ratios(
        velocity_speed_ratios, final_drive_ratios, r_dynamic):
    """
    Calculates gear box ratios [-].

    :param velocity_speed_ratios:
        Constant velocity speed ratios of the gear box [km/(h*RPM)].
    :type velocity_speed_ratios: dict

    :param final_drive_ratios:
        Final drive ratios [-].
    :type final_drive_ratios: dict

    :param r_dynamic:
        Dynamic radius of the wheels [m].
    :type r_dynamic: float

    :return:
        Gear box ratios [-].
    :rtype: dict
    """

    c = 30 / (3.6 * math.pi * r_dynamic)

    r = calculate_velocity_speed_ratios(velocity_speed_ratios)

    return {k: v / (c * final_drive_ratios[k]) for k, v in r.items() if k != 0}


def calculate_speed_velocity_ratios(
        gear_box_ratios, final_drive_ratios, r_dynamic):
    """
    Calculates speed velocity ratios of the gear box [h*RPM/km].

    :param gear_box_ratios:
        Gear box ratios [-].
    :type gear_box_ratios: dict

    :param final_drive_ratios:
        Final drive ratios [-].
    :type final_drive_ratios: dict

    :param r_dynamic:
        Dynamic radius of the wheels [m].
    :type r_dynamic: float

    :return:
        Speed velocity ratios of the gear box [h*RPM/km].
    :rtype: dict
    """

    c = 30 / (3.6 * math.pi * r_dynamic)

    svr = {k: c * v * final_drive_ratios[k] for k, v in gear_box_ratios.items()}

    svr[0] = defaults.dfl.INF

    return svr


def calculate_velocity_speed_ratios(speed_velocity_ratios):
    """
    Calculates velocity speed (or speed velocity) ratios of the gear box
    [km/(h*RPM) or h*RPM/km].

    :param speed_velocity_ratios:
        Constant speed velocity (or velocity speed) ratios of the gear box
        [h*RPM/km or km/(h*RPM)].
    :type speed_velocity_ratios: dict

    :return:
        Constant velocity speed (or speed velocity) ratios of the gear box
        [km/(h*RPM) or h*RPM/km].
    :rtype: dict
    """

    def inverse(v):
        if v <= 0:
            return defaults.dfl.INF
        elif v >= defaults.dfl.INF:
            return 0.0
        else:
            return 1 / v

    return {k: inverse(v) for k, v in speed_velocity_ratios.items()}


def identify_max_gear(speed_velocity_ratios):
    """
    Identifies the maximum gear of the gear box [-].

    :param speed_velocity_ratios:
        Speed velocity ratios of the gear box [h*RPM/km].
    :type speed_velocity_ratios: dict

    :return:
        Maximum gear of the gear box [-].
    :rtype: int
    """

    return int(max(speed_velocity_ratios))


def mechanical():
    """
    Defines the mechanical gear box model.

    .. dispatcher:: d

        >>> d = mechanical()

    :return:
        The gear box mechanical model.
    :rtype: schedula.Dispatcher
    """

    d = sh.Dispatcher(
        name='mechanical model',
        description='Models the gear box mechanical.'
    )

    d.add_data(
        data_id='stop_velocity',
        default_value=defaults.dfl.values.stop_velocity
    )

    d.add_data(
        data_id='plateau_acceleration',
        default_value=defaults.dfl.values.plateau_acceleration
    )

    d.add_data(
        data_id='change_gear_window_width',
        default_value=defaults.dfl.values.change_gear_window_width
    )

    d.add_function(
        function=identify_gears,
        inputs=['times', 'velocities', 'accelerations', 'engine_speeds_out',
                'velocity_speed_ratios', 'stop_velocity',
                'plateau_acceleration', 'change_gear_window_width',
                'idle_engine_speed'],
        outputs=['gears']
    )

    d.add_function(
        function=calculate_gear_box_speeds_in,
        inputs=['gears', 'velocities', 'velocity_speed_ratios',
                'stop_velocity'],
        outputs=['gear_box_speeds_in'],
        weight=25
    )

    d.add_function(
        function=calculate_gear_box_speeds_in_v1,
        inputs=['gears', 'gear_box_speeds_out', 'gear_box_ratios'],
        outputs=['gear_box_speeds_in']
    )

    d.add_function(
        function=calculate_speed_velocity_ratios,
        inputs=['gear_box_ratios', 'final_drive_ratios', 'r_dynamic'],
        outputs=['speed_velocity_ratios']
    )

    d.add_function(
        function=identify_speed_velocity_ratios,
        inputs=['gears', 'velocities', 'gear_box_speeds_in', 'stop_velocity'],
        outputs=['speed_velocity_ratios'],
        weight=5
    )

    d.add_function(
        function=identify_speed_velocity_ratios,
        inputs=['gears', 'velocities', 'engine_speeds_out', 'stop_velocity'],
        outputs=['speed_velocity_ratios'],
        weight=10
    )

    d.add_function(
        function=calculate_velocity_speed_ratios,
        inputs=['speed_velocity_ratios'],
        outputs=['velocity_speed_ratios']
    )

    d.add_function(
        function=identify_n_gears,
        inputs=['gear_box_ratios'],
        outputs=['n_gears']
    )

    d.add_function(
        function=identify_velocity_speed_ratios,
        inputs=['n_gears', 'engine_speeds_out', 'velocities',
                'idle_engine_speed', 'stop_velocity'],
        outputs=['velocity_speed_ratios'],
        weight=49
    )

    d.add_function(
        function=identify_velocity_speed_ratios_v1,
        inputs=['engine_speeds_out', 'velocities', 'idle_engine_speed',
                'stop_velocity'],
        outputs=['velocity_speed_ratios'],
        weight=50
    )

    d.add_function(
        function=calculate_gear_box_ratios,
        inputs=['velocity_speed_ratios', 'final_drive_ratios', 'r_dynamic'],
        outputs=['gear_box_ratios']
    )

    d.add_function(
        function=identify_max_gear,
        inputs=['speed_velocity_ratios'],
        outputs=['max_gear']
    )

    return d
