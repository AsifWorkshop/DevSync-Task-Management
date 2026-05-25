from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/task/(?P<workspace_slug>[\w-]+)/$', consumers.TaskConsumer.as_asgi()),
    re_path(r'ws/issue/(?P<task_slug>[\w-]+)/$', consumers.IssueConsumer.as_asgi()),
]