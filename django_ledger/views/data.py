from django.http import JsonResponse
from django.views.generic import View


class TestJsonData(View):
    http_method_names = ['get']

    def get(self, request):
        if request.user.is_authenticated:
            return JsonResponse({
                'data': 'You got this!'.split()
            })
        return JsonResponse({
            'message': 'Unauthorized'
        }, status=401)
