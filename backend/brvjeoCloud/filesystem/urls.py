from django.urls import include, path

from rest_framework.routers import DefaultRouter

from . import views
from .views import FileViewSet


router = DefaultRouter()
router.register(r"files", FileViewSet, basename="file")

urlpatterns = [
    path("api/", include([
        router.urls,
        path("<str:token>/", views.PublicSharedFileView.as_view(), name="public-file"),
    ])),
]