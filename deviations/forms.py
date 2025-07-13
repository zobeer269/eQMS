from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import (
    Deviation, DeviationInvestigation, DeviationApproval, 
    DeviationAttachment, Product
)
from accounts.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, ButtonHolder, Submit, Div, Field, HTML
from crispy_forms.bootstrap import TabHolder, Tab
import datetime

class DeviationCreateForm(forms.ModelForm):
    """نموذج إنشاء انحراف جديد"""
    
    class Meta:
        model = Deviation
        fields = [
            'title', 'description', 'deviation_type', 'severity',
            'occurrence_date', 'detection_date', 'location', 'department',
            'affected_products', 'affected_batches', 'immediate_actions',
            'containment_actions'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Brief description of the deviation')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Detailed description of what happened')
            }),
            'deviation_type': forms.Select(attrs={'class': 'form-select'}),
            'severity': forms.Select(attrs={'class': 'form-select'}),
            'occurrence_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'detection_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Building/Room/Area')
            }),
            'department': forms.Select(attrs={'class': 'form-select'}),
            'affected_products': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'size': 5
            }),
            'affected_batches': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Enter batch numbers separated by commas')
            }),
            'immediate_actions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('What immediate actions were taken?')
            }),
            'containment_actions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Actions to prevent spread/recurrence')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set default dates
        now = datetime.datetime.now()
        self.fields['occurrence_date'].initial = now
        self.fields['detection_date'].initial = now
        
        # Set required fields
        self.fields['immediate_actions'].required = True
        
        # Configure helper
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.layout = Layout(
            Fieldset(
                _('Basic Information'),
                Div(
                    Field('title', css_class='mb-3'),
                    Field('description', css_class='mb-3'),
                    css_class='row'
                ),
                Div(
                    Div('deviation_type', css_class='col-md-6'),
                    Div('severity', css_class='col-md-6'),
                    css_class='row mb-3'
                ),
            ),
            Fieldset(
                _('When and Where'),
                Div(
                    Div('occurrence_date', css_class='col-md-6'),
                    Div('detection_date', css_class='col-md-6'),
                    css_class='row mb-3'
                ),
                Div(
                    Div('location', css_class='col-md-6'),
                    Div('department', css_class='col-md-6'),
                    css_class='row mb-3'
                ),
            ),
            Fieldset(
                _('Affected Items'),
                'affected_products',
                'affected_batches',
            ),
            Fieldset(
                _('Immediate Response'),
                'immediate_actions',
                'containment_actions',
            ),
            ButtonHolder(
                Submit('submit', _('Report Deviation'), css_class='btn btn-primary'),
                HTML('<a href="{% url "deviations:list" %}" class="btn btn-secondary ms-2">{% trans "Cancel" %}</a>')
            )
        )
    
    def clean(self):
        cleaned_data = super().clean()
        occurrence_date = cleaned_data.get('occurrence_date')
        detection_date = cleaned_data.get('detection_date')
        
        if occurrence_date and detection_date:
            if detection_date < occurrence_date:
                raise ValidationError({
                    'detection_date': _('Detection date cannot be before occurrence date')
                })
            
            # Check if reporting is too late
            days_diff = (datetime.datetime.now() - detection_date.replace(tzinfo=None)).days
            if days_diff > 30:
                self.add_error(None, _('Warning: This deviation is being reported more than 30 days after detection'))
        
        return cleaned_data


class DeviationInvestigationForm(forms.ModelForm):
    """نموذج التحقيق في الانحراف"""
    
    investigation_team = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label=_('Investigation Team Members')
    )
    
    class Meta:
        model = DeviationInvestigation
        fields = [
            'investigation_lead', 'investigation_team', 'investigation_methods',
            'findings', 'root_cause_category', 'recommendations'
        ]
        widgets = {
            'investigation_lead': forms.Select(attrs={'class': 'form-select'}),
            'investigation_methods': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('e.g., Fishbone diagram, 5 Whys, Interviews, Document review')
            }),
            'findings': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Detailed findings from the investigation')
            }),
            'root_cause_category': forms.Select(attrs={'class': 'form-select'}),
            'recommendations': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Recommended actions to prevent recurrence')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        self.deviation = kwargs.pop('deviation', None)
        super().__init__(*args, **kwargs)
        
        # Limit investigation lead to qualified users
        self.fields['investigation_lead'].queryset = User.objects.filter(
            is_active=True,
            is_quality_manager=True
        )


class DeviationUpdateForm(forms.ModelForm):
    """نموذج تحديث الانحراف"""
    
    class Meta:
        model = Deviation
        fields = [
            'assigned_to', 'qa_reviewer', 'impact_assessment', 
            'risk_assessment', 'root_cause', 'investigation_summary',
            'requires_capa', 'requires_change_control', 'is_recurring',
            'previous_occurrences'
        ]
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-select'}),
            'qa_reviewer': forms.Select(attrs={'class': 'form-select'}),
            'impact_assessment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Assess the impact on product quality, safety, etc.')
            }),
            'risk_assessment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Evaluate risks and potential consequences')
            }),
            'root_cause': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': _('Root cause analysis results')
            }),
            'investigation_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': _('Summary of investigation findings')
            }),
            'requires_capa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_change_control': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_recurring': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'previous_occurrences': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('List previous similar occurrences with dates')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Limit assignees to active users
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        self.fields['qa_reviewer'].queryset = User.objects.filter(
            is_active=True,
            is_quality_manager=True
        )


class DeviationApprovalForm(forms.Form):
    """نموذج الموافقة على الانحراف"""
    
    action = forms.ChoiceField(
        label=_('Action'),
        choices=[
            ('approve', _('Approve')),
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
    
    electronic_signature = forms.CharField(
        label=_('Electronic Signature'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password to sign')
        }),
        help_text=_('Enter your password as electronic signature')
    )


class DeviationCloseForm(forms.Form):
    """نموذج إغلاق الانحراف"""
    
    closure_summary = forms.CharField(
        label=_('Closure Summary'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': _('Summarize the deviation, investigation, and actions taken')
        }),
        required=True
    )
    
    effectiveness_verified = forms.BooleanField(
        label=_('Effectiveness of Actions Verified'),
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    lessons_learned = forms.CharField(
        label=_('Lessons Learned'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Key takeaways from this deviation')
        }),
        required=False
    )
    
    electronic_signature = forms.CharField(
        label=_('Electronic Signature'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password to sign')
        }),
        help_text=_('Enter your password to authorize closure')
    )


class DeviationAttachmentForm(forms.ModelForm):
    """نموذج رفع المرفقات"""
    
    class Meta:
        model = DeviationAttachment
        fields = ['title', 'file', 'file_type', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Attachment title')
            }),
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'file_type': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': _('Brief description (optional)')
            }),
        }
    
    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            # Check file size (max 10MB)
            if file.size > 10 * 1024 * 1024:
                raise ValidationError(_('File size cannot exceed 10 MB'))
            
            # Check file type
            allowed_extensions = ['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
            ext = file.name.split('.')[-1].lower()
            if ext not in allowed_extensions:
                raise ValidationError(
                    _('File type not allowed. Allowed types: %(types)s') % {
                        'types': ', '.join(allowed_extensions)
                    }
                )
        return file


class DeviationSearchForm(forms.Form):
    """نموذج البحث في الانحرافات"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Search by number, title, or description...')
        })
    )
    
    deviation_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + Deviation.DEVIATION_TYPES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    severity = forms.ChoiceField(
        required=False,
        choices=[('', _('All Severities'))] + Deviation.SEVERITY_LEVELS,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Status'))] + Deviation.STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    department = forms.ChoiceField(
        required=False,
        choices=[('', _('All Departments'))] + [
            ('production', _('Production')),
            ('quality', _('Quality')),
            ('warehouse', _('Warehouse')),
            ('laboratory', _('Laboratory')),
            ('engineering', _('Engineering')),
            ('other', _('Other')),
        ],
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
    
    requires_capa = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )