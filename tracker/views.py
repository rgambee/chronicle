from django.http import HttpRequest, HttpResponse


def index(_: HttpRequest) -> HttpResponse:
    """Placeholder view for the root url"""
    return HttpResponse("index")
