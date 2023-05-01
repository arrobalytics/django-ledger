Quickstart
==========

.. code:: ipython3

    import os

    import django
    import pandas as pd

    os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
    os.environ['DJANGO_SETTINGS_MODULE'] = 'dev_env.settings'
    os.chdir('/Users/s64420/git/django-ledger/')

    django.setup()

    from django_ledger.models.entity import EntityModel
    from django.contrib.auth import get_user_model
    from django_ledger.io import roles

.. code:: ipython3

    UserModel = get_user_model()
    user_model = UserModel.objects.get(username__exact='elarroba')
    user_model




.. parsed-literal::

    <User: elarroba>



.. code:: ipython3

    entity_model = EntityModel.objects.first()
    entity_model.slug




.. parsed-literal::

    'miguel-sanda-l28qpqar'



Get All Accounts
----------------

.. code:: ipython3

    coa_qs, coa_map = entity_model.get_all_coa_accounts()

    coa_qs




.. parsed-literal::

    <ChartOfAccountModelQuerySet [<ChartOfAccountModel: miguel-sanda-l28qpqarpx960x-coa: Default CoA>]>



Get Default CoA Accounts
------------------------

.. code:: ipython3

    entity_model.get_default_coa_accounts()




.. parsed-literal::

    <AccountModelQuerySet [<AccountModel: ASSETS - 1010: Cash (ASSET_CA_CASH/debit)>, <AccountModel: ASSETS - 1050: Short Term Investments (ASSET_CA_MKT_SEC/debit)>, <AccountModel: ASSETS - 1100: Accounts Receivable (ASSET_CA_RECV/debit)>, <AccountModel: ASSETS - 1110: Uncollectibles (ASSET_CA_UNCOLL/credit)>, <AccountModel: ASSETS - 1200: Inventory (ASSET_CA_INV/debit)>, <AccountModel: ASSETS - 1300: Prepaid Expenses (ASSET_CA_PREPAID/debit)>, <AccountModel: ASSETS - 1453AVC: A cool account created from the EntityModel API! (ASSET_CA_INV/debit)>, <AccountModel: ASSETS - 1453AVC2: A cool account created from the EntityModel API! (ASSET_CA_INV/debit)>, <AccountModel: ASSETS - 1453AVC23: A cool account created from the EntityModel API! (ASSET_CA_INV/debit)>, <AccountModel: ASSETS - 1453AVC233: A cool account created from the EntityModel API! (ASSET_CA_INV/debit)>, <AccountModel: ASSETS - 1510: Notes Receivable (ASSET_LTI_NOTES/debit)>, <AccountModel: ASSETS - 1520: Land (ASSET_LTI_LAND/debit)>, <AccountModel: ASSETS - 1530: Securities (ASSET_LTI_SEC/debit)>, <AccountModel: ASSETS - 1610: Buildings (ASSET_PPE_BUILD/debit)>, <AccountModel: ASSETS - 1611: Less: Buildings Accumulated Depreciation (ASSET_PPE_BUILD_ACCUM_DEPR/credit)>, <AccountModel: ASSETS - 1620: Plant (ASSET_PPE_PLANT/debit)>, <AccountModel: ASSETS - 1621: Less: Plant Accumulated Depreciation (ASSET_PPE_PLANT_DEPR/credit)>, <AccountModel: ASSETS - 1630: Equipment (ASSET_PPE_EQUIP/debit)>, <AccountModel: ASSETS - 1631: Less: Equipment Accumulated Depreciation (ASSET_PPE_EQUIP_ACCUM_DEPR/credit)>, <AccountModel: ASSETS - 1640: Vehicles (ASSET_PPE_PLANT/debit)>, '...(remaining elements truncated)...']>



Get Given CoA Accounts
----------------------

.. code:: ipython3

    account_qs = entity_model.get_coa_accounts(coa_model=coa_qs.first())
    account_qs


::


    ---------------------------------------------------------------------------

    NameError                                 Traceback (most recent call last)

    Cell In[4], line 1
    ----> 1 account_qs = entity_model.get_coa_accounts(coa_model=coa_qs.first())
          2 account_qs


    NameError: name 'coa_qs' is not defined


.. code:: ipython3

    entity_model.get_coa_accounts(coa_model=coa_qs.first().uuid)




.. parsed-literal::

    <AccountModelQuerySet [<AccountModel: EQUITY - 3110: Common Stock (EQ_STOCK_COMMON/credit)>, <AccountModel: EQUITY - 3910: Available for Sale (EQ_ADJUSTMENT/credit)>, <AccountModel: EQUITY - 3030: Capital Account 3 (EQ_CAPITAL/credit)>, <AccountModel: EQUITY - 3920: PPE Unrealized Gains/Losses (EQ_ADJUSTMENT/credit)>, <AccountModel: EQUITY - 3930: Dividends & Distributions (EQ_DIVIDENDS/debit)>, <AccountModel: EQUITY - 3120: Preferred Stock (EQ_STOCK_PREFERRED/credit)>, <AccountModel: EQUITY - 3010: Capital Account 1 (EQ_CAPITAL/credit)>, <AccountModel: EQUITY - 3020: Capital Account 2 (EQ_CAPITAL/credit)>, <AccountModel: EQUITY - 4020: Investing Income (IN_PASSIVE/credit)>, <AccountModel: EQUITY - 4010: Sales Income (IN_OPERATIONAL/credit)>, <AccountModel: EQUITY - 4030: Interest Income (IN_INTEREST/credit)>, <AccountModel: EQUITY - 4050: Other Income (IN_OTHER/credit)>, <AccountModel: EQUITY - 4040: Capital Gain/Loss Income (IN_GAIN_LOSS/credit)>, <AccountModel: EQUITY - 5010: Cost of Goods Sold (COGS_REGULAR/debit)>, <AccountModel: ASSETS - 1110: Uncollectibles (ASSET_CA_UNCOLL/credit)>, <AccountModel: ASSETS - 1530: Securities (ASSET_LTI_SEC/debit)>, <AccountModel: ASSETS - 1620: Plant (ASSET_PPE_PLANT/debit)>, <AccountModel: ASSETS - 1300: Prepaid Expenses (ASSET_CA_PREPAID/debit)>, <AccountModel: ASSETS - 1920: PPE Unrealized Gains/Losses (ASSET_ADJUSTMENT/debit)>, <AccountModel: ASSETS - 1200: Inventory (ASSET_CA_INV/debit)>, '...(remaining elements truncated)...']>



.. code:: ipython3

    entity_model.get_coa_accounts(coa_model=coa_qs.first().slug)




.. parsed-literal::

    <AccountModelQuerySet [<AccountModel: EQUITY - 3110: Common Stock (EQ_STOCK_COMMON/credit)>, <AccountModel: EQUITY - 3910: Available for Sale (EQ_ADJUSTMENT/credit)>, <AccountModel: EQUITY - 3030: Capital Account 3 (EQ_CAPITAL/credit)>, <AccountModel: EQUITY - 3920: PPE Unrealized Gains/Losses (EQ_ADJUSTMENT/credit)>, <AccountModel: EQUITY - 3930: Dividends & Distributions (EQ_DIVIDENDS/debit)>, <AccountModel: EQUITY - 3120: Preferred Stock (EQ_STOCK_PREFERRED/credit)>, <AccountModel: EQUITY - 3010: Capital Account 1 (EQ_CAPITAL/credit)>, <AccountModel: EQUITY - 3020: Capital Account 2 (EQ_CAPITAL/credit)>, <AccountModel: EQUITY - 4020: Investing Income (IN_PASSIVE/credit)>, <AccountModel: EQUITY - 4010: Sales Income (IN_OPERATIONAL/credit)>, <AccountModel: EQUITY - 4030: Interest Income (IN_INTEREST/credit)>, <AccountModel: EQUITY - 4050: Other Income (IN_OTHER/credit)>, <AccountModel: EQUITY - 4040: Capital Gain/Loss Income (IN_GAIN_LOSS/credit)>, <AccountModel: EQUITY - 5010: Cost of Goods Sold (COGS_REGULAR/debit)>, <AccountModel: ASSETS - 1110: Uncollectibles (ASSET_CA_UNCOLL/credit)>, <AccountModel: ASSETS - 1530: Securities (ASSET_LTI_SEC/debit)>, <AccountModel: ASSETS - 1620: Plant (ASSET_PPE_PLANT/debit)>, <AccountModel: ASSETS - 1300: Prepaid Expenses (ASSET_CA_PREPAID/debit)>, <AccountModel: ASSETS - 1920: PPE Unrealized Gains/Losses (ASSET_ADJUSTMENT/debit)>, <AccountModel: ASSETS - 1200: Inventory (ASSET_CA_INV/debit)>, '...(remaining elements truncated)...']>



Get Accounts With Codes
-----------------------

.. code:: ipython3

    entity_model.get_accounts_with_codes(code_list='1453AVC233')




.. parsed-literal::

    <AccountModelQuerySet [<AccountModel: ASSETS - 1453AVC233: A cool account created from the EntityModel API! (ASSET_CA_INV/debit)>]>



Create Account Model
--------------------

.. code:: ipython3

    coa_model, account_model = entity_model.create_account_model(
        account_model_kwargs={
            'code': '1453AVC233',
            'role': roles.ASSET_CA_INVENTORY,
            'name': 'A cool account created from the EntityModel API!',
            'balance_type': roles.DEBIT,
            'active': True
        })

Vendor Models
=============

.. code:: ipython3

    entity_model.get_vendors()




.. parsed-literal::

    <VendorModelQuerySet [<VendorModel: Vendor: Brown-Perez>, <VendorModel: Vendor: Anthony Mullins>, <VendorModel: Vendor: Howard, Schmidt and Scott>, <VendorModel: Vendor: Griffin, Turner and Nelson>, <VendorModel: Vendor: Miller-Hughes>, <VendorModel: Vendor: Barton LLC>, <VendorModel: Vendor: Roach, Smith and Jenkins>, <VendorModel: Vendor: Michelle Hahn>]>



Customer Models
===============

.. code:: ipython3

    entity_model.get_customers()




.. parsed-literal::

    <CustomerModelQueryset [<CustomerModel: Customer: Bridget Ewing>, <CustomerModel: Customer: Leslie Robles>, <CustomerModel: Customer: Peterson, Butler and Perry>, <CustomerModel: Customer: Paula Cook>, <CustomerModel: Customer: William Wallace>, <CustomerModel: Customer: Hinton-Scott>, <CustomerModel: Customer: Heidi Perez>, <CustomerModel: Customer: Jonathan Vasquez>, <CustomerModel: Customer: Laurie Watkins>, <CustomerModel: Customer: Kenneth Perez>, <CustomerModel: Customer: Sara Hurley>, <CustomerModel: Customer: Michael Dennis>, <CustomerModel: Customer: Connie Johnson>, <CustomerModel: Customer: Brandi Mills>, <CustomerModel: Customer: Seth Garrison>, <CustomerModel: Customer: Joann Delgado DVM>, <CustomerModel: Customer: Joyce Murphy>]>



Bill Models
===========

.. code:: ipython3

    entity_model.get_bills()




.. parsed-literal::

    <BillModelQuerySet [<BillModel: Bill: B-2022-0000000052>, <BillModel: Bill: B-2022-0000000051>, <BillModel: Bill: B-2022-0000000050>, <BillModel: Bill: B-2022-0000000049>, <BillModel: Bill: B-2022-0000000048>, <BillModel: Bill: B-2023-0000000005>, <BillModel: Bill: B-2022-0000000047>, <BillModel: Bill: B-2022-0000000046>, <BillModel: Bill: B-2022-0000000045>, <BillModel: Bill: B-2022-0000000044>, <BillModel: Bill: B-2022-0000000043>, <BillModel: Bill: B-2022-0000000042>, <BillModel: Bill: B-2022-0000000041>, <BillModel: Bill: B-2022-0000000040>, <BillModel: Bill: B-2022-0000000039>, <BillModel: Bill: B-2022-0000000038>, <BillModel: Bill: B-2022-0000000037>, <BillModel: Bill: B-2022-0000000036>, <BillModel: Bill: B-2022-0000000035>, <BillModel: Bill: B-2022-0000000034>, '...(remaining elements truncated)...']>



Invoice Models
==============

.. code:: ipython3

    entity_model.get_invoices()




.. parsed-literal::

    <InvoiceModelQuerySet [<InvoiceModel: Invoice: I-2022-0000000046>, <InvoiceModel: Invoice: I-2022-0000000045>, <InvoiceModel: Invoice: I-2022-0000000044>, <InvoiceModel: Invoice: I-2022-0000000043>, <InvoiceModel: Invoice: I-2023-0000000004>, <InvoiceModel: Invoice: I-2022-0000000042>, <InvoiceModel: Invoice: I-2022-0000000041>, <InvoiceModel: Invoice: I-2022-0000000040>, <InvoiceModel: Invoice: I-2022-0000000039>, <InvoiceModel: Invoice: I-2022-0000000038>, <InvoiceModel: Invoice: I-2022-0000000037>, <InvoiceModel: Invoice: I-2022-0000000036>, <InvoiceModel: Invoice: I-2022-0000000035>, <InvoiceModel: Invoice: I-2022-0000000034>, <InvoiceModel: Invoice: I-2022-0000000033>, <InvoiceModel: Invoice: I-2022-0000000032>, <InvoiceModel: Invoice: I-2022-0000000031>, <InvoiceModel: Invoice: I-2022-0000000030>, <InvoiceModel: Invoice: I-2022-0000000029>, <InvoiceModel: Invoice: I-2022-0000000028>, '...(remaining elements truncated)...']>





