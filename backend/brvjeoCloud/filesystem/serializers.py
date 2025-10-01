from rest_framework import serializers

from .models import File


class FileSerializer(serializers.ModelSerializer):
    preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = File
        fields = [ 
            "id", "name", "size", "mime_type",
            "uploaded_at", "preview_url", "download_url"
        ]
    
    def get_preview_url(self, obj):
        request = self.context.get("request")
        if obj.preview_image:
            return request.build_absolute_uri(f"/api/files/{obj.id}/preview/")
        return None

    def get_download_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(f"/api/files/{obj.id}/download/")