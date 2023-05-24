#
# Copyright 2023 SUSE LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import datetime
import pytest
import urllib.error

from unittest.mock import Mock, patch

from csp_billing_adapter_microsoft import plugin
from csp_billing_adapter.config import Config
from csp_billing_adapter.adapter import get_plugin_manager

pm = get_plugin_manager()
config = Config.load_from_file(
    'tests/data/good_config.yaml',
    pm.hook
)


def test_setup():
    plugin.setup_adapter(config)  # Currently no-op


def test_meter_billing(mock_boto3):


def test_meter_billing_error(mock_boto3):


def test_get_csp_name():
    assert plugin.get_csp_name(config) == 'amazon'


@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_account_info(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        b'secrettoken',
        b'{"some": "info"}',
        b'signature',
        b'pkcs7'
    ]
    mock_urlopen.return_value = urlopen

    info = plugin.get_account_info(config)
    assert info == {
        'cloud_provider': 'amazon',
        'document': {'some': 'info'},
        'pkcs7': 'pkcs7',
        'signature': 'signature'
    }


@patch('csp_billing_adapter_amazon.plugin.urllib.request.urlopen')
def test_get_api_header_token_fail(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get token!')
    ]
    mock_urlopen.return_value = urlopen

    header = plugin._get_api_header()
    assert header == {}


@patch('csp_billing_adapter_amazon.plugin.urllib.request.urlopen')
def test_fetch_metadata_fail(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!')
    ]
    mock_urlopen.return_value = urlopen

    metadata = plugin._fetch_metadata('metadata', {'header': 'data'})
    assert metadata is None
