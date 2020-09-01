from django.http import JsonResponse
from django.views.generic import View
from django_ledger.models.entity import EntityModel
from calendar import month_name


class TestJsonData(View):
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            entity = EntityModel.objects.for_user(
                user_model=self.request.user).get(
                slug__exact=self.kwargs['entity_slug'])

            entity_digest = entity.digest(
                user_model=self.request.user,
                equity_only=True,
                by_period=True,
                process_groups=True
            )

            group_balance_by_period = entity_digest['tx_digest']['group_balance_by_period']
            entity_data = {f'{month_name[k[1] + 1]} {k[0]}': {d: float(f) for d, f in v.items()} for k, v in
                           group_balance_by_period.items()}
            return JsonResponse({
                'results': {
                    'entity_slug': entity.slug,
                    'entity_name': entity.name,
                    'entity_data': entity_data
                }
            })

        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)
