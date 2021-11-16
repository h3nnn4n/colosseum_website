from django.contrib import admin

from app import models


admin.site.register(models.Agent)
admin.site.register(models.Game)
admin.site.register(models.Match)
admin.site.register(models.Tournament)
