# CSP Billing Adapter Microsoft Plugin

This is a plugin for
[csp-billing-adapter](https://github.com/SUSE-Enceladus/csp-billing-adapter)
that provides CSP hook implementations. This includes the hooks defined in the
[csp_hookspecs.py module](https://github.com/SUSE-Enceladus/csp-billing-adapter/blob/main/csp_billing_adapter/csp_hookspecs.py).


## Meter billing

The `meter_billing` function accepts a dictionary mapping of dimension name
to usage quantity. This information is used to bill the customer for
the product ID that is configured in the adapter. If there is an exception
with metered billing the exception is raised.

## Get CSP Name

The `get_csp_name` function returns the name of the CSP provider. In this
case it is *Microsoft*.

## Get Account Info

The `get_account_info` function provides metadata information for the running
instance or container. The structure of this information is as follows:

```
{
    "document": {
        "subscriptionId": "5f40eec9-a9be-4851-90c1-621e6d65df81",
        "azEnvironment": "AzurePublicCloud",
        "licenseType": "",
        "osType": "Linux",
        "offer": "sles-12-sp5-byos",
        "publisher": "suse",
        "sku": "gen2",
        "version": "2023.01.16"
        "vmId": "1e28d8bb-f244-4957-bf51-f1732373050f"
        "vmSize": "Standard_B2s",
        "privateIpAddress": "10.0.0.4",
        "location": "eastus"
    },
    "signature": "signature",
    "pkcs7": "pkcs7",
    "cloud_provider": "microsoft"
}
```

This information is pulled from the Azure Instance metadata endpoint:
http://169.254.169.254/metadata/instance?api-version=2021-02-01. Note: the exact information in the
*document* entry may vary.
