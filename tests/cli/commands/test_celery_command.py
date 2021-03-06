#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import importlib
import unittest
from argparse import Namespace

import mock
import pytest
import sqlalchemy

import airflow
from airflow.bin import cli
from airflow.cli.commands import celery_command
from tests.test_utils.config import conf_vars

mock.patch('airflow.utils.cli.action_logging', lambda x: x).start()
mock_args = Namespace(queues=1, concurrency=1)


class TestWorkerPrecheck(unittest.TestCase):
    @mock.patch('airflow.settings.validate_session')
    def test_error(self, mock_validate_session):
        """
        Test to verify the exit mechanism of airflow-worker cli
        by mocking validate_session method
        """
        mock_validate_session.return_value = False
        with self.assertRaises(SystemExit) as cm:
            # airflow.bin.cli.worker(mock_args)
            celery_command.worker(mock_args)
        self.assertEqual(cm.exception.code, 1)

    @conf_vars({('core', 'worker_precheck'): 'False'})
    def test_worker_precheck_exception(self):
        """
        Test to check the behaviour of validate_session method
        when worker_precheck is absent in airflow configuration
        """
        self.assertTrue(airflow.settings.validate_session())

    @mock.patch('sqlalchemy.orm.session.Session.execute')
    @conf_vars({('core', 'worker_precheck'): 'True'})
    def test_validate_session_dbapi_exception(self, mock_session):
        """
        Test to validate connection failure scenario on SELECT 1 query
        """
        mock_session.side_effect = sqlalchemy.exc.OperationalError("m1", "m2", "m3", "m4")
        self.assertEqual(airflow.settings.validate_session(), False)


@pytest.mark.integration("redis")
@pytest.mark.integration("rabbitmq")
class TestWorkerServeLogs(unittest.TestCase):

    @classmethod
    @conf_vars({("core", "executor"): "CeleryExecutor"})
    def setUpClass(cls):
        importlib.reload(cli)
        cls.parser = cli.CLIFactory.get_parser()

    def tearDown(self):
        importlib.reload(cli)

    def test_serve_logs_on_worker_start(self):
        with mock.patch('airflow.cli.commands.celery_command.Process') as mock_process:
            args = self.parser.parse_args(['celery', 'worker', '-c', '-1'])

            with mock.patch('celery.platforms.check_privileges') as mock_privil:
                mock_privil.return_value = 0
                celery_command.worker(args)
                mock_process.assert_called()

    def test_skip_serve_logs_on_worker_start(self):
        with mock.patch('airflow.cli.commands.celery_command.Process') as mock_popen:
            args = self.parser.parse_args(['celery', 'worker', '-c', '-1', '-s'])

            with mock.patch('celery.platforms.check_privileges') as mock_privil:
                mock_privil.return_value = 0
                celery_command.worker(args)
                mock_popen.assert_not_called()
