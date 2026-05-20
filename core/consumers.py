import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import json
from django.core.serializers.json import DjangoJSONEncoder

class NotificationConsumer(AsyncWebsocketConsumer):
    ...