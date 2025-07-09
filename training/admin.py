from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    TrainingProgram, TrainingSession, TrainingRecord,
    TrainingMaterial, TrainingEvaluation
)


class TrainingMaterialInline(admin.TabularInline):
    model = TrainingMaterial
    extra = 1
    fields = ('title', 'material_type', 'file', 'order', 'is_mandatory')
    ordering = ['order']


class TrainingSessionInline(admin.TabularInline):
    model = TrainingSession
    extra = 0
    fields = ('session_code', 'scheduled_date', 'trainer', 'status', 'participants_count')
    readonly_fields = ('session_code', 'participants_count')
    
    def participants_count(self, obj):
        if obj.pk:
            return obj.participants_count
        return 0
    participants_count.short_description = _('Participants')


@admin.register(TrainingProgram)
class TrainingProgramAdmin(admin.ModelAdmin):
    list_display = (
        'program_id', 'title', 'training_type', 'delivery_method',
        'duration_hours', 'validity_months', 'is_mandatory', 'is_active'
    )
    list_filter = (
        'training_type', 'delivery_method', 'is_mandatory', 'is_active',
        'created_date'
    )
    search_fields = ('program_id', 'title', 'title_en', 'description')
    readonly_fields = ('created_date', 'created_by')
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'program_id', 'title', 'title_en', 'description',
                'training_type', 'delivery_method'
            )
        }),
        (_('Requirements'), {
            'fields': (
                'duration_hours', 'passing_score', 'validity_months',
                'is_mandatory', 'prerequisites'
            )
        }),
        (_('Assignment'), {
            'fields': (
                'target_departments', 'related_documents', 'trainer'
            )
        }),
        (_('Status'), {
            'fields': ('is_active', 'created_date', 'created_by')
        }),
    )
    
    filter_horizontal = ('prerequisites', 'target_departments', 'related_documents')
    inlines = [TrainingMaterialInline, TrainingSessionInline]
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = (
        'session_code', 'program', 'scheduled_date', 'trainer',
        'status_badge', 'participants_display', 'location'
    )
    list_filter = ('status', 'scheduled_date', 'program__training_type')
    search_fields = (
        'session_code', 'program__title', 'trainer__username',
        'trainer__first_name', 'trainer__last_name'
    )
    readonly_fields = ('session_code', 'created_date', 'created_by', 'participants_count')
    date_hierarchy = 'scheduled_date'
    
    fieldsets = (
        (_('Program'), {
            'fields': ('program', 'session_code')
        }),
        (_('Schedule'), {
            'fields': ('scheduled_date', 'actual_date', 'location', 'trainer')
        }),
        (_('Settings'), {
            'fields': ('status', 'max_participants', 'participants_count')
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('created_date', 'created_by'),
            'classes': ('collapse',)
        }),
    )
    
    def status_badge(self, obj):
        colors = {
            'scheduled': 'info',
            'in_progress': 'warning',
            'completed': 'success',
            'cancelled': 'danger'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def participants_display(self, obj):
        return f"{obj.participants_count}/{obj.max_participants}"
    participants_display.short_description = _('Participants')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TrainingRecord)
class TrainingRecordAdmin(admin.ModelAdmin):
    list_display = (
        'trainee_name', 'session_display', 'status_badge',
        'attendance_status', 'test_score', 'certificate_status'
    )
    list_filter = (
        'status', 'session__program', 'enrolled_date',
        'certificate_expiry_date'
    )
    search_fields = (
        'trainee__username', 'trainee__first_name', 'trainee__last_name',
        'session__session_code', 'certificate_number'
    )
    readonly_fields = (
        'enrolled_date', 'certificate_number', 'electronic_signature',
        'attendance_signature'
    )
    date_hierarchy = 'enrolled_date'
    
    fieldsets = (
        (_('Enrollment'), {
            'fields': ('trainee', 'session', 'status', 'enrolled_date')
        }),
        (_('Attendance'), {
            'fields': ('attendance_date', 'attendance_signature')
        }),
        (_('Assessment'), {
            'fields': (
                'pre_test_score', 'post_test_score', 'test_date',
                'effectiveness_score', 'feedback'
            )
        }),
        (_('Certification'), {
            'fields': (
                'certificate_number', 'certificate_issued_date',
                'certificate_expiry_date'
            )
        }),
        (_('Completion'), {
            'fields': (
                'completed_date', 'electronic_signature', 'signature_date'
            )
        }),
    )
    
    actions = ['mark_as_completed', 'generate_certificates']
    
    def trainee_name(self, obj):
        return obj.trainee.get_full_name()
    trainee_name.short_description = _('Trainee')
    trainee_name.admin_order_field = 'trainee__last_name'
    
    def session_display(self, obj):
        return f"{obj.session.program.title} ({obj.session.session_code})"
    session_display.short_description = _('Training Session')
    
    def status_badge(self, obj):
        colors = {
            'enrolled': 'info',
            'attended': 'primary',
            'completed': 'success',
            'failed': 'danger',
            'absent': 'warning',
            'cancelled': 'secondary'
        }
        color = colors.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    
    def attendance_status(self, obj):
        if obj.attendance_date:
            return format_html(
                '<i class="fas fa-check text-success"></i> {}',
                obj.attendance_date.strftime('%Y-%m-%d %H:%M')
            )
        return format_html('<i class="fas fa-times text-danger"></i> Not Attended')
    attendance_status.short_description = _('Attendance')
    
    def test_score(self, obj):
        if obj.post_test_score is not None:
            color = 'success' if obj.is_passed else 'danger'
            return format_html(
                '<span class="text-{}">{:.1f}%</span>',
                color,
                obj.post_test_score
            )
        return '-'
    test_score.short_description = _('Test Score')
    
    def certificate_status(self, obj):
        if obj.certificate_number:
            if obj.is_expired:
                return format_html(
                    '<span class="text-danger">Expired ({})</span>',
                    obj.certificate_expiry_date
                )
            else:
                return format_html(
                    '<span class="text-success">{}</span>',
                    obj.certificate_number
                )
        return '-'
    certificate_status.short_description = _('Certificate')
    
    def mark_as_completed(self, request, queryset):
        count = 0
        for record in queryset:
            if record.status == 'attended' and record.is_passed:
                record.status = 'completed'
                record.completed_date = timezone.now()
                record.save()
                count += 1
        
        self.message_user(
            request,
            f'{count} training records marked as completed.'
        )
    mark_as_completed.short_description = _('Mark selected as completed')
    
    def generate_certificates(self, request, queryset):
        count = 0
        for record in queryset.filter(status='completed', certificate_number__isnull=True):
            record.save()  # This will trigger certificate generation
            count += 1
        
        self.message_user(
            request,
            f'{count} certificates generated.'
        )
    generate_certificates.short_description = _('Generate certificates')


@admin.register(TrainingMaterial)
class TrainingMaterialAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'program', 'material_type', 'order',
        'is_mandatory', 'file_size_display', 'uploaded_date'
    )
    list_filter = ('material_type', 'is_mandatory', 'program')
    search_fields = ('title', 'description', 'program__title')
    readonly_fields = ('file_size', 'uploaded_date', 'uploaded_by')
    
    def file_size_display(self, obj):
        if obj.file_size:
            size_mb = obj.file_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        return '-'
    file_size_display.short_description = _('File Size')
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(TrainingEvaluation)
class TrainingEvaluationAdmin(admin.ModelAdmin):
    list_display = (
        'training_record', 'average_score_display', 'overall_rating',
        'would_recommend', 'submitted_date'
    )
    list_filter = ('would_recommend', 'overall_rating', 'submitted_date')
    search_fields = (
        'training_record__trainee__username',
        'training_record__session__program__title'
    )
    readonly_fields = ('training_record', 'submitted_date', 'average_score')
    date_hierarchy = 'submitted_date'
    
    fieldsets = (
        (_('Training Record'), {
            'fields': ('training_record',)
        }),
        (_('Content Evaluation'), {
            'fields': (
                'content_relevance', 'content_clarity', 'content_completeness'
            )
        }),
        (_('Trainer Evaluation'), {
            'fields': (
                'trainer_knowledge', 'trainer_presentation', 'trainer_interaction'
            )
        }),
        (_('Facility Evaluation'), {
            'fields': ('facility_rating', 'materials_rating')
        }),
        (_('Overall Assessment'), {
            'fields': (
                'overall_rating', 'would_recommend', 'average_score'
            )
        }),
        (_('Comments'), {
            'fields': ('strengths', 'improvements', 'additional_comments'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('submitted_date',),
            'classes': ('collapse',)
        }),
    )
    
    def average_score_display(self, obj):
        return f"{obj.average_score:.1f}/5.0"
    average_score_display.short_description = _('Average Score')
    
    def has_add_permission(self, request):
        return False  # Evaluations should be submitted by users, not admins