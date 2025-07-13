from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class CAPA(models.Model):
    """نموذج الإجراءات التصحيحية والوقائية"""
    
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
    ]
    
    PRIORITY_LEVELS = [
        ('high', _('High')),
        ('medium', _('Medium')),
        ('low', _('Low')),
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
    
    # التواريخ
    initiated_date = models.DateTimeField(
        _('Initiated Date'),
        auto_now_add=True
    )
    due_date = models.DateField(
        _('Due Date'),
        help_text=_('Target completion date')
    )
    completion_date = models.DateField(
        _('Completion Date'),
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
        on_delete=models.PROTECT,
        related_name='initiated_capas',
        verbose_name=_('Initiated By')
    )
    capa_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_capas',
        verbose_name=_('CAPA Owner')
    )
    capa_coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coordinated_capas',
        verbose_name=_('CAPA Coordinator')
    )
    
    # الأقسام المتأثرة
    affected_departments = models.ManyToManyField(
        'accounts.User',
        limit_choices_to={'department__isnull': False},
        related_name='department_capas',
        verbose_name=_('Affected Departments')
    )
    
    # تحليل السبب الجذري
    problem_statement = models.TextField(
        _('Problem Statement'),
        help_text=_('Clear description of the problem')
    )
    root_cause_analysis = models.TextField(
        _('Root Cause Analysis'),
        blank=True
    )
    root_cause_category = models.CharField(
        _('Root Cause Category'),
        max_length=50,
        blank=True,
        choices=[
            ('people', _('People')),
            ('process', _('Process')),
            ('equipment', _('Equipment')),
            ('material', _('Material')),
            ('environment', _('Environment')),
            ('measurement', _('Measurement')),
            ('management', _('Management')),
        ]
    )
    
    # تقييم المخاطر
    risk_assessment = models.TextField(
        _('Risk Assessment'),
        blank=True
    )
    risk_level = models.CharField(
        _('Risk Level'),
        max_length=20,
        blank=True,
        choices=[
            ('critical', _('Critical')),
            ('high', _('High')),
            ('medium', _('Medium')),
            ('low', _('Low')),
        ]
    )
    
    # العلاقات
    related_documents = models.ManyToManyField(
        'documents.Document',
        blank=True,
        verbose_name=_('Related Documents')
    )
    
    class Meta:
        verbose_name = _('CAPA')
        verbose_name_plural = _('CAPAs')
        ordering = ['-initiated_date']
        permissions = [
            ('can_approve_capa', 'Can approve CAPA'),
            ('can_close_capa', 'Can close CAPA'),
            ('can_verify_capa', 'Can verify CAPA effectiveness'),
        ]
    
    def __str__(self):
        return f"{self.capa_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.capa_number:
            # توليد رقم CAPA تلقائياً
            year = timezone.now().year
            last_capa = CAPA.objects.filter(
                capa_number__startswith=f'CAPA-{year}-'
            ).order_by('-capa_number').first()
            
            if last_capa:
                last_number = int(last_capa.capa_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.capa_number = f'CAPA-{year}-{new_number:03d}'
        
        super().save(*args, **kwargs)
    
    @property
    def is_overdue(self):
        """التحقق من تأخر CAPA"""
        if self.status in ['closed', 'cancelled']:
            return False
        return timezone.now().date() > self.due_date
    
    @property
    def days_until_due(self):
        """عدد الأيام حتى الاستحقاق"""
        if self.status in ['closed', 'cancelled']:
            return None
        delta = self.due_date - timezone.now().date()
        return delta.days


class CAPAAction(models.Model):
    """الإجراءات التفصيلية ل CAPA"""
    
    ACTION_TYPES = [
        ('immediate', _('Immediate Action')),
        ('corrective', _('Corrective Action')),
        ('preventive', _('Preventive Action')),
        ('interim', _('Interim Action')),
    ]
    
    STATUS_CHOICES = [
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('verified', _('Verified')),
        ('cancelled', _('Cancelled')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='actions'
    )
    
    action_number = models.PositiveIntegerField(
        _('Action Number'),
        help_text=_('Sequential number within CAPA')
    )
    
    action_type = models.CharField(
        _('Action Type'),
        max_length=20,
        choices=ACTION_TYPES
    )
    
    # تفاصيل الإجراء
    action_description = models.TextField(
        _('Action Description')
    )
    responsible_person = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='responsible_actions',
        verbose_name=_('Responsible Person')
    )
    
    # الحالة والتواريخ
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned'
    )
    planned_date = models.DateField(
        _('Planned Completion Date')
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
        related_name='verified_actions',
        verbose_name=_('Verified By')
    )
    verification_date = models.DateField(
        _('Verification Date'),
        null=True,
        blank=True
    )
    verification_comments = models.TextField(
        _('Verification Comments'),
        blank=True
    )
    
    # الأدلة
    evidence_description = models.TextField(
        _('Evidence Description'),
        blank=True,
        help_text=_('Description of evidence/documentation')
    )
    
    class Meta:
        verbose_name = _('CAPA Action')
        verbose_name_plural = _('CAPA Actions')
        ordering = ['capa', 'action_number']
        unique_together = ['capa', 'action_number']


class CAPAEffectivenessCheck(models.Model):
    """فحص فعالية CAPA"""
    
    EFFECTIVENESS_RESULTS = [
        ('effective', _('Effective')),
        ('partially_effective', _('Partially Effective')),
        ('not_effective', _('Not Effective')),
        ('pending', _('Pending')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='effectiveness_checks'
    )
    
    check_number = models.PositiveIntegerField(
        _('Check Number'),
        default=1
    )
    
    # جدولة الفحص
    planned_date = models.DateField(
        _('Planned Check Date')
    )
    actual_date = models.DateField(
        _('Actual Check Date'),
        null=True,
        blank=True
    )
    
    # طريقة الفحص
    check_method = models.TextField(
        _('Check Method'),
        help_text=_('How effectiveness will be verified')
    )
    acceptance_criteria = models.TextField(
        _('Acceptance Criteria'),
        help_text=_('Criteria for determining effectiveness')
    )
    
    # النتائج
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='performed_effectiveness_checks',
        verbose_name=_('Performed By')
    )
    
    result = models.CharField(
        _('Result'),
        max_length=30,
        choices=EFFECTIVENESS_RESULTS,
        default='pending'
    )
    
    findings = models.TextField(
        _('Findings'),
        blank=True
    )
    
    # الإجراءات الإضافية
    additional_actions_required = models.BooleanField(
        _('Additional Actions Required'),
        default=False
    )
    additional_actions_description = models.TextField(
        _('Additional Actions Description'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('CAPA Effectiveness Check')
        verbose_name_plural = _('CAPA Effectiveness Checks')
        ordering = ['capa', 'check_number']
        unique_together = ['capa', 'check_number']


class CAPAApproval(models.Model):
    """موافقات CAPA"""
    
    APPROVAL_STAGES = [
        ('initiation', _('CAPA Initiation')),
        ('action_plan', _('Action Plan')),
        ('completion', _('CAPA Completion')),
        ('effectiveness', _('Effectiveness Verification')),
        ('closure', _('CAPA Closure')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('withdrawn', _('Withdrawn')),
    ]
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    
    approval_stage = models.CharField(
        _('Approval Stage'),
        max_length=30,
        choices=APPROVAL_STAGES
    )
    
    # المراجع/الموافق
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='capa_approvals',
        verbose_name=_('Approver')
    )
    approval_role = models.CharField(
        _('Approval Role'),
        max_length=50,
        choices=[
            ('qa_manager', _('QA Manager')),
            ('department_head', _('Department Head')),
            ('technical_director', _('Technical Director')),
            ('quality_director', _('Quality Director')),
        ]
    )
    
    # الحالة والتواريخ
    status = models.CharField(
        _('Status'),
        max_length=20,
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
    
    # التعليقات والتوقيع
    comments = models.TextField(
        _('Comments'),
        blank=True
    )
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
        verbose_name = _('CAPA Approval')
        verbose_name_plural = _('CAPA Approvals')
        ordering = ['requested_date']
        unique_together = ['capa', 'approval_stage', 'approver']


class CAPAAttachment(models.Model):
    """مرفقات CAPA"""
    
    capa = models.ForeignKey(
        CAPA,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    title = models.CharField(_('Title'), max_length=200)
    file = models.FileField(
        _('File'),
        upload_to='capa/attachments/%Y/%m/'
    )
    attachment_type = models.CharField(
        _('Attachment Type'),
        max_length=50,
        choices=[
            ('evidence', _('Evidence')),
            ('root_cause', _('Root Cause Analysis')),
            ('action_plan', _('Action Plan')),
            ('verification', _('Verification Document')),
            ('effectiveness', _('Effectiveness Check')),
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
        verbose_name = _('CAPA Attachment')
        verbose_name_plural = _('CAPA Attachments')
        ordering = ['-uploaded_date']