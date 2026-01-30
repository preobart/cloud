from urllib.parse import quote

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..tasks import generate_preview
from .models import File, Folder, SharedLink
from .permissions import IsOwner
from .serializers import FileSerializer, FolderSerializer


class FileViewSet(viewsets.ModelViewSet):
    queryset = File.objects.all()
    serializer_class = FileSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return File.objects.none()
        return File.objects.filter(owner=self.request.user, deleted_at__isnull=True)
    
    def perform_destroy(self, instance):
        instance.deleted_at = timezone.now()
        instance.save()

    @swagger_auto_schema(
        request_body=None,
        consumes=["multipart/form-data"],
        responses={201: FileSerializer()},
    )
    def create(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get('file')
        folder = request.data.get('folder')
        name = request.data.get('name')

        if not uploaded_file:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        used = File.objects.filter(owner=request.user, deleted_at__isnull=True).aggregate(s=Sum('size'))['s'] or 0
        if used + uploaded_file.size > settings.QUOTA_STORAGE_BYTES_PER_USER:
            return Response({'error': 'Storage quota exceeded'}, status=status.HTTP_403_FORBIDDEN)

        folder = Folder.objects.filter(id=folder, owner=request.user).first() if folder else None
        file_obj = File(
            owner=request.user,
            name=name or uploaded_file.name,
            size=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            folder=folder
        )
        file_obj.save() 

        file_obj.file = uploaded_file
        file_obj.save()

        generate_preview.delay(file_obj.pk)

        serializer = self.get_serializer(file_obj, context={'request': request})
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        file_obj = self.get_object()
        if not file_obj.file or not file_obj.file.name:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        internal_path = '/protected-media/' + file_obj.file.name.lstrip('/')
        response = HttpResponse()
        response['Content-Type'] = file_obj.mime_type or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{quote(file_obj.name)}"'
        response['X-Accel-Redirect'] = internal_path
        return response
    
    @action(detail=True)
    def preview(self, request, pk=None):
        file_obj = self.get_object()
        if not file_obj.preview_image or not file_obj.preview_image.name:
            return Response({'error': 'Preview not available'}, status=status.HTTP_404_NOT_FOUND)
        internal_path = '/protected-media/' + file_obj.preview_image.name.lstrip('/')
        response = HttpResponse()
        response['Content-Type'] = 'image/jpeg'
        response['X-Accel-Redirect'] = internal_path
        response['Cache-Control'] = 'private, max-age=3600'
        return response
    
    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        file_obj = self.get_object()
        folder = request.data.get('folder')
        if folder is not None:
            folder_obj = Folder.objects.filter(id=folder, owner=request.user).first()
            if folder_obj is None:
                return Response({'message': 'Folder not found'}, status=status.HTTP_400_BAD_REQUEST)
            file_obj.folder_id = folder_obj.id
        else:
            file_obj.folder_id = None
        file_obj.save()
        return Response({'message': f'File {file_obj.name} moved'})
    
    @swagger_auto_schema(
        consumes=["multipart/form-data"],
        request_body=None,
        responses={201: FileSerializer(many=True)},
    )
    @transaction.atomic
    @action(detail=False, methods=['post'])
    def bulk_upload(self, request):
        files = request.FILES.getlist('files')
        uploaded_files = []
        name = request.data.get('name')
        folder = request.data.get('folder')
        folder_obj = None
        if folder is not None:
            try:
                folder_obj = Folder.objects.get(pk=folder, owner=request.user)
            except Folder.DoesNotExist:
                return Response({'error': 'Folder not found'}, status=status.HTTP_400_BAD_REQUEST)

        used = File.objects.filter(owner=request.user, deleted_at__isnull=True).aggregate(s=Sum('size'))['s'] or 0
        total_new = sum(f.size for f in files)
        if used + total_new > settings.QUOTA_STORAGE_BYTES_PER_USER:
            return Response({'error': 'Storage quota exceeded'}, status=status.HTTP_403_FORBIDDEN)

        for uploaded_file in files:
            file_obj = File.objects.create(
                owner=request.user,
                name=name or uploaded_file.name,
                size=uploaded_file.size,
                mime_type=uploaded_file.content_type,
                file=uploaded_file,
                folder=folder_obj
            )
            uploaded_files.append(file_obj)
            generate_preview.delay(file_obj.id)

        serializer = self.get_serializer(uploaded_files, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        file_obj = self.get_object()
        ttl_minutes = int(request.data.get('ttl_minutes', 60))
        shared_link = file_obj.shared_links.create(
            expires_at=timezone.now() + timezone.timedelta(minutes=ttl_minutes),
            max_downloads=request.data.get('max_downloads', None)
        )
        url = request.build_absolute_uri(f'/p/{shared_link.token}/')
        return Response({'url': url})
    

    @action(detail=False, methods=['get'])
    def trash(self, request):
        deleted_files = File.objects.filter(owner=request.user, deleted_at__isnull=False).order_by('-deleted_at')
        serializer = self.get_serializer(deleted_files, many=True, context={'request': request})
        return Response(serializer.data)


    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        try:
            file_obj = File.objects.get(id=pk, owner=request.user, deleted_at__isnull=False)
        except File.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        if not file_obj.can_restore():
            return Response(status=status.HTTP_403_FORBIDDEN)
        
        file_obj.deleted_at = None
        file_obj.save()
        serializer = self.get_serializer(file_obj, context={'request': request})
        return Response(serializer.data)
    
    
    @action(detail=True, methods=['post'])
    def permanent_delete(self, request, pk=None):
        try:
            file_obj = File.objects.get(id=pk, owner=request.user, deleted_at__isnull=False)
        except File.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        
        file_obj.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class FolderViewSet(viewsets.ModelViewSet):
    queryset = Folder.objects.all()
    serializer_class = FolderSerializer
    permission_classes = [IsOwner]

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Folder.objects.none()
        return Folder.objects.filter(owner=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
        
    @transaction.atomic
    def perform_destroy(self, instance):
        files = File.objects.filter(folder=instance, deleted_at__isnull=True)
        files.update(deleted_at=timezone.now())
        instance.delete()
    
    @action(detail=True)
    def content(self, request, pk=None):
        folder = self.get_object()
        subfolders = Folder.objects.filter(parent=folder, owner=request.user)
        files = File.objects.filter(owner=request.user, folder=folder, deleted_at__isnull=True)
        folder_serializer = FolderSerializer(subfolders, many=True, context={'request': request})
        file_serializer = FileSerializer(files, many=True, context={'request': request})
        return Response({
            "folders": folder_serializer.data,
            "files": file_serializer.data
        })


class PublicSharedFileView(APIView):
    def get(self, request, token):
        shared_link = get_object_or_404(SharedLink, token=token)
        if not shared_link.is_valid():
            return Response({'error': 'Link is invalid or expired'}, status=status.HTTP_404_NOT_FOUND)
        
        file_obj = shared_link.file
        shared_link.increment_download()
        if not file_obj.file or not file_obj.file.name:
            return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        internal_path = '/protected-media/' + file_obj.file.name.lstrip('/')
        response = HttpResponse()
        response['Content-Type'] = file_obj.mime_type or 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
        response['X-Accel-Redirect'] = internal_path
        return response
