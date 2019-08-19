from django.http import HttpResponse


def index(request):
    return HttpResponse('Project Alice user interface')