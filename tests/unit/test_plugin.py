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

import pytest
import urllib.error

from unittest.mock import Mock, patch

from csp_billing_adapter_microsoft import plugin
from csp_billing_adapter.config import Config
from csp_billing_adapter.adapter import get_plugin_manager
import csp_billing_adapter.exceptions as cba_exceptions


pm = get_plugin_manager()
config = Config.load_from_file(
    'tests/data/good_config.yaml',
    pm.hook
)


@patch(
    'csp_billing_adapter_microsoft.plugin.'
    '_is_required_metadata_version_available'
)
def test_setup(mock_check_metadata_version):
    mock_check_metadata_version.return_value = True
    plugin.setup_adapter(config)  # Currently no-op


@pytest.mark.skipif(not hasattr(cba_exceptions, 'MetadataCollectorError'),
                    reason='MetadataCollectorError not defined yet')
@patch(
    'csp_billing_adapter_microsoft.plugin.'
    '_is_required_metadata_version_available'
)
def test_setup_adapter_fails(mock_check_metadata_version):
    mock_check_metadata_version.return_value = False
    with pytest.raises(cba_exceptions.MetadataCollectorError):
        plugin.setup_adapter(config)  # Cur


def test_meter_billing():
    pass


def test_meter_billing_error():
    pass


def test_get_csp_name():
    assert plugin.get_csp_name(config) == 'microsoft'


@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_account_info(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        b'{"compute": "info", "network": "info"}',
        b'{"signature": "signature", "pkcs7": "pkcs7"}'
    ]
    mock_urlopen.return_value = urlopen

    info = plugin.get_account_info(config)
    assert info == {
        'compute': 'info',
        'network': 'info',
        'attestedData': {'pkcs7': 'pkcs7', 'signature': 'signature'},
        'cloud_provider': 'microsoft',
    }


@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_fetch_metadata_fail(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!')
    ]
    mock_urlopen.return_value = urlopen

    metadata = plugin._fetch_metadata('http://foo.abc.org')
    assert metadata == {}


@patch('csp_billing_adapter_microsoft.plugin._get_instance_metadata')
@patch('csp_billing_adapter_microsoft.plugin._get_signature')
def test_get_metadata_fail(mock_get_signature, mock_get_instance_metadata):
    mock_get_instance_metadata.side_effect = ValueError('foo')
    mock_get_signature.side_effect = ValueError('foo')

    metadata = plugin._get_metadata()
    assert metadata == {'attestedData': {}, 'compute': {}, 'network': {}}


@patch('csp_billing_adapter_microsoft.plugin._fetch_metadata')
@patch('csp_billing_adapter_microsoft.plugin.json.loads')
def test_is_required_metadata_version_available_is_true(
    mock_json_loads, mock_fetch_metadata
):
    mock_json_loads.return_value = {'apiVersions': ['2020-09-01']}
    assert plugin._is_required_metadata_version_available() is True


@patch('csp_billing_adapter_microsoft.plugin._fetch_metadata')
@patch('csp_billing_adapter_microsoft.plugin.json.loads')
def test_is_required_metadata_version_available_is_false(
    mock_json_loads, mock_fetch_metadata
):
    mock_json_loads.return_value = {'apiVersions': ['2021-09-01']}
    assert plugin._is_required_metadata_version_available() is False


@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_api_token(mock_urlopen):
    urlopen = Mock()
    urlopen.read.side_effect = [
        b'{"access_token": "info", "expires_in": "info"}'
    ]
    mock_urlopen.return_value = urlopen

    info = plugin._get_api_token()
    assert info == {
        'access_token': 'info',
        'expires_in': 'info'
    }
