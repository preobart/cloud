import io
from datetime import timedelta

from django.core.files import File as DjangoFile
from django.utils import timezone

import ffmpeg
from celery import shared_task
from PIL import Image

from cloud.filesystem.models import File


@shared_task
def generate_preview(file_id):
    file = File.objects.get(pk=file_id)
    orig_path = file.file.path
    if file.mime_type.startswith("image/"):
        image = Image.open(orig_path)
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.thumbnail((300, 300))
        buf = io.BytesIO()
        image.save(buf, format="JPEG")
        buf.seek(0)
        file.preview_image.save(f"{file.id}.jpg", DjangoFile(buf), save=True)
    elif file.mime_type.startswith("video/"):
        process = (
            ffmpeg
            .input(orig_path, ss=0.5)
            .filter("scale", 300, -1)
            .output("pipe:", vframes=1, format="image2", vcodec="mjpeg")
            .run(capture_stdout=True, capture_stderr=True)
        )
        stdout, _ = process
        buf = io.BytesIO(stdout)
        file.preview_image.save(f"{file.id}.jpg", DjangoFile(buf), save=True)


@shared_task
def delete_old_files():
    old_files = File.objects.filter(
        deleted_at__isnull=False,
        deleted_at__lt=timezone.now() - timedelta(days=30)
    )

    for file_obj in old_files:
        if file_obj.file:
            file_obj.file.delete(save=False)
        if file_obj.preview_image:
            file_obj.preview_image.delete(save=False)
        file_obj.delete()
        
    
