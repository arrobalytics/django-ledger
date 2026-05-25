"""Country-specific defaults for Germany."""

DE_SETTING_DEFAULTS = {
    'CURRENCY_SYMBOL': '€',
    'SPACED_CURRENCY_SYMBOL': True,
    'REQUIRE_SUPPORTING_DOCUMENT_ON_POST': True,
    'DEFAULT_COA': 'skr03',
    # EntityTaxProfile defaults for new entities (override when status is granted):
    # 'exempt' | 'small_business' | 'standard'
    'DEFAULT_TAX_REGIME': 'exempt',
    'DEFAULT_VAT_RATE': '0.19',
    'KLEINUNTERNEHMER_PRIOR_YEAR_LIMIT': 22000,
    'KLEINUNTERNEHMER_CURRENT_YEAR_LIMIT': 50000,
}
