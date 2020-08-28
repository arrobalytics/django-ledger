from django.http import JsonResponse
from django.views.generic import View


class TestJsonData(View):

    def get(self, request):
        return JsonResponse({
            'data': 'You got this!'.split()
        })
