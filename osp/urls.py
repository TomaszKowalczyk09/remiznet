from django.urls import path
from . import views
from django.contrib.auth import logout as django_logout
from django.contrib.auth import views as auth_views

app_name = 'osp'

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('panel/', views.panel, name='panel'),
    path('units/<int:unit_pk>/firefighters/add/', views.firefighter_create, name='firefighter_add'),
    path('units/<int:unit_pk>/requests/new/', views.request_create, name='request_create'),
    path('requests/', views.request_list, name='request_list'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/respond/', views.request_respond, name='request_respond'),
]
