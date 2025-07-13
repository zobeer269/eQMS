from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class ChangeControl(models.Model):
    """نموذج التحكم بالتغيير الرئيسي"""
    
    CHANGE_TYPES = [
        ('process', _('Process Change')),
        ('equipment', _('Equipment Change')),
        ('facility', _('Facility Change')),
        ('supplier', _('Supplier Change')),
        ('material', _('Material Change')),
        ('specification', _('Specification Change')),
        ('software', _('Software Change')),
        ('document', _('Document Change')),
        ('other', _('Other')),
    ]
    
    CHANGE_CATEGORIES = [
        ('minor', _('Minor Change')),
        ('major', _('Major Change')),
        ('critical', _('Critical Change')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('under_review', _('Under Review')),
        ('impact_assessment', _('Impact Assessment')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('implementation', _('Implementation')),
        ('verification', _('Verification')),
        ('closed', _('Closed')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
    ]
    
    URGENCY_LEVELS = [
        ('emergency', _('Emergency')),
        ('urgent', _('Urgent')),
        ('normal', _('Normal')),
        ('low', _('Low')),
    ]
    
    # معرف التغيير
    change_number = models.CharField(
        _('Change Control Number'),
        max_length=50,
        unique=True,
        help_text=_('e.g., CC-2025-001')
    )
    
    # معلومات أساسية
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description of Change'))
    change_type = models.CharField(
        _('Change Type'),
        max_length=20,
        choices=CHANGE_TYPES
    )
    change_category = models.CharField(
        _('Change Category'),
        max_length=20,
        choices=CHANGE_CATEGORIES
    )
    urgency = models.CharField(
        _('Urgency Level'),
        max_length=20,
        choices=URGENCY_LEVELS,
        default='normal'
    )
    status = models.CharField(
        _('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # سبب التغيير
    change_reason = models.TextField(
        _('Reason for Change'),
        help_text=_('Detailed justification for the change')
    )
    change_benefits = models.TextField(
        _('Expected Benefits'),
        blank=True
    )
    
    # التواريخ
    submission_date = models.DateTimeField(
        _('Submission Date'),
        null=True,
        blank=True
    )
    target_implementation_date = models.DateField(
        _('Target Implementation Date')
    )
    actual_implementation_date = models.DateField(
        _('Actual Implementation Date'),
        null=True,
        blank=True
    )
    closure_date = models.DateTimeField(
        _('Closure Date'),
        null=True,
        blank=True
    )
    
    # الأشخاص المسؤولون
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='initiated_changes',
        verbose_name=_('Initiated By')
    )
    change_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_changes',
        verbose_name=_('Change Owner')
    )
    change_coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coordinated_changes',
        verbose_name=_('Change Coordinator')
    )
    
    # الأقسام والمناطق المتأثرة
    affected_departments = models.ManyToManyField(
        'accounts.User',
        limit_choices_to={'department__isnull': False},
        related_name='department_changes',
        verbose_name=_('Affected Departments')
    )
    affected_areas = models.TextField(
        _('Affected Areas'),
        help_text=_('List all areas/systems affected by this change')
    )
    
    # المنتجات المتأثرة
    affected_products = models.ManyToManyField(
        'deviations.Product',
        blank=True,
        verbose_name=_('Affected Products')
    )
    
    # تقييم المخاطر
    requires_risk_assessment = models.BooleanField(
        _('Requires Risk Assessment'),
        default=True
    )
    requires_validation = models.BooleanField(
        _('Requires Validation'),
        default=False
    )
    requires_regulatory_approval = models.BooleanField(
        _('Requires Regulatory Approval'),
        default=False
    )
    
    # العلاقات
    related_documents = models.ManyToManyField(
        'documents.Document',
        blank=True,
        verbose_name=_('Related Documents')
    )
    related_deviations = models.ManyToManyField(
        'deviations.Deviation',
        blank=True,
        verbose_name=_('Related Deviations')
    )
    related_capas = models.ManyToManyField(
        'capa.CAPA',
        blank=True,
        verbose_name=_('Related CAPAs')
    )
    
    class Meta:
        verbose_name = _('Change Control')
        verbose_name_plural = _('Change Controls')
        ordering = ['-submission_date', '-id']
        permissions = [
            ('can_approve_change', 'Can approve change control'),
            ('can_implement_change', 'Can implement change'),
            ('can_close_change', 'Can close change control'),
        ]
    
    def __str__(self):
        return f"{self.change_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.change_number:
            # توليد رقم التغيير تلقائياً
            year = timezone.now().year
            last_change = ChangeControl.objects.filter(
                change_number__startswith=f'CC-{year}-'
            ).order_by('-change_number').first()
            
            if last_change:
                last_number = int(last_change.change_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.change_number = f'CC-{year}-{new_number:03d}'
        
        # تحديث تاريخ التقديم عند تغيير الحالة
        if self.status == 'submitted' and not self.submission_date:
            self.submission_date = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """التحقق من تأخر التنفيذ"""
        if self.status in ['closed', 'rejected', 'cancelled']:
            return False
        if self.status in ['implementation', 'verification'] and self.target_implementation_date:
            return timezone.now().date() > self.target_implementation_date
        return False


class ChangeImpactAssessment(models.Model):
    """تقييم تأثير التغيير"""
    
    IMPACT_LEVELS = [
        ('no_impact', _('No Impact')),
        ('low', _('Low Impact')),
        ('medium', _('Medium Impact')),
        ('high', _('High Impact')),
        ('critical', _('Critical Impact')),
    ]
    
    change_control = models.OneToOneField(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='impact_assessment'
    )
    
    # تقييم التأثير على مختلف الجوانب
    quality_impact = models.CharField(
        _('Quality Impact'),
        max_length=20,
        choices=IMPACT_LEVELS
    )
    quality_impact_description = models.TextField(
        _('Quality Impact Description'),
        blank=True
    )
    
    safety_impact = models.CharField(
        _('Safety Impact'),
        max_length=20,
        choices=IMPACT_LEVELS
    )
    safety_impact_description = models.TextField(
        _('Safety Impact Description'),
        blank=True
    )
    
    regulatory_impact = models.CharField(
        _('Regulatory Impact'),
        max_length=20,
        choices=IMPACT_LEVELS
    )
    regulatory_impact_description = models.TextField(
        _('Regulatory Impact Description'),
        blank=True
    )
    
    environmental_impact = models.CharField(
        _('Environmental Impact'),
        max_length=20,
        choices=IMPACT_LEVELS
    )
    environmental_impact_description = models.TextField(
        _('Environmental Impact Description'),
        blank=True
    )
    
    cost_impact = models.CharField(
        _('Cost Impact'),
        max_length=20,
        choices=IMPACT_LEVELS
    )
    estimated_cost = models.DecimalField(
        _('Estimated Cost'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # تقييم المخاطر
    risk_assessment = models.TextField(
        _('Risk Assessment'),
        blank=True
    )
    risk_mitigation = models.TextField(
        _('Risk Mitigation Measures'),
        blank=True
    )
    
    # الموارد المطلوبة
    resources_required = models.TextField(
        _('Resources Required'),
        help_text=_('Personnel, equipment, materials, etc.')
    )
    training_required = models.BooleanField(
        _('Training Required'),
        default=False
    )
    training_description = models.TextField(
        _('Training Description'),
        blank=True
    )
    
    # الوثائق المتأثرة
    documents_to_update = models.TextField(
        _('Documents to Update'),
        blank=True,
        help_text=_('List all documents requiring updates')
    )
    
    # التقييم بواسطة
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_('Assessed By')
    )
    assessment_date = models.DateTimeField(
        _('Assessment Date'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Change Impact Assessment')
        verbose_name_plural = _('Change Impact Assessments')


class ChangeImplementationPlan(models.Model):
    """خطة تنفيذ التغيير"""
    
    change_control = models.OneToOneField(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='implementation_plan'
    )
    
    # خطة التنفيذ
    implementation_steps = models.TextField(
        _('Implementation Steps'),
        help_text=_('Detailed step-by-step implementation plan')
    )
    
    # الجدول الزمني
    planned_start_date = models.DateField(
        _('Planned Start Date')
    )
    planned_end_date = models.DateField(
        _('Planned End Date')
    )
    
    # معايير القبول
    acceptance_criteria = models.TextField(
        _('Acceptance Criteria'),
        help_text=_('Criteria for successful implementation')
    )
    
    # خطة التراجع
    rollback_plan = models.TextField(
        _('Rollback Plan'),
        help_text=_('Plan to revert changes if needed')
    )
    
    # التواصل
    communication_plan = models.TextField(
        _('Communication Plan'),
        help_text=_('How change will be communicated')
    )
    
    # التحقق والتحقق من الصحة
    verification_method = models.TextField(
        _('Verification Method'),
        help_text=_('How implementation will be verified')
    )
    validation_required = models.BooleanField(
        _('Validation Required'),
        default=False
    )
    validation_protocol = models.TextField(
        _('Validation Protocol'),
        blank=True
    )
    
    # الموافقة على الخطة
    plan_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_implementation_plans',
        verbose_name=_('Plan Approved By')
    )
    plan_approval_date = models.DateTimeField(
        _('Plan Approval Date'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Change Implementation Plan')
        verbose_name_plural = _('Change Implementation Plans')


class ChangeTask(models.Model):
    """مهام تنفيذ التغيير"""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('verified', _('Verified')),
        ('cancelled', _('Cancelled')),
    ]
    
    change_control = models.ForeignKey(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    
    task_number = models.PositiveIntegerField(
        _('Task Number')
    )
    task_description = models.TextField(
        _('Task Description')
    )
    
    # المسؤول والحالة
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='assigned_change_tasks',
        verbose_name=_('Assigned To')
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # التواريخ
    planned_start_date = models.DateField(
        _('Planned Start Date')
    )
    planned_end_date = models.DateField(
        _('Planned End Date')
    )
    actual_start_date = models.DateField(
        _('Actual Start Date'),
        null=True,
        blank=True
    )
    actual_end_date = models.DateField(
        _('Actual End Date'),
        null=True,
        blank=True
    )
    
    # التبعيات
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        blank=True,
        related_name='dependent_tasks',
        verbose_name=_('Depends On')
    )
    
    # التحقق
    verification_required = models.BooleanField(
        _('Verification Required'),
        default=True
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_change_tasks',
        verbose_name=_('Verified By')
    )
    verification_date = models.DateField(
        _('Verification Date'),
        null=True,
        blank=True
    )
    
    # التعليقات والملاحظات
    comments = models.TextField(
        _('Comments'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('Change Task')
        verbose_name_plural = _('Change Tasks')
        ordering = ['change_control', 'task_number']
        unique_together = ['change_control', 'task_number']


class ChangeApproval(models.Model):
    """موافقات التغيير"""
    
    APPROVAL_TYPES = [
        ('initial_review', _('Initial Review')),
        ('impact_assessment', _('Impact Assessment Review')),
        ('implementation_plan', _('Implementation Plan Approval')),
        ('pre_implementation', _('Pre-Implementation Approval')),
        ('post_implementation', _('Post-Implementation Verification')),
        ('closure', _('Change Closure Approval')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('approved_with_conditions', _('Approved with Conditions')),
        ('rejected', _('Rejected')),
        ('withdrawn', _('Withdrawn')),
    ]
    
    change_control = models.ForeignKey(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    
    approval_type = models.CharField(
        _('Approval Type'),
        max_length=30,
        choices=APPROVAL_TYPES
    )
    
    # المراجع/الموافق
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='change_approvals',
        verbose_name=_('Approver')
    )
    approval_role = models.CharField(
        _('Approval Role'),
        max_length=50,
        choices=[
            ('department_head', _('Department Head')),
            ('qa_manager', _('QA Manager')),
            ('technical_director', _('Technical Director')),
            ('regulatory_affairs', _('Regulatory Affairs')),
            ('quality_director', _('Quality Director')),
            ('general_manager', _('General Manager')),
        ]
    )
    
    # الحالة والتواريخ
    status = models.CharField(
        _('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending'
    )
    requested_date = models.DateTimeField(
        _('Requested Date'),
        auto_now_add=True
    )
    action_date = models.DateTimeField(
        _('Action Date'),
        null=True,
        blank=True
    )
    
    # التعليقات والشروط
    comments = models.TextField(
        _('Comments'),
        blank=True
    )
    conditions = models.TextField(
        _('Conditions'),
        blank=True,
        help_text=_('Conditions for approval if applicable')
    )
    
    # التوقيع الإلكتروني
    electronic_signature = models.UUIDField(
        _('Electronic Signature'),
        null=True,
        blank=True
    )
    signature_meaning = models.CharField(
        _('Signature Meaning'),
        max_length=200,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Change Approval')
        verbose_name_plural = _('Change Approvals')
        ordering = ['requested_date']
        unique_together = ['change_control', 'approval_type', 'approver']


class ChangeAttachment(models.Model):
    """مرفقات التغيير"""
    
    change_control = models.ForeignKey(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    title = models.CharField(_('Title'), max_length=200)
    file = models.FileField(
        _('File'),
        upload_to='change_control/attachments/%Y/%m/'
    )
    attachment_type = models.CharField(
        _('Attachment Type'),
        max_length=50,
        choices=[
            ('proposal', _('Change Proposal')),
            ('impact_assessment', _('Impact Assessment')),
            ('risk_assessment', _('Risk Assessment')),
            ('implementation_plan', _('Implementation Plan')),
            ('validation_protocol', _('Validation Protocol')),
            ('verification_report', _('Verification Report')),
            ('approval_document', _('Approval Document')),
            ('other', _('Other')),
        ]
    )
    description = models.TextField(
        _('Description'),
        blank=True
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_('Uploaded By')
    )
    uploaded_date = models.DateTimeField(
        _('Uploaded Date'),
        auto_now_add=True
    )
    
    class Meta:
        verbose_name = _('Change Attachment')
        verbose_name_plural = _('Change Attachments')
        ordering = ['-uploaded_date']