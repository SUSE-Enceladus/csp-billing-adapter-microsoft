import csp_billing_adapter

from csp_billing_adapter.config import Config


@csp_billing_adapter.hookimpl
def setup_adapter(config: Config):
    pass


@csp_billing_adapter.hookimpl(trylast=True)
def meter_billing(
    config: Config,
    dimensions: dict,
    timestamp: str,
):
    pass


@csp_billing_adapter.hookimpl(trylast=True)
def get_csp_name(config: Config):
    return 'microsoft'


@csp_billing_adapter.hookimpl(trylast=True)
def get_account_info(config: Config):
    pass
