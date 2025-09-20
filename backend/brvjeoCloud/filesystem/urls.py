from django.urls import path

from rest_framework.routers import SimpleRouter

from . import views


router = SimpleRouter()
# router.register(r'files', views.FileViewSet, basename='file')
# router.register(r'folders', views.FolderViewSet, basename='folder')

urlpatterns = [
    # --- Files ---
    path("api/files/upload/", views.FileUploadView.as_view(), name="file-upload"),
    path("api/files/", views.FileListView.as_view(), name="file-list"),
    path("api/files/<int:pk>/download/", views.FileDownloadView.as_view(), name="file-download"),
    path("api/files/<int:pk>/preview/", views.FilePreviewView.as_view(), name="file-preview"),
    path("api/files/<int:pk>/", views.FileDeleteView.as_view(), name="file-delete"),
    path("api/files/<int:pk>/share/", views.FileShareView.as_view(), name="file-share"),
    path("api/files/<int:pk>/move/", views.FileMoveView.as_view(), name="file-move"),
    path("api/files/bulk-upload/", views.FileBulkUploadView.as_view(), name="file-bulk-upload"),

    # --- Folders ---
    path("api/folders/", views.FolderCreateView.as_view(), name="folder-create"),

    # --- Public link (без аутентификации) ---
    path("p/<str:token>/", views.PublicSharedFileView.as_view(), name="public-file"),
]

# urlpatterns += router.urls