from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, AuditLog, SecureSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'employee_id', 'email', 'first_name', 'last_name', 
                    'department', 'is_active', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'department', 
                   'is_quality_manager', 'is_document_controller')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'employee_id')
    ordering = ('username',)
    
    fieldsets = BaseUserAdmin.fieldsets + (
        (_('Employee Information'), {
            'fields': ('employee_id', 'department', 'position', 'phone', 
                      'preferred_language')
        }),
        (_('Permissions'), {
            'fields': ('is_quality_manager', 'is_document_controller', 
                      'can_approve_documents')
        }),
        (_('Security'), {
            'fields': ('electronic_signature', 'signature_image', 
                      'must_change_password', 'failed_login_attempts')
        }),
        (_('Training'), {
            'fields': ('is_trained', 'training_date')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'employee_id', 'email', 'password1', 
                      'password2', 'department', 'position'),
        }),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'username', 'action', 'model_name', 
                    'object_repr', 'ip_address')
    list_filter = ('action', 'model_name', 'timestamp')
    search_fields = ('username', 'object_repr', 'ip_address')
    date_hierarchy = 'timestamp'
    readonly_fields = ('user', 'username', 'action', 'model_name', 'object_id',
                      'object_repr', 'old_values', 'new_values', 'timestamp',
                      'ip_address', 'user_agent', 'reason', 'electronic_signature',
                      'signature_meaning')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SecureSession)
class SecureSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'ip_address', 'created_at', 'last_activity', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('user__username', 'ip_address')
    readonly_fields = ('session_key', 'created_at')