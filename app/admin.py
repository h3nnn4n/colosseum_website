from django.contrib import admin

from app import models


@admin.register(models.Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "owner", "wins", "loses", "draws", "score", "elo")
    search_fields = ("name", "id", "owner")


@admin.register(models.Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "active", "start_date", "end_date")


@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("name", "id")


@admin.register(models.Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "player1", "player2", "ran", "ran_at")
    list_filter = ("ran",)


@admin.register(models.Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = ("name", "id", "mode", "start_date", "end_date")
    list_filter = ("mode",)
    search_fields = ("name", "id")
