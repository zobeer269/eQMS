# deviations/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
import uuid

class Product(models.Model):
    """نموذج المنتجات المحسن"""
    
    product_code = models.CharField(
        _('Product Code'),
        max_length=50,
        unique=True,
        help_text=_('Unique product identifier')
    )
    product_name = models.CharField(_('Product Name'), max_length=200)
    product_name_en = models.CharField(_('Product Name (English)'), max_length=200, blank=True)
    description = models.TextField(_('Description'), blank=True)
    
    # التصنيف
    product_category = models.CharField(
        _('Product Category'),
        max_length=50,
        choices=[
            ('pharmaceutical', _('Pharmaceutical')),
            ('medical_device', _('Medical Device')),
            ('cosmetic', _('Cosmetic')),
            ('food_supplement', _('Food Supplement')),
            ('other', _('Other')),
        ],
        default='pharmaceutical'
    )
    
    # معلومات تنظيمية
    registration_number = models.CharField(
        _('Registration Number'),
        max_length=100,
        blank=True
    )
    regulatory_status = models.CharField(
        _('Regulatory Status'),
        max_length=50,
        choices=[
            ('registered', _('Registered')),
            ('pending', _('Pending Registration')),
            ('suspended', _('Suspended')),
            ('withdrawn', _('Withdrawn')),
        ],
        default='registered'
    )
    
    # معلومات التصنيع
    manufacturer = models.CharField(_('Manufacturer'), max_length=200, blank=True)
    manufacturing_site = models.CharField(_('Manufacturing Site'), max_length=200, blank=True)
    batch_size = models.CharField(_('Standard Batch Size'), max_length=100, blank=True)
    
    # معلومات الجودة
    shelf_life = models.CharField(_('Shelf Life'), max_length=50, blank=True)
    storage_conditions = models.TextField(_('Storage Conditions'), blank=True)
    specification_version = models.CharField(_('Specification Version'), max_length=50, blank=True)
    
    # الحالة
    is_active = models.BooleanField(_('Is Active'), default=True)
    discontinuation_date = models.DateField(_('Discontinuation Date'), null=True, blank=True)
    
    # بيانات وصفية
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('Product')
        verbose_name_plural = _('Products')
        ordering = ['product_code']
    
    def __str__(self):
        return f"{self.product_code} - {self.product_name}"


class Deviation(models.Model):
    """نموذج الانحرافات المحسن"""
    
    DEVIATION_TYPES = [
        ('process', _('Process Deviation')),
        ('product_quality', _('Product Quality')),
        ('facility', _('Facility/Equipment')),
        ('documentation', _('Documentation')),
        ('personnel', _('Personnel/Training')),
        ('supplier', _('Supplier Related')),
        ('environmental', _('Environmental')),
        ('system', _('Computer System')),
        ('validation', _('Validation/Qualification')),
        ('regulatory', _('Regulatory Compliance')),
        ('other', _('Other')),
    ]
    
    SEVERITY_LEVELS = [
        ('critical', _('Critical')),
        ('major', _('Major')),
        ('minor', _('Minor')),
        ('informational', _('Informational')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('open', _('Open')),
        ('investigation', _('Under Investigation')),
        ('pending_approval', _('Pending Approval')),
        ('approved', _('Approved')),
        ('capa_required', _('CAPA Required')),
        ('capa_in_progress', _('CAPA In Progress')),
        ('pending_closure', _('Pending Closure')),
        ('closed', _('Closed')),
        ('cancelled', _('Cancelled')),
    ]
    
    IMPACT_ASSESSMENTS = [
        ('none', _('No Impact')),
        ('minimal', _('Minimal Impact')),
        ('moderate', _('Moderate Impact')),
        ('significant', _('Significant Impact')),
        ('major', _('Major Impact')),
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
        max_length=30,
        choices=DEVIATION_TYPES
    )
    severity = models.CharField(
        _('Severity'),
        max_length=20,
        choices=SEVERITY_LEVELS
    )
    
    # الحالة والتواريخ
    status = models.CharField(
        _('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )
    occurrence_date = models.DateTimeField(_('Occurrence Date'))
    reported_date = models.DateTimeField(_('Reported Date'), auto_now_add=True)
    due_date = models.DateField(_('Due Date'), null=True, blank=True)
    closure_date = models.DateTimeField(_('Closure Date'), null=True, blank=True)
    
    # الأشخاص المسؤولون
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
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
    investigation_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='owned_investigations',
        verbose_name=_('Investigation Owner')
    )
    
    # تفاصيل الانحراف
    department = models.CharField(
        _('Department'),
        max_length=50,
        choices=[
            ('production', _('Production')),
            ('quality_control', _('Quality Control')),
            ('quality_assurance', _('Quality Assurance')),
            ('warehouse', _('Warehouse')),
            ('laboratory', _('Laboratory')),
            ('engineering', _('Engineering')),
            ('maintenance', _('Maintenance')),
            ('regulatory', _('Regulatory Affairs')),
            ('purchasing', _('Purchasing')),
            ('other', _('Other')),
        ]
    )
    area_location = models.CharField(
        _('Area/Location'),
        max_length=200,
        help_text=_('Specific area or location where deviation occurred')
    )
    
    # المنتجات والدفعات المتأثرة
    affected_products = models.ManyToManyField(
        Product,
        blank=True,
        verbose_name=_('Affected Products')
    )
    affected_batches = models.TextField(
        _('Affected Batches'),
        blank=True,
        help_text=_('List of affected batch numbers')
    )
    batch_quantity = models.CharField(
        _('Batch Quantity'),
        max_length=100,
        blank=True
    )
    
    # تقييم التأثير
    quality_impact = models.CharField(
        _('Quality Impact'),
        max_length=20,
        choices=IMPACT_ASSESSMENTS,
        default='none'
    )
    safety_impact = models.CharField(
        _('Safety Impact'),
        max_length=20,
        choices=IMPACT_ASSESSMENTS,
        default='none'
    )
    regulatory_impact = models.CharField(
        _('Regulatory Impact'),
        max_length=20,
        choices=IMPACT_ASSESSMENTS,
        default='none'
    )
    customer_impact = models.CharField(
        _('Customer Impact'),
        max_length=20,
        choices=IMPACT_ASSESSMENTS,
        default='none'
    )
    
    # تفاصيل الأثر
    impact_description = models.TextField(
        _('Impact Description'),
        blank=True,
        help_text=_('Detailed description of the impact')
    )
    immediate_actions = models.TextField(
        _('Immediate Actions Taken'),
        blank=True,
        help_text=_('Actions taken immediately after discovery')
    )
    
    # التحقيق
    investigation_summary = models.TextField(
        _('Investigation Summary'),
        blank=True
    )
    root_cause_analysis = models.TextField(
        _('Root Cause Analysis'),
        blank=True
    )
    contributing_factors = models.TextField(
        _('Contributing Factors'),
        blank=True
    )
    
    # الإجراءات التصحيحية والوقائية
    corrective_actions = models.TextField(
        _('Corrective Actions'),
        blank=True
    )
    preventive_actions = models.TextField(
        _('Preventive Actions'),
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
    parent_deviation = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_deviations',
        verbose_name=_('Parent Deviation')
    )
    
    # متطلبات خاصة
    requires_capa = models.BooleanField(_('Requires CAPA'), default=False)
    requires_change_control = models.BooleanField(_('Requires Change Control'), default=False)
    requires_regulatory_notification = models.BooleanField(_('Requires Regulatory Notification'), default=False)
    requires_customer_notification = models.BooleanField(_('Requires Customer Notification'), default=False)
    
    # التصنيف الإضافي
    is_recurring = models.BooleanField(_('Is Recurring'), default=False)
    recurrence_frequency = models.CharField(
        _('Recurrence Frequency'),
        max_length=50,
        blank=True,
        help_text=_('How often does this type of deviation occur?')
    )
    previous_occurrences = models.TextField(
        _('Previous Occurrences'),
        blank=True,
        help_text=_('References to previous similar deviations')
    )
    
    # التكاليف
    estimated_cost = models.DecimalField(
        _('Estimated Cost'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_('Estimated cost of deviation and remediation')
    )
    actual_cost = models.DecimalField(
        _('Actual Cost'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    # بيانات وصفية
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('Deviation')
        verbose_name_plural = _('Deviations')
        ordering = ['-reported_date']
        permissions = [
            ('can_approve_deviation', 'Can approve deviations'),
            ('can_close_deviation', 'Can close deviations'),
            ('can_assign_deviation', 'Can assign deviations'),
            ('can_investigate_deviation', 'Can investigate deviations'),
        ]
    
    def __str__(self):
        return f"{self.deviation_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.deviation_number:
            # توليد رقم الانحراف تلقائياً
            year = timezone.now().year
            last_deviation = Deviation.objects.filter(
                deviation_number__startswith=f'DEV-{year}-'
            ).order_by('-id').first()
            
            if last_deviation:
                last_num = int(last_deviation.deviation_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            self.deviation_number = f'DEV-{year}-{next_num:03d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('deviations:detail', kwargs={'pk': self.pk})
    
    @property
    def is_overdue(self):
        """فحص إذا كان الانحراف متأخر"""
        if self.due_date and self.status not in ['closed', 'cancelled']:
            return timezone.now().date() > self.due_date
        return False
    
    @property
    def days_open(self):
        """عدد الأيام منذ فتح الانحراف"""
        if self.status == 'closed' and self.closure_date:
            return (self.closure_date.date() - self.reported_date.date()).days
        else:
            return (timezone.now().date() - self.reported_date.date()).days
    
    @property
    def overall_impact_level(self):
        """مستوى التأثير الإجمالي"""
        impact_scores = {
            'none': 0,
            'minimal': 1,
            'moderate': 2,
            'significant': 3,
            'major': 4
        }
        
        impacts = [
            self.quality_impact,
            self.safety_impact,
            self.regulatory_impact,
            self.customer_impact
        ]
        
        max_score = max(impact_scores.get(impact, 0) for impact in impacts)
        
        if max_score >= 4:
            return 'major'
        elif max_score >= 3:
            return 'significant'
        elif max_score >= 2:
            return 'moderate'
        elif max_score >= 1:
            return 'minimal'
        else:
            return 'none'
    
    @property
    def requires_immediate_action(self):
        """فحص إذا كان يتطلب إجراء فوري"""
        return (
            self.severity in ['critical', 'major'] or
            self.overall_impact_level in ['major', 'significant']
        )


class DeviationInvestigation(models.Model):
    """تحقيق الانحراف"""
    
    INVESTIGATION_METHODS = [
        ('interview', _('Interviews')),
        ('document_review', _('Document Review')),
        ('observation', _('Direct Observation')),
        ('testing', _('Testing/Analysis')),
        ('expert_consultation', _('Expert Consultation')),
        ('trend_analysis', _('Trend Analysis')),
        ('other', _('Other')),
    ]
    
    STATUS_CHOICES = [
        ('initiated', _('Initiated')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('reviewed', _('Reviewed')),
        ('approved', _('Approved')),
    ]
    
    deviation = models.OneToOneField(
        Deviation,
        on_delete=models.CASCADE,
        related_name='investigation',
        verbose_name=_('Deviation')
    )
    
    # معلومات التحقيق
    investigation_plan = models.TextField(
        _('Investigation Plan'),
        help_text=_('Detailed plan for investigating the deviation')
    )
    investigation_method = models.CharField(
        _('Investigation Method'),
        max_length=30,
        choices=INVESTIGATION_METHODS
    )
    investigation_team = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='investigations',
        verbose_name=_('Investigation Team')
    )
    
    # الحالة والتواريخ
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='initiated'
    )
    started_date = models.DateTimeField(_('Started Date'), auto_now_add=True)
    completed_date = models.DateTimeField(_('Completed Date'), null=True, blank=True)
    target_completion_date = models.DateField(_('Target Completion Date'))
    
    # النتائج
    findings = models.TextField(
        _('Key Findings'),
        blank=True,
        help_text=_('Summary of investigation findings')
    )
    evidence_collected = models.TextField(
        _('Evidence Collected'),
        blank=True,
        help_text=_('List and description of evidence')
    )
    interviews_conducted = models.TextField(
        _('Interviews Conducted'),
        blank=True,
        help_text=_('Summary of interviews and personnel involved')
    )
    
    # تحليل السبب الجذري
    root_cause_identified = models.BooleanField(_('Root Cause Identified'), default=False)
    root_cause_description = models.TextField(
        _('Root Cause Description'),
        blank=True
    )
    contributing_factors = models.TextField(
        _('Contributing Factors'),
        blank=True
    )
    
    # التوصيات
    recommendations = models.TextField(
        _('Recommendations'),
        blank=True,
        help_text=_('Recommended actions based on investigation')
    )
    capa_recommended = models.BooleanField(_('CAPA Recommended'), default=False)
    change_control_recommended = models.BooleanField(_('Change Control Recommended'), default=False)
    
    # المراجعة والموافقة
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_investigations',
        verbose_name=_('Reviewed By')
    )
    review_date = models.DateTimeField(_('Review Date'), null=True, blank=True)
    review_comments = models.TextField(_('Review Comments'), blank=True)
    
    class Meta:
        verbose_name = _('Deviation Investigation')
        verbose_name_plural = _('Deviation Investigations')
    
    def __str__(self):
        return f"Investigation for {self.deviation.deviation_number}"
    
    @property
    def is_overdue(self):
        """فحص إذا كان التحقيق متأخر"""
        if self.target_completion_date and self.status not in ['completed', 'reviewed', 'approved']:
            return timezone.now().date() > self.target_completion_date
        return False


class DeviationApproval(models.Model):
    """موافقات الانحراف"""
    
    APPROVAL_TYPES = [
        ('investigation', _('Investigation Approval')),
        ('corrective_action', _('Corrective Action Approval')),
        ('closure', _('Closure Approval')),
        ('capa_initiation', _('CAPA Initiation Approval')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('more_info', _('More Information Required')),
    ]
    
    deviation = models.ForeignKey(
        Deviation,
        on_delete=models.CASCADE,
        related_name='approvals',
        verbose_name=_('Deviation')
    )
    
    approval_type = models.CharField(
        _('Approval Type'),
        max_length=30,
        choices=APPROVAL_TYPES
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deviation_approvals',
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
    approval_date = models.DateTimeField(_('Approval Date'), null=True, blank=True)
    
    # تعليقات
    comments = models.TextField(_('Comments'), blank=True)
    conditions = models.TextField(
        _('Conditions'),
        blank=True,
        help_text=_('Any conditions for approval')
    )
    
    class Meta:
        verbose_name = _('Deviation Approval')
        verbose_name_plural = _('Deviation Approvals')
        unique_together = ['deviation', 'approval_type', 'approver']
    
    def __str__(self):
        return f"{self.deviation.deviation_number} - {self.get_approval_type_display()} - {self.approver}"
    
    @property
    def is_overdue(self):
        """فحص إذا كانت الموافقة متأخرة"""
        if self.due_date and self.status == 'pending':
            return timezone.now() > self.due_date
        return False


class DeviationAttachment(models.Model):
    """مرفقات الانحراف"""
    
    ATTACHMENT_TYPES = [
        ('evidence', _('Evidence')),
        ('investigation_report', _('Investigation Report')),
        ('corrective_action_plan', _('Corrective Action Plan')),
        ('test_results', _('Test Results')),
        ('photos', _('Photos')),
        ('documentation', _('Documentation')),
        ('correspondence', _('Correspondence')),
        ('other', _('Other')),
    ]
    
    deviation = models.ForeignKey(
        Deviation,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('Deviation')
    )
    
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    file = models.FileField(
        _('File'),
        upload_to='deviations/attachments/%Y/%m/'
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
        related_name='uploaded_deviation_attachments',
        verbose_name=_('Uploaded By')
    )
    
    class Meta:
        verbose_name = _('Deviation Attachment')
        verbose_name_plural = _('Deviation Attachments')
        ordering = ['-uploaded_date']
    
    def __str__(self):
        return f"{self.title} - {self.deviation.deviation_number}"
    
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


class DeviationComment(models.Model):
    """تعليقات الانحراف"""
    
    deviation = models.ForeignKey(
        Deviation,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name=_('Deviation')
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='deviation_comments',
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
        verbose_name = _('Deviation Comment')
        verbose_name_plural = _('Deviation Comments')
        ordering = ['-created_date']
    
    def __str__(self):
        return f"Comment by {self.user} on {self.deviation.deviation_number}"


class DeviationTrendAnalysis(models.Model):
    """تحليل اتجاهات الانحرافات"""
    
    ANALYSIS_PERIODS = [
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('semi_annual', _('Semi-Annual')),
        ('annual', _('Annual')),
    ]
    
    analysis_period = models.CharField(
        _('Analysis Period'),
        max_length=20,
        choices=ANALYSIS_PERIODS
    )
    period_start = models.DateField(_('Period Start'))
    period_end = models.DateField(_('Period End'))
    
    # إحصائيات
    total_deviations = models.IntegerField(_('Total Deviations'), default=0)
    critical_deviations = models.IntegerField(_('Critical Deviations'), default=0)
    major_deviations = models.IntegerField(_('Major Deviations'), default=0)
    minor_deviations = models.IntegerField(_('Minor Deviations'), default=0)
    
    # التحليل
    top_deviation_types = models.JSONField(
        _('Top Deviation Types'),
        default=dict,
        help_text=_('Most frequent deviation types')
    )
    top_departments = models.JSONField(
        _('Top Departments'),
        default=dict,
        help_text=_('Departments with most deviations')
    )
    trend_summary = models.TextField(
        _('Trend Summary'),
        help_text=_('Summary of trends identified')
    )
    
    # التوصيات
    recommendations = models.TextField(
        _('Recommendations'),
        help_text=_('Recommendations based on trend analysis')
    )
    action_items = models.TextField(
        _('Action Items'),
        blank=True,
        help_text=_('Specific action items to address trends')
    )
    
    # المعد والمراجع
    prepared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='prepared_trend_analyses',
        verbose_name=_('Prepared By')
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_trend_analyses',
        verbose_name=_('Reviewed By')
    )
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Deviation Trend Analysis')
        verbose_name_plural = _('Deviation Trend Analyses')
        ordering = ['-period_end']
        unique_together = ['analysis_period', 'period_start', 'period_end']
    
    def __str__(self):
        return f"Trend Analysis - {self.get_analysis_period_display()} ({self.period_start} to {self.period_end})"