# change_control/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    ChangeControl, ChangeImpactAssessment, ChangeImplementationPlan,
    ChangeTask, ChangeApproval, ChangeAttachment
)
from accounts.models import User
from documents.models import Document
from deviations.models import Deviation, Product
from capa.models import CAPA
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Div, Field, HTML, Row, Column
from crispy_forms.bootstrap import TabHolder, Tab, PrependedText
import datetime


class ChangeControlCreateForm(forms.ModelForm):
    """نموذج إنشاء طلب تغيير جديد"""
    
    class Meta:
        model = ChangeControl
        fields = [
            'title', 'description', 'change_type', 'change_category',
            'urgency', 'change_reason', 'change_benefits',
            'target_implementation_date', 'change_owner',
            'affected_departments', 'affected_areas', 'affected_products',
            'requires_risk_assessment', 'requires_validation',
            'requires_regulatory_approval', 'requires_training',
            'related_documents', 'related_deviations', 'related_capas'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Brief title for the change')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Detailed description of the proposed change')
            }),
            'change_type': forms.Select(attrs={'class': 'form-select'}),
            'change_category': forms.Select(attrs={'class': 'form-select'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'change_reason': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Why is this change necessary?')
            }),
            'change_benefits': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('What are the expected benefits?')
            }),
            'target_implementation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'change_owner': forms.Select(attrs={'class': 'form-select'}),
            'affected_departments': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '5'
            }),
            'affected_areas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List all areas/systems affected')
            }),
            'affected_products': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'requires_risk_assessment': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_validation': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_regulatory_approval': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'requires_training': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'related_documents': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'related_deviations': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'related_capas': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص خيارات المالك
        self.fields['change_owner'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production']
        ).distinct()
        
        # تخصيص الأقسام المتأثرة
        self.fields['affected_departments'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Production', 'Engineering', 'Regulatory']
        ).distinct()
        
        # المنتجات النشطة فقط
        self.fields['affected_products'].queryset = Product.objects.filter(is_active=True)
        
        # الوثائق المنشورة فقط
        self.fields['related_documents'].queryset = Document.objects.filter(
            status='published'
        )
        
        # الانحرافات النشطة
        self.fields['related_deviations'].queryset = Deviation.objects.filter(
            status__in=['open', 'investigation', 'pending_approval']
        )
        
        # الـ CAPAs النشطة
        self.fields['related_capas'].queryset = CAPA.objects.filter(
            status__in=['open', 'in_progress', 'pending_verification']
        )
        
        # Crispy Forms Helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(_('Basic Information'),
                    Row(
                        Column('title', css_class='col-md-8'),
                        Column('urgency', css_class='col-md-4'),
                    ),
                    'description',
                    Row(
                        Column('change_type', css_class='col-md-6'),
                        Column('change_category', css_class='col-md-6'),
                    ),
                    'change_reason',
                    'change_benefits',
                ),
                Tab(_('Implementation Details'),
                    Row(
                        Column('target_implementation_date', css_class='col-md-6'),
                        Column('change_owner', css_class='col-md-6'),
                    ),
                    'affected_areas',
                    Row(
                        Column('affected_departments', css_class='col-md-6'),
                        Column('affected_products', css_class='col-md-6'),
                    ),
                ),
                Tab(_('Requirements'),
                    Row(
                        Column(
                            Field('requires_risk_assessment', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                        Column(
                            Field('requires_validation', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                    ),
                    Row(
                        Column(
                            Field('requires_regulatory_approval', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                        Column(
                            Field('requires_training', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                    ),
                ),
                Tab(_('Related Items'),
                    'related_documents',
                    'related_deviations',
                    'related_capas',
                ),
            ),
            ButtonHolder(
                Submit('submit', _('Create Change Request'), css_class='btn btn-primary'),
                HTML('<a href="{% url "change_control:list" %}" class="btn btn-secondary">{% trans "Cancel" %}</a>')
            )
        )
    
    def clean_target_implementation_date(self):
        date = self.cleaned_data.get('target_implementation_date')
        if date and date <= timezone.now().date():
            raise ValidationError(_('Target implementation date must be in the future.'))
        return date
    
    def clean(self):
        cleaned_data = super().clean()
        
        # التحقق من أن التغييرات التي تتطلب موافقة تنظيمية لها تاريخ تنفيذ كافٍ
        requires_regulatory = cleaned_data.get('requires_regulatory_approval')
        target_date = cleaned_data.get('target_implementation_date')
        
        if requires_regulatory and target_date:
            min_date = timezone.now().date() + datetime.timedelta(days=30)
            if target_date < min_date:
                raise ValidationError({
                    'target_implementation_date': _(
                        'Changes requiring regulatory approval need at least 30 days lead time.'
                    )
                })
        
        return cleaned_data


class ChangeControlEditForm(forms.ModelForm):
    """نموذج تعديل طلب التغيير"""
    
    class Meta:
        model = ChangeControl
        fields = [
            'title', 'description', 'change_type', 'change_category',
            'urgency', 'change_reason', 'change_benefits',
            'target_implementation_date', 'change_owner', 'change_coordinator',
            'affected_areas', 'affected_products',
            'requires_risk_assessment', 'requires_validation',
            'requires_regulatory_approval', 'requires_training'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'change_type': forms.Select(attrs={'class': 'form-select'}),
            'change_category': forms.Select(attrs={'class': 'form-select'}),
            'urgency': forms.Select(attrs={'class': 'form-select'}),
            'change_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'change_benefits': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'target_implementation_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'change_owner': forms.Select(attrs={'class': 'form-select'}),
            'change_coordinator': forms.Select(attrs={'class': 'form-select'}),
            'affected_areas': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'affected_products': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص الخيارات
        self.fields['change_owner'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production']
        ).distinct()
        
        self.fields['change_coordinator'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Project Management']
        ).distinct()
        
        self.fields['affected_products'].queryset = Product.objects.filter(is_active=True)


class ChangeSearchForm(forms.Form):
    """نموذج البحث في التغييرات"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by number, title, or description...')
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Status'))] + ChangeControl.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    change_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + ChangeControl.CHANGE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    change_category = forms.ChoiceField(
        required=False,
        choices=[('', _('All Categories'))] + ChangeControl.CHANGE_CATEGORIES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    urgency = forms.ChoiceField(
        required=False,
        choices=[('', _('All Urgency Levels'))] + ChangeControl.URGENCY_LEVELS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    is_overdue = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class ChangeImpactAssessmentForm(forms.ModelForm):
    """نموذج تقييم تأثير التغيير"""
    
    class Meta:
        model = ChangeImpactAssessment
        fields = [
            'quality_impact', 'quality_impact_description',
            'safety_impact', 'safety_impact_description',
            'regulatory_impact', 'regulatory_impact_description',
            'environmental_impact', 'environmental_impact_description',
            'cost_impact', 'estimated_cost',
            'risk_assessment', 'risk_mitigation',
            'resources_required', 'training_required', 'training_description',
            'documents_to_update'
        ]
        widgets = {
            'quality_impact': forms.Select(attrs={'class': 'form-select'}),
            'quality_impact_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe quality impact')
            }),
            'safety_impact': forms.Select(attrs={'class': 'form-select'}),
            'safety_impact_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe safety impact')
            }),
            'regulatory_impact': forms.Select(attrs={'class': 'form-select'}),
            'regulatory_impact_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe regulatory impact')
            }),
            'environmental_impact': forms.Select(attrs={'class': 'form-select'}),
            'environmental_impact_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe environmental impact')
            }),
            'cost_impact': forms.Select(attrs={'class': 'form-select'}),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Estimated cost in USD')
            }),
            'risk_assessment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Comprehensive risk assessment')
            }),
            'risk_mitigation': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Risk mitigation strategies')
            }),
            'resources_required': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Personnel, equipment, materials needed')
            }),
            'training_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'training_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe training requirements')
            }),
            'documents_to_update': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List documents that need updating')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Crispy Forms Helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(_('Impact Assessment'),
                    Fieldset(_('Quality Impact'),
                        Row(
                            Column('quality_impact', css_class='col-md-4'),
                            Column('quality_impact_description', css_class='col-md-8'),
                        ),
                    ),
                    Fieldset(_('Safety Impact'),
                        Row(
                            Column('safety_impact', css_class='col-md-4'),
                            Column('safety_impact_description', css_class='col-md-8'),
                        ),
                    ),
                    Fieldset(_('Regulatory Impact'),
                        Row(
                            Column('regulatory_impact', css_class='col-md-4'),
                            Column('regulatory_impact_description', css_class='col-md-8'),
                        ),
                    ),
                    Fieldset(_('Environmental Impact'),
                        Row(
                            Column('environmental_impact', css_class='col-md-4'),
                            Column('environmental_impact_description', css_class='col-md-8'),
                        ),
                    ),
                    Fieldset(_('Cost Impact'),
                        Row(
                            Column('cost_impact', css_class='col-md-4'),
                            Column('estimated_cost', css_class='col-md-8'),
                        ),
                    ),
                ),
                Tab(_('Risk & Resources'),
                    'risk_assessment',
                    'risk_mitigation',
                    'resources_required',
                    Row(
                        Column(
                            Field('training_required', wrapper_class='form-check'),
                            css_class='col-md-3'
                        ),
                        Column('training_description', css_class='col-md-9'),
                    ),
                    'documents_to_update',
                ),
            ),
            ButtonHolder(
                Submit('submit', _('Save Impact Assessment'), css_class='btn btn-primary'),
            )
        )


class ChangeImplementationPlanForm(forms.ModelForm):
    """نموذج خطة تنفيذ التغيير"""
    
    class Meta:
        model = ChangeImplementationPlan
        fields = [
            'implementation_approach', 'planned_start_date', 'planned_end_date',
            'rollback_plan', 'success_criteria', 'verification_plan'
        ]
        widgets = {
            'implementation_approach': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Detailed approach for implementing the change')
            }),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'rollback_plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Plan for rolling back if implementation fails')
            }),
            'success_criteria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('How to measure successful implementation')
            }),
            'verification_plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('How to verify the change was implemented correctly')
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('planned_start_date')
        end_date = cleaned_data.get('planned_end_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'planned_end_date': _('End date must be after start date.')
                })
            
            if start_date <= timezone.now().date():
                raise ValidationError({
                    'planned_start_date': _('Start date must be in the future.')
                })
        
        return cleaned_data


class ChangeTaskForm(forms.ModelForm):
    """نموذج مهمة تنفيذ التغيير"""
    
    class Meta:
        model = ChangeTask
        fields = [
            'title', 'description', 'priority', 'assigned_to',
            'due_date', 'depends_on', 'verification_required', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Task title')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Task description')
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'depends_on': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'verification_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Additional notes')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        implementation_plan = kwargs.pop('implementation_plan', None)
        super().__init__(*args, **kwargs)
        
        # تخصيص المستخدمين المعينين
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production', 'Maintenance']
        ).distinct()
        
        # تخصيص التبعيات للمهام في نفس خطة التنفيذ
        if implementation_plan:
            self.fields['depends_on'].queryset = implementation_plan.tasks.all()
        else:
            self.fields['depends_on'].queryset = ChangeTask.objects.none()
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date <= timezone.now().date():
            raise ValidationError(_('Due date must be in the future.'))
        return due_date


class ChangeApprovalActionForm(forms.Form):
    """نموذج إجراء الموافقة"""
    
    ACTION_CHOICES = [
        ('approved', _('Approve')),
        ('rejected', _('Reject')),
        ('more_info', _('Request More Information')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Comments (required for rejection or more info request)')
        }),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        comments = cleaned_data.get('comments')
        
        if action in ['rejected', 'more_info'] and not comments:
            raise ValidationError({
                'comments': _('Comments are required when rejecting or requesting more information.')
            })
        
        return cleaned_data


class ChangeAttachmentForm(forms.ModelForm):
    """نموذج مرفقات التغيير"""
    
    class Meta:
        model = ChangeAttachment
        fields = ['title', 'description', 'file', 'attachment_type']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Attachment title')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Attachment description (optional)')
            }),
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png'
            }),
            'attachment_type': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        
        if file:
            # فحص حجم الملف (أقصى 25 ميجابايت)
            if file.size > 25 * 1024 * 1024:
                raise ValidationError(_('File size cannot exceed 25 MB.'))
            
            # فحص نوع الملف
            allowed_extensions = [
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                'txt', 'jpg', 'jpeg', 'png', 'gif'
            ]
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(
                    _('File type not allowed. Allowed types: %(types)s') % {
                        'types': ', '.join(allowed_extensions)
                    }
                )
        
        return file


class TaskUpdateStatusForm(forms.Form):
    """نموذج تحديث حالة المهمة"""
    
    status = forms.ChoiceField(
        choices=ChangeTask.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    progress_percentage = forms.IntegerField(
        min_value=0,
        max_value=100,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Progress percentage')
        }),
        required=False
    )
    
    notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Update notes (optional)')
        }),
        required=False
    )


class TaskVerificationForm(forms.Form):
    """نموذج التحقق من المهمة"""
    
    verification_status = forms.ChoiceField(
        choices=[
            ('verified', _('Verified - Task Completed Successfully')),
            ('needs_correction', _('Needs Correction')),
            ('rejected', _('Rejected - Task Not Completed Properly')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    verification_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Verification notes and any corrections needed')
        }),
        required=True
    )
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('verification_status')
        notes = cleaned_data.get('verification_notes')
        
        if status in ['needs_correction', 'rejected'] and not notes:
            raise ValidationError({
                'verification_notes': _('Detailed notes are required when requesting corrections or rejecting.')
            })
        
        return cleaned_data