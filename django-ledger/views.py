from django.shortcuts import render


# from django.views.generic import DetailView
# from books.models import SubjectModel

def debug(request):

    context = dict()
    context['title'] = 'Books App Debug'
    context['msg'] = 'Hello There'
    return render(request,
                  template_name="books/debug_template.html",
                  context=context)

# def debug(request):
#     subj, created = SubjectModel.objects.get_or_create(subject_id='rental-1')
#     subj.reset_ledger('forecast')
#
#     PP = 217450
#     PD = '2017-4-15'
#     RMONTHS = 2
#     CC = .06
#     RENOV_INIT = 5000
#     RENOV_EXIT = 3500
#     H = 10
#     APR_RATE = .02
#     LTV = .8
#     MORT_INT = .045
#     VAC_RATE = .1
#     MONTHSTORENT = 2
#     rent_month = 1800
#
#     subj.prop_manager.add_horizon(years=H)
#     subj.prop_manager.add_purchase(purchase_price=PP, purchase_date=PD)
#     subj.prop_manager.add_financing(ltv=LTV, int_rate=MORT_INT, mort_years=30)
#
#     # subj.prop_manager.add_renovation(init_months=RMONTHS, init_amt=RENOV_INIT, exit_amt=RENOV_EXIT)
#     # subj.prop_manager.add_property_taxes(prop_taxes_amt=2250)
#     # subj.prop_manager.add_insurance(amount=55, freq='monthly')
#     # subj.prop_manager.add_prop_mgmnt_rate(prop_mgmt_rate=.10)
#     # subj.prop_manager.add_hoa(hoa_amount=257, freq='monthly')
#     # subj.prop_manager.add_months_to_rent(months=MONTHSTORENT)
#     # subj.prop_manager.add_rent(amount=rent_month)
#     # subj.prop_manager.add_vacancy(vac_rate=VAC_RATE)
#     # subj.prop_manager.add_repair_allowance(rep_allow_rate=.10)
#
#     # subj.prop_manager.add_utilities(amount=20, freq='monthly')
#     # subj.prop_manager.add_discount_rate(disc_rate=.04)
#     # subj.prop_manager.add_rent_growth(rent_growth_rate=50/1800)
#     # subj.prop_manager.add_closing_costs(percent_pp=CC)
#
#     subj.io.create_forecast()
#
#     context = dict()
#     context['title'] = 'Books App Debug'
#     context['msg'] = 'Hello There'
#     context['subj'] = subj
#
#     for p in subj.prop_list:
#         context[p] = subj.prop_manager.get(p)
#
#     return render(request,
#                   template_name="books/debug_template.html",
#                   context=context)
