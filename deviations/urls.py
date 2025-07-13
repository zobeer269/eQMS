from django.urls import path
from . import views

app_name = 'deviations'

urlpatterns = [
    # القوائم والصفحة الرئيسية
    path('', views.deviation_list, name='list'),
    path('dashboard/', views.deviation_dashboard, name='dashboard'),
    path('my/', views.my_deviations, name='my_deviations'),
    
    # إنشاء وعرض
    path('create/', views.deviation_create, name='create'),
    path('<int:pk>/', views.deviation_detail, name='detail'),
    path('<int:pk>/print/', views.deviation_print, name='print'),
    
    # التحديث والإجراءات
    path('<int:pk>/edit/', views.deviation_edit, name='edit'),
    path('<int:pk>/assign/', views.deviation_assign, name='assign'),
    path('<int:pk>/investigate/', views.deviation_investigate, name='investigate'),
    path('<int:pk>/close/', views.deviation_close, name='close'),
    
    # التحقيق
    path('<int:pk>/investigation/create/', views.investigation_create, name='investigation_create'),
    path('<int:pk>/investigation/edit/', views.investigation_edit, name='investigation_edit'),
    path('<int:pk>/investigation/complete/', views.investigation_complete, name='investigation_complete'),
    
    # الموافقات
    path('<int:pk>/approve/', views.deviation_approve, name='approve'),
    path('approval/<int:approval_id>/action/', views.approval_action, name='approval_action'),
    
    # المرفقات
    path('<int:pk>/attachments/', views.attachment_list, name='attachment_list'),
    path('<int:pk>/attachment/upload/', views.attachment_upload, name='attachment_upload'),
    path('attachment/<int:attachment_id>/download/', views.attachment_download, name='attachment_download'),
    path('attachment/<int:attachment_id>/delete/', views.attachment_delete, name='attachment_delete'),
    
    # CAPA والتغيير
    path('<int:pk>/create-capa/', views.create_capa, name='create_capa'),
    path('<int:pk>/create-change/', views.create_change_control, name='create_change_control'),
    
    # التقارير والإحصائيات
    path('reports/', views.deviation_reports, name='reports'),
    path('statistics/', views.deviation_statistics, name='statistics'),
    path('trend-analysis/', views.trend_analysis, name='trend_analysis'),
    
    # API endpoints
    path('api/search-products/', views.search_products, name='api_search_products'),
    path('api/deviation-chart-data/', views.deviation_chart_data, name='api_chart_data'),
]