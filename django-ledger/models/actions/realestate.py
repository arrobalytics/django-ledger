# from dateutil.relativedelta import relativedelta
# from django.core.exceptions import ValidationError
# from django.db.models import Q, Sum
# from numpy import array as np_array
#
# from books.models.io import IOBase
# from books.params import params_mort
#
#
# class IORealEstate(IOBase):
#
#     def get_cashflow(self, cum=False):
#
#         activities = ['op', 'fin']
#         cf = getattr(self, 'ledger').get_ts_df(cum=cum, activity=activities, account=1010).sum()
#         return cf
#
#     def tx_buy_real_estate(self, cost, purchase_date, desc=None, ltv_ratio=0,
#                            mortgage_rate=None, loan_type='conv30',
#                            add_depr=True):
#
#         if ltv_ratio > 0 and mortgage_rate is None:
#             raise ValidationError('"mortgage_rate" parameter is required if ltv > 0')
#         elif mortgage_rate and mortgage_rate < 0:
#             raise ValidationError('Rate must be greater than 0')
#
#         origin = 'tx_buy_real_estate'
#         activity = 'inv'
#         start_date, end_date, je_desc = self.preproc_je(start_date=purchase_date,
#                                                         desc=desc,
#                                                         origin=origin)
#         freq = 'nr'
#         je = getattr(self, 'ledger').jes.create(desc=je_desc,
#                                                 freq=freq,
#                                                 start_date=start_date,
#                                                 origin=origin,
#                                                 activity=activity)
#
#         tx_params = dict()
#         tx_params['freq'] = freq
#         tx_params['amount'] = cost * (1 - ltv_ratio)
#
#         je.txs.create(tx_type='credit',
#                       account=getattr(self, 'ACM').objects.get(code__exact=1010),
#                       params=tx_params,
#                       amount=tx_params['amount'])
#
#         tx_params['amount'] = cost
#         je.txs.create(tx_type='debit',
#                       account=getattr(self, 'ACM').objects.get(code__exact=1610),
#                       params=tx_params,
#                       amount=tx_params['amount'])
#
#         if ltv_ratio > 0:
#             tx_params['amount'] = cost * ltv_ratio
#             je.txs.create(tx_type='credit',
#                           account=getattr(self, 'ACM').objects.get(code__exact=2130),
#                           params=tx_params,
#                           amount=tx_params['amount'])
#
#             self.tx_mort(loan_amount=cost * ltv_ratio, rate=mortgage_rate, start_date=purchase_date,
#                          loan_type=loan_type)
#
#         try:
#             je.clean()
#         except ValidationError:
#             je.txs.all().delete()
#             je.delete()
#             raise ValidationError('Something went wrong cleaning journal entry ID:{x1}'.format(x1=je.id))
#
#         # todo: use parent_je??
#         if add_depr:
#             self.tx_depreciation(start_date=start_date, dep_amount=cost, desc=desc)
#
#         # if add_apr:
#         #     # todo: need to customize function for generic calls.
#         #     # todo: add more validation to the transaction.
#         #     self.tx_appreciation(ledger=self.ledger, start_date=start_date, apr_base=cost, apr_rate=apr_rate,
#         #                          apr_years=apr_years, apr_months=apr_months)
#
#     def tx_rental_monthly_income(self, rent_amt, start_date, end_date):
#         act = 'op'
#
#         self.tx_income(income=rent_amt, start_date=start_date, activity=act, freq='m',
#                        end_date=end_date)
#
#     def tx_mort(self, loan_amount, rate, start_date, asset_acc=1010, int_exp_acc=6130, mort_ltl_acc=2130,
#                 loan_type='conv30', desc=None, parent_je=None):
#         origin = 'tx_mort'
#         activity = 'fin'
#         start_date, end_date, je_desc = self.preproc_je(start_date=start_date, desc=desc,
#                                                         origin=origin)
#
#         if loan_type == 'conv30':
#             periods = 360
#             freq = 'sm'
#             start_date = start_date + relativedelta(months=2)
#             end_date = start_date + relativedelta(years=int(periods / 12))
#             mort_params = params_mort(rate=rate / 12, amount=loan_amount, periods=periods)
#
#         elif loan_type == 'int_only':
#             periods = 360
#             freq = 'sm'
#             end_date = start_date + relativedelta(years=int(periods / 12))
#             mort_params = params_mort(rate=rate / 12, amount=loan_amount, periods=periods, fv=loan_amount)
#
#         je = self.ledger.jes.create(desc=je_desc,
#                                     freq=freq,
#                                     start_date=start_date,
#                                     end_date=end_date,
#                                     origin=origin,
#                                     activity=activity,
#                                     parent=parent_je)
#
#         tx_params = dict()
#         tx_params['freq'] = freq
#         tx_params['start_date'] = start_date.strftime('%Y-%m-%d')
#         tx_params['end_date'] = end_date.strftime('%Y-%m-%d')
#         tx_params['periods'] = periods
#         tx_params['rate'] = rate
#
#         tx_params['amount'] = mort_params['payments'] * periods
#         tx_params['mort_payment'] = mort_params['payments']
#         tx_params['series'] = np_array([mort_params['payments']] * periods)
#         je.txs.create(tx_type='credit',
#                       account=getattr(self, 'ACM').objects.get(code__exact=asset_acc),
#                       params=tx_params,
#                       amount=tx_params['amount'])
#
#         tx_params['series'] = -mort_params['i_payments']
#         tx_params['amount'] = -mort_params['i_payments'].sum()
#         je.txs.create(tx_type='debit',
#                       account=getattr(self, 'ACM').objects.get(code__exact=int_exp_acc),
#                       params=tx_params,
#                       amount=tx_params['amount'])
#
#         i_payments = mort_params['payments'] + mort_params['i_payments']
#         tx_params['series'] = i_payments
#         tx_params['amount'] = i_payments.sum()
#         je.txs.create(tx_type='debit',
#                       account=getattr(self, 'ACM').objects.get(code__exact=mort_ltl_acc),
#                       params=tx_params,
#                       amount=tx_params['amount'])
#
#     def tx_vacancy(self, method='months', months=None, rate=None, start_date=None, end_date=None, desc=None):
#         origin = 'tx_vacancy'
#         act = 'op'
#
#         monthly_rent = self.get_subject_prop('monthly_rent')
#
#         if start_date is None:
#             start_date = self.get_subject_prop('purchase_date')
#
#         if monthly_rent is None:
#             raise ValidationError('Must determine monthly rent first')
#
#         else:
#             if method == 'months':
#                 if months is None:
#                     raise ValidationError('Must provide months parameter')
#                 else:
#                     tx_params = dict(vacancy_method='months', vacancy_months=months)
#                     amount = months * monthly_rent / 12
#
#             elif method == rate:
#                 if rate is None:
#                     raise ValidationError('Must provide rate parameter')
#                 else:
#                     tx_params = dict(vacancy_method='rate', vacancy_rate=rate)
#                     amount = 12 * monthly_rent * rate
#
#             self.tx_generic(amount=amount, start_date=start_date, debit_acc=6400, credit_acc=1010,
#                             activity=act, tx_params=tx_params, freq='m', end_date=end_date, origin=origin, desc=desc)
#
#     def cap_rate(self, return_noi=False, return_ppeval=False, to_json=False):
#         net_op_inc = self.ledger.income_statement(cum=False, activity='op', signs=True)
#         if return_noi:
#             return net_op_inc
#         net_op_inc = net_op_inc.resample(rule='12m', axis=1, closed='left').sum().sum()
#         net_op_inc.name = 'Net Operating Income'
#
#         ppe_val = self.ledger.get_ts_df(role='ppe')
#         if return_ppeval:
#             return ppe_val
#         ppe_val = ppe_val[ppe_val.index.get_level_values('name') == 'Buildings'].reset_index(drop=True).sum()
#         ppe_val.name = 'Property Value'
#
#         cap_r_ser = net_op_inc / ppe_val
#         cap_r_ser.name = 'Cap Rate'
#         cap_r_ser.dropna(inplace=True)
#
#         if to_json:
#             return cap_r_ser.to_json(orient='index', date_format='iso')
#         return cap_r_ser
#
#     def coc_rate(self, return_cashinv=False, to_json=False):
#         cash_inv = getattr(self, 'TXM').objects.filter(
#             Q(journal_entry__activity='inv') &
#             Q(journal_entry__txs__account__code=1610) &
#             Q(account__code=1010)
#         ).aggregate(Sum('amount'))['amount__sum']
#         if return_cashinv:
#             return cash_inv
#
#         cf = self.get_cashflow(cum=False)
#         cf = cf.resample(rule='12m', closed='left').sum()
#
#         coc_rate_ser = cf / float(cash_inv)
#         coc_rate_ser.reset_index(drop=True, inplace=True)
#         coc_rate_ser.dropna(inplace=True)
#         coc_rate_ser.name = 'CoC Rate'
#
#         if to_json:
#             return coc_rate_ser.to_json(orient='index', date_format='iso')
#         return coc_rate_ser
#
#     def roi(self, return_rinc=False, return_uinc=False, return_cashinv=False, to_json=False):
#         # todo: add if any() is true, validation error.
#         r_inc = self.income(activity='op') + self.income(activity='fin')
#         r_inc.rename('r_income', inplace=True)
#         if return_rinc:
#             return r_inc
#
#         u_inc = self.get_ts_df(account=3920, cum=False)
#         u_inc = u_inc.sum()
#         u_inc.rename('u_income', inplace=True)
#         if return_uinc:
#             return return_uinc
#
#         inc = r_inc + u_inc
#         inc = inc.resample(rule='12m', closed='left').sum().dropna()
#         cash_inv = getattr(self, 'TXM').objects.filter(
#             Q(journal_entry__activity='inv') &
#             Q(journal_entry__transactions__account__acc_code=1610) &
#             Q(account__acc_code=1010)
#         ).aggregate(Sum('amount'))['amount__sum']
#         if return_cashinv:
#             return cash_inv
#
#         roi_ser = inc / float(cash_inv)
#         roi_ser.name = 'RoI'
#         roi_ser.dropna(inplace=True)
#
#         if to_json:
#             return roi_ser.to_json(orient='index', date_format='iso')
#         return roi_ser
#
#     # def init_forecast(self):
#     #
#     #     # if not self.id:
#     #     #     self.full_clean()
#     #     #     self.save()
#     #
#     #     fcst, created = self.forecast.get_or_create(desc=self.name,
#     #                                                 years_horizon=self.horizon)
#     #
#     #     if not created:
#     #         print('Forecast already initiated for {x1}'.format(x1=self.__str__()))
#     #
#     #     return fcst
#
#     # def delete_forecast(self):
#     #
#     #     self.forecast.all().delete()
#
#     def create_forecast(self,
#                         # replace=True,
#                         add_depr=True,
#                         # add_apr=True,
#                         extra_funding=1.05):
#
#         # if replace:
#         #     self.delete_forecast()
#         #
#         # fcst = self.init_forecast()
#
#         # Purchase Property:
#         self.tx_buy_real_estate(
#             cost=self.get_subject_prop('init_cost'),
#             purchase_date=self.get_subject_prop('purchase_date'),
#             ltv_ratio=self.get_subject_prop('mort_ltv'),
#             mortgage_rate=self.get_subject_prop('mort_rate'),
#             add_depr=add_depr,
#         )
#         # Renovations:
#         if self.get_subject_prop('renovation_init') is not None:
#             self.tx_generic(amount=self.get_subject_prop('renovation_init'),
#                             start_date=self.get_subject_prop('renovation_start_date'),
#                             end_date=self.get_subject_prop('renovation_end_date'),
#                             debit_acc=1610,
#                             credit_acc=1010,
#                             activity='inv',
#                             desc='{x1}-Renovations Init'.format(x1=self.subject.name),
#                             freq='m')
#
#         if self.get_subject_prop('renovation_exit') is not None:
#             self.tx_generic(amount=self.get_subject_prop('renovation_exit'),
#                             start_date=self.get_subject_prop('sale_date'),
#                             debit_acc=1610,
#                             credit_acc=1010,
#                             activity='inv',
#                             desc='{x1}-Renovations Exit'.format(x1=self.subject.name),
#                             freq='nr')
#
#         # # Closing Costs:
#         if self.get_subject_prop('closing_costs'):
#             self.tx_generic(amount=self.get_subject_prop('closing_costs'),
#                             start_date=self.get_subject_prop('purchase_date'),
#                             debit_acc=1610,
#                             credit_acc=1010,
#                             activity='inv',
#                             desc='{x1}-Closing Costs'.format(x1=self.subject.name),
#                             freq='nr')
#
#         # Prop Management -----------
#         if self.get_subject_prop('prop_mgmt_rate'):
#             self.tx_generic(amount=self.get_subject_prop('prop_mgmt_monthly'),
#                             start_date=self.get_subject_prop('start_rent_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6300,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-Property Mgmt'.format(x1=self.subject.name),
#                             freq='m')
#
#         # HOA -----------
#         if self.get_subject_prop('prop_hoa_year'):
#             self.tx_generic(amount=self.get_subject_prop('prop_hoa_month'),
#                             start_date=self.get_subject_prop('purchase_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6253,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-HOA'.format(x1=self.subject.name),
#                             freq='m')
#
#         # Vacancy Cost -----------------
#         if self.get_subject_prop('vacancy_rate'):
#             self.tx_generic(amount=self.get_subject_prop('vacancy_cost_monthly'),
#                             start_date=self.get_subject_prop('start_rent_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6400,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-Vacancy'.format(x1=self.subject.name),
#                             freq='m')
#
#         # Repairs -------------
#         if self.get_subject_prop('repair_allow_rate'):
#             self.tx_generic(amount=self.get_subject_prop('repair_monthly'),
#                             start_date=self.get_subject_prop('start_rent_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6252,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-Vacancy'.format(x1=self.subject.name),
#                             freq='m')
#
#         # Property Taxes -------------
#         if self.get_subject_prop('prop_taxes_year'):
#             self.tx_generic(amount=self.get_subject_prop('prop_taxes_monthly'),
#                             start_date=self.get_subject_prop('purchase_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6280,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-Prop.Taxes'.format(x1=self.subject.name),
#                             freq='m')
#
#         # Insurance -------------
#         if self.get_subject_prop('insurance_year'):
#             self.tx_generic(amount=self.get_subject_prop('insurance_monthly'),
#                             start_date=self.get_subject_prop('purchase_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6120,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-Insurance'.format(x1=self.subject.name),
#                             freq='m')
#
#         # Utilities -------------
#         if self.get_subject_prop('utilities_year'):
#             self.tx_generic(amount=self.get_subject_prop('utilities_month'),
#                             start_date=self.get_subject_prop('purchase_date'),
#                             end_date=self.get_subject_prop('sale_date'),
#                             debit_acc=6290,
#                             credit_acc=1010,
#                             activity='op',
#                             desc='{x1}-Utilities'.format(x1=self.subject.name),
#                             freq='m')
#
#         # Add Cash For Purchase w/Safety Net
#         self.tx_capital(
#             capital=self.get_subject_prop('init_cost') * (1 - self.get_subject_prop('mort_ltv')) * extra_funding,
#             start_date=self.get_subject_prop('purchase_date'),
#             desc='{x1}-Capital Contribution'.format(x1=self.subject.name),
#             freq='nr')
#
#         # Monthly Rent:
#         if self.get_subject_prop('rent_year'):
#             self.tx_income(desc='{x1}-Rent Income'.format(x1=self.subject.name),
#                            income=self.get_subject_prop('rent_month'),
#                            start_date=self.get_subject_prop('start_rent_date'),
#                            end_date=self.get_subject_prop('sale_date'),
#                            activity='op',
#                            freq='m')  # todo: next months!!
#
#         # todo: Add Disposal -------------
#         # if self.cost_of_sale_rate:
#         #     self.forecast.x_generic(amount=self.cost_of_sale,
#         #                             start_date=self.sale_date,
#         #                             debit_acc=6290,
#         #                             credit_acc=1010,
#         #                             activity='inv',
#         #                             desc='{x1}-Cost of Sale'.format(x1=self.name),
#         #                             freq='nr')
