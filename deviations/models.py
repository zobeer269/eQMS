from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Deviation(models.Model):
    """نموذج الانحراف الرئيسي"""
    
    DEVIATION_TYPES = [
        ('process', _('Process Deviation')),
        ('product', _('Product Deviation')),
        ('equipment', _('Equipment Deviation')),
        ('environmental', _('Environmental Deviation')),
        ('documentation', _('Documentation Deviation')),
        ('quality', _('Quality Deviation')),
        ('safety', _('Safety Deviation')),
        ('other', _('Other')),
    ]
    
    SEVERITY_LEVELS = [
        ('critical', _('Critical')),
        ('major', _('Major')),
        ('minor', _('Minor')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('open', _('Open')),
        ('under_investigation', _('Under Investigation')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('closed', _('Closed')),
        ('cancelled', _('Cancelled')),
    ]
    
    # معرف الانحراف
    deviation_number = models.CharField(
        _('Deviation Number'),
        max_length=50,
        unique=True,
        help_text=_('e.g., DEV-2025-001')
    )
    
    # معلومات أساسية
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    deviation_type = models.CharField(
        _('Deviation Type'),
        max_length=20,
        choices=DEVIATION_TYPES
    )
    severity = models.CharField(
        _('Severity Level'),
        max_length=20,
        choices=SEVERITY_LEVELS
    )
    status = models.CharField(
        _('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # التواريخ
    occurrence_date = models.DateTimeField(_('Occurrence Date'))
    detection_date = models.DateTimeField(_('Detection Date'))
    reported_date = models.DateTimeField(_('Reported Date'), auto_now_add=True)
    closed_date = models.DateTimeField(_('Closed Date'), null=True, blank=True)
    
    # الأشخاص المسؤولون
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reported_deviations',
        verbose_name=_('Reported By')
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_deviations',
        verbose_name=_('Assigned To')
    )
    qa_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='qa_reviewed_deviations',
        verbose_name=_('QA Reviewer')
    )
    
    # التفاصيل
    location = models.CharField(_('Location'), max_length=200)
    department = models.CharField(
        _('Department'),
        max_length=100,
        choices=[
            ('production', _('Production')),
            ('quality', _('Quality')),
            ('warehouse', _('Warehouse')),
            ('laboratory', _('Laboratory')),
            ('engineering', _('Engineering')),
            ('other', _('Other')),
        ]
    )
    
    # المنتجات والدفعات المتأثرة
    affected_products = models.ManyToManyField(
        'Product',
        blank=True,
        verbose_name=_('Affected Products')
    )
    affected_batches = models.TextField(
        _('Affected Batches'),
        blank=True,
        help_text=_('List batch numbers separated by commas')
    )
    
    # التأثير والمخاطر
    impact_assessment = models.TextField(
        _('Impact Assessment'),
        blank=True
    )
    risk_assessment = models.TextField(
        _('Risk Assessment'),
        blank=True
    )
    
    # الإجراءات الفورية
    immediate_actions = models.TextField(
        _('Immediate Actions Taken'),
        blank=True
    )
    containment_actions = models.TextField(
        _('Containment Actions'),
        blank=True
    )
    
    # التحقيق
    root_cause = models.TextField(
        _('Root Cause Analysis'),
        blank=True
    )
    investigation_summary = models.TextField(
        _('Investigation Summary'),
        blank=True
    )
    
    # العلاقات
    related_documents = models.ManyToManyField(
        'documents.Document',
        blank=True,
        verbose_name=_('Related Documents')
    )
    related_capa = models.OneToOneField(
        'capa.CAPA',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deviation',
        verbose_name=_('Related CAPA')
    )
    related_change_control = models.ForeignKey(
        'change_control.ChangeControl',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deviations',
        verbose_name=_('Related Change Control')
    )
    
    # الموافقات
    requires_capa = models.BooleanField(
        _('Requires CAPA'),
        default=False
    )
    requires_change_control = models.BooleanField(
        _('Requires Change Control'),
        default=False
    )
    
    # بيانات وصفية
    is_recurring = models.BooleanField(
        _('Is Recurring'),
        default=False
    )
    previous_occurrences = models.TextField(
        _('Previous Occurrences'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('Deviation')
        verbose_name_plural = _('Deviations')
        ordering = ['-reported_date']
        permissions = [
            ('can_approve_deviation', 'Can approve deviations'),
            ('can_close_deviation', 'Can close deviations'),
            ('can_assign_deviation', 'Can assign deviations'),
        ]
    
    def __str__(self):
        return f"{self.deviation_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.deviation_number:
            # توليد رقم الانحراف تلقائياً
            year = timezone.now().year
            last_deviation = Deviation.objects.filter(
                deviation_number__startswith=f'DEV-{year}-'
            ).order_by('-deviation_number').first()
            
            if last_deviation:
                last_number = int(last_deviation.deviation_number.split('-')[-1])
                new_number = last_number + 1
            else:
                new_number = 1
            
            self.deviation_number = f'DEV-{year}-{new_number:03d}'
        
        super().save(*args, **kwargs)
    
    @property
    def days_open(self):
        """عدد الأيام منذ فتح الانحراف"""
        if self.closed_date:
            return (self.closed_date - self.reported_date).days
        return (timezone.now() - self.reported_date).days
    
    @property
    def is_overdue(self):
        """التحقق من تأخر الانحراف"""
        if self.status in ['closed', 'cancelled']:
            return False
        
        # Critical: 7 days, Major: 14 days, Minor: 30 days
        due_days = {'critical': 7, 'major': 14, 'minor': 30}
        return self.days_open > due_days.get(self.severity, 30)


class DeviationInvestigation(models.Model):
    """تحقيق الانحراف"""
    
    deviation = models.OneToOneField(
        Deviation,
        on_delete=models.CASCADE,
        related_name='investigation'
    )
    
    # تفاصيل التحقيق
    investigation_team = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='deviation_investigations',
        verbose_name=_('Investigation Team')
    )
    investigation_lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='led_investigations',
        verbose_name=_('Investigation Lead')
    )
    
    # الجدول الزمني
    investigation_start_date = models.DateTimeField(
        _('Investigation Start Date'),
        default=timezone.now
    )
    investigation_end_date = models.DateTimeField(
        _('Investigation End Date'),
        null=True,
        blank=True
    )
    
    # طرق التحقيق
    investigation_methods = models.TextField(
        _('Investigation Methods'),
        help_text=_('e.g., Fishbone diagram, 5 Whys, etc.')
    )
    
    # النتائج
    findings = models.TextField(_('Investigation Findings'))
    root_cause_category = models.CharField(
        _('Root Cause Category'),
        max_length=50,
        choices=[
            ('human_error', _('Human Error')),
            ('equipment_failure', _('Equipment Failure')),
            ('process_failure', _('Process Failure')),
            ('material_defect', _('Material Defect')),
            ('environmental', _('Environmental Factors')),
            ('procedure_inadequate', _('Inadequate Procedure')),
            ('training_gap', _('Training Gap')),
            ('other', _('Other')),
        ]
    )
    
    # المرفقات
    attachments = models.ManyToManyField(
        'DeviationAttachment',
        blank=True,
        verbose_name=_('Attachments')
    )
    
    # التوصيات
    recommendations = models.TextField(
        _('Recommendations'),
        blank=True
    )
    
    class Meta:
        verbose_name = _('Deviation Investigation')
        verbose_name_plural = _('Deviation Investigations')


class DeviationApproval(models.Model):
    """موافقات الانحراف"""
    
    APPROVAL_TYPES = [
        ('initial', _('Initial Review')),
        ('investigation', _('Investigation Approval')),
        ('closure', _('Closure Approval')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('withdrawn', _('Withdrawn')),
    ]
    
    deviation = models.ForeignKey(
        Deviation,
        on_delete=models.CASCADE,
        related_name='approvals'
    )
    
    approval_type = models.CharField(
        _('Approval Type'),
        max_length=20,
        choices=APPROVAL_TYPES
    )
    
    # المراجع/الموافق
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='deviation_approvals',
        verbose_name=_('Approver')
    )
    approval_role = models.CharField(
        _('Approval Role'),
        max_length=50,
        choices=[
            ('qa_reviewer', _('QA Reviewer')),
            ('qa_manager', _('QA Manager')),
            ('production_manager', _('Production Manager')),
            ('technical_director', _('Technical Director')),
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
        verbose_name = _('Deviation Approval')
        verbose_name_plural = _('Deviation Approvals')
        ordering = ['requested_date']
        unique_together = ['deviation', 'approval_type', 'approver']


class DeviationAttachment(models.Model):
    """مرفقات الانحراف"""
    
    deviation = models.ForeignKey(
        Deviation,
        on_delete=models.CASCADE,
        related_name='attachments'
    )
    
    title = models.CharField(_('Title'), max_length=200)
    file = models.FileField(
        _('File'),
        upload_to='deviations/attachments/%Y/%m/'
    )
    file_type = models.CharField(
        _('File Type'),
        max_length=50,
        choices=[
            ('photo', _('Photo')),
            ('document', _('Document')),
            ('report', _('Report')),
            ('evidence', _('Evidence')),
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
        verbose_name = _('Deviation Attachment')
        verbose_name_plural = _('Deviation Attachments')
        ordering = ['-uploaded_date']


class Product(models.Model):
    """نموذج المنتج (مؤقت - يمكن نقله لتطبيق منفصل)"""
    
    product_code = models.CharField(
        _('Product Code'),
        max_length=50,
        unique=True
    )
    product_name = models.CharField(
        _('Product Name'),
        max_length=200
    )
    product_name_en = models.CharField(
        _('Product Name (English)'),
        max_length=200,
        blank=True
    )
    description = models.TextField(
        _('Description'),
        blank=True
    )
    is_active = models.BooleanField(
        _('Is Active'),
        default=True
    )
    
    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['product_code']
    
    def __str__(self):
        return f"{self.product_code} - {self.product_name}"