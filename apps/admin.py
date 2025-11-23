from django.contrib import admin
from apps.models import App, AppUser


class AppUserInline(admin.TabularInline):
    model = AppUser
    extra = 0
    readonly_fields = ("invited_at",)


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "created_at")
    search_fields = ("name", "owner__email")
    inlines = [AppUserInline]


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ("app", "user", "role", "invited_at")
    list_filter = ("role",)
    search_fields = ("app__name", "user__email")
