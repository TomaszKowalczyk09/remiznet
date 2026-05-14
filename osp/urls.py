
from django.urls import path
from . import views
from django.contrib.auth import logout as django_logout
from django.contrib.auth import views as auth_views

app_name = 'osp'

urlpatterns = [
    path('operations/reports/monthly/', views.rescue_monthly_report, name='rescue_monthly_report'),
    path('operations/reports/monthly/csv/', views.rescue_monthly_report_csv, name='rescue_monthly_report_csv'),
    path('operations/reports/monthly/pdf/', views.rescue_monthly_report_pdf, name='rescue_monthly_report_pdf'),
    path('operations/<int:pk>/report/csv/', views.rescue_operation_report_csv, name='rescue_operation_report_csv'),
    path('operations/<int:pk>/report/pdf/', views.rescue_operation_report_pdf, name='rescue_operation_report_pdf'),
    path('operations/<int:pk>/message/', views.rescue_operation_add_message, name='rescue_operation_add_message'),
    path('operations/<int:pk>/status/', views.rescue_operation_update_status, name='rescue_operation_update_status'),
    path('operations/<int:pk>/finalize/', views.rescue_operation_finalize, name='rescue_operation_finalize'),
    path('operations/<int:pk>/archive/', views.rescue_operation_archive, name='rescue_operation_archive'),
    path('operations/<int:pk>/', views.rescue_operation_detail, name='rescue_operation_detail'),
    path('operations/', views.rescue_operation_list, name='rescue_operation_list'),
    path('units/<int:unit_pk>/operations/new/', views.rescue_operation_create, name='rescue_operation_create'),
    path('requests/<int:pk>/sign/', views.request_sign, name='request_sign'),
    path('requests/<int:pk>/archive/', views.request_archive, name='request_archive'),
    path('requests/<int:pk>/pdf/', views.request_pdf, name='request_pdf'),
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('panel/', views.panel, name='panel'),
    path('units/<int:unit_pk>/firefighters/add/', views.firefighter_create, name='firefighter_add'),
    path('firefighters/', views.firefighter_list, name='firefighter_list'),
    path('units/<int:unit_pk>/firefighters/', views.firefighter_list, name='firefighter_list_unit'),
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('units/<int:unit_pk>/equipment/', views.equipment_list, name='equipment_list_unit'),
    path('units/<int:unit_pk>/equipment/add/', views.equipment_create, name='equipment_add'),
    path('personnel/', views.personnel_list, name='personnel_list'),
    path('units/<int:unit_pk>/personnel/', views.personnel_list, name='personnel_list_unit'),
    path('units/<int:unit_pk>/personnel/add/', views.personnel_create, name='personnel_add'),
    path('units/<int:unit_pk>/requests/new/', views.request_create, name='request_create'),
    path('requests/', views.request_list, name='request_list'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/respond/', views.request_respond, name='request_respond'),
    path('firefighters/<int:pk>/edit/', views.firefighter_edit, name='firefighter_edit'),
    
    # ==================== OSP REPORTING URLS ====================
    path('reports/', views.osp_report_list, name='osp_report_list'),
    path('units/<int:unit_pk>/reports/', views.osp_report_list, name='osp_report_list_unit'),
    path('units/<int:unit_pk>/reports/new/', views.osp_report_create, name='osp_report_create'),
    path('reports/<int:pk>/', views.osp_report_detail, name='osp_report_detail'),
    path('reports/<int:pk>/edit/', views.osp_report_edit, name='osp_report_edit'),
    path('reports/<int:pk>/submit/', views.osp_report_submit, name='osp_report_submit'),
    path('reports/<int:pk>/export/pdf/', views.osp_report_export_pdf, name='osp_report_export_pdf'),
    path('reports/<int:report_pk>/fuel/add/', views.fuel_usage_add, name='fuel_usage_add'),
    path('units/<int:unit_pk>/vehicles/insurance/add/', views.vehicle_insurance_add, name='vehicle_insurance_add'),
    path('units/<int:unit_pk>/vehicles/insurance/', views.vehicle_insurance_list, name='vehicle_insurance_list'),
    path('firefighters/<int:firefighter_pk>/test/add/', views.firefighter_test_add, name='firefighter_test_add'),
    path('units/<int:unit_pk>/maintenance/', views.equipment_maintenance_list, name='equipment_maintenance_list'),
    path('firefighters/<int:firefighter_pk>/training/', views.training_record_list, name='training_record_list'),
]
