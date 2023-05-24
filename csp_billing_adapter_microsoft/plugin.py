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
import urllib.request
import urllib.error

import csp_billing_adapter

from datetime import datetime

from csp_billing_adapter.config import Config

log = logging.getLogger('CSPBillingAdapter')

METADATA_ADDR = 'http://169.254.169.254/metadata'
METADATA_API_VERSION = '?api-version=2021-12-13'
METADATA_INSTANCE_PATH = '/instance'
METADATA_TOKEN_PATH = '/identity/oauth2/token'
METADATA_TOKEN_RESOURCE = '&resource=https://management.azure.com/'

METADATA_INSTANCE_URL = METADATA_ADDR + METADATA_INSTANCE_PATH
METADATA_TOKEN_URL = \
    METADATA_ADDR + METADATA_TOKEN_PATH + METADATA_API_VERSION + \
    METADATA_TOKEN_RESOURCE


@csp_billing_adapter.hookimpl
def setup_adapter(config: Config):
    """Handle any plugin specific setup at adapter start"""
    pass


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
    account_info['compute'] = json.loads(account_info.get('compute', '{}'))
    account_info['network'] = json.loads(account_info.get('network', '{}'))
    account_info['cloud_provider'] = get_csp_name(config)

    return account_info


def get_api_header():
    """
    Get the header to be used in requests

    Prefer IMDS which requires a token.
    """
    request = urllib.request.Request(
        METADATA_TOKEN_URL,
        headers={'Metadata': 'True'},
        method='GET'
    )

    try:
        token = urllib.request.urlopen(request).read().decode()
    except urllib.error.URLError as error:
        log.error(f'Failed to retrieve metadata token: {str(error)}')
        return {}

    return token


def _get_metadata():
    metadata_options = ['compute', 'network']
    return {
        metadata_option: _fetch_metadata(metadata_option)
        for metadata_option in metadata_options
    }


def _fetch_metadata(uri):
    """Return the response of the metadata request."""
    url = f'{METADATA_INSTANCE_URL}/{uri}{METADATA_API_VERSION}'
    data_request = urllib.request.Request(
        url,
        headers={'Metadata': 'True'},
        method='GET'
    )

    try:
        value = urllib.request.urlopen(data_request).read()
    except urllib.error.URLError as error:
        log.error(f'Failed to retrieve metadata for: {url}. {str(error)}')
        return None

    return value.decode()
