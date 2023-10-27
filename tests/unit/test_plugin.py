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
import json
import logging
import os
import pytest
import urllib.error

from unittest.mock import Mock, MagicMock, patch

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
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        json.dumps({
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
        }).encode("utf-8")
    ]
    mock_get_msi_token.return_value = "Bearer 123456789"

    urlopen.__enter__.return_value = urlopen
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
    assert "New metered billing record added" in caplog.records[0].msg


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_urllib_error(mock_urlopen, mock_get_msi_token):
    """ Test urllib error"""
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!'),
        urllib.error.URLError('Cannot get metadata!'),
        urllib.error.URLError('Cannot get metadata!')
    ]
    mock_get_msi_token.return_value = {
            "Bearer 123456789"
    }

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen

    dimensions = {'tier_1': 10}
    timestamp = datetime.datetime.now(datetime.timezone.utc)

    mock_urlopen.return_value = urlopen
    usage = plugin.meter_billing(config, dimensions, timestamp, dry_run=False)
    assert usage["tier_1"] == {
        'status': 'failed',
        'error': "Failed to meter bill dimensions {'tier_1': 10}: "
        "<urlopen error Cannot get metadata!>"
    }


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_quantity_is_zero(
    mock_urlopen,
    mock_get_msi_token,
    caplog
):
    """ Test when a 0 is passed as the quantity"""
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
    ) == {}

    assert 'A "0" value was reported for' in caplog.records[0].msg
    assert \
        "Nothing to meter bill: No dimensions have non zero quantity values" \
        in caplog.records[1].msg


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_non_accepted_status_from_batchUsageEvent(
    mock_urlopen,
    mock_get_msi_token,
    caplog
):
    """Test for a non accepted status"""
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        json.dumps({
            "count": 1,
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
                }
            ]
        }).encode("utf-8")
    ]
    mock_get_msi_token.return_value = {
            "Bearer 123456789"
    }

    urlopen.__enter__.return_value = urlopen
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
    assert test_record["tier_1"].get("error") == (
        'Failed to meter bill dimensions: Status: '
        'Duplicate Message: This usage event already exist.'
    )
    assert "Unable to log metered billing record" in caplog.records[0].msg


# @patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_resource_uri')
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_non_accepted_status_from_batchUsageEvent_vm(
    mock_urlopen,
    mock_get_msi_token,
    mock_get_resource_uri,
    caplog
):
    """Test for a non accepted status on VM"""
    mock_get_resource_uri.return_value = "super_resource_id"
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        json.dumps({
            "count": 1,
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
                }
            ]
        }).encode("utf-8")
    ]
    mock_get_msi_token.return_value = {
        "Bearer 123456789"
    }

    urlopen.__enter__.return_value = urlopen
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
    assert test_record["tier_1"].get("error") == (
        'Failed to meter bill dimensions: Status: '
        'Duplicate Message: This usage event already exist.'
    )
    assert "Unable to log metered billing record" in caplog.records[0].msg


@patch.dict(os.environ, {'EXTENSION_RESOURCE_ID': 'foo', 'PLAN_ID': 'foo'})
@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_meter_billing_missing_keys_in_response_from_batchUsageEvent(
    mock_urlopen,
    mock_get_msi_token,
    caplog
):
    """Test for a non accepted status"""
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        json.dumps({
            "count": 1,
            "result": [
                {
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
                        "code": "Conflict"
                    },
                    "resourceUri": "1001",
                    "quantity": 10.0,
                    "dimension": "tier_1",
                    "planId": "foo"
                }
            ]
        }).encode("utf-8")
    ]
    mock_get_msi_token.return_value = {
            "Bearer 123456789"
    }

    urlopen.__enter__.return_value = urlopen
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

    assert test_record["tier_1"].get("status") == "failed"
    assert test_record["tier_1"].get("error") == (
        'Failed to meter bill dimensions: Status: '
        'None Message: None'
    )


def test_get_csp_name():
    """Test getting csp name"""
    assert plugin.get_csp_name(config) == 'microsoft'


@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_account_info(mock_urlopen):
    """Test getting account info"""
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        b'{"compute": "info", "network": "info"}',
        b'{"signature": "signature", "pkcs7": "pkcs7"}'
    ]
    urlopen.__enter__.return_value = urlopen
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
    """Test unable to reach metadata service"""
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get metadata!')
    ]
    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen

    metadata = plugin._fetch_metadata('http://foo.abc.org')
    assert metadata == "{}"


@patch('csp_billing_adapter_microsoft.plugin._get_instance_metadata')
@patch('csp_billing_adapter_microsoft.plugin._get_signature')
def test_get_metadata_fail(mock_get_signature, mock_get_instance_metadata):
    """Test no metadata returned"""
    mock_get_instance_metadata.side_effect = ValueError('foo')
    mock_get_signature.side_effect = ValueError('foo')

    metadata = plugin._get_metadata()
    assert metadata == {'attestedData': {}, 'compute': {}, 'network': {}}


@patch('csp_billing_adapter_microsoft.plugin._fetch_metadata')
@patch('csp_billing_adapter_microsoft.plugin.json.loads')
def test_is_required_metadata_version_available_is_true(
    mock_json_loads, mock_fetch_metadata
):
    """Test metadata version exists"""
    mock_json_loads.return_value = {'apiVersions': ['2020-09-01']}
    assert plugin._is_required_metadata_version_available() is True


@patch('csp_billing_adapter_microsoft.plugin._fetch_metadata')
@patch('csp_billing_adapter_microsoft.plugin.json.loads')
def test_is_required_metadata_version_available_is_false(
    mock_json_loads, mock_fetch_metadata
):
    """Test metadata version dos not exist"""
    mock_json_loads.return_value = {'apiVersions': ['2021-09-01']}
    assert plugin._is_required_metadata_version_available() is False


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token(mock_urlopen, mock_os_environ):
    """Test get token for metadata service"""
    urlopen = MagicMock()

    urlopen.read.side_effect = [
        b'{"access_token": "123456789", "token_type": "Bearer"}'
    ]

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen
    mock_os_environ.return_value = "12345"

    info = plugin._get_msi_token(config)
    assert info == "Bearer 123456789"


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token_vm(mock_urlopen, mock_os_environ):
    """Test get token for metadata service on VM"""
    urlopen = MagicMock()

    config_vm = dict(config)
    config_vm['api'] = 'foo'
    urlopen.read.side_effect = [
        b'{"access_token": "123456789", "token_type": "Bearer"}'
    ]

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen
    mock_os_environ.return_value = "12345"

    info = plugin._get_msi_token(config_vm)
    assert info == "Bearer 123456789"


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token_error(mock_urlopen, mock_os_environ, caplog):
    """Test error getting token"""
    urlopen = MagicMock()
    urlopen.read.side_effect = ValueError()

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen

    with pytest.raises(cba_exceptions.CSPBillingAdapterException):
        plugin._get_msi_token(config)

    assert "Unable to acquire an MSI token" in caplog.records[0].msg


@patch('csp_billing_adapter_microsoft.plugin.os.environ')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
def test_get_msi_token_invalid(mock_urlopen, mock_os_environ, caplog):
    """Test Invalid token received"""
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        b'{"access_token": "123456789", "token_type": "Foo"}'
    ]

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen

    with pytest.raises(cba_exceptions.CSPBillingAdapterException):
        plugin._get_msi_token(config)

    assert "Invalid MSI token retrieved" in caplog.records[0].msg


def test_get_version():
    version = plugin.get_version()
    assert version[0] == 'microsoft_plugin'
    assert version[1]


@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
@patch('csp_billing_adapter_microsoft.plugin._get_instance_metadata')
@patch('csp_billing_adapter_microsoft.plugin._get_signature')
def test_get_managed_identity(
    mock_get_signature,
    mock_get_instance_metadata,
    mock_urlopen,
    mock_get_msi_token
):
    """Test get managed identity API"""
    mock_get_instance_metadata.return_value = {
        "compute": {
            "subscriptionId": "info",
            "resourceGroupName": "info",
        },
        "network": "info",
        "signature": "signature",
        "pkcs7": "pkcs7"
    }
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        json.dumps({
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
        }).encode("utf-8")
    ]
    mock_get_msi_token.return_value = "Bearer 123456789"

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen
    plugin._get_managed_identity()


@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
@patch('csp_billing_adapter_microsoft.plugin._get_instance_metadata')
@patch('csp_billing_adapter_microsoft.plugin._get_signature')
def test_get_managed_identity_wrong_metadata(
    mock_get_signature,
    mock_get_instance_metadata,
    mock_urlopen,
    mock_get_msi_token
):
    """Test get managed identity with wrong metadata"""
    mock_get_instance_metadata.return_value = {
        "network": "info",
        "signature": "signature",
        "pkcs7": "pkcs7"
    }
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        json.dumps({
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
        }).encode("utf-8")
    ]
    mock_get_msi_token.return_value = "Bearer 123456789"

    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen
    with pytest.raises(cba_exceptions.CSPMetadataRetrievalError):
        plugin._get_managed_identity()


@patch('csp_billing_adapter_microsoft.plugin._get_msi_token')
@patch('csp_billing_adapter_microsoft.plugin.urllib.request.urlopen')
@patch('csp_billing_adapter_microsoft.plugin._get_instance_metadata')
@patch('csp_billing_adapter_microsoft.plugin._get_signature')
def test_get_managed_identity_request_failed(
    mock_get_signature,
    mock_get_instance_metadata,
    mock_urlopen,
    mock_get_msi_token
):
    """Test get managed identity request failure"""
    mock_get_instance_metadata.return_value = {
        "compute": {
            "subscriptionId": "info",
            "resourceGroupName": "info",
        },
        "network": "info",
        "signature": "signature",
        "pkcs7": "pkcs7"
    }
    mock_get_msi_token.return_value = "Bearer 123456789"
    urlopen = MagicMock()
    urlopen.read.side_effect = [
        urllib.error.URLError('Cannot get managed_identity!')
    ]
    urlopen.__enter__.return_value = urlopen
    mock_urlopen.return_value = urlopen
    assert plugin._get_managed_identity() == {}


@patch('csp_billing_adapter_microsoft.plugin._get_managed_identity')
def test_get_resource_uri(mock_get_managed_identity):
    """Test get resource uri"""
    mock_get_managed_identity.return_value = {
        "managedBy": "secret identity"
    }
    assert plugin._get_resource_uri() == 'secret identity'


@patch('csp_billing_adapter_microsoft.plugin._get_managed_identity')
def test_get_resource_uri_error(
    mock_get_managed_identity,
    caplog
):
    """Test get resource uri error"""
    mock_get_managed_identity.return_value = {
        "notManagedBy": "secret identity"
    }

    plugin._get_resource_uri()
    message = (
        'Failed to retrieve resource uri managed identity response '
        'missing managedBy'
    )
    assert message in caplog.records[0].msg
