from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('workspaces/<slug:workspace_slug>/', views.workspace_detail_view, name='workspace_dashboard'),
    path('TaskCard/<slug:task_slug>/<slug:workspace_slug>/<str:action>/',views.TaskCard.as_view(),name='task_card'),
    path('Issue/<slug:issue_slug>/<slug:task_slug>/<str:action>/',views.IssueView.as_view(),name='Issue')
]