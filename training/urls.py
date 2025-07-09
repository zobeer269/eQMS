from django.urls import path
from . import views

app_name = 'training'

urlpatterns = [
    # القوائم الرئيسية
    path('', views.training_dashboard, name='dashboard'),
    path('programs/', views.program_list, name='program_list'),
    path('sessions/', views.session_list, name='session_list'),
    path('my-training/', views.my_training, name='my_training'),
    
    # البرامج التدريبية
    path('programs/create/', views.program_create, name='program_create'),
    path('programs/<int:pk>/', views.program_detail, name='program_detail'),
    path('programs/<int:pk>/edit/', views.program_edit, name='program_edit'),
    path('programs/<int:pk>/materials/', views.program_materials, name='program_materials'),
    path('programs/<int:pk>/materials/add/', views.material_add, name='material_add'),
    
    # الجلسات التدريبية
    path('sessions/create/', views.session_create, name='session_create'),
    path('sessions/<int:pk>/', views.session_detail, name='session_detail'),
    path('sessions/<int:pk>/edit/', views.session_edit, name='session_edit'),
    path('sessions/<int:pk>/enroll/', views.session_enroll, name='session_enroll'),
    path('sessions/<int:pk>/attendance/', views.session_attendance, name='session_attendance'),
    path('sessions/<int:pk>/complete/', views.session_complete, name='session_complete'),
    
    # سجلات التدريب
    path('records/<int:pk>/', views.record_detail, name='record_detail'),
    path('records/<int:pk>/test/', views.record_test, name='record_test'),
    path('records/<int:pk>/evaluate/', views.record_evaluate, name='record_evaluate'),
    path('records/<int:pk>/certificate/', views.record_certificate, name='record_certificate'),
    
    # التقارير
    path('reports/', views.training_reports, name='reports'),
    path('reports/compliance/', views.compliance_report, name='compliance_report'),
    path('reports/effectiveness/', views.effectiveness_report, name='effectiveness_report'),
    path('reports/attendance/', views.attendance_report, name='attendance_report'),
    
    # واجهة برمجة التطبيقات (API)
    path('api/sessions/calendar/', views.sessions_calendar_api, name='sessions_calendar_api'),
    path('api/training/stats/', views.training_stats_api, name='training_stats_api'),
]
