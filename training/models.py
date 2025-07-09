from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
import uuid

class TrainingProgram(models.Model):
    """برنامج التدريب"""
    
    TRAINING_TYPES = [
        ('initial', _('Initial Training')),
        ('refresher', _('Refresher Training')),
        ('update', _('Update Training')),
        ('compliance', _('Compliance Training')),
        ('technical', _('Technical Training')),
        ('quality', _('Quality Training')),
        ('safety', _('Safety Training')),
    ]
    
    DELIVERY_METHODS = [
        ('classroom', _('Classroom')),
        ('online', _('Online')),
        ('practical', _('Practical')),
        ('self_study', _('Self Study')),
        ('blended', _('Blended')),
    ]
    
    # معلومات أساسية
    program_id = models.CharField(
        _('Program ID'),
        max_length=50,
        unique=True,
        help_text=_('e.g., TRN-QA-001')
    )
    title = models.CharField(_('Title'), max_length=200)
    title_en = models.CharField(_('Title (English)'), max_length=200, blank=True)
    description = models.TextField(_('Description'))
    
    # التصنيف
    training_type = models.CharField(
        _('Training Type'),
        max_length=20,
        choices=TRAINING_TYPES
    )
    delivery_method = models.CharField(
        _('Delivery Method'),
        max_length=20,
        choices=DELIVERY_METHODS,
        default='classroom'
    )
    
    # المدة والتفاصيل
    duration_hours = models.DecimalField(
        _('Duration (Hours)'),
        max_digits=5,
        decimal_places=2
    )
    passing_score = models.IntegerField(
        _('Passing Score %'),
        default=80,
        help_text=_('Minimum score required to pass')
    )
    
    # الصلاحية
    validity_months = models.IntegerField(
        _('Validity (Months)'),
        help_text=_('How long the training remains valid'),
        default=12
    )
    
    # المتطلبات
    prerequisites = models.ManyToManyField(
        'self',
        blank=True,
        symmetrical=False,
        related_name='required_for',
        verbose_name=_('Prerequisites')
    )
    
    # الأقسام المستهدفة
    target_departments = models.ManyToManyField(
        'accounts.User',
        limit_choices_to={'department__isnull': False},
        related_name='required_training_programs',
        verbose_name=_('Target Departments')
    )
    
    # الوثائق المرتبطة
    related_documents = models.ManyToManyField(
        'documents.Document',
        blank=True,
        related_name='training_programs',
        verbose_name=_('Related Documents')
    )
    
    # المدرب
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='training_programs_conducted',
        verbose_name=_('Default Trainer'),
        null=True,
        blank=True
    )
    
    # التواريخ والحالة
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='training_programs_created'
    )
    is_active = models.BooleanField(_('Active'), default=True)
    is_mandatory = models.BooleanField(_('Mandatory'), default=False)
    
    class Meta:
        verbose_name = _('Training Program')
        verbose_name_plural = _('Training Programs')
        ordering = ['-created_date']
    
    def __str__(self):
        return f"{self.program_id} - {self.title}"


class TrainingSession(models.Model):
    """جلسة تدريبية"""
    
    SESSION_STATUS = [
        ('scheduled', _('Scheduled')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    
    # البرنامج التدريبي
    program = models.ForeignKey(
        TrainingProgram,
        on_delete=models.CASCADE,
        related_name='sessions',
        verbose_name=_('Training Program')
    )
    
    # معلومات الجلسة
    session_code = models.CharField(
        _('Session Code'),
        max_length=50,
        unique=True,
        help_text=_('Auto-generated')
    )
    
    # التوقيت والمكان
    scheduled_date = models.DateTimeField(_('Scheduled Date'))
    actual_date = models.DateTimeField(_('Actual Date'), null=True, blank=True)
    location = models.CharField(_('Location'), max_length=200)
    
    # المدرب
    trainer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='training_sessions_conducted',
        verbose_name=_('Trainer')
    )
    
    # الحالة
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=SESSION_STATUS,
        default='scheduled'
    )
    
    # السعة
    max_participants = models.IntegerField(
        _('Maximum Participants'),
        default=20
    )
    
    # ملاحظات
    notes = models.TextField(_('Notes'), blank=True)
    
    # التواريخ
    created_date = models.DateTimeField(_('Created Date'), auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='training_sessions_created'
    )
    
    class Meta:
        verbose_name = _('Training Session')
        verbose_name_plural = _('Training Sessions')
        ordering = ['-scheduled_date']
    
    def __str__(self):
        return f"{self.session_code} - {self.program.title}"
    
    def save(self, *args, **kwargs):
        if not self.session_code:
            # توليد رمز الجلسة
            date_str = timezone.now().strftime('%Y%m%d')
            count = TrainingSession.objects.filter(
                created_date__date=timezone.now().date()
            ).count() + 1
            self.session_code = f"SES-{date_str}-{count:03d}"
        super().save(*args, **kwargs)
    
    @property
    def participants_count(self):
        return self.participants.filter(status='enrolled').count()
    
    @property
    def is_full(self):
        return self.participants_count >= self.max_participants


class TrainingRecord(models.Model):
    """سجل تدريب الموظف"""
    
    ENROLLMENT_STATUS = [
        ('enrolled', _('Enrolled')),
        ('attended', _('Attended')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('absent', _('Absent')),
        ('cancelled', _('Cancelled')),
    ]
    
    # المتدرب والجلسة
    trainee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='training_records',
        verbose_name=_('Trainee')
    )
    session = models.ForeignKey(
        TrainingSession,
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name=_('Training Session')
    )
    
    # الحالة والدرجات
    status = models.CharField(
        _('Status'),
        max_length=20,
        choices=ENROLLMENT_STATUS,
        default='enrolled'
    )
    
    # الحضور
    attendance_date = models.DateTimeField(
        _('Attendance Date'),
        null=True,
        blank=True
    )
    attendance_signature = models.UUIDField(
        _('Attendance Signature'),
        null=True,
        blank=True
    )
    
    # الاختبار
    pre_test_score = models.DecimalField(
        _('Pre-Test Score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    post_test_score = models.DecimalField(
        _('Post-Test Score'),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    test_date = models.DateTimeField(
        _('Test Date'),
        null=True,
        blank=True
    )
    
    # الشهادة
    certificate_number = models.CharField(
        _('Certificate Number'),
        max_length=50,
        unique=True,
        null=True,
        blank=True
    )
    certificate_issued_date = models.DateField(
        _('Certificate Issued Date'),
        null=True,
        blank=True
    )
    certificate_expiry_date = models.DateField(
        _('Certificate Expiry Date'),
        null=True,
        blank=True
    )
    
    # التقييم
    effectiveness_score = models.IntegerField(
        _('Training Effectiveness Score'),
        null=True,
        blank=True,
        help_text=_('1-5 scale')
    )
    feedback = models.TextField(_('Feedback'), blank=True)
    
    # التواريخ
    enrolled_date = models.DateTimeField(_('Enrolled Date'), auto_now_add=True)
    completed_date = models.DateTimeField(
        _('Completed Date'),
        null=True,
        blank=True
    )
    
    # التوقيع الإلكتروني
    electronic_signature = models.UUIDField(
        _('Electronic Signature'),
        null=True,
        blank=True
    )
    signature_date = models.DateTimeField(
        _('Signature Date'),
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Training Record')
        verbose_name_plural = _('Training Records')
        ordering = ['-enrolled_date']
        unique_together = ['trainee', 'session']
    
    def __str__(self):
        return f"{self.trainee.get_full_name()} - {self.session.program.title}"
    
    def save(self, *args, **kwargs):
        # توليد رقم الشهادة عند الإكمال
        if self.status == 'completed' and not self.certificate_number:
            year = timezone.now().year
            count = TrainingRecord.objects.filter(
                certificate_issued_date__year=year
            ).count() + 1
            self.certificate_number = f"CERT-{year}-{count:05d}"
            self.certificate_issued_date = timezone.now().date()
            
            # حساب تاريخ انتهاء الشهادة
            if self.session.program.validity_months:
                from dateutil.relativedelta import relativedelta
                self.certificate_expiry_date = (
                    self.certificate_issued_date + 
                    relativedelta(months=self.session.program.validity_months)
                )
        
        super().save(*args, **kwargs)
    
    @property
    def is_passed(self):
        if self.post_test_score is not None:
            return self.post_test_score >= self.session.program.passing_score
        return False
    
    @property
    def is_expired(self):
        if self.certificate_expiry_date:
            return self.certificate_expiry_date < timezone.now().date()
        return False


class TrainingMaterial(models.Model):
    """المواد التدريبية"""
    
    MATERIAL_TYPES = [
        ('presentation', _('Presentation')),
        ('document', _('Document')),
        ('video', _('Video')),
        ('quiz', _('Quiz')),
        ('exercise', _('Exercise')),
        ('reference', _('Reference Material')),
    ]
    
    # البرنامج التدريبي
    program = models.ForeignKey(
        TrainingProgram,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name=_('Training Program')
    )
    
    # معلومات المادة
    title = models.CharField(_('Title'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    material_type = models.CharField(
        _('Material Type'),
        max_length=20,
        choices=MATERIAL_TYPES
    )
    
    # الملف
    file = models.FileField(
        _('File'),
        upload_to='training_materials/'
    )
    file_size = models.IntegerField(_('File Size (bytes)'), default=0)
    
    # الترتيب
    order = models.IntegerField(_('Order'), default=0)
    
    # الإعدادات
    is_mandatory = models.BooleanField(_('Mandatory'), default=True)
    is_downloadable = models.BooleanField(_('Downloadable'), default=True)
    
    # التواريخ
    uploaded_date = models.DateTimeField(_('Uploaded Date'), auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    
    class Meta:
        verbose_name = _('Training Material')
        verbose_name_plural = _('Training Materials')
        ordering = ['program', 'order', 'title']
    
    def __str__(self):
        return f"{self.program.program_id} - {self.title}"
    
    def save(self, *args, **kwargs):
        if self.file:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class TrainingEvaluation(models.Model):
    """تقييم التدريب"""
    
    # السجل التدريبي
    training_record = models.OneToOneField(
        TrainingRecord,
        on_delete=models.CASCADE,
        related_name='evaluation',
        verbose_name=_('Training Record')
    )
    
    # تقييم المحتوى
    content_relevance = models.IntegerField(
        _('Content Relevance'),
        help_text=_('1-5 scale')
    )
    content_clarity = models.IntegerField(
        _('Content Clarity'),
        help_text=_('1-5 scale')
    )
    content_completeness = models.IntegerField(
        _('Content Completeness'),
        help_text=_('1-5 scale')
    )
    
    # تقييم المدرب
    trainer_knowledge = models.IntegerField(
        _('Trainer Knowledge'),
        help_text=_('1-5 scale')
    )
    trainer_presentation = models.IntegerField(
        _('Trainer Presentation'),
        help_text=_('1-5 scale')
    )
    trainer_interaction = models.IntegerField(
        _('Trainer Interaction'),
        help_text=_('1-5 scale')
    )
    
    # تقييم البيئة
    facility_rating = models.IntegerField(
        _('Facility Rating'),
        help_text=_('1-5 scale')
    )
    materials_rating = models.IntegerField(
        _('Materials Rating'),
        help_text=_('1-5 scale')
    )
    
    # التقييم العام
    overall_rating = models.IntegerField(
        _('Overall Rating'),
        help_text=_('1-5 scale')
    )
    would_recommend = models.BooleanField(
        _('Would Recommend'),
        default=True
    )
    
    # التعليقات
    strengths = models.TextField(_('Strengths'), blank=True)
    improvements = models.TextField(_('Areas for Improvement'), blank=True)
    additional_comments = models.TextField(_('Additional Comments'), blank=True)
    
    # التواريخ
    submitted_date = models.DateTimeField(_('Submitted Date'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Training Evaluation')
        verbose_name_plural = _('Training Evaluations')
        ordering = ['-submitted_date']
    
    def __str__(self):
        return f"Evaluation for {self.training_record}"
    
    @property
    def average_score(self):
        scores = [
            self.content_relevance,
            self.content_clarity,
            self.content_completeness,
            self.trainer_knowledge,
            self.trainer_presentation,
            self.trainer_interaction,
            self.facility_rating,
            self.materials_rating,
            self.overall_rating
        ]
        return sum(scores) / len(scores)