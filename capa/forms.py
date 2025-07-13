from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
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
            'requires_regulatory_approval'
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
                'class': 'form-select',
                'size': 5
            }),
            'affected_areas': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List all areas/systems affected')
            }),
            'affected_products': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
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
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default target date
        self.fields['target_implementation_date'].initial = (
            datetime.date.today() + datetime.timedelta(days=60)
        )
        
        # Limit change owner to qualified users
        self.fields['change_owner'].queryset = User.objects.filter(
            is_active=True
        ).filter(
            models.Q(is_quality_manager=True) | 
            models.Q(department__in=['quality', 'engineering', 'production'])
        )
        
        # Set default for risk assessment
        self.fields['requires_risk_assessment'].initial = True
        
        # Configure helper for crispy forms
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    _('Basic Information'),
                    Fieldset(
                        '',
                        'title',
                        'description',
                        Row(
                            Column('change_type', css_class='col-md-4'),
                            Column('change_category', css_class='col-md-4'),
                            Column('urgency', css_class='col-md-4'),
                        ),
                        'change_reason',
                        'change_benefits',
                    )
                ),
                Tab(
                    _('Planning'),
                    Fieldset(
                        '',
                        Row(
                            Column('target_implementation_date', css_class='col-md-6'),
                            Column('change_owner', css_class='col-md-6'),
                        ),
                        'affected_departments',
                        'affected_areas',
                        'affected_products',
                    )
                ),
                Tab(
                    _('Requirements'),
                    Fieldset(
                        '',
                        'requires_risk_assessment',
                        'requires_validation',
                        'requires_regulatory_approval',
                    )
                ),
            ),
            ButtonHolder(
                Submit('submit', _('Create Change Request'), css_class='btn btn-primary'),
                Submit('submit_draft', _('Save as Draft'), css_class='btn btn-secondary'),
                HTML('<a href="{% url "change_control:list" %}" class="btn btn-outline-secondary ms-2">{% trans "Cancel" %}</a>')
            )
        )
    
    def clean_target_implementation_date(self):
        date = self.cleaned_data.get('target_implementation_date')
        if date and date < datetime.date.today():
            raise ValidationError(_('Target implementation date cannot be in the past'))
        return date


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
                'placeholder': _('List all documents requiring updates')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False


class ChangeImplementationPlanForm(forms.ModelForm):
    """نموذج خطة تنفيذ التغيير"""
    
    class Meta:
        model = ChangeImplementationPlan
        fields = [
            'implementation_steps', 'planned_start_date', 'planned_end_date',
            'acceptance_criteria', 'rollback_plan', 'communication_plan',
            'verification_method', 'validation_required', 'validation_protocol'
        ]
        widgets = {
            'implementation_steps': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Step-by-step implementation plan')
            }),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'acceptance_criteria': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Criteria for successful implementation')
            }),
            'rollback_plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Plan to revert changes if needed')
            }),
            'communication_plan': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('How will the change be communicated?')
            }),
            'verification_method': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('How will implementation be verified?')
            }),
            'validation_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'validation_protocol': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Validation protocol details')
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('planned_start_date')
        end_date = cleaned_data.get('planned_end_date')
        
        if start_date and end_date:
            if end_date < start_date:
                raise ValidationError({
                    'planned_end_date': _('End date cannot be before start date')
                })
        
        return cleaned_data


class ChangeTaskForm(forms.ModelForm):
    """نموذج مهمة التغيير"""
    
    class Meta:
        model = ChangeTask
        fields = [
            'task_description', 'assigned_to', 'planned_start_date',
            'planned_end_date', 'depends_on', 'verification_required'
        ]
        widgets = {
            'task_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Describe the task')
            }),
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'planned_start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'planned_end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'depends_on': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 3
            }),
            'verification_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.change_control = kwargs.pop('change_control', None)
        super().__init__(*args, **kwargs)
        
        # Limit assigned users to active ones
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        
        # Limit dependencies to tasks from same change control
        if self.change_control:
            self.fields['depends_on'].queryset = ChangeTask.objects.filter(
                change_control=self.change_control
            )
            if self.instance.pk:
                # Exclude self from dependencies
                self.fields['depends_on'].queryset = self.fields['depends_on'].queryset.exclude(
                    pk=self.instance.pk
                )


class ChangeApprovalForm(forms.Form):
    """نموذج الموافقة على التغيير"""
    
    action = forms.ChoiceField(
        label=_('Action'),
        choices=[
            ('approve', _('Approve')),
            ('approve_with_conditions', _('Approve with Conditions')),
            ('reject', _('Reject')),
            ('request_info', _('Request More Information')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    
    comments = forms.CharField(
        label=_('Comments'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': _('Provide your review comments')
        }),
        required=True
    )
    
    conditions = forms.CharField(
        label=_('Conditions (if applicable)'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Specify conditions for approval')
        }),
        required=False
    )
    
    electronic_signature = forms.CharField(
        label=_('Electronic Signature'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password to sign')
        }),
        help_text=_('Enter your password as electronic signature')
    )


class ChangeSearchForm(forms.Form):
    """نموذج البحث في طلبات التغيير"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by number, title, or description...')
        })
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
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Status'))] + ChangeControl.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    urgency = forms.ChoiceField(
        required=False,
        choices=[('', _('All Urgencies'))] + ChangeControl.URGENCY_LEVELS,
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
    
    owner = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True),
        empty_label=_('All Owners'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    requires_validation = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    is_overdue = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )