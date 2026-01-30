from django.contrib import admin

from .models import File, Folder, SharedLink


admin.site.register(File)
admin.site.register(Folder)
admin.site.register(SharedLink)
# Register your models here.
