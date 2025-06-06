# admin.py
from django.contrib import admin
from .models import Categoria


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('nome',)}  # Corrigido
    list_display = ('nome','tipo_medida', 'slug', 'sistema')
    list_filter = ('tipo_medida', 'sistema')
    readonly_fields = ('sistema',)
    
    def has_delete_permission(self, request, obj=None):
        if obj and obj.sistema:
            return False
        return super().has_delete_permission(request, obj)


