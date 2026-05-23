import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
import json
from django.core.serializers.json import DjangoJSONEncoder
from .models import Workspace,Task,Member,Assign,Review,Feedback,Response,ActivityLog,UserEventCursor,Attachment,Issue,Subtask
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count,Q

class NotificationConsumer(AsyncWebsocketConsumer):
    ...

class TaskConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def get_membership(self,user,workspace_slug):
            return Member.objects.get(
            workspace__slug=workspace_slug,
            member_of=user
        )

    async def connect(self):
        self.user=self.scope.get('user')
        self.workspace_slug=self.scope['url_route']['kwargs']['workspace_slug']
        if not self.user or self.user.is_anonymous:
            await self.close()
            return
        try:
            membership= await self.get_membership(self.user,self.workspace_slug)
            self.role=str(membership.role)
            await self.accept()
            self.group_name=f"workspace_{self.workspace_slug}"
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            undelivered_objects=[]
            if self.role=='ADMIN':
                undelivered_objects=await self.get_admin_offline_task(self.user,self.workspace_slug)
            elif self.role=='REVIEWER':
                undelivered_objects=await self.get_reviewer_offline_task(self.user,self.workspace_slug)
            elif self.role=='WORKER':
                undelivered_objects=await self.get_worker_offline_task(self.user,self.workspace_slug)
            else:
                raise ObjectDoesNotExist('No valid Role Found')
            
            # await self.send(text_data=json.dumps(undelivered_objects))
            await self.send(text_data=json.dumps({
                    'role': self.role.lower(),
                    'tasks': undelivered_objects
                }))

        except ObjectDoesNotExist:
            await self.close()
            return
        
    async def disconnect(self, code):
        if hasattr(self,'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        print(f"Connection closed for user {self.user} with code: {code}")
    
    async def receive(self, text_data = None, bytes_data = None):
        pass

    async def workspace_broadcast(self, event):
        action=event.get('action')
        payload=event.get('payload')
        sender = event.get('sender_channel_name')
        if self.channel_name != sender:
            await self.send(text_data=json.dumps({
                'type': action,
                'payload': payload
            }))
    
    @database_sync_to_async
    def get_admin_offline_task(self,user,workspace_slug):
        # will implement later 
        return []

    @database_sync_to_async
    def get_worker_offline_task(self,user,workspace_slug):
        logs=ActivityLog.objects.filter(
            user=user,
            workspace__slug=workspace_slug,
            task__isnull=False,
        ).select_related('task').prefetch_related('task__task_subtask').order_by('task_id', '-created_at').distinct('task_id')

        column_map = {
            'TODO': 'TO DO',
            'PROGRESS': 'IN PROGRESS',
            'REVIEW': 'Apply Review',
            'ISSUE': 'ISSUE FOUND',
            'DONE': 'DONE'
        }


        task_ids = [log.task_id for log in logs]
        issue_counts = dict(
            Issue.objects.filter(task_id__in=task_ids)
            .values('task_id')
            .annotate(count=Count('id'))
            .values_list('task_id', 'count')
        )

        feedback_counts = dict(
            Feedback.objects.filter(task_id__in=task_ids)
            .values('task_id')
            .annotate(count=Count('id'))
            .values_list('task_id', 'count')
        )

        undelivered_objects = []

        for log in logs:
            task=log.task
            all_subtask=list(task.task_subtask.filter(
               Q(type='PUBLIC') | Q(type='PRIVATE', created_by=user)
            ))

            list_private=[
                {    
                    'id': s.id,
                    'title':s.title,
                    'type': 'private',
                    'checked': str(s.checked),
                }
                for s in all_subtask if s.type=='PRIVATE'
            ]

            list_public=[
                {   
                    'id': s.id,
                    'title':s.title,
                    'type': 'public',
                    'checked': str(s.checked),
                }
                for s in all_subtask if s.type=='PUBLIC'
            ]

            issue_count = issue_counts.get(task.id, 0)
            feedback_count = feedback_counts.get(task.id, 0)

            task_data = {
                'role':'worker',
                'column': column_map.get(task.status, task.status),
                'task_slug':task.slug,
                'priority': str(task.priority),
                'issue_count': issue_count,
                'title': task.title,
                'description': task.description,
                'subtask_private': list_private,
                'subtask_public': list_public,
                'expires_at': str(task.expires_at) if task.expires_at else None,
                'feedback_count': feedback_count
            }
            undelivered_objects.append(task_data)
        
        return undelivered_objects
    

    @database_sync_to_async
    def get_reviewer_offline_task(self,user,workspace_slug):
        logs=ActivityLog.objects.filter(
            user=user,
            workspace__slug=workspace_slug,
            task__isnull=False,
        ).select_related('task').prefetch_related('task__task_subtask').order_by('task_id', '-created_at').distinct('task_id')

        column_map = {
            'REVIEW': 'Apply Review',
            'ISSUE': 'ISSUE FOUND',
            'DONE': 'DONE',
        }

        task_ids = [log.task_id for log in logs]
        issue_counts = dict(
            Issue.objects.filter(task_id__in=task_ids)
            .values('task_id')
            .annotate(count=Count('id'))
            .values_list('task_id', 'count')
        )

        feedback_counts = dict(
            Feedback.objects.filter(task_id__in=task_ids)
            .values('task_id')
            .annotate(count=Count('id'))
            .values_list('task_id', 'count')
        )

        undelivered_objects = []

        for log in logs:
            task=log.task
            all_subtask=list(task.task_subtask.filter(
               Q(type='PUBLIC') | Q(type='PRIVATE', created_by=user)
            ))

            list_private=[
                {    
                    'id': s.id,
                    'title':s.title,
                    'type': 'private',
                    'checked': str(s.checked),
                }
                for s in all_subtask if s.type=='PRIVATE'
            ]

            list_public=[
                {   
                    'id': s.id,
                    'title':s.title,
                    'type': 'public',
                    'checked': str(s.checked),
                }
                for s in all_subtask if s.type=='PUBLIC'
            ]

            issue_count = issue_counts.get(task.id, 0)
            feedback_count = feedback_counts.get(task.id, 0)

            task_data = {
                'role':'reviewer',
                'column': column_map.get(task.status, task.status),
                'task_slug':task.slug,
                'priority': str(task.priority),
                'issue_count': issue_count,
                'title': task.title,
                'description': task.description,
                'subtask_private': list_private,
                'subtask_public': list_public,
                'expires_at': str(task.expires_at) if task.expires_at else None,
                'feedback_count': feedback_count
            }
            undelivered_objects.append(task_data)
        
        return undelivered_objects
    

    


        


    