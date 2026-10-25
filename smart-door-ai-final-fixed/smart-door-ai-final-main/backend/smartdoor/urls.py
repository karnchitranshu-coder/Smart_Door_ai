from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path


def api_root(request):
    return JsonResponse({
        "service": "Smart Door AI API",
        "status": "ok",
        "health": "/api/health",
        "api_root": "/api/",
        "note": "Use the documented /api/* endpoints; the dashboard is hosted separately.",
    })

urlpatterns = [
    path("", api_root),
    path("admin/", admin.site.urls),
    path("api/", include("door.urls")),
]
