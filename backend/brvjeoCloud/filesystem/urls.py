from django.urls import include, path

from rest_framework.routers import SimpleRouter

from . import views


router = SimpleRouter()
router.register('files', views.FileViewSet, basename='file')
router.register('folders', views.FolderViewSet, basename='folder')

urlpatterns = [
    path("api/", include([
        path("files/upload/", views.FileUploadView.as_view(), name="file-upload"),
        path("files/<int:pk>/download/", views.FileDownloadView.as_view(), name="file-download"),
        path("files/<int:pk>/preview/", views.FilePreviewView.as_view(), name="file-preview"),
        path("files/<int:pk>/share/", views.FileShareView.as_view(), name="file-share"),
        path("files/<int:pk>/move/", views.FileMoveView.as_view(), name="file-move"),
        path("files/bulk-upload/", views.FileBulkUploadView.as_view(), name="file-bulk-upload"),
        path("<str:token>/", views.PublicSharedFileView.as_view(), name="public-file"),
        path("", include(router.urls)),
    ])),
]