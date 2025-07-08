from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User, AuditLog
from django.core.exceptions import ValidationError
import re

class MultilingualLoginForm(AuthenticationForm):
    """نموذج تسجيل الدخول مع دعم اللغات"""
    
    username = forms.CharField(
        label=_('Username'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your username'),
            'autofocus': True,
            'dir': 'auto'  # اتجاه تلقائي حسب اللغة
        })
    )
    
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your password'),
            'dir': 'auto'
        })
    )
    
    language = forms.ChoiceField(
        label=_('Language'),
        choices=[('ar', 'العربية'), ('en', 'English')],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'language-selector'
        }),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # تحديد اللغة الافتراضية من الجلسة
        if 'initial' not in kwargs:
            self.fields['language'].initial = 'ar'


class UserRegistrationForm(UserCreationForm):
    """نموذج تسجيل مستخدم جديد"""
    
    employee_id = forms.CharField(
        label=_('Employee ID'),
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('e.g., EMP001')
        })
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'dir': 'auto'
        })
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'dir': 'auto'
        })
    )
    
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('email@example.com')
        })
    )
    
    department = forms.ChoiceField(
        label=_('Department'),
        choices=User._meta.get_field('department').choices,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    position = forms.CharField(
        label=_('Position'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'dir': 'auto'
        })
    )
    
    phone = forms.CharField(
        label=_('Phone Number'),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _('+964 XXX XXX XXXX')
        })
    )
    
    preferred_language = forms.ChoiceField(
        label=_('Preferred Language'),
        choices=[('ar', 'العربية'), ('en', 'English')],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'employee_id', 'first_name', 'last_name',
            'email', 'department', 'position', 'phone',
            'preferred_language', 'password1', 'password2'
        ]
    
    def clean_password1(self):
        """التحقق من قوة كلمة المرور"""
        password = self.cleaned_data.get('password1')
        
        # التحقق من الطول
        if len(password) < 8:
            raise ValidationError(_('Password must be at least 8 characters long'))
        
        # التحقق من وجود أحرف كبيرة وصغيرة
        if not re.search(r'[A-Z]', password):
            raise ValidationError(_('Password must contain at least one uppercase letter'))
        
        if not re.search(r'[a-z]', password):
            raise ValidationError(_('Password must contain at least one lowercase letter'))
        
        # التحقق من وجود أرقام
        if not re.search(r'\d', password):
            raise ValidationError(_('Password must contain at least one number'))
        
        # التحقق من وجود رموز خاصة
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(_('Password must contain at least one special character'))
        
        return password


class PasswordChangeForm(forms.Form):
    """نموذج تغيير كلمة المرور مع سبب التغيير"""
    
    old_password = forms.CharField(
        label=_('Current Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    new_password1 = forms.CharField(
        label=_('New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    new_password2 = forms.CharField(
        label=_('Confirm New Password'),
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    reason = forms.CharField(
        label=_('Reason for Change'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': _('Please provide a reason for changing your password')
        }),
        help_text=_('Required for audit purposes')
    )
    
    electronic_signature = forms.CharField(
        label=_('Electronic Signature'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Re-enter your current password as signature')
        }),
        help_text=_('This serves as your electronic signature for this action')
    )