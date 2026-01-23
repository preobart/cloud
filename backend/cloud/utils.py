from django.conf import settings


def file_upload_path(self, filename):
    ext = filename.split('.')[-1]
    uid = str(self.id).replace('-', '')
    return f"{settings.CONTENT_DIR}/{uid[:2]}/{uid[2:4]}/{self.id}.{ext}"

def preview_upload_path(self, filename):
    uid = str(self.id).replace('-', '')
    return f"{settings.PREVIEWS_DIR}/{uid[:2]}/{uid[2:4]}/{self.id}.jpeg"
