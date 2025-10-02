from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import HttpResponse
from django.utils import timezone
from django.shortcuts import get_object_or_404

from rest_framework.views import APIView
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import File, Folder, SharedLink
from .serializers import FileSerializer, FolderSerializer

class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer

    def get_queryset(self):
        return File.objects.filter(owner=self.request.user, deleted_at__isnull=True)
    
    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({'error': 'Файл не передан'}, status=status.HTTP_400_BAD_REQUEST)
        
        if uploaded_file.size > settings.MAX_FILE_UPLOAD_MB * 1024 * 1024:
            return Response({'error': 'Размер файла превышает допустимый'}, status=status.HTTP_400_BAD_REQUEST)
        
        if uploaded_file.content_type not in settings.ALLOWED_FILE_MIME_TYPE:
            return Response({'error': 'Недопустимый размер файла'}, status=status.HTTP_400_BAD_REQUEST)
        
        path = default_storage.save(f'user_{request.user.id}/{uploaded_file.name}', ContentFile(uploaded_file.read()))
        file_obj = File.objects.create(
            owner=request.user,
            name=uploaded_file.name,
            size=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            path=path
        )
        
        # generate_preview.delay(file_obj.id)

        serializer = self.get_serializer(file_obj, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True):
    def download(self, request, pk=None):
       file_obj = self.get_object() 
       internal_path = '/protected-media/' + quote(file_obj.path.lstrip('/'))
       response = HttpResponse()
       response['Content-Type'] = file_obj.mime_type or 'application/octet-stream'
       response['Content-Disposition'] = f'attachment; filename="{quote(file_obj.name)}"'
       response['X-Accel-Redirect'] = internal_path
       return response
    
    @action(detail=True)
    def preview(self, request, pk=None):
        file_obj = self.get_object()
        if not file_obj.preview_image:
            return Responce({'error': 'Не удалось загрузить превью'})
        
        internal_path = '/protected-media/' + quote(file_obj.preview_image.lstrip('/'))
        response = HttpResponse()
        response['Content-Type'] = 'image/jpeg'
        response['X-Accel-Redirect'] = internal_path
        return response
    
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        file_obj = self.get_object()
        folder_id = request.data.get('folder_id')

        if not folder_id:
            return Response({'message': f'Не указан folder_id'})
        
        file_obj.folder_id = folder_id
        file_obj.save()
        return Response({'message': f'Файл {file_obj.name} перемещен'})
    
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        files = request.FILES.getlist('files')
        uploaded_files = []

        for uploaded_file in files:
            path = default_storage.save(
                f'user_{request.user.id}/{uploaded_file.name}', 
                ContentFile(uploaded_file.read())
            )
            file_obj = File.objects.create(
                owner=request.user,
                name=uploaded_file.name,
                size=uploaded_file.size,
                mime_type=uploaded_file.content_type,
                path=path
            )
            uploaded_files.append(file_obj)
            serializer = self.get_serializer(uploaded_files, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def share(self, request, pk=None):
        file_obj = self.get_object()
        ttl_minutes = int(request.data.get('ttl_minutes', 60))
        shared_link = file_obj.shared_links.create(expires_at=timezone.now()+timezone.timedelta(minutes=ttl_minutes),
                                                   max_downloads=request.data.get('max_downloads', None))
        url = request.build_absolute_uri(f'/p/{shared_link.token}/')
        return Response({'url': url})


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer

    def get_queryset(self):
        return Folder.objects.filter(owner=self.request.user)
    
    def perform_destroy(self, instance):
        files = File.objects.filter(folder=instance, deleted_at__isnull=True)
        files.update(deleted_at=timezone.now())
        # instance.delete()
    
    @action(detail=True)
    def files(self, request, pk=None):
        folder = self.get_object()
        files = File.objects.filter(owner=request.user, folder=folder, deleted_at_isnull=True)
        serializer = FileSerializer(files, many=True, context={'request': request})
        return Response(serializer.data)


class PublicSharedFileView(APIView):
    def get(self, request, token):
        shared_link = get_object_or_404(SharedLink, token=token)
        if shared_link.expires_at and timezone.now() > shared_link.expires_at:
            return Response({'error': 'Срок действия ссылки истек'}, status=status.HTTP_404_NOT_FOUND)
        if shared_link.max_downloads and shared_link.download_count >= shared_link.max_downloads:
            return Response({'error': 'Лимит скачивания файла исчерпан'})
        
        file_obj = shared_link.file

        shared_link.download_count += 1
        shared_link.save(update_fields=['download_count'])

        internal_path = '/protected-media/' + file_obj.path.lstrip('/')
        response = HttpResponse()
        response['Content-Type'] = file_obj.mime_type or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
        response['X-Accel-Redirect'] = internal_path
        return response