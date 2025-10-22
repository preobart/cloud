import io
import os

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

import ffmpeg
from PIL import Image

from brvjeoCloud.filesystem.models import File
from brvjeoCloud.tasks import generate_preview


MEDIA_ROOT = "mediafiles/uploads/files"
PREVIEWS_DIR = "mediafiles/uploads/previews"


class GeneratePreviewTaskTests(TestCase):
    def setUp(self):
        os.makedirs(MEDIA_ROOT, exist_ok=True)
        os.makedirs(PREVIEWS_DIR, exist_ok=True)

        self.user = User.objects.create_user(username="testuser", password="password123")

        img_io = io.BytesIO()
        img = Image.new("RGB", (640, 480), color="red")
        img.save(img_io, format="JPEG")
        img_io.seek(0)
        uploaded_img = SimpleUploadedFile(
            "test_image.jpg", img_io.read(), content_type="image/jpeg"
        )
        self.image_file = File.objects.create(
            owner=self.user,
            name="test_image.jpg",
            mime_type="image/jpeg",
            size=uploaded_img.size,
            file=uploaded_img,
            updated_at=timezone.now(),
        )

        video_path = os.path.join(MEDIA_ROOT, "temp_video.mp4")
        ffmpeg.input("color=c=black:s=320x240:d=1", f="lavfi") \
              .output(video_path, vcodec="libx264", pix_fmt="yuv420p") \
              .run(overwrite_output=True, quiet=True)
        with open(video_path, "rb") as f:
            uploaded_video = SimpleUploadedFile(
                "test_video.mp4", f.read(), content_type="video/mp4"
            )
        self.video_file = File.objects.create(
            owner=self.user,
            name="test_video.mp4",
            mime_type="video/mp4",
            size=uploaded_video.size,
            file=uploaded_video,
            updated_at=timezone.now(),
        )
        os.remove(video_path)

    def test_generate_preview_image(self):
        generate_preview(self.image_file.id)
        self.image_file.refresh_from_db()
        self.assertIsNotNone(self.image_file.preview_image)
        self.assertTrue(os.path.exists(self.image_file.preview_image.path))

    def test_generate_preview_video(self):
        generate_preview(self.video_file.id)
        self.video_file.refresh_from_db()
        self.assertIsNotNone(self.video_file.preview_image)
        self.assertTrue(os.path.exists(self.video_file.preview_image.path))