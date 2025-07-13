# capa/__init__.py
# (empty file)

# capa/apps.py
from django.apps import AppConfig

class CapaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'capa'
    verbose_name = 'CAPA Management'

# capa/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    CAPA, CAPAAction, CAPAEffectivenessCheck, 
    CAPAApproval, CAPAAttachment
)

class CAPAActionInline(admin.TabularInline):
    model = CAPAAction
    extra = 0
    fields = ('action_number', 'action_type', 'action_description', 'responsible_person', 
              'status', 'planned_date', 'actual_completion_date')
    readonly_fields = ('action_number',)

@admin.register(CAPA)
class CAPAAdmin(admin.ModelAdmin):
    list_display = ('capa_number', 'title', 'capa_type', 'source_type', 'priority_badge', 
                    'status_badge', 'capa_owner', 'due_date', 'is_overdue_badge')
    list_filter = ('status', 'capa_type', 'source_type', 'priority', 'risk_level')
    search_fields = ('capa_number', 'title', 'description', 'source_reference')
    date_hierarchy = 'initiated_date'
    readonly_fields = ('capa_number', 'initiated_date', 'is_overdue', 'days_until_due')
    inlines = [CAPAActionInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('capa_number', 'title', 'description', 'capa_type', 
                      'source_type', 'source_reference')
        }),
        (_('Status and Priority'), {
            'fields': ('status', 'priority', 'due_date', 'completion_date', 'closed_date')
        }),
        (_('Responsible Persons'), {
            'fields': ('initiated_by', 'capa_owner', 'capa_coordinator')
        }),
        (_('Problem Analysis'), {
            'fields': ('problem_statement', 'root_cause_analysis', 'root_cause_category')
        }),
        (_('Risk Assessment'), {
            'fields': ('risk_assessment', 'risk_level')
        }),
        (_('Affected Areas'), {
            'fields': ('affected_departments', 'related_documents'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'open': 'warning',
            'in_progress': 'info',
            'pending_verification': 'primary',
            'pending_effectiveness': 'primary',
            'closed': 'success',
            'cancelled': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def priority_badge(self, obj):
        colors = {
            'high': 'danger',
            'medium': 'warning',
            'low': 'info'
        }
        color = colors.get(obj.priority, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = _('Priority')
    
    def is_overdue_badge(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span class="badge bg-danger">Overdue</span>'
            )
        elif obj.days_until_due and obj.days_until_due <= 7:
            return format_html(
                '<span class="badge bg-warning">{} days</span>',
                obj.days_until_due
            )
        return format_html(
            '<span class="badge bg-success">On Track</span>'
        )
    is_overdue_badge.short_description = _('Due Status')

@admin.register(CAPAAction)
class CAPAActionAdmin(admin.ModelAdmin):
    list_display = ('capa', 'action_number', 'action_type', 'responsible_person', 
                    'status', 'planned_date', 'actual_completion_date')
    list_filter = ('status', 'action_type', 'verification_required')
    search_fields = ('capa__capa_number', 'action_description')
    readonly_fields = ('verification_date',)

@admin.register(CAPAEffectivenessCheck)
class CAPAEffectivenessCheckAdmin(admin.ModelAdmin):
    list_display = ('capa', 'check_number', 'planned_date', 'actual_date', 
                    'performed_by', 'result')
    list_filter = ('result', 'additional_actions_required')
    search_fields = ('capa__capa_number', 'findings')
    readonly_fields = ('check_number',)

@admin.register(CAPAApproval)
class CAPAApprovalAdmin(admin.ModelAdmin):
    list_display = ('capa', 'approval_stage', 'approver', 'approval_role', 
                    'status', 'requested_date', 'action_date')
    list_filter = ('status', 'approval_stage', 'approval_role')
    search_fields = ('capa__capa_number', 'approver__username')
    readonly_fields = ('requested_date', 'electronic_signature')
    
    def has_add_permission(self, request):
        return False

@admin.register(CAPAAttachment)
class CAPAAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'capa', 'attachment_type', 'uploaded_by', 'uploaded_date')
    list_filter = ('attachment_type', 'uploaded_date')
    search_fields = ('title', 'description', 'capa__capa_number')
    readonly_fields = ('uploaded_date',)