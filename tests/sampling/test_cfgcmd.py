#! python
# -*- coding: UTF-8 -*-
#
# Copyright 2015-2017 European Commission (JRC);
# Licensed under the EUPL (the 'Licence');
# You may not use this work except in compliance with the Licence.
# You may obtain a copy of the Licence at: http://ec.europa.eu/idabc/eupl

from co2mpas.__main__ import init_logging
import logging
import os
import subprocess as sbp
import unittest

import ddt

import os.path as osp

init_logging(level=logging.DEBUG)

log = logging.getLogger(__name__)

mydir = osp.dirname(__file__)


@ddt.ddt
class TcfgcmdShell(unittest.TestCase):
    def test_paths_smoketest(self):
        ret = sbp.check_call('co2dice config paths', env=os.environ)
        self.assertEqual(ret, 0)

    def test_show_smoketest(self):
        ret = sbp.check_call('co2dice config show', env=os.environ)
        self.assertEqual(ret, 0)

    def test_desc_smoketest(self):
        ret = sbp.check_call('co2dice config desc', env=os.environ)
        self.assertEqual(ret, 0)

        ret = sbp.check_call('co2dice config desc TstampReceiver', env=os.environ)
        self.assertEqual(ret, 0)
