# change_control/__init__.py
# (empty file)

# change_control/apps.py
from django.apps import AppConfig

class ChangeControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'change_control'
    verbose_name = 'Change Control Management'

# change_control/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from .models import (
    ChangeControl, ChangeImpactAssessment, ChangeImplementationPlan,
    ChangeTask, ChangeApproval, ChangeAttachment
)

class ChangeTaskInline(admin.TabularInline):
    model = ChangeTask
    extra = 0
    fields = ('task_number', 'task_description', 'assigned_to', 'status', 
              'planned_start_date', 'planned_end_date')
    readonly_fields = ('task_number',)

@admin.register(ChangeControl)
class ChangeControlAdmin(admin.ModelAdmin):
    list_display = ('change_number', 'title', 'change_type', 'category_badge', 
                    'urgency_badge', 'status_badge', 'change_owner', 
                    'target_implementation_date', 'is_overdue_badge')
    list_filter = ('status', 'change_type', 'change_category', 'urgency', 
                   'requires_risk_assessment', 'requires_validation', 
                   'requires_regulatory_approval')
    search_fields = ('change_number', 'title', 'description', 'change_reason')
    date_hierarchy = 'submission_date'
    readonly_fields = ('change_number', 'submission_date', 'is_overdue')
    inlines = [ChangeTaskInline]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('change_number', 'title', 'description', 'change_type', 
                      'change_category', 'urgency', 'status')
        }),
        (_('Change Justification'), {
            'fields': ('change_reason', 'change_benefits')
        }),
        (_('Dates'), {
            'fields': ('submission_date', 'target_implementation_date', 
                      'actual_implementation_date', 'closure_date')
        }),
        (_('Responsible Persons'), {
            'fields': ('initiated_by', 'change_owner', 'change_coordinator')
        }),
        (_('Affected Areas'), {
            'fields': ('affected_departments', 'affected_areas', 'affected_products')
        }),
        (_('Requirements'), {
            'fields': ('requires_risk_assessment', 'requires_validation', 
                      'requires_regulatory_approval')
        }),
        (_('Related Items'), {
            'fields': ('related_documents', 'related_deviations', 'related_capas'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'submitted': 'info',
            'under_review': 'warning',
            'impact_assessment': 'warning',
            'pending_approval': 'primary',
            'approved': 'success',
            'implementation': 'info',
            'verification': 'primary',
            'closed': 'dark',
            'rejected': 'danger',
            'cancelled': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def category_badge(self, obj):
        colors = {
            'minor': 'info',
            'major': 'warning',
            'critical': 'danger'
        }
        color = colors.get(obj.change_category, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_change_category_display()
        )
    category_badge.short_description = _('Category')
    
    def urgency_badge(self, obj):
        colors = {
            'emergency': 'danger',
            'urgent': 'warning',
            'normal': 'info',
            'low': 'secondary'
        }
        color = colors.get(obj.urgency, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_urgency_display()
        )
    urgency_badge.short_description = _('Urgency')
    
    def is_overdue_badge(self, obj):
        if obj.is_overdue:
            return format_html(
                '<span class="badge bg-danger">Overdue</span>'
            )
        return format_html(
            '<span class="badge bg-success">On Track</span>'
        )
    is_overdue_badge.short_description = _('Schedule Status')

@admin.register(ChangeImpactAssessment)
class ChangeImpactAssessmentAdmin(admin.ModelAdmin):
    list_display = ('change_control', 'quality_impact', 'safety_impact', 
                    'regulatory_impact', 'cost_impact', 'assessed_by', 'assessment_date')
    list_filter = ('quality_impact', 'safety_impact', 'regulatory_impact', 
                   'environmental_impact', 'cost_impact')
    search_fields = ('change_control__change_number', 'risk_assessment')
    readonly_fields = ('assessment_date',)

@admin.register(ChangeImplementationPlan)
class ChangeImplementationPlanAdmin(admin.ModelAdmin):
    list_display = ('change_control', 'planned_start_date', 'planned_end_date', 
                    'validation_required', 'plan_approved_by', 'plan_approval_date')
    list_filter = ('validation_required', 'planned_start_date')
    search_fields = ('change_control__change_number', 'implementation_steps')
    readonly_fields = ('plan_approval_date',)

@admin.register(ChangeTask)
class ChangeTaskAdmin(admin.ModelAdmin):
    list_display = ('change_control', 'task_number', 'assigned_to', 'status', 
                    'planned_start_date', 'planned_end_date', 'verification_required')
    list_filter = ('status', 'verification_required')
    search_fields = ('change_control__change_number', 'task_description')
    filter_horizontal = ('depends_on',)

@admin.register(ChangeApproval)
class ChangeApprovalAdmin(admin.ModelAdmin):
    list_display = ('change_control', 'approval_type', 'approver', 'approval_role', 
                    'status', 'requested_date', 'action_date')
    list_filter = ('status', 'approval_type', 'approval_role')
    search_fields = ('change_control__change_number', 'approver__username')
    readonly_fields = ('requested_date', 'electronic_signature')
    
    def has_add_permission(self, request):
        return False

@admin.register(ChangeAttachment)
class ChangeAttachmentAdmin(admin.ModelAdmin):
    list_display = ('title', 'change_control', 'attachment_type', 'uploaded_by', 'uploaded_date')
    list_filter = ('attachment_type', 'uploaded_date')
    search_fields = ('title', 'description', 'change_control__change_number')
    readonly_fields = ('uploaded_date',)