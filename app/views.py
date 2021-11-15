from django.http import HttpResponse


def index(request):
    return HttpResponse("Hi")


def about(request):
    return HttpResponse("Soon")
