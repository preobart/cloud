import os
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from PIL import Image
from rest_framework.test import APIClient

from cloud.filesystem.models import File, Folder
from cloud.tasks import generate_preview


class FileViewSetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = APIClient()
        self.client.login(username="testuser", password="password123")

        self.folder = Folder.objects.create(owner=self.user, name="folder")
        self.file = File.objects.create(
            owner=self.user,
            name="file.txt",
            size=10,
            mime_type="text/plain",
            file="file.txt",  
            updated_at=timezone.now(),
        )

    def test_list_files(self):
        url = reverse("file-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], self.file.name)

    def test_create_file(self):
        url = reverse("file-list")
        data = {
            "file": SimpleUploadedFile("hello.txt", b"Hello World", content_type="text/plain"),
            "folder": self.folder.id,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "hello.txt")

    def test_move_file(self):
        url = reverse("file-move", args=[self.file.id])
        response = self.client.post(url, {"folder": self.folder.id})
        self.assertEqual(response.status_code, 200)
        self.file.refresh_from_db()
        self.assertEqual(self.file.folder_id, self.folder.id)

    def test_bulk_upload(self):
        url = reverse("file-bulk-upload")
        f1 = SimpleUploadedFile("file1.txt", b"file1", content_type="text/plain")
        f2 = SimpleUploadedFile("file2.txt", b"file2", content_type="text/plain")
        response = self.client.post(
            url,
            {"files": [f1, f2], "folder": self.folder.id},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertGreaterEqual(len(response.data), 1)

    def test_share_file(self):
        url = reverse("file-share", args=[self.file.id])
        response = self.client.post(url, {"ttl_minutes": 120, "max_downloads": 10})
        self.assertEqual(response.status_code, 200)
        self.assertIn("url", response.data)

    def test_download(self):
        url = reverse("file-download", args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Accel-Redirect", response)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="file.txt"')

    def test_preview_without_preview(self):
        url = reverse("file-preview", args=[self.file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_preview_with_preview(self):
        image_path = os.path.join(settings.CONTENT_DIR, "preview_test.jpg")
        os.makedirs(os.path.dirname(image_path), exist_ok=True)
        Image.new("RGB", (100, 100), color="blue").save(image_path)
        image_file = File.objects.create(
            owner=self.user,
            name="preview_test.jpg",
            mime_type="image/jpeg",
            size=os.path.getsize(image_path),
            file="content/preview_test.jpg",
            folder=self.folder,
        )
        generate_preview(image_file.pk)
        image_file.refresh_from_db()
        self.assertIsNotNone(image_file.preview_image)
        url = reverse("file-preview", args=[image_file.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Accel-Redirect", response)
        self.assertEqual(response["Content-Type"], "image/jpeg")

    def test_create_missing_file(self):
        url = reverse("file-list")
        response = self.client.post(url, {"folder": self.folder.id}, format="multipart")
        self.assertEqual(response.status_code, 400)
        response = self.client.post(
            url,
            {"file": SimpleUploadedFile("x.txt", b"x", content_type="text/plain")},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)

    @override_settings(QUOTA_STORAGE_BYTES_PER_USER=5)
    def test_create_quota_exceeded(self):
        url = reverse("file-list")
        data = {
            "file": SimpleUploadedFile("big.txt", b"x" * 10, content_type="text/plain"),
            "folder": self.folder.id,
        }
        response = self.client.post(url, data, format="multipart")
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    @override_settings(QUOTA_STORAGE_BYTES_PER_USER=5)
    def test_bulk_upload_quota_exceeded(self):
        url = reverse("file-bulk-upload")
        f1 = SimpleUploadedFile("f1.txt", b"x" * 10, content_type="text/plain")
        response = self.client.post(url, {"files": [f1], "folder": self.folder.id}, format="multipart")
        self.assertEqual(response.status_code, 403)
        self.assertIn("error", response.data)

    def test_trash(self):
        url = reverse("file-detail", args=[self.file.id])
        self.client.delete(url)
        trash_url = reverse("file-trash")
        response = self.client.get(trash_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], self.file.name)

    def test_restore(self):
        url = reverse("file-detail", args=[self.file.id])
        self.client.delete(url)
        self.file.refresh_from_db()
        self.assertIsNotNone(self.file.deleted_at)
        restore_url = reverse("file-restore", args=[self.file.id])
        response = self.client.post(restore_url)
        self.assertEqual(response.status_code, 200)
        self.file.refresh_from_db()
        self.assertIsNone(self.file.deleted_at)

    def test_permanent_delete(self):
        url = reverse("file-detail", args=[self.file.id])
        self.client.delete(url)
        perm_url = reverse("file-permanent-delete", args=[self.file.id])
        response = self.client.post(perm_url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(File.objects.filter(pk=self.file.id).exists())


class FolderViewSetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = APIClient()
        self.client.login(username="testuser", password="password123")

        self.folder = Folder.objects.create(owner=self.user, name="folder")
        self.file = File.objects.create(
            owner=self.user,
            name="file.txt",
            size=10,
            mime_type="text/plain",
            file="file.txt",  
            updated_at=timezone.now(),
            folder=self.folder,
        )

    def test_list_folders(self):
        url = reverse("folder-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]["name"], self.folder.name)

    def test_folder_content(self):
        url = reverse("folder-content", args=[self.folder.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        files = response.data["files"]
        self.assertGreater(len(files), 0)

        self.assertEqual(files[0]["name"], self.file.name)

    def test_delete_folder_soft_deletes_files(self):
        url = reverse("folder-detail", args=[self.folder.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.file.refresh_from_db()
        self.assertIsNotNone(self.file.deleted_at)


class PublicSharedFileViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password123")
        self.client = APIClient()
        self.client.login(username="testuser", password="password123")

        self.file = File.objects.create(
            owner=self.user,
            name="file.txt",
            size=10,
            mime_type="text/plain",
            file="file.txt",  
            updated_at=timezone.now(),
        )

        self.shared_link = self.file.shared_links.create(
            expires_at=timezone.now() + timedelta(minutes=60),
            max_downloads=5,
        )

    def test_public_shared_file(self):
        url = reverse("public-file", args=[self.shared_link.token])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Accel-Redirect", response)

    def test_public_shared_file_expired(self):
        self.shared_link.expires_at = timezone.now() - timedelta(minutes=1)
        self.shared_link.save()
        url = reverse("public-file", args=[self.shared_link.token])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_public_shared_file_max_downloads(self):
        self.shared_link.download_count = self.shared_link.max_downloads
        self.shared_link.save()
        url = reverse("public-file", args=[self.shared_link.token])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
