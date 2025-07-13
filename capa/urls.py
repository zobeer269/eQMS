from django.urls import path
from . import views

app_name = 'capa'

urlpatterns = [
    # القوائم والصفحة الرئيسية
    path('', views.capa_list, name='list'),
    path('dashboard/', views.capa_dashboard, name='dashboard'),
    path('my/', views.my_capas, name='my_capas'),
    
    # إنشاء وعرض
    path('create/', views.capa_create, name='create'),
    path('create/<str:source_type>/<str:source_ref>/', views.capa_create_from_source, name='create_from_source'),
    path('<int:pk>/', views.capa_detail, name='detail'),
    path('<int:pk>/print/', views.capa_print, name='print'),
    
    # التحديث والإجراءات
    path('<int:pk>/edit/', views.capa_edit, name='edit'),
    path('<int:pk>/assign/', views.capa_assign, name='assign'),
    path('<int:pk>/close/', views.capa_close, name='close'),
    
    # خطة العمل
    path('<int:pk>/actions/', views.action_list, name='action_list'),
    path('<int:pk>/action/create/', views.action_create, name='action_create'),
    path('action/<int:action_id>/edit/', views.action_edit, name='action_edit'),
    path('action/<int:action_id>/complete/', views.action_complete, name='action_complete'),
    path('action/<int:action_id>/verify/', views.action_verify, name='action_verify'),
    
    # فحص الفعالية
    path('<int:pk>/effectiveness/', views.effectiveness_list, name='effectiveness_list'),
    path('<int:pk>/effectiveness/create/', views.effectiveness_create, name='effectiveness_create'),
    path('effectiveness/<int:check_id>/perform/', views.effectiveness_perform, name='effectiveness_perform'),
    
    # الموافقات
    path('<int:pk>/approve/', views.capa_approve, name='approve'),
    path('approval/<int:approval_id>/action/', views.approval_action, name='approval_action'),
    
    # المرفقات
    path('<int:pk>/attachments/', views.attachment_list, name='attachment_list'),
    path('<int:pk>/attachment/upload/', views.attachment_upload, name='attachment_upload'),
    path('attachment/<int:attachment_id>/download/', views.attachment_download, name='attachment_download'),
    path('attachment/<int:attachment_id>/delete/', views.attachment_delete, name='attachment_delete'),
    
    # التقارير والإحصائيات
    path('reports/', views.capa_reports, name='reports'),
    path('statistics/', views.capa_statistics, name='statistics'),
    path('effectiveness-report/', views.effectiveness_report, name='effectiveness_report'),
    path('overdue-report/', views.overdue_report, name='overdue_report'),
    
    # API endpoints
    path('api/capa-chart-data/', views.capa_chart_data, name='api_chart_data'),
    path('api/effectiveness-data/', views.effectiveness_chart_data, name='api_effectiveness_data'),
    path('api/action-timeline/<int:pk>/', views.action_timeline_data, name='api_action_timeline'),
]