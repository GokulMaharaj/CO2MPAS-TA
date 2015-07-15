#-*- coding: utf-8 -*-
#
# Copyright 2015 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""
It provides a final drive model.

The model is defined by a Dispatcher that wraps all the functions needed.
"""

__author__ = 'Vincenzo_Arcidiacono'

from compas.dispatcher import Dispatcher
from compas.functions.physical.final_drive import *


def final_drive():
    """
    Define the final drive model.

    .. dispatcher:: dsp

        >>> dsp = final_drive()

    :return:
        The final drive model.
    :rtype: Dispatcher
    """

    final_drive = Dispatcher(
        name='Final drive',
        description='Models the final drive.'
    )

    final_drive.add_data(
        data_id='final_drive_ratio',
        default_value=1.0
    )

    final_drive.add_function(
        function=calculate_final_drive_speeds_in,
        inputs=['final_drive_speeds_out', 'final_drive_ratio'],
        outputs=['final_drive_speeds_in']
    )

    final_drive.add_data(
        data_id='final_drive_efficiency',
        default_value=1.0
    )

    final_drive.add_function(
        function=calculate_final_drive_powers_in,
        inputs=['final_drive_powers_out', 'final_drive_efficiency'],
        outputs=['final_drive_powers_in']
    )

    final_drive.add_data(
        data_id='final_drive_torque_loss',
        default_value=0.0
    )

    final_drive.add_function(
        function=calculate_final_drive_torques_in,
        inputs=['final_drive_torques_out', 'final_drive_ratio',
                'final_drive_torque_loss'],
        outputs=['final_drive_torques_in']
    )

    final_drive.add_function(
        function=calculate_final_drive_torques_in_v1,
        inputs=['final_drive_torques_out', 'final_drive_efficiency', 'final_drive_ratio'],
        outputs=['final_drive_torques_in'],
        weight=10
    )

    return final_drive
