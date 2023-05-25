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
COMPUTE_URL = METADATA_URL + 'instance/compute?api-version=2017-08-01'
# version 2020-09-01 include license type
# for more info check https://learn.microsoft.com/en-us/azure/virtual-machines/instance-metadata-service?tabs=linux#attested-data
SIGNATURE_URL = METADATA_URL + 'attested/document?api-version=2020-09-01'
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
    metadata = {}
    try:
        metadata = _get_signature()
        metadata['compute'] = _get_compute_metadata()
    except ValueError as error:
        log.error('Could not load JSON from metadata: {}'.format(error))
        for key in ['compute', 'signature']:
            if not metadata.get(key):
                metadata[key] = {}

    return metadata


def _get_compute_metadata():
    compute = json.loads(_fetch_metadata(COMPUTE_URL))

    return {
        'offer': compute.get('offer'),
        'location': compute.get('location')
    }


def _get_signature():
    attested_data = json.loads(_fetch_metadata(SIGNATURE_URL))
    del attested_data['encoding']

    return attested_data


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
