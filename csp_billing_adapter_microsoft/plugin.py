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

METADATA_URL = 'http://169.254.169.254/metadata/'
INSTANCE_INFO_URL = METADATA_URL + 'instance?api-version={latest}'
VERSIONS_URL = METADATA_URL + 'versions'
METADATA_TOKEN = '/identity/oauth2/token?api-version={version}&resource=https://management.azure.com/'

METADATA_TOKEN_URL = METADATA_URL + METADATA_TOKEN
SIGNATURE_URL = METADATA_URL + 'attested/document?api-version={latest}'
METADATA_HEADER = {'Metadata': 'True'}


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
    account_info['cloud_provider'] = get_csp_name(config)

    return account_info


def _get_metadata():
    """Return a dict containing compute, network and signature information."""
    metadata = {}
    try:
        metadata = _get_instance_metadata()
        metadata['attestedData'] = _get_signature()
    except ValueError as error:
        log.error('Could not load JSON from metadata: {}'.format(error))
        for key in ['compute', 'network', 'signature', 'pkcs7']:
            if not metadata.get(key):
                metadata[key] = {}

    return metadata


def _get_instance_metadata():
    """Return all compute and network information from metadata."""
    api_latest_version = _get_latest_api_version()
    return json.loads(
        _fetch_metadata(
            INSTANCE_INFO_URL.format(latest=api_latest_version)
        )
    )


def _get_signature():
    """Return attested data signature from metadata."""
    api_latest_version = _get_latest_api_version()
    return json.loads(
        _fetch_metadata(
            SIGNATURE_URL.format(latest=api_latest_version)
        )
    )


def _get_latest_api_version():
    """
    Return the newest API version available

    Otherwise, return minimum API version to get
    license type on the signature.
    """
    versions = json.loads(_fetch_metadata(VERSIONS_URL))
    if versions:
        return versions['apiVersions'][-1]

    # minimum API version with license type
    # for more info check https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service?tabs=linux#attested-data
    return '2020-09-01'


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
        log.error('Failed to retrieve metadata for: {url}. {error}'.format(
            url=url,
            error=str(error)
        ))
        return {}
