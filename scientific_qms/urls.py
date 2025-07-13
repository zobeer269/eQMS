from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.views.generic import TemplateView
from . import views as main_views  # استيراد views

# URLs بدون ترجمة (للملفات الثابتة والإدارة)
urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),  # لتغيير اللغة
]

# URLs مع دعم الترجمة
urlpatterns += i18n_patterns(
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('dashboard/', main_views.dashboard_view, name='dashboard'),  # تم التعديل هنا
    path('accounts/', include('accounts.urls')),
    path('documents/', include('documents.urls')),
    # سنضيف باقي التطبيقات هنا لاحقاً
    path('training/', include('training.urls')),
    path('deviations/', include('deviations.urls')),
    path('capa/', include('capa.urls')),
    path('change-control/', include('change_control.urls')),
    # path('suppliers/', include('suppliers.urls')),
    # path('equipment/', include('equipment.urls')),
    # path('audits/', include('audits.urls')),
    prefix_default_language=False,  # لا تضع ar/ في الرابط للغة الافتراضية
)

# الملفات الثابتة والوسائط (فقط في التطوير)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# إعدادات الإدارة
admin.site.site_header = "نظام إدارة الجودة الإلكتروني"
admin.site.site_title = "eQMS Admin"
admin.site.index_title = "مرحباً بك في لوحة إدارة eQMS"
