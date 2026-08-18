from django.contrib import admin
from unfold.admin import ModelAdmin

from taxonomy.models import Industry, ServiceCluster, Tag


@admin.register(Industry)
class IndustryAdmin(ModelAdmin):
    list_display = ["name", "order", "show_in_nav", "use_case_count"]
    list_editable = ["order", "show_in_nav"]
    list_filter = ["show_in_nav"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Use cases")
    def use_case_count(self, obj):
        return obj.use_cases.count()


@admin.register(ServiceCluster)
class ServiceClusterAdmin(ModelAdmin):
    list_display = ["name", "order"]
    list_editable = ["order"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
