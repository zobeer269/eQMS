# deviations/__init__.py
# (empty file)

# deviations/apps.py
from django.apps import AppConfig

class DeviationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'deviations'
    verbose_name = 'Deviations Management'

# deviations/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    Deviation, DeviationInvestigation, DeviationApproval,
    DeviationAttachment, Product
)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_code', 'product_name', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('product_code', 'product_name', 'product_name_en')
    ordering = ('product_code',)

@admin.register(Deviation)
class DeviationAdmin(admin.ModelAdmin):
    list_display = ('deviation_number', 'title', 'deviation_type', 'severity', 'status_badge', 
                    'reported_by', 'occurrence_date', 'days_open')
    list_filter = ('status', 'severity', 'deviation_type', 'department', 'is_recurring', 
                   'requires_capa', 'requires_change_control')
    search_fields = ('deviation_number', 'title', 'description', 'reported_by__username')
    date_hierarchy = 'reported_date'
    readonly_fields = ('deviation_number', 'reported_date', 'days_open', 'is_overdue')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('deviation_number', 'title', 'description', 'deviation_type', 
                      'severity', 'status', 'location', 'department')
        }),
        (_('Dates'), {
            'fields': ('occurrence_date', 'detection_date', 'reported_date', 'closed_date')
        }),
        (_('Responsible Persons'), {
            'fields': ('reported_by', 'assigned_to', 'qa_reviewer')
        }),
        (_('Affected Items'), {
            'fields': ('affected_products', 'affected_batches')
        }),
        (_('Assessment'), {
            'fields': ('impact_assessment', 'risk_assessment', 'immediate_actions', 
                      'containment_actions')
        }),
        (_('Investigation'), {
            'fields': ('root_cause', 'investigation_summary')
        }),
        (_('Actions Required'), {
            'fields': ('requires_capa', 'requires_change_control', 'related_capa', 
                      'related_change_control')
        }),
        (_('Recurrence'), {
            'fields': ('is_recurring', 'previous_occurrences'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'open': 'warning',
            'under_investigation': 'info',
            'pending_approval': 'primary',
            'approved': 'success',
            'closed': 'dark',
            'cancelled': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def days_open(self, obj):
        days = obj.days_open
        if obj.is_overdue:
            return format_html('<span class="text-danger">{} days</span>', days)
        return f"{days} days"
    days_open.short_description = _('Days Open')

@admin.register(DeviationInvestigation)
class DeviationInvestigationAdmin(admin.ModelAdmin):
    list_display = ('deviation', 'investigation_lead', 'investigation_start_date', 
                    'investigation_end_date', 'root_cause_category')
    list_filter = ('root_cause_category', 'investigation_start_date')
    search_fields = ('deviation__deviation_number', 'deviation__title')
    raw_id_fields = ('deviation',)

@admin.register(DeviationApproval)
class DeviationApprovalAdmin(admin.ModelAdmin):
    list_display = ('deviation', 'approval_type', 'approver', 'approval_role', 
                    'status', 'requested_date', 'action_date')
    list_filter = ('status', 'approval_type', 'approval_role')
    search_fields = ('deviation__deviation_number', 'approver__username')
    readonly_fields = ('requested_date', 'electronic_signature')
    
    def has_add_permission(self, request):
        return False

@admin.register(DeviationAttachment)
class DeviationAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'deviation', 'file_type', 'uploaded_by', 'uploaded_date')
    list_filter = ('file_type', 'uploaded_date')
    search_fields = ('title', 'description', 'deviation__deviation_number')
    readonly_fields = ('uploaded_date',)