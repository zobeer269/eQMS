# capa/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
import uuid

class CAPA(models.Model):
    """نموذج الإجراءات التصحيحية والوقائية المحسن"""
    
    CAPA_TYPES = [
        ('corrective', _('Corrective Action')),
        ('preventive', _('Preventive Action')),
        ('both', _('Corrective and Preventive Action')),
    ]
    
    SOURCE_TYPES = [
        ('deviation', _('Deviation')),
        ('audit', _('Audit Finding')),
        ('complaint', _('Customer Complaint')),
        ('management_review', _('Management Review')),
        ('risk_assessment', _('Risk Assessment')),
        ('trend_analysis', _('Trend Analysis')),
        ('regulatory', _('Regulatory Requirement')),
        ('change_control', _('Change Control')),
        ('supplier_issue', _('Supplier Issue')),
        ('training_gap', _('Training Gap')),
        ('other', _('Other')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('open', _('Open')),
        ('in_progress', _('In Progress')),
        ('pending_verification', _('Pending Verification')),
        ('pending_effectiveness', _('Pending Effectiveness Check')),
        ('closed', _('Closed')),
        ('cancelled', _('Cancelled')),
        ('on_hold', _('On Hold')),
    ]
    
    PRIORITY_LEVELS = [
        ('critical', _('Critical')),
        ('high', _('High')),
        ('medium', _('Medium')),
        ('low', _('Low')),
    ]
    
    RISK_LEVELS = [
        ('very_high', _('Very High Risk')),
        ('high', _('High Risk')),
        ('medium', _('Medium Risk')),
        ('low', _('Low Risk')),
        ('very_low', _('Very Low Risk')),
    ]
    
    # معرف CAPA
    capa_number = models.CharField(
        _('CAPA Number'),
        max_length=50,
        unique=True,
        help_text=_('e.g., CAPA-2025-001')
    )
    
    # معلومات أساسية
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    capa_type = models.CharField(
        _('CAPA Type'),
        max_length=20,
        choices=CAPA_TYPES
    )
    source_type = models.CharField(
        _('Source Type'),
        max_length=30,
        choices=SOURCE_TYPES
    )
    source_reference = models.CharField(
        _('Source Reference'),
        max_length=100,
        blank=True,
        help_text=_('e.g., DEV-2025-001, AUD-2025-002')
    )
    
    # الحالة والأولوية
    status = models.CharField(
        _('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='medium'
    )
    risk_level = models.CharField(
        _('Risk Level'),
        max_length=20,
        choices=RISK_LEVELS,
        default='medium'
    )
    
    # التواريخ
    initiated_date = models.DateTimeField(_('Initiated Date'), auto_now_add=True)
    due_date = models.DateField(_('Due Date'))
    target_completion_date = models.DateField(
        _('Target Completion Date'),
        null=True,
        blank=True
    )
    actual_completion_date = models.DateField(
        _('Actual Completion Date'),
        null=True,
        blank=True
    )
    closed_date = models.DateTimeField(
        _('Closed Date'),
        null=True,
        blank=True
    )
    
    # الأشخاص المسؤولون
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='initiated_capas',
        verbose_name=_('Initiated By')
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_capas',
        verbose_name=_('Assigned To')
    )
    capa_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_capas',
        verbose_name=_('CAPA Owner')
    )
    
    # تحليل السبب الجذري
    problem_statement = models.TextField(
        _('Problem Statement'),
        help_text=_('Clear description of the problem')
    )
    root_cause_analysis = models.TextField(
        _('Root Cause Analysis'),
        blank=True,
        help_text=_('Detailed analysis of root causes')
    )
    root_cause_method = models.CharField(
        _('Root Cause Method'),
        max_length=50,
        choices=[
            ('5_why', _('5 Why Analysis')),
            ('fishbone', _('Fishbone Diagram')),
            ('fault_tree', _('Fault Tree Analysis')),
            ('brainstorming', _('Brainstorming')),
            ('other', _('Other')),
        ],
        blank=True
    )
    
    # الأقسام المتأثرة
    affected_departments = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={'groups__name__in': ['Quality', 'Production', 'Engineering', 'Regulatory']},
        related_name='department_capas',
        verbose_name=_('Affected Departments'),
        blank=True
    )
    affected_processes = models.TextField(
        _('Affected Processes'),
        blank=True,
        help_text=_('List of affected processes')
    )
    
    # المنتجات المتأثرة
    affected_products = models.ManyToManyField(
        'deviations.Product',
        blank=True,
        verbose_name=_('Affected Products')
    )
    
    # متطلبات خاصة
    requires_regulatory_notification = models.BooleanField(
        _('Requires Regulatory Notification'),
        default=False
    )
    requires_customer_notification = models.BooleanField(
        _('Requires Customer Notification'),
        default=False
    )
    requires_validation = models.BooleanField(
        _('Requires Validation'),
        default=False
    )
    requires_training = models.BooleanField(
        _('Requires Training'),
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
    related_changes = models.ManyToManyField(
        'change_control.ChangeControl',
        blank=True,
        verbose_name=_('Related Changes')
    )
    parent_capa = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_capas',
        verbose_name=_('Parent CAPA')
    )
    
    # تقييم التكاليف والمنافع
    estimated_cost = models.DecimalField(
        _('Estimated Cost'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    actual_cost = models.DecimalField(
        _('Actual Cost'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    expected_benefits = models.TextField(
        _('Expected Benefits'),
        blank=True
    )
    
    # بيانات وصفية
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('CAPA')
        verbose_name_plural = _('CAPAs')
        ordering = ['-initiated_date']
        permissions = [
            ('can_approve_capa', 'Can approve CAPAs'),
            ('can_close_capa', 'Can close CAPAs'),
            ('can_assign_capa', 'Can assign CAPAs'),
            ('can_verify_effectiveness', 'Can verify effectiveness'),
        ]
    
    def __str__(self):
        return f"{self.capa_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.capa_number:
            # توليد رقم CAPA تلقائياً
            year = timezone.now().year
            last_capa = CAPA.objects.filter(
                capa_number__startswith=f'CAPA-{year}-'
            ).order_by('-id').first()
            
            if last_capa:
                last_num = int(last_capa.capa_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            self.capa_number = f'CAPA-{year}-{next_num:03d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('capa:detail', kwargs={'pk': self.pk})
    
    @property
    def is_overdue(self):
        """فحص إذا كان CAPA متأخر"""
        if self.due_date and self.status not in ['closed', 'cancelled']:
            return timezone.now().date() > self.due_date
        return False
    
    @property
    def days_overdue(self):
        """عدد الأيام المتأخرة"""
        if self.is_overdue:
            return (timezone.now().date() - self.due_date).days
        return 0
    
    @property
    def days_until_due(self):
        """عدد الأيام حتى الاستحقاق"""
        if self.due_date and not self.is_overdue:
            return (self.due_date - timezone.now().date()).days
        return 0
    
    @property
    def completion_percentage(self):
        """نسبة الإنجاز"""
        total_actions = self.actions.count()
        if total_actions == 0:
            return 0
        
        completed_actions = self.actions.filter(status='completed').count()
        return round((completed_actions / total_actions) * 100, 1)
    
    @property
    def effectiveness_status(self):
        """حالة فعالية CAPA"""
        effectiveness_checks = self.effectiveness_checks.all()
        if not effectiveness_checks.exists():
            return 'not_checked'
        
        latest_check = effectiveness_checks.order_by('-check_date').first()
        return latest_check.result


class CAPAAction(models.Model):
    """إجراءات CAPA"""
    
    ACTION_TYPES = [
        ('immediate', _('Immediate Action')),
        ('corrective', _('Corrective Action')),
        ('preventive', _('Preventive Action')),
        ('verification', _('Verification Action')),
    ]
    
    STATUS_CHOICES = [
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('verified', _('Verified')),
        ('on_hold', _('On Hold')),
        ('cancelled', _('Cancelled')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='actions',
        verbose_name=_('CAPA')
    )
    
    action_number = models.CharField(
        _('Action Number'),
        max_length=20,
        help_text=_('e.g., A001, A002')
    )
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    action_type = models.CharField(
        _('Action Type'),
        max_length=20,
        choices=ACTION_TYPES
    )
    
    # الحالة والمسؤولية
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned'
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_capa_actions',
        verbose_name=_('Assigned To')
    )
    
    # التواريخ
    planned_start_date = models.DateField(_('Planned Start Date'))
    planned_completion_date = models.DateField(_('Planned Completion Date'))
    actual_start_date = models.DateField(
        _('Actual Start Date'),
        null=True,
        blank=True
    )
    actual_completion_date = models.DateField(
        _('Actual Completion Date'),
        null=True,
        blank=True
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
        related_name='verified_capa_actions',
        verbose_name=_('Verified By')
    )
    verification_date = models.DateTimeField(
        _('Verification Date'),
        null=True,
        blank=True
    )
    verification_notes = models.TextField(
        _('Verification Notes'),
        blank=True
    )
    
    # الموارد والتكاليف
    resources_required = models.TextField(
        _('Resources Required'),
        blank=True
    )
    estimated_cost = models.DecimalField(
        _('Estimated Cost'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    actual_cost = models.DecimalField(
        _('Actual Cost'),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # الأولوية والتبعيات
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=CAPA.PRIORITY_LEVELS,
        default='medium'
    )
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependent_actions',
        blank=True,
        verbose_name=_('Depends On')
    )
    
    # التقدم والملاحظات
    progress_percentage = models.IntegerField(
        _('Progress Percentage'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    notes = models.TextField(_('Notes'), blank=True)
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('CAPA Action')
        verbose_name_plural = _('CAPA Actions')
        ordering = ['action_number']
        unique_together = ['capa', 'action_number']
    
    def __str__(self):
        return f"{self.action_number} - {self.title}"
    
    @property
    def is_overdue(self):
        """فحص إذا كان الإجراء متأخر"""
        if self.planned_completion_date and self.status not in ['completed', 'verified', 'cancelled']:
            return timezone.now().date() > self.planned_completion_date
        return False
    
    @property
    def can_start(self):
        """فحص إذا كان يمكن البدء في الإجراء"""
        if self.status != 'planned':
            return False
        
        # فحص التبعيات
        for dependency in self.depends_on.all():
            if dependency.status not in ['completed', 'verified']:
                return False
        
        return True


class CAPAEffectivenessCheck(models.Model):
    """فحص فعالية CAPA"""
    
    RESULT_CHOICES = [
        ('effective', _('Effective')),
        ('partially_effective', _('Partially Effective')),
        ('ineffective', _('Ineffective')),
        ('pending', _('Pending Evaluation')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='effectiveness_checks',
        verbose_name=_('CAPA')
    )
    
    check_number = models.CharField(
        _('Check Number'),
        max_length=20,
        help_text=_('e.g., EC001, EC002')
    )
    check_date = models.DateField(_('Check Date'))
    check_period_start = models.DateField(_('Check Period Start'))
    check_period_end = models.DateField(_('Check Period End'))
    
    # المعايير والطرق
    evaluation_criteria = models.TextField(
        _('Evaluation Criteria'),
        help_text=_('Criteria used to evaluate effectiveness')
    )
    evaluation_method = models.TextField(
        _('Evaluation Method'),
        help_text=_('Methods used for evaluation')
    )
    
    # النتائج
    result = models.CharField(
        _('Result'),
        max_length=20,
        choices=RESULT_CHOICES,
        default='pending'
    )
    findings = models.TextField(
        _('Findings'),
        help_text=_('Detailed findings from the effectiveness check')
    )
    evidence = models.TextField(
        _('Evidence'),
        blank=True,
        help_text=_('Evidence supporting the findings')
    )
    
    # التوصيات والإجراءات المطلوبة
    recommendations = models.TextField(
        _('Recommendations'),
        blank=True,
        help_text=_('Recommendations for improvement')
    )
    additional_actions_required = models.BooleanField(
        _('Additional Actions Required'),
        default=False
    )
    
    # الأشخاص المسؤولون
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_effectiveness_checks',
        verbose_name=_('Performed By')
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_effectiveness_checks',
        verbose_name=_('Reviewed By')
    )
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('CAPA Effectiveness Check')
        verbose_name_plural = _('CAPA Effectiveness Checks')
        ordering = ['-check_date']
        unique_together = ['capa', 'check_number']
    
    def __str__(self):
        return f"{self.check_number} - {self.capa.capa_number}"


class CAPAApproval(models.Model):
    """موافقات CAPA"""
    
    APPROVAL_TYPES = [
        ('initiation', _('CAPA Initiation')),
        ('action_plan', _('Action Plan')),
        ('implementation', _('Implementation')),
        ('effectiveness', _('Effectiveness Check')),
        ('closure', _('CAPA Closure')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('more_info', _('More Information Required')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='approvals',
        verbose_name=_('CAPA')
    )
    
    approval_type = models.CharField(
        _('Approval Type'),
        max_length=20,
        choices=APPROVAL_TYPES
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='capa_approvals',
        verbose_name=_('Approver')
    )
    
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # تواريخ
    requested_date = models.DateTimeField(_('Requested Date'), auto_now_add=True)
    due_date = models.DateTimeField(_('Due Date'))
    approval_date = models.DateTimeField(
        _('Approval Date'),
        null=True,
        blank=True
    )
    
    # تعليقات
    comments = models.TextField(_('Comments'), blank=True)
    conditions = models.TextField(
        _('Conditions'),
        blank=True,
        help_text=_('Any conditions for approval')
    )
    
    class Meta:
        verbose_name = _('CAPA Approval')
        verbose_name_plural = _('CAPA Approvals')
        unique_together = ['capa', 'approval_type', 'approver']
    
    def __str__(self):
        return f"{self.capa.capa_number} - {self.get_approval_type_display()} - {self.approver}"
    
    @property
    def is_overdue(self):
        """فحص إذا كانت الموافقة متأخرة"""
        if self.due_date and self.status == 'pending':
            return timezone.now() > self.due_date
        return False


class CAPAAttachment(models.Model):
    """مرفقات CAPA"""
    
    ATTACHMENT_TYPES = [
        ('root_cause_analysis', _('Root Cause Analysis')),
        ('action_plan', _('Action Plan')),
        ('evidence', _('Evidence')),
        ('verification_document', _('Verification Document')),
        ('effectiveness_check', _('Effectiveness Check')),
        ('training_material', _('Training Material')),
        ('communication', _('Communication')),
        ('other', _('Other')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('CAPA')
    )
    
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    file = models.FileField(
        _('File'),
        upload_to='capa/attachments/%Y/%m/'
    )
    attachment_type = models.CharField(
        _('Attachment Type'),
        max_length=30,
        choices=ATTACHMENT_TYPES,
        default='other'
    )
    
    uploaded_date = models.DateTimeField(_('Uploaded Date'), auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_capa_attachments',
        verbose_name=_('Uploaded By')
    )
    
    class Meta:
        verbose_name = _('CAPA Attachment')
        verbose_name_plural = _('CAPA Attachments')
        ordering = ['-uploaded_date']
    
    def __str__(self):
        return f"{self.title} - {self.capa.capa_number}"
    
    @property
    def file_size(self):
        """حجم الملف بالميجابايت"""
        if self.file:
            return round(self.file.size / 1024 / 1024, 2)
        return 0
    
    @property
    def file_extension(self):
        """امتداد الملف"""
        if self.file:
            return self.file.name.split('.')[-1].upper()
        return ''


class CAPAComment(models.Model):
    """تعليقات CAPA"""
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('CAPA')
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='capa_comments',
        verbose_name=_('User')
    )
    
    comment = models.TextField(_('Comment'))
    is_internal = models.BooleanField(
        _('Internal Comment'),
        default=True,
        help_text=_('Internal comments are not visible to external stakeholders')
    )
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('CAPA Comment')
        verbose_name_plural = _('CAPA Comments')
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Comment by {self.user} on {self.capa.capa_number}"