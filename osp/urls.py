
from django.urls import path
from . import views
from django.contrib.auth import logout as django_logout
from django.contrib.auth import views as auth_views

app_name = 'osp'

urlpatterns = [
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
]
