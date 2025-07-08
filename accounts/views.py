from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.translation import gettext as _
from django.utils.translation import activate
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from .forms import MultilingualLoginForm, UserRegistrationForm, PasswordChangeForm
from .models import User, AuditLog, SecureSession
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """الحصول على IP العميل الحقيقي"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def create_audit_log(user, action, request, **kwargs):
    """إنشاء سجل تدقيق"""
    # احصل على اسم المستخدم بطريقة آمنة
    if user and hasattr(user, 'username'):
        username = user.username
    elif 'username' in kwargs:
        username = kwargs.pop('username')  # أزل username من kwargs
    else:
        username = 'Anonymous'
    
    audit_log = AuditLog(
        user=user if user and user.is_authenticated else None,
        username=username,
        action=action,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
        **kwargs
    )
    audit_log.save()
    return audit_log


@csrf_protect
@never_cache
def login_view(request):
    """عرض تسجيل الدخول مع دعم اللغات"""
    
    # تعيين اللغة من الطلب
    lang = request.GET.get('lang', request.session.get('django_language', 'ar'))
    activate(lang)
    request.session['django_language'] = lang
    
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = MultilingualLoginForm(request, data=request.POST)
        
        # تغيير اللغة إذا تم اختيارها
        selected_lang = request.POST.get('language', lang)
        if selected_lang != lang:
            activate(selected_lang)
            request.session['django_language'] = selected_lang
            return redirect(f"{request.path}?lang={selected_lang}")
        
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # التحقق من حالة الحساب
                if not user.is_active:
                    messages.error(request, _('Your account has been deactivated.'))
                    create_audit_log(
                        user, 'login_failed', request,
                        reason='Account deactivated'
                    )
                    return render(request, 'accounts/login.html', {'form': form})
                
                # التحقق من عدد محاولات الدخول الفاشلة
                if hasattr(settings, 'MAX_LOGIN_ATTEMPTS') and user.failed_login_attempts >= settings.MAX_LOGIN_ATTEMPTS:
                    if user.last_failed_login:
                        time_since_last_attempt = timezone.now() - user.last_failed_login
                        lockout_duration = getattr(settings, 'LOCKOUT_DURATION', 1800)
                        if time_since_last_attempt.total_seconds() < lockout_duration:
                            remaining_time = lockout_duration - int(time_since_last_attempt.total_seconds())
                            messages.error(
                                request, 
                                _('Account locked. Try again in %(minutes)d minutes.') % {
                                    'minutes': remaining_time // 60
                                }
                            )
                            return render(request, 'accounts/login.html', {'form': form})
                        else:
                            # إعادة تعيين المحاولات الفاشلة
                            user.failed_login_attempts = 0
                            user.save()
                
                # تسجيل الدخول
                login(request, user)
                
                # تعيين اللغة المفضلة للمستخدم
                activate(user.preferred_language)
                request.session['django_language'] = user.preferred_language
                
                # إنشاء جلسة آمنة
                if request.session.session_key:
                    SecureSession.objects.create(
                        user=user,
                        session_key=request.session.session_key,
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
                    )
                
                # إنشاء سجل تدقيق
                create_audit_log(user, 'login', request)
                
                # إعادة تعيين المحاولات الفاشلة
                user.failed_login_attempts = 0
                user.save()
                
                # رسالة ترحيب
                messages.success(
                    request, 
                    _('Welcome back, %(name)s!') % {'name': user.get_full_name() or user.username}
                )
                
                # التحقق من ضرورة تغيير كلمة المرور
                if user.must_change_password:
                    messages.warning(request, _('You must change your password.'))
                    return redirect('accounts:change_password')
                
                # التوجيه للصفحة المطلوبة أو لوحة التحكم
                next_url = request.GET.get('next', 'dashboard')
                return redirect(next_url)
            else:
                messages.error(request, _('Invalid username or password.'))
        else:
            # محاولة دخول فاشلة
            username = request.POST.get('username', '')
            if username:
                try:
                    user = User.objects.get(username=username)
                    user.failed_login_attempts += 1
                    user.last_failed_login = timezone.now()
                    user.save()
                    
                    create_audit_log(
                        user, 'login_failed', request,
                        reason='Invalid password'
                    )
                    
                    max_attempts = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
                    if user.failed_login_attempts >= max_attempts:
                        messages.error(
                            request,
                            _('Too many failed attempts. Account locked for 30 minutes.')
                        )
                    else:
                        remaining = max_attempts - user.failed_login_attempts
                        messages.error(
                            request,
                            _('Invalid credentials. %(remaining)d attempts remaining.') % {
                                'remaining': remaining
                            }
                        )
                except User.DoesNotExist:
                    messages.error(request, _('Invalid username or password.'))
                    # أنشئ log مباشرة بدون استخدام الدالة المساعدة
                    AuditLog.objects.create(
                        user=None,
                        username=username,
                        action='login_failed',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                        reason='User not found'
                    )
            else:
                messages.error(request, _('Please enter username and password.'))
    else:
        form = MultilingualLoginForm(request)
        form.fields['language'].initial = lang
    
    return render(request, 'accounts/login.html', {
        'form': form,
        'current_language': lang,
        'languages': settings.LANGUAGES,
    })


@login_required
@never_cache
def logout_view(request):
    """تسجيل الخروج"""
    if request.user.is_authenticated:
        # إنهاء الجلسة الآمنة
        try:
            if request.session.session_key:
                session = SecureSession.objects.get(
                    user=request.user,
                    session_key=request.session.session_key,
                    is_active=True
                )
                session.is_active = False
                session.save()
        except SecureSession.DoesNotExist:
            pass
        
        # سجل التدقيق
        create_audit_log(request.user, 'logout', request)
        
        # تسجيل الخروج
        logout(request)
        messages.success(request, _('You have been logged out successfully.'))
    
    return redirect('accounts:login')


@login_required
def change_password_view(request):
    """تغيير كلمة المرور"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.POST)
        if form.is_valid():
            user = request.user
            old_password = form.cleaned_data['old_password']
            new_password = form.cleaned_data['new_password1']
            electronic_signature = form.cleaned_data['electronic_signature']
            
            # التحقق من كلمة المرور الحالية
            if not user.check_password(old_password):
                messages.error(request, _('Current password is incorrect.'))
                return render(request, 'accounts/change_password.html', {'form': form})
            
            # التحقق من التوقيع الإلكتروني
            if not user.check_password(electronic_signature):
                messages.error(request, _('Electronic signature is invalid.'))
                return render(request, 'accounts/change_password.html', {'form': form})
            
            # التحقق من أن كلمة المرور الجديدة مختلفة
            if old_password == new_password:
                messages.error(request, _('New password must be different from current password.'))
                return render(request, 'accounts/change_password.html', {'form': form})
            
            # تغيير كلمة المرور
            user.set_password(new_password)
            user.password_changed_at = timezone.now()
            user.must_change_password = False
            user.save()
            
            # سجل التدقيق مع التوقيع الإلكتروني
            create_audit_log(
                user, 'password_change', request,
                reason=form.cleaned_data['reason'],
                electronic_signature=user.electronic_signature,
                signature_meaning=_('I confirm this password change')
            )
            
            # إعادة تسجيل الدخول
            login(request, user)
            
            messages.success(request, _('Password changed successfully.'))
            return redirect('dashboard')
    else:
        form = PasswordChangeForm()
    
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def profile_view(request):
    """عرض وتعديل الملف الشخصي"""
    user = request.user
    
    if request.method == 'POST':
        # تحديث المعلومات الشخصية
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone = request.POST.get('phone', user.phone)
        user.preferred_language = request.POST.get('preferred_language', user.preferred_language)
        
        # حفظ التوقيع إذا تم رفعه
        if 'signature_image' in request.FILES:
            user.signature_image = request.FILES['signature_image']
        
        user.save()
        
        # تغيير اللغة
        activate(user.preferred_language)
        request.session['django_language'] = user.preferred_language
        
        # سجل التدقيق
        create_audit_log(
            user, 'update', request,
            model_name='User',
            object_id=user.id,
            object_repr=str(user)
        )
        
        messages.success(request, _('Profile updated successfully.'))
        return redirect('accounts:profile')
    
    # سجلات التدقيق الأخيرة للمستخدم
    recent_activities = AuditLog.objects.filter(user=user).order_by('-timestamp')[:10]
    
    # الجلسات النشطة
    active_sessions = SecureSession.objects.filter(user=user, is_active=True)
    
    return render(request, 'accounts/profile.html', {
        'user': user,
        'recent_activities': recent_activities,
        'active_sessions': active_sessions,
    })