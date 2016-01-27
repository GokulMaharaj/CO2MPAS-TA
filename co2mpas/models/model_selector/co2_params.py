# -*- coding: utf-8 -*-
#
# Copyright 2015 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

"""
It provides a model to select co2_params.

The model is defined by a Dispatcher that wraps all the functions needed.
"""


from co2mpas.dispatcher import Dispatcher
from co2mpas.functions.model_selector import *
from co2mpas.functions.model_selector.co2_params import *
from functools import partial
import co2mpas.dispatcher.utils as dsp_utl
from ..model_selector import model_errors
from itertools import chain


def co2_params_model_selector(
        name, data_in, data_out, setting, hide_warn_msgbox=False):
    """
    Defines the co2_params model selector.

    .. dispatcher:: dsp
        >>> from co2mpas.functions.model_selector import sub_models
        >>> setting = sub_models()['co2_params']
        >>> dsp_name, ids = 'co2_params', ('WLTP-H', 'WLTP-L')
        >>> dsp = co2_params_model_selector(dsp_name, ids, ids, setting)

    :param name:

    :return:
        The co2_params model selector.
    :rtype: Dispatcher
    """

    dsp = Dispatcher(
        name='%s selector' % name,
        description='Select the calibrated models.',
    )

    errors = []

    _sort_models = setting.pop('sort_models', sort_models)

    if 'weights' in setting:
        _weights = dsp_utl.map_list(setting['targets'], *setting.pop('weights'))
    else:
        _weights = None

    _get_best_model = partial(setting.pop('get_best_model', get_best_model),
                              models_wo_err=setting.pop('models_wo_err', None),
                              hide_warn_msgbox=hide_warn_msgbox,
                              selector_id=dsp.name)

    for i in chain(data_in, ['ALL']):
        e = 'error/%s' % i

        errors.append(e)

        dsp.add_function(
            function=model_errors(name, i, data_out, setting),
            inputs=[i] + [k for k in data_out if k != i],
            outputs=[e]
        )

    dsp.add_function(
        function=partial(_sort_models, weights=_weights),
        inputs=errors[:-1],
        outputs=['rank<0>']
    )

    dsp.add_function(
        function=partial(calibrate_co2_params_ALL, data_id=data_in),
        inputs=['rank<0>'] + errors[:-1],
        outputs=['ALL']
    )

    dsp.add_function(
        function=partial(co2_sort_models, weights=_weights),
        inputs=['rank<0>'] + [errors[-1]],
        outputs=['rank']
    )

    dsp.add_function(
        function=partial(_get_best_model, hide_warn_msgbox=hide_warn_msgbox),
        inputs=['rank'],
        outputs=['model', 'errors']
    )

    return dsp_utl.SubDispatch(dsp, outputs=['model', 'errors'],
                               output_type='list')
