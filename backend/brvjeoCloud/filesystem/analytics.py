from django.db.models import Count, Sum

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import File


class AnalyticsViewSet(viewsets.ViewSet):
    @action(detail=False)
    def count_by_type(self, request):
        data = File.objects.filter(owner=request.user, deleted_at__isnull=True).values('mime_type').annotate(count=Count('id')).order_by('-count')
        return Response(data)
    
    @action(detail=False)
    def total_storage(self, request):
        data = File.objects.filter(owner=request.user, deleted_at__isnull=True).aggregate(total_size=Sum('size'))
        return Response(data)
    
    @action(detail=False)
    def storage_by_type(self, request):
        data = (
            File.objects.filter(owner=request.user, deleted_at__isnull=True)
            .values('mime_type')
            .annotate(total_size=Sum('size'))
            .order_by('-total_size')
        )
        return Response(data)