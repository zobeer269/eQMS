# change_control/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
import uuid

class ChangeControl(models.Model):
    """نموذج إدارة التغيير"""
    
    CHANGE_TYPES = [
        ('temporary', _('Temporary Change')),
        ('permanent', _('Permanent Change')),
        ('emergency', _('Emergency Change')),
        ('standard', _('Standard Change')),
    ]
    
    CHANGE_CATEGORIES = [
        ('sop', _('Standard Operating Procedure')),
        ('equipment', _('Equipment/Infrastructure')),
        ('system', _('Computer System')),
        ('facility', _('Facility/Building')),
        ('personnel', _('Personnel/Organization')),
        ('supplier', _('Supplier/Vendor')),
        ('product', _('Product/Process')),
        ('regulatory', _('Regulatory/Compliance')),
        ('other', _('Other')),
    ]
    
    URGENCY_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('under_review', _('Under Review')),
        ('impact_assessment', _('Impact Assessment')),
        ('approval_pending', _('Approval Pending')),
        ('approved', _('Approved')),
        ('implementation_planning', _('Implementation Planning')),
        ('implementation_approved', _('Implementation Approved')),
        ('in_progress', _('In Progress')),
        ('testing', _('Testing')),
        ('verification', _('Verification')),
        ('completed', _('Completed')),
        ('rejected', _('Rejected')),
        ('cancelled', _('Cancelled')),
        ('on_hold', _('On Hold')),
    ]
    
    # معرف التغيير
    change_number = models.CharField(
        _('Change Number'),
        max_length=50,
        unique=True,
        help_text=_('e.g., CHG-2025-001')
    )
    
    # معلومات أساسية
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    change_type = models.CharField(
        _('Change Type'),
        max_length=20,
        choices=CHANGE_TYPES
    )
    change_category = models.CharField(
        _('Change Category'),
        max_length=30,
        choices=CHANGE_CATEGORIES
    )
    urgency = models.CharField(
        _('Urgency'),
        max_length=20,
        choices=URGENCY_LEVELS,
        default='medium'
    )
    
    # الحالة والتواريخ
    status = models.CharField(
        _('Status'),
        max_length=30,
        choices=STATUS_CHOICES,
        default='draft'
    )
    submission_date = models.DateTimeField(
        _('Submission Date'),
        null=True,
        blank=True
    )
    target_implementation_date = models.DateField(
        _('Target Implementation Date'),
        null=True,
        blank=True
    )
    actual_implementation_date = models.DateField(
        _('Actual Implementation Date'),
        null=True,
        blank=True
    )
    completion_date = models.DateTimeField(
        _('Completion Date'),
        null=True,
        blank=True
    )
    
    # الأشخاص المسؤولون
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='requested_changes',
        verbose_name=_('Requester')
    )
    change_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
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
    
    # سبب التغيير والفوائد
    change_reason = models.TextField(
        _('Change Reason'),
        help_text=_('Why is this change necessary?')
    )
    change_benefits = models.TextField(
        _('Change Benefits'),
        blank=True,
        help_text=_('What are the expected benefits?')
    )
    
    # الأقسام والمناطق المتأثرة
    affected_departments = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        limit_choices_to={'groups__name__in': ['Quality', 'Production', 'Engineering', 'Regulatory']},
        related_name='department_changes',
        verbose_name=_('Affected Departments'),
        blank=True
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
    
    # تقييم المخاطر والمتطلبات
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
    related_capas = models.ManyToManyField(
        'capa.CAPA',
        blank=True,
        verbose_name=_('Related CAPAs')
    )
    parent_change = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_changes',
        verbose_name=_('Parent Change')
    )
    
    # بيانات وصفية
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_changes',
        verbose_name=_('Created By')
    )
    
    class Meta:
        verbose_name = _('Change Control')
        verbose_name_plural = _('Change Controls')
        ordering = ['-submission_date', '-id']
        permissions = [
            ('can_approve_change', 'Can approve changes'),
            ('can_implement_change', 'Can implement changes'),
            ('can_coordinate_change', 'Can coordinate changes'),
            ('can_view_all_changes', 'Can view all changes'),
        ]
    
    def __str__(self):
        return f"{self.change_number} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.change_number:
            # توليد رقم التغيير تلقائياً
            year = timezone.now().year
            last_change = ChangeControl.objects.filter(
                change_number__startswith=f'CHG-{year}-'
            ).order_by('-id').first()
            
            if last_change:
                last_num = int(last_change.change_number.split('-')[-1])
                next_num = last_num + 1
            else:
                next_num = 1
            
            self.change_number = f'CHG-{year}-{next_num:03d}'
        
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('change_control:detail', kwargs={'pk': self.pk})
    
    @property
    def is_overdue(self):
        """فحص إذا كان التغيير متأخر"""
        if self.target_implementation_date and self.status not in ['completed', 'cancelled', 'rejected']:
            return timezone.now().date() > self.target_implementation_date
        return False
    
    @property
    def days_until_implementation(self):
        """عدد الأيام حتى التنفيذ"""
        if self.target_implementation_date:
            delta = self.target_implementation_date - timezone.now().date()
            return delta.days
        return None
    
    @property
    def implementation_progress(self):
        """نسبة تقدم التنفيذ"""
        if not hasattr(self, 'implementation_plan'):
            return 0
        
        total_tasks = self.implementation_plan.tasks.count()
        if total_tasks == 0:
            return 0
        
        completed_tasks = self.implementation_plan.tasks.filter(status='completed').count()
        return round((completed_tasks / total_tasks) * 100, 1)


class ChangeImpactAssessment(models.Model):
    """تقييم تأثير التغيير"""
    
    IMPACT_LEVELS = [
        ('none', _('No Impact')),
        ('minimal', _('Minimal Impact')),
        ('moderate', _('Moderate Impact')),
        ('significant', _('Significant Impact')),
        ('major', _('Major Impact')),
    ]
    
    change_control = models.OneToOneField(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='impact_assessment',
        verbose_name=_('Change Control')
    )
    
    # تأثير على الجودة
    quality_impact = models.CharField(
        _('Quality Impact'),
        max_length=20,
        choices=IMPACT_LEVELS,
        default='none'
    )
    quality_impact_description = models.TextField(
        _('Quality Impact Description'),
        blank=True
    )
    
    # تأثير على السلامة
    safety_impact = models.CharField(
        _('Safety Impact'),
        max_length=20,
        choices=IMPACT_LEVELS,
        default='none'
    )
    safety_impact_description = models.TextField(
        _('Safety Impact Description'),
        blank=True
    )
    
    # تأثير على الامتثال التنظيمي
    regulatory_impact = models.CharField(
        _('Regulatory Impact'),
        max_length=20,
        choices=IMPACT_LEVELS,
        default='none'
    )
    regulatory_impact_description = models.TextField(
        _('Regulatory Impact Description'),
        blank=True
    )
    
    # تأثير بيئي
    environmental_impact = models.CharField(
        _('Environmental Impact'),
        max_length=20,
        choices=IMPACT_LEVELS,
        default='none'
    )
    environmental_impact_description = models.TextField(
        _('Environmental Impact Description'),
        blank=True
    )
    
    # التأثير المالي
    cost_impact = models.CharField(
        _('Cost Impact'),
        max_length=20,
        choices=IMPACT_LEVELS,
        default='none'
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
        help_text=_('Comprehensive risk assessment for this change')
    )
    risk_mitigation = models.TextField(
        _('Risk Mitigation'),
        help_text=_('Plans to mitigate identified risks')
    )
    
    # الموارد المطلوبة
    resources_required = models.TextField(
        _('Resources Required'),
        help_text=_('Personnel, equipment, materials needed')
    )
    
    # التدريب المطلوب
    training_required = models.BooleanField(
        _('Training Required'),
        default=False
    )
    training_description = models.TextField(
        _('Training Description'),
        blank=True
    )
    
    # الوثائق التي تحتاج تحديث
    documents_to_update = models.TextField(
        _('Documents to Update'),
        blank=True,
        help_text=_('List of documents that need updating')
    )
    
    # تواريخ
    assessed_date = models.DateTimeField(_('Assessed Date'), auto_now_add=True)
    assessed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assessed_changes',
        verbose_name=_('Assessed By')
    )
    
    class Meta:
        verbose_name = _('Change Impact Assessment')
        verbose_name_plural = _('Change Impact Assessments')
    
    def __str__(self):
        return f"Impact Assessment for {self.change_control.change_number}"
    
    @property
    def overall_impact_level(self):
        """حساب مستوى التأثير الإجمالي"""
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
            self.environmental_impact,
            self.cost_impact
        ]
        
        total_score = sum(impact_scores.get(impact, 0) for impact in impacts)
        max_score = max(impact_scores.get(impact, 0) for impact in impacts)
        
        if max_score >= 4:
            return 'major'
        elif max_score >= 3:
            return 'significant'
        elif total_score >= 8:
            return 'moderate'
        elif total_score >= 4:
            return 'minimal'
        else:
            return 'none'


class ChangeImplementationPlan(models.Model):
    """خطة تنفيذ التغيير"""
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('under_review', _('Under Review')),
        ('approved', _('Approved')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('on_hold', _('On Hold')),
    ]
    
    change_control = models.OneToOneField(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='implementation_plan',
        verbose_name=_('Change Control')
    )
    
    implementation_approach = models.TextField(
        _('Implementation Approach'),
        help_text=_('Detailed approach for implementing the change')
    )
    
    # التواريخ
    planned_start_date = models.DateField(_('Planned Start Date'))
    planned_end_date = models.DateField(_('Planned End Date'))
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
    
    # الحالة
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )
    
    # خطة التراجع
    rollback_plan = models.TextField(
        _('Rollback Plan'),
        help_text=_('Plan for rolling back if implementation fails')
    )
    
    # معايير النجاح
    success_criteria = models.TextField(
        _('Success Criteria'),
        help_text=_('How to measure successful implementation')
    )
    
    # خطة التحقق
    verification_plan = models.TextField(
        _('Verification Plan'),
        help_text=_('How to verify the change was implemented correctly')
    )
    
    # المعتمد والتواريخ
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_implementation_plans',
        verbose_name=_('Approved By')
    )
    approval_date = models.DateTimeField(
        _('Approval Date'),
        null=True,
        blank=True
    )
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_implementation_plans',
        verbose_name=_('Created By')
    )
    
    class Meta:
        verbose_name = _('Change Implementation Plan')
        verbose_name_plural = _('Change Implementation Plans')
    
    def __str__(self):
        return f"Implementation Plan for {self.change_control.change_number}"


class ChangeTask(models.Model):
    """مهام تنفيذ التغيير"""
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('verified', _('Verified')),
        ('on_hold', _('On Hold')),
        ('cancelled', _('Cancelled')),
    ]
    
    PRIORITY_LEVELS = [
        ('low', _('Low')),
        ('medium', _('Medium')),
        ('high', _('High')),
        ('critical', _('Critical')),
    ]
    
    implementation_plan = models.ForeignKey(
        ChangeImplementationPlan,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name=_('Implementation Plan')
    )
    
    task_number = models.CharField(
        _('Task Number'),
        max_length=20,
        help_text=_('e.g., T001, T002')
    )
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'))
    
    # الأولوية والحالة
    priority = models.CharField(
        _('Priority'),
        max_length=20,
        choices=PRIORITY_LEVELS,
        default='medium'
    )
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )
    
    # المسؤول والتواريخ
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='assigned_change_tasks',
        verbose_name=_('Assigned To')
    )
    due_date = models.DateField(_('Due Date'))
    completion_date = models.DateTimeField(
        _('Completion Date'),
        null=True,
        blank=True
    )
    
    # التبعيات
    depends_on = models.ManyToManyField(
        'self',
        symmetrical=False,
        related_name='dependent_tasks',
        blank=True,
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
    verification_date = models.DateTimeField(
        _('Verification Date'),
        null=True,
        blank=True
    )
    verification_notes = models.TextField(
        _('Verification Notes'),
        blank=True
    )
    
    # التقدم
    progress_percentage = models.IntegerField(
        _('Progress Percentage'),
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    # ملاحظات
    notes = models.TextField(_('Notes'), blank=True)
    
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    updated_date = models.DateTimeField(_('Updated Date'), auto_now=True)
    
    class Meta:
        verbose_name = _('Change Task')
        verbose_name_plural = _('Change Tasks')
        ordering = ['task_number']
        unique_together = ['implementation_plan', 'task_number']
    
    def __str__(self):
        return f"{self.task_number} - {self.title}"
    
    @property
    def is_overdue(self):
        """فحص إذا كانت المهمة متأخرة"""
        if self.due_date and self.status not in ['completed', 'verified', 'cancelled']:
            return timezone.now().date() > self.due_date
        return False
    
    @property
    def can_start(self):
        """فحص إذا كان يمكن البدء في المهمة"""
        if self.status != 'pending':
            return False
        
        # فحص التبعيات
        for dependency in self.depends_on.all():
            if dependency.status not in ['completed', 'verified']:
                return False
        
        return True


class ChangeApproval(models.Model):
    """موافقات التغيير"""
    
    APPROVAL_TYPES = [
        ('change_review', _('Change Review')),
        ('impact_assessment', _('Impact Assessment')),
        ('implementation_plan', _('Implementation Plan')),
        ('final_approval', _('Final Approval')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('more_info', _('More Information Required')),
    ]
    
    change_control = models.ForeignKey(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='approvals',
        verbose_name=_('Change Control')
    )
    
    approval_type = models.CharField(
        _('Approval Type'),
        max_length=30,
        choices=APPROVAL_TYPES
    )
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='change_approvals',
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
        verbose_name = _('Change Approval')
        verbose_name_plural = _('Change Approvals')
        unique_together = ['change_control', 'approval_type', 'approver']
    
    def __str__(self):
        return f"{self.change_control.change_number} - {self.get_approval_type_display()} - {self.approver}"
    
    @property
    def is_overdue(self):
        """فحص إذا كانت الموافقة متأخرة"""
        if self.due_date and self.status == 'pending':
            return timezone.now() > self.due_date
        return False


class ChangeAttachment(models.Model):
    """مرفقات التغيير"""
    
    ATTACHMENT_TYPES = [
        ('impact_assessment', _('Impact Assessment Document')),
        ('implementation_plan', _('Implementation Plan')),
        ('risk_assessment', _('Risk Assessment')),
        ('validation_protocol', _('Validation Protocol')),
        ('test_results', _('Test Results')),
        ('approval_memo', _('Approval Memo')),
        ('training_material', _('Training Material')),
        ('communication', _('Communication')),
        ('other', _('Other')),
    ]
    
    change_control = models.ForeignKey(
        ChangeControl,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('Change Control')
    )
    
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    file = models.FileField(
        _('File'),
        upload_to='change_control/attachments/%Y/%m/'
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
        related_name='uploaded_change_attachments',
        verbose_name=_('Uploaded By')
    )
    
    class Meta:
        verbose_name = _('Change Attachment')
        verbose_name_plural = _('Change Attachments')
        ordering = ['-uploaded_date']
    
    def __str__(self):
        return f"{self.title} - {self.change_control.change_number}"
    
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