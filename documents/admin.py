from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    DocumentCategory, Document, DocumentVersion,
    DocumentApproval, DocumentAccess, DocumentDistribution,
    DocumentComment
)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'name_en', 'parent', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'name_en', 'code')
    ordering = ('code',)


class DocumentVersionInline(admin.TabularInline):
    model = DocumentVersion
    extra = 0
    readonly_fields = ('version_number', 'created_date', 'created_by', 'is_current')
    fields = ('version_number', 'change_reason', 'created_date', 'created_by', 'is_current')
    can_delete = False


class DocumentApprovalInline(admin.TabularInline):
    model = DocumentApproval
    extra = 0
    readonly_fields = ('requested_date', 'action_date', 'status')
    fields = ('approver', 'approval_role', 'status', 'requested_date', 'action_date')
    can_delete = False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'document_id', 'title', 'document_type', 'category',
        'version', 'status_badge', 'author', 'created_date'
    )
    list_filter = (
        'status', 'document_type', 'category', 'language',
        'requires_training', 'is_controlled', 'created_date'
    )
    search_fields = (
        'document_id', 'title', 'title_en', 'description',
        'keywords', 'author__username', 'owner__username'
    )
    readonly_fields = (
        'created_date', 'electronic_signature_display',
        'file_size', 'is_expired', 'is_due_for_review'
    )
    date_hierarchy = 'created_date'
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'document_id', 'title', 'title_en', 'description',
                'document_type', 'category', 'language'
            )
        }),
        (_('Version & Status'), {
            'fields': ('version', 'status', 'file')
        }),
        (_('Dates'), {
            'fields': (
                'created_date', 'effective_date', 'review_date', 'expiry_date'
            )
        }),
        (_('Ownership'), {
            'fields': ('author', 'owner')
        }),
        (_('Control & Compliance'), {
            'fields': (
                'requires_training', 'is_controlled', 'is_public',
                'retention_years', 'keywords'
            )
        }),
        (_('File Information'), {
            'fields': ('file_size', 'file_pages'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [DocumentVersionInline, DocumentApprovalInline]
    
    def status_badge(self, obj):
        colors = {
            'draft': 'secondary',
            'review': 'info',
            'approved': 'success',
            'published': 'primary',
            'obsolete': 'dark'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def electronic_signature_display(self, obj):
        if hasattr(obj, 'electronic_signature'):
            return format_html('<code>{}</code>', obj.electronic_signature)
        return '-'
    electronic_signature_display.short_description = _('Electronic Signature')
    
    def save_model(self, request, obj, form, change):
        if not change:  # إذا كانت وثيقة جديدة
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(DocumentVersion)
class DocumentVersionAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'version_number', 'created_by',
        'created_date', 'is_current'
    )
    list_filter = ('is_current', 'created_date')
    search_fields = ('document__document_id', 'document__title', 'version_number')
    readonly_fields = ('document', 'version_number', 'created_date', 'created_by')
    date_hierarchy = 'created_date'


@admin.register(DocumentApproval)
class DocumentApprovalAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'approver', 'approval_role',
        'status_badge', 'requested_date', 'action_date'
    )
    list_filter = ('status', 'approval_role', 'requested_date')
    search_fields = (
        'document__document_id', 'document__title',
        'approver__username', 'approver__first_name'
    )
    readonly_fields = (
        'document', 'approver', 'requested_date',
        'action_date', 'electronic_signature'
    )
    date_hierarchy = 'requested_date'
    
    def status_badge(self, obj):
        colors = {
            'pending': 'warning',
            'approved': 'success',
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


@admin.register(DocumentAccess)
class DocumentAccessAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'user', 'access_type',
        'access_date', 'acknowledged', 'ip_address'
    )
    list_filter = (
        'access_type', 'acknowledged', 'access_date'
    )
    search_fields = (
        'document__document_id', 'document__title',
        'user__username', 'ip_address'
    )
    readonly_fields = (
        'document', 'user', 'access_type',
        'access_date', 'ip_address', 'user_agent'
    )
    date_hierarchy = 'access_date'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(DocumentDistribution)
class DocumentDistributionAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'user', 'department', 'external_party',
        'distribution_date', 'receipt_confirmed', 'is_withdrawn'
    )
    list_filter = (
        'receipt_confirmed', 'is_withdrawn', 'distribution_date'
    )
    search_fields = (
        'document__document_id', 'document__title',
        'user__username', 'department', 'external_party'
    )
    readonly_fields = ('distribution_date', 'distributed_by')
    date_hierarchy = 'distribution_date'


@admin.register(DocumentComment)
class DocumentCommentAdmin(admin.ModelAdmin):
    list_display = (
        'document', 'user', 'created_date',
        'is_review_comment', 'resolved'
    )
    list_filter = (
        'is_review_comment', 'resolved', 'created_date'
    )
    search_fields = (
        'document__document_id', 'document__title',
        'user__username', 'comment'
    )
    readonly_fields = (
        'document', 'user', 'created_date',
        'resolved_by', 'resolved_date'
    )
    date_hierarchy = 'created_date'
    
    def has_add_permission(self, request):
        return False