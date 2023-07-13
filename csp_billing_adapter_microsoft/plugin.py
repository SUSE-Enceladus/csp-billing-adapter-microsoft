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

import csp_billing_adapter
import csp_billing_adapter.exceptions as cba_exceptions

from datetime import datetime, timezone

from csp_billing_adapter.config import Config

log = logging.getLogger('CSPBillingAdapter')

METADATA_URL = 'http://169.254.169.254/metadata/'
# We want the attested data, this is the version that supports that endpoint
REQUIRED_METADATA_VERSION = '2020-09-01'

SIGNATURE_URL = (METADATA_URL + 'attested/document?api-version='
                 + REQUIRED_METADATA_VERSION)
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
    metered_billing_data = {"request": []}

    for dimension_name, quantity in dimensions.items():
        if quantity == 0:
            log.info(
                f'"0" value reported for {dimension_name}, skipping logging'
            )
            continue

        # Setup request body for the usage event API
        metered_billing_data["request"].append(
            {
                'resourceUri': os.environ['EXTENSION_RESOURCE_ID'],
                'quantity': quantity,
                'dimension': dimension_name,
                'effectiveStartTime': str(timestamp.astimezone(timezone.utc)),
                'planId': os.environ['PLAN_ID']
            }
        )

    if metered_billing_data["request"]:
        metered_billing_data_bytes = json.dumps(metered_billing_data).encode()
        # Setup request header for the usage event API
        metered_billing_header = {
            'Content-type': 'application/json',
            'Content-Length': len(metered_billing_data_bytes),
            'x-ms-correlationid': uuid.uuid4(),
            'authorization': _get_msi_token()
        }

        # Make request to the usage event API
        data_request = urllib.request.Request(
            'https://marketplaceapi.microsoft.com/api/batchUsageEvent'
            '?api-version=2018-08-31',
            data=metered_billing_data_bytes,
            headers=metered_billing_header,
            method='POST'
        )

        exc = None
        value = None
        retries = 3

        while retries > 0:
            try:
                value = urllib.request.urlopen(data_request).read()
                retries = 0
            except urllib.error.URLError as error:
                exc = error
                retries -= 1
                continue

        if exc:
            log.error(
                f'Cannot call batchUsageEvent API for: {metered_billing_data}:'
                f'return from http POST request is; {exc}'
            )
            raise exc  # Re-raise exception to calling scope

        if value and _create_metered_billing_response(value):
            return _create_metered_billing_response(value)

    log.info('Nothing to meter bill: No tiers have non zero quantity values')
    return None


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
        log.error(f'Could not load JSON from metadata: {error}')
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
    versions = json.loads(_fetch_metadata(METADATA_URL + 'versions'))
    return REQUIRED_METADATA_VERSION in versions.get('apiVersions', [])


def _fetch_metadata(url):
    """Return the response of the metadata request."""
    data_request = urllib.request.Request(
        url,
        headers=METADATA_HEADER,
        method='GET'
    )
    try:
        value = urllib.request.urlopen(data_request).read()
        return value.decode()
    except urllib.error.URLError as error:
        log.error(f'Failed to retrieve metadata for: {url}. {str(error)}')
        return {}


def _get_msi_token():
    """Get the MSI token to authenticate when using the Billing API"""
    # https://learn.microsoft.com/en-us/partner-center/marketplace/marketplace-metering-service-authentication

    resource = '20e940b3-4c77-4b0b-9a53-9e16a1b010a7'
    clientid = os.environ['CLIENT_ID']
    msi_url = (
        f"{METADATA_URL}"
        f"identity/oauth2/token?api-version=2018-02-01&clientId={clientid}"
        f"&resource={resource}"
    )
    try:
        auth_token = json.loads(_fetch_metadata(msi_url))
        if auth_token["token_type"] == "Bearer" and auth_token["access_token"]:
            return "Bearer " + auth_token["access_token"]
        log.error('Invalid MSI token retrieved: {auth_token}')
        raise cba_exceptions.CSPBillingAdapterException
    except ValueError as error:
        log.error(f'Unable to acquire an MSI token: {error}')
        raise cba_exceptions.CSPBillingAdapterException from error


def _create_metered_billing_response(value):
    """Return a dict of the dimension and metered billing record id"""
    metered_billing_response = {}
    if value and value.get("count") > 0:
        for resp in value["result"]:
            if resp["status"] == "Accepted":
                metered_billing_response[resp["dimension"]] = \
                    {"record_id": resp["usageEventId"], "status": "submitted"}
                log.info(
                    f'New metered billing record added: '
                    f'{resp["dimension"]}: {resp["usageEventId"]}'
                )
            else:
                metered_billing_response[resp["dimension"]] = \
                    {'record_id': None, 'status': 'failed'}
                log.error(
                    f'Unable to log metered billing record: '
                    f'return from batchUsageEvent API is {resp}'
                )
    return (metered_billing_response or None)
