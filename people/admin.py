from django.contrib import admin
from unfold.admin import ModelAdmin

from people.models import TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(ModelAdmin):
    list_display = ["name", "role", "show_on_about", "order"]
    list_editable = ["show_on_about", "order"]
    list_filter = ["show_on_about"]
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ["name", "role"]
