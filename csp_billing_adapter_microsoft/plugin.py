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

"""
Implements the CSP hook functions for Microsoft Azure AWS. This handles the
metered billing of product usage in the Azure.
"""

import json
import logging
import os
import urllib.request
import urllib.error
import uuid

from datetime import datetime

import csp_billing_adapter
import csp_billing_adapter.exceptions as cba_exceptions

from csp_billing_adapter.config import Config

log = logging.getLogger('CSPBillingAdapter')

METADATA_URL = 'http://169.254.169.254/metadata/'
# We want the attested data, this is the version that supports that endpoint
REQUIRED_METADATA_VERSION = '2020-09-01'

SIGNATURE_URL = (
    f"{METADATA_URL}attested/document?api-version={REQUIRED_METADATA_VERSION}"
)
METADATA_HEADER = {'Metadata': 'True'}


@csp_billing_adapter.hookimpl
def setup_adapter(config: Config):
    """Handle any plugin specific setup at adapter start"""
    is_available = _is_required_metadata_version_available()
    if not is_available:
        raise cba_exceptions.CSPMetadataRetrievalError(
            "Running in Azure context with insufficient IMDS API version"
        )


@csp_billing_adapter.hookimpl(trylast=True)
def meter_billing(
    config: Config,
    dimensions: dict,
    timestamp: datetime,
    dry_run: bool
):
    """
    Process a metered billing based on the dimensions provided

    If a single dimension is provided the meter_usage API is
    used for the metering. If there is an error the metering
    is attempted 3 times before re-raising the exception to
    calling scope.
    """

    status = {}
    usage = _create_usage_list(dimensions, timestamp)

    if len(usage) > 0:
        data_request = urllib.request.Request(
            'https://marketplaceapi.microsoft.com/api/batchUsageEvent'
            '?api-version=2018-08-31',
            data=json.dumps({"request": usage}).encode("utf-8"),
            headers={
                'Content-type': 'application/json',
                'x-ms-correlationid': str(uuid.uuid4()),
                'authorization': _get_msi_token()
            },
            method='POST'
        )

        retries = 3
        exc = None
        response = None

        while retries > 0:
            try:
                with urllib.request.urlopen(data_request) as url_open_return:
                    response = json.loads(
                        url_open_return.read().decode("utf-8")
                    )
                    break
            except urllib.error.URLError as error:
                exc = error
                retries -= 1
                continue

        if exc:
            msg = (
                f"Failed to meter bill dimensions "
                f"{dimensions}: {str(exc)}"
            )
            for dimension_name in dimensions:
                status[dimension_name] = {
                    "status": "failed",
                    "error": msg
                }
            log.error(msg)
            return status

        if response and (response.get("count", 0) > 0):
            return _create_status_dict(response)

    log.info(
        'Nothing to meter bill: No dimensions have non zero quantity values'
    )
    return status


@csp_billing_adapter.hookimpl(trylast=True)
def get_csp_name(config: Config):
    """Return CSP provider name"""
    return 'microsoft'


@csp_billing_adapter.hookimpl(trylast=True)
def get_account_info(config: Config):
    """
    Return a dictionary with account information

    The information contains the metadata for compute and network.
    """
    account_info = _get_metadata()
    account_info['cloud_provider'] = get_csp_name(config)

    return account_info


def _get_metadata():
    """Return a dict containing compute, network and signature information."""
    metadata = {}
    try:
        metadata = _get_instance_metadata()
        metadata['attestedData'] = _get_signature()
    except ValueError as error:
        log.error('Could not load JSON from metadata %s:', error)
        for key in ['compute', 'network', 'attestedData']:
            if key not in metadata:
                metadata[key] = {}

    return metadata


def _get_instance_metadata():
    """Return all compute and network information from metadata."""
    instance_info_url = \
        f'{METADATA_URL}instance?api-version={REQUIRED_METADATA_VERSION}'
    return json.loads(
        _fetch_metadata(instance_info_url)
    )


def _get_signature():
    """Return attested data signature from metadata."""
    return json.loads(
        _fetch_metadata(SIGNATURE_URL)
    )


def _is_required_metadata_version_available():
    """
    Check if the metadata version we want is available
    """
    versions = json.loads(_fetch_metadata(f"{METADATA_URL}versions"))
    return REQUIRED_METADATA_VERSION in versions.get('apiVersions', [])


def _fetch_metadata(url):
    """Return the response of the metadata request."""
    data_request = urllib.request.Request(
        url,
        headers=METADATA_HEADER,
        method='GET'
    )
    try:
        with urllib.request.urlopen(data_request) as value:
            return value.read().decode("utf-8")
    except urllib.error.URLError as error:
        log.error('Failed to retrieve metadata for: %s: %s', url, str(error))
        return "{}"


def _get_msi_token():
    """Get the MSI token to authenticate when using the Billing API"""
    # https://learn.microsoft.com/en-us/partner-center/marketplace/marketplace-metering-service-authentication

    # Set resource id to the required value needed to to retrieve an
    # MSI Authentication Token
    resource = '20e940b3-4c77-4b0b-9a53-9e16a1b010a7'
    client_id = os.environ['CLIENT_ID']
    url = (
        f"{METADATA_URL}"
        f"identity/oauth2/token?api-version=2018-02-01&client_id={client_id}"
        f"&resource={resource}"
    )
    try:
        auth_token = json.loads(_fetch_metadata(url))

        if auth_token["token_type"] == "Bearer" and auth_token["access_token"]:
            return f'Bearer {auth_token["access_token"]}'

        log.error('Invalid MSI token retrieved: %s', auth_token)
        raise cba_exceptions.CSPBillingAdapterException
    except ValueError as error:
        log.error('Unable to acquire an MSI token %s:', str(error))
        raise cba_exceptions.CSPBillingAdapterException from error


def _create_usage_list(dimensions: dict, timestamp: datetime):
    """Create the usage list used with the batchEventUsage API"""

    usage = []
    for dimension_name, quantity in dimensions.items():
        if quantity == 0:
            log.info(
                'A "0" value was reported for %s, skipping meter billing',
                dimension_name
            )
            continue

        # Setup request body for the usage event API
        usage.append(
            {
                'resourceUri': os.environ['EXTENSION_RESOURCE_ID'],
                'quantity': quantity,
                'dimension': dimension_name,
                'effectiveStartTime': str(timestamp),
                'planId': os.environ['PLAN_ID']
            }
        )
    return usage


def _create_status_dict(response: dict):
    """Create the status dict from the response from the batchUsageEvent API"""
    status = {}
    for resp in response["result"]:
        if resp.get("status") == "Accepted":
            dim_status = {
                "record_id": resp.get("usageEventId", None),
                "status": "submitted"
            }
            log.info(
                'New metered billing record added with ID %s:',
                dim_status["record_id"]
            )
        else:
            log.error(
                'Unable to log metered billing record: %s',
                resp
            )
            dim_status = {
                "status": "failed",
                "error":
                    f'Failed to meter bill dimensions: '
                    f'Status: {resp.get("status")} '
                    f'Message: {resp.get("error", {}).get("message")}'
            }
        status[resp["dimension"]] = dim_status
    return status
