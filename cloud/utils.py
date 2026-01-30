def file_upload_path(instance, filename):
    ext = filename.split('.')[-1]
    uid = str(instance.id).replace('-', '')
    return f"content/{uid[:2]}/{uid[2:4]}/{instance.id}.{ext}"


def preview_upload_path(instance, filename):
    uid = str(instance.id).replace('-', '')
    return f"previews/{uid[:2]}/{uid[2:4]}/{instance.id}.jpeg"
