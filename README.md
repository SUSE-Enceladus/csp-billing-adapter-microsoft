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
case it is *microsoft*.

## Get Account Info

The `get_account_info` function provides metadata information for the running
instance or container. The structure of this information is as follows:

```
{
    "compute": {
        "azEnvironment": "AzurePublicCloud",
        "customData": "",
        "isHostCompatibilityLayerVm": "false",
        "licenseType": "",
        "location": "eastus",
        "name": "csp-adapter-test",
        "offer": "sles-15-sp4-byos",
        "osProfile": {
            "adminUsername": "foo",
            "computerName": "csp-adapter-test"
        },
        "osType": "Linux",
        "placementGroupId": "",
        "plan": {
            "name": "",
            "product": "",
            "publisher": ""
        },
        "platformFaultDomain": "0",
        "platformUpdateDomain": "0",
        "provider": "Microsoft.Compute",
        "publicKeys": [
            {
                "keyData": ssh_public_key,
                "path": "/home/foo/.ssh/authorized_keys"
            }
        ],
        "publisher": "suse",
        "resourceGroupName": "foo",
        "resourceId": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/foo/providers/Microsoft.Compute/virtualMachines/csp-adapter-test",
        "securityProfile": {
            "secureBootEnabled": "false",
            "virtualTpmEnabled": "false"
        },
        "sku": "gen2",
        "storageProfile": {
            "dataDisks": [],
            "imageReference": {
                "id": "",
                "offer": "sles-15-sp4-byos",
                "publisher": "suse",
                "sku": "gen2",
                "version": "2023.05.06"
            },
            "osDisk": {
                "caching": "ReadWrite",
                "createOption": "FromImage",
                "diffDiskSettings": {
                    "option": ""
                },
                "diskSizeGB": "30",
                "encryptionSettings": {
                    "enabled": "false"
                },
                "image": {
                    "uri": ""
                },
                "managedDisk": {
                    "id": "/subscriptions/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx/resourceGroups/foo/providers/Microsoft.Compute/disks/csp-adapter-test_Os_Disk_1_12345678901234567890",
                    "storageAccountType": "Premium_LRS"
                },
                "name": "csp-adapter-test_Os_Disk_1_12345678901234567890",
                "osType": "Linux",
                "vhd": {
                    "uri": ""
                },
                "writeAcceleratorEnabled": "false"
            }
        },
        "subscriptionId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "tags": "Cost Center:123456789;Department:foo;Environment:foo;Finance Business Partner:foo;General Ledger Code:123456789;Group:foo;Owner:foo;Stakeholder:foo",
        "tagsList": [
            {
                "name": "Cost Center",
                "value": "12345678"
            },
            {
                "name": "Department",
                "value": "foo"
            },
            {
                "name": "Environment",
                "value": "foo"
            },
            {
                "name": "Finance Business Partner",
                "value": "foo"
            },
            {
                "name": "General Ledger Code",
                "value": "123456789"
            },
            {
                "name": "Group",
                "value": "foo"
            },
            {
                "name": "Owner",
                "value": "foo"
            },
            {
                "name": "Stakeholder",
                "value": "foo"
            }
        ],
        "version": "2023.05.06",
        "vmId": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "vmScaleSetName": "",
        "vmSize": "Standard_B2s",
        "zone": ""
    },
    "network": {
        "interface": [
            {
                "ipv4": {
                    "ipAddress": [
                        {
                            "privateIpAddress": "10.0.0.8",
                            "publicIpAddress": "192.168.1.1"
                        }
                    ],
                    "subnet": [
                        {
                            "address": "10.0.0.0",
                            "prefix": "24"
                        }
                    ]
                },
                "ipv6": {
                    "ipAddress": []
                },
                "macAddress": "123456789ABCD"
            }
        ]
    },
    "attestedData": {
        "encoding": "pkcs7",
        "signature": signature
    },
    "cloud_provider": "microsoft"
}
```

This information is pulled from the Azure Instance metadata endpoint:
http://169.254.169.254/metadata/instance?api-version=2021-02-01. Note: the exact information in the
*document* entry may vary.
