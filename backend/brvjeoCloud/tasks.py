import ffmpeg
from celery import shared_task
from filesystem.models import File
from PIL import Image


@shared_task
def generate_preview(file_id):
    file = File.objects.get(id=file_id)
    if file.mime_type.startswith('image/'):
        image = Image.open(file.path)
        image.thumbnail((300, 300))
        preview_path = file.path.replace('.', '_preview.')
        image.save(preview_path)
        file.preview_image = preview_path
        file.save()
    elif file.mime_type.startswith('video/'):
        preview_path = file.path.replace('.', '_preview.jpg')
        (ffmpeg.input(file.path, ss=1).filter('scale', 300, -1).output(preview_path, vframes=1).run())
        file.preview_image = preview_path
        file.save()
