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
import logging
import os
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


@patch(
    'csp_billing_adapter_microsoft.plugin.'
    '_is_required_metadata_version_available'
)
def test_setup_adapter_fails(mock_check_metadata_version):
    mock_check_metadata_version.return_value = False
    with pytest.raises(cba_exceptions.CSPMetadataRetrievalError):
        plugin.setup_adapter(config)  # Cur


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing(mock_urlopen, mock_get_msi_token, caplog):
    urlopen = Mock()
    urlopen.read.side_effect = [
        {
            "count": 2,
            "result": [
                {
                    "usageEventId": "1000",
                    "resourceUri": "foo",
                    "quantity": 10,
                    "dimension": "tier_1",
                    "planId": "foo",
                    "status": "Accepted"
                },
                {
                    "usageEventId": "1001",
                    "resourceUri": "foo",
                    "quantity": 5,
                    "dimension": "tier_2",
                    "planId": "foo",
                    "status": "Accepted"
                }
            ]
        }
    ]
    mock_get_msi_token.return_value = "Bearer 123456789"

    mock_urlopen.return_value = urlopen
    caplog.set_level(logging.INFO)

    dimensions = {'tier_1': 10, 'tier_2': 5}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    mock_urlopen.return_value = urlopen
    usage_id = plugin.meter_billing(
        config,
        dimensions,
        timestamp,
        dry_run=False
    )
    assert usage_id["tier_1"] == {"record_id": "1000", "status": "submitted"}
    assert usage_id["tier_2"] == {"record_id": "1001", "status": "submitted"}
    assert "New metered billing record added" in caplog.records[0].msg
    assert "New metered billing record added" in caplog.records[1].msg


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_error(mock_urlopen, mock_get_msi_token):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!'),
        urllib.error.URLError('Cannot get metadata!'),
        urllib.error.URLError('Cannot get metadata!')
    ]
    mock_get_msi_token.return_value = {
            "Bearer 123456789"
    }

    mock_urlopen.return_value = urlopen

    dimensions = {'tier_1': 10}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    mock_urlopen.return_value = urlopen
    with pytest.raises(urllib.error.URLError):
        plugin.meter_billing(config, dimensions, timestamp, dry_run=False)


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_quantity_is_zero(
    mock_urlopen,
    mock_get_msi_token,
    caplog
):
    urlopen = Mock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!'),
        urllib.error.URLError('Cannot get metadata!'),
        urllib.error.URLError('Cannot get metadata!')
    ]
    mock_get_msi_token.return_value = {
            "Bearer 123456789"
    }

    mock_urlopen.return_value = urlopen
    caplog.set_level(logging.INFO)

    dimensions = {'tier_1': 0}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    mock_urlopen.return_value = urlopen
    assert plugin.meter_billing(
        config,
        dimensions,
        timestamp,
        dry_run=False
    ) is None

    assert '"0" value reported for' in caplog.records[0].msg
    assert "Nothing to meter bill: No tiers have non zero quantity values" in \
        caplog.records[1].msg


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_non_accepted_status_from_batchUsageEvent(
    mock_urlopen,
    mock_get_msi_token,
    caplog
):
    urlopen = Mock()
    urlopen.read.side_effect = [
        {
            "count": 2,
            "result": [
                {
                    "status": "Duplicate",
                    "error": {
                        "additionalInfo": {
                            "acceptedMessage": {
                                "usageEventId": "1000",
                                "status": "Duplicate",
                                "resourceUri": "foo",
                                "quantity": 10.0,
                                "dimension": "tier_1",
                                "planId": "foo"
                            }
                        },
                        "message": "This usage event already exist.",
                        "code": "Conflict"
                    },
                    "resourceUri": "1001",
                    "quantity": 10.0,
                    "dimension": "tier_1",
                    "planId": "foo"
                },
                {
                    "usageEventId": "1002",
                    "resourceUri": "foo",
                    "quantity": 5,
                    "dimension": "tier_2",
                    "planId": "foo",
                    "status": "Duplicate"
                }
            ]
        }
    ]
    mock_get_msi_token.return_value = {
            "Bearer 123456789"
    }

    mock_urlopen.return_value = urlopen

    dimensions = {'tier_1': 10, 'tier_2': 5}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    mock_urlopen.return_value = urlopen
    test_record = plugin.meter_billing(
        config,
        dimensions,
        timestamp,
        dry_run=False
    )
    assert test_record["tier_1"].get("record_id") is None
    assert test_record["tier_1"].get("status") == 'failed'

    assert "Unable to log metered billing record" in caplog.records[0].msg
    assert "Unable to log metered billing record" in caplog.records[1].msg


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


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token(mock_urlopen, mock_os_environ):
    urlopen = Mock()

    urlopen.read.side_effect = [
        b'{"access_token": "123456789", "token_type": "Bearer"}'
    ]

    mock_urlopen.return_value = urlopen
    mock_os_environ.return_value = "12345"

    info = plugin._get_msi_token()
    assert info == "Bearer 123456789"


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token_error(mock_urlopen, mock_os_environ, caplog):
    urlopen = Mock()
    urlopen.read.side_effect = ValueError()

    mock_urlopen.return_value = urlopen

    with pytest.raises(cba_exceptions.CSPBillingAdapterException):
        plugin._get_msi_token()

    assert "Unable to acquire an MSI token" in caplog.records[0].msg


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token_invalid(mock_urlopen, mock_os_environ, caplog):
    urlopen = Mock()
    urlopen.read.side_effect = [
        b'{"access_token": "123456789", "token_type": "Foo"}'
    ]

    mock_urlopen.return_value = urlopen

    with pytest.raises(cba_exceptions.CSPBillingAdapterException):
        plugin._get_msi_token()

    assert "Invalid MSI token retrieved" in caplog.records[0].msg
