# capa/forms.py
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import (
    CAPA, CAPAAction, CAPAEffectivenessCheck, CAPAApproval, 
    CAPAAttachment, CAPAComment
)
from accounts.models import User
from documents.models import Document
from deviations.models import Deviation, Product
from change_control.models import ChangeControl
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Div, Field, HTML, Row, Column
from crispy_forms.bootstrap import TabHolder, Tab, PrependedText
import datetime


class CAPACreateForm(forms.ModelForm):
    """نموذج إنشاء CAPA جديد"""
    
    class Meta:
        model = CAPA
        fields = [
            'title', 'description', 'capa_type', 'source_type', 'source_reference',
            'priority', 'risk_level', 'due_date', 'target_completion_date',
            'assigned_to', 'capa_owner', 'problem_statement', 'root_cause_analysis',
            'root_cause_method', 'affected_departments', 'affected_processes',
            'affected_products', 'requires_regulatory_notification',
            'requires_customer_notification', 'requires_validation', 'requires_training',
            'estimated_cost', 'expected_benefits', 'related_documents',
            'related_deviations', 'related_changes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Brief title for the CAPA')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Detailed description of the CAPA')
            }),
            'capa_type': forms.Select(attrs={'class': 'form-select'}),
            'source_type': forms.Select(attrs={'class': 'form-select'}),
            'source_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('e.g., DEV-2025-001')
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'target_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'capa_owner': forms.Select(attrs={'class': 'form-select'}),
            'problem_statement': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Clear description of the problem')
            }),
            'root_cause_analysis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Detailed analysis of root causes')
            }),
            'root_cause_method': forms.Select(attrs={'class': 'form-select'}),
            'affected_departments': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '5'
            }),
            'affected_processes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List of affected processes')
            }),
            'affected_products': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Estimated cost in USD')
            }),
            'expected_benefits': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Expected benefits and outcomes')
            }),
            'related_documents': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'related_deviations': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'related_changes': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص خيارات المستخدمين
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production', 'Regulatory']
        ).distinct()
        
        self.fields['capa_owner'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Management']
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
        
        # التغييرات النشطة
        self.fields['related_changes'].queryset = ChangeControl.objects.filter(
            status__in=['submitted', 'approved', 'in_progress']
        )
        
        # Crispy Forms Helper
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(_('Basic Information'),
                    Row(
                        Column('title', css_class='col-md-8'),
                        Column('priority', css_class='col-md-4'),
                    ),
                    'description',
                    Row(
                        Column('capa_type', css_class='col-md-4'),
                        Column('source_type', css_class='col-md-4'),
                        Column('source_reference', css_class='col-md-4'),
                    ),
                    Row(
                        Column('risk_level', css_class='col-md-6'),
                        Column('due_date', css_class='col-md-6'),
                    ),
                ),
                Tab(_('Assignment & Ownership'),
                    Row(
                        Column('assigned_to', css_class='col-md-6'),
                        Column('capa_owner', css_class='col-md-6'),
                    ),
                    'target_completion_date',
                    'affected_processes',
                    Row(
                        Column('affected_departments', css_class='col-md-6'),
                        Column('affected_products', css_class='col-md-6'),
                    ),
                ),
                Tab(_('Problem Analysis'),
                    'problem_statement',
                    'root_cause_analysis',
                    'root_cause_method',
                ),
                Tab(_('Requirements & Impact'),
                    Row(
                        Column(
                            Field('requires_regulatory_notification', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                        Column(
                            Field('requires_customer_notification', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                    ),
                    Row(
                        Column(
                            Field('requires_validation', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                        Column(
                            Field('requires_training', wrapper_class='form-check'),
                            css_class='col-md-6'
                        ),
                    ),
                    'estimated_cost',
                    'expected_benefits',
                ),
                Tab(_('Related Items'),
                    'related_documents',
                    'related_deviations',
                    'related_changes',
                ),
            ),
            ButtonHolder(
                Submit('submit', _('Create CAPA'), css_class='btn btn-primary'),
                HTML('<a href="{% url "capa:list" %}" class="btn btn-secondary">{% trans "Cancel" %}</a>')
            )
        )
    
    def clean_due_date(self):
        due_date = self.cleaned_data.get('due_date')
        if due_date and due_date <= timezone.now().date():
            raise ValidationError(_('Due date must be in the future.'))
        return due_date
    
    def clean_target_completion_date(self):
        target_date = self.cleaned_data.get('target_completion_date')
        due_date = self.cleaned_data.get('due_date')
        
        if target_date:
            if target_date <= timezone.now().date():
                raise ValidationError(_('Target completion date must be in the future.'))
            
            if due_date and target_date > due_date:
                raise ValidationError(_('Target completion date cannot be after due date.'))
        
        return target_date


class CAPAEditForm(forms.ModelForm):
    """نموذج تعديل CAPA"""
    
    class Meta:
        model = CAPA
        fields = [
            'title', 'description', 'priority', 'risk_level',
            'due_date', 'target_completion_date', 'assigned_to', 'capa_owner',
            'problem_statement', 'root_cause_analysis', 'root_cause_method',
            'affected_processes', 'affected_products',
            'requires_regulatory_notification', 'requires_customer_notification',
            'requires_validation', 'requires_training',
            'estimated_cost', 'expected_benefits'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'risk_level': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'target_completion_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'capa_owner': forms.Select(attrs={'class': 'form-select'}),
            'problem_statement': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'root_cause_analysis': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'root_cause_method': forms.Select(attrs={'class': 'form-select'}),
            'affected_processes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'affected_products': forms.SelectMultiple(attrs={'class': 'form-control'}),
            'estimated_cost': forms.NumberInput(attrs={'class': 'form-control'}),
            'expected_benefits': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص الخيارات
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production', 'Regulatory']
        ).distinct()
        
        self.fields['capa_owner'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Management']
        ).distinct()
        
        self.fields['affected_products'].queryset = Product.objects.filter(is_active=True)


class CAPASearchForm(forms.Form):
    """نموذج البحث في CAPAs"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by number, title, or description...')
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Status'))] + CAPA.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    capa_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + CAPA.CAPA_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    source_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Sources'))] + CAPA.SOURCE_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        required=False,
        choices=[('', _('All Priorities'))] + CAPA.PRIORITY_LEVELS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    risk_level = forms.ChoiceField(
        required=False,
        choices=[('', _('All Risk Levels'))] + CAPA.RISK_LEVELS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    assigned_to = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('All Assignees')
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


class CAPAActionForm(forms.ModelForm):
    """نموذج إجراء CAPA"""
    
    class Meta:
        model = CAPAAction
        fields = [
            'title', 'description', 'action_type', 'assigned_to',
            'planned_start_date', 'planned_completion_date', 'priority',
            'depends_on', 'verification_required', 'resources_required',
            'estimated_cost', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Action title')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Detailed description of the action')
            }),
            'action_type': forms.Select(attrs={'class': 'form-select'}),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_completion_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'depends_on': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': '4'
            }),
            'verification_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'resources_required': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Resources needed for this action')
            }),
            'estimated_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': _('Estimated cost')
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Additional notes')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        capa = kwargs.pop('capa', None)
        super().__init__(*args, **kwargs)
        
        # تخصيص المستخدمين المعينين
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production', 'Maintenance', 'Regulatory']
        ).distinct()
        
        # تخصيص التبعيات للإجراءات في نفس CAPA
        if capa:
            self.fields['depends_on'].queryset = capa.actions.all()
        else:
            self.fields['depends_on'].queryset = CAPAAction.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('planned_start_date')
        end_date = cleaned_data.get('planned_completion_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'planned_completion_date': _('Completion date must be after start date.')
                })
            
            if start_date <= timezone.now().date():
                raise ValidationError({
                    'planned_start_date': _('Start date should be in the future.')
                })
        
        return cleaned_data


class CAPAEffectivenessCheckForm(forms.ModelForm):
    """نموذج فحص فعالية CAPA"""
    
    class Meta:
        model = CAPAEffectivenessCheck
        fields = [
            'check_date', 'check_period_start', 'check_period_end',
            'evaluation_criteria', 'evaluation_method', 'result',
            'findings', 'evidence', 'recommendations',
            'additional_actions_required', 'reviewed_by'
        ]
        widgets = {
            'check_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'check_period_start': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'check_period_end': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'evaluation_criteria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Criteria used to evaluate effectiveness')
            }),
            'evaluation_method': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Methods used for evaluation')
            }),
            'result': forms.Select(attrs={'class': 'form-select'}),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Detailed findings from the effectiveness check')
            }),
            'evidence': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Evidence supporting the findings')
            }),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Recommendations for improvement')
            }),
            'additional_actions_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'reviewed_by': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص المراجعين
        self.fields['reviewed_by'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Management']
        ).distinct()
        
        # تعيين التاريخ الافتراضي
        if not self.instance.pk:
            self.fields['check_date'].initial = timezone.now().date()
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('check_period_start')
        end_date = cleaned_data.get('check_period_end')
        check_date = cleaned_data.get('check_date')
        
        if start_date and end_date:
            if start_date >= end_date:
                raise ValidationError({
                    'check_period_end': _('End date must be after start date.')
                })
        
        if check_date and start_date and check_date < start_date:
            raise ValidationError({
                'check_date': _('Check date cannot be before the period start date.')
            })
        
        return cleaned_data


class CAPAApprovalActionForm(forms.Form):
    """نموذج إجراء موافقة CAPA"""
    
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
    
    conditions = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('Any conditions for approval (optional)')
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


class CAPAAttachmentForm(forms.ModelForm):
    """نموذج مرفقات CAPA"""
    
    class Meta:
        model = CAPAAttachment
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


class CAPACommentForm(forms.ModelForm):
    """نموذج تعليقات CAPA"""
    
    class Meta:
        model = CAPAComment
        fields = ['comment', 'is_internal']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Add your comment...')
            }),
            'is_internal': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }


class ActionUpdateForm(forms.Form):
    """نموذج تحديث حالة الإجراء"""
    
    status = forms.ChoiceField(
        choices=CAPAAction.STATUS_CHOICES,
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
    
    actual_cost = forms.DecimalField(
        max_digits=8,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Actual cost (if completed)')
        }),
        required=False
    )


class EffectivenessCheckForm(forms.Form):
    """نموذج سريع لفحص الفعالية"""
    
    result = forms.ChoiceField(
        choices=CAPAEffectivenessCheck.RESULT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    findings = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Key findings from effectiveness evaluation')
        })
    )
    
    recommendations = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Recommendations (if any)')
        }),
        required=False
    )
    
    additional_actions = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )


class CAPAAssignForm(forms.Form):
    """نموذج تعيين CAPA"""
    
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('Select assignee')
    )
    
    capa_owner = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        empty_label=_('Select owner'),
        required=False
    )
    
    due_date = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    comments = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Assignment comments')
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # تخصيص المستخدمين حسب الأدوار
        self.fields['assigned_to'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Engineering', 'Production', 'Regulatory']
        ).distinct()
        
        self.fields['capa_owner'].queryset = User.objects.filter(
            is_active=True,
            groups__name__in=['Quality', 'Management']
        ).distinct()


class CAPACloseForm(forms.Form):
    """نموذج إغلاق CAPA"""
    
    closure_reason = forms.ChoiceField(
        choices=[
            ('completed', _('Successfully Completed')),
            ('superseded', _('Superseded by Another CAPA')),
            ('no_longer_applicable', _('No Longer Applicable')),
            ('ineffective', _('Proven Ineffective')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    closure_summary = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Summary of CAPA outcomes and closure rationale')
        })
    )
    
    lessons_learned = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Key lessons learned from this CAPA')
        }),
        required=False
    )
    
    final_cost = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Final total cost')
        }),
        required=False
    )
    
    follow_up_required = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        required=False
    )
    
    follow_up_details = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': _('Follow-up details if required')
        }),
        required=False
    )
    
    def clean(self):
        cleaned_data = super().clean()
        follow_up = cleaned_data.get('follow_up_required')
        follow_up_details = cleaned_data.get('follow_up_details')
        
        if follow_up and not follow_up_details:
            raise ValidationError({
                'follow_up_details': _('Follow-up details are required when follow-up is needed.')
            })
        
        return cleaned_data