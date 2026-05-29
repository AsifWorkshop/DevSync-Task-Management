from django.shortcuts import render
from . import utils
from django.http import HttpResponse,JsonResponse,Http404
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Workspace,Task,Member,Assign,Review,Feedback,ActivityLog,UserEventCursor,Attachment,Issue,Subtask
from django.views import View
import json
from django.views.decorators.http import require_POST
from django.utils import timezone
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q

def welcome(request):
    return render(request,'dashboard.html')

@login_required
def dashboard_view(request):
    corporate_workspaces = Member.objects.select_related('workspace').filter(
        member_of=request.user, workspace__type='CORPORATE'
    )
    personal_workspaces = Member.objects.select_related('workspace').filter(
        member_of=request.user, workspace__type='PERSONAL'
    )

    context = {
        'user':request.user.username,
        'corporate_workspaces': corporate_workspaces,
        'personal_workspaces': personal_workspaces,
        'active_workspace': None 
    }
    return render(request, 'dashboard.html', context)

@login_required
def workspace_detail_view(request, workspace_slug):
    corporate_workspaces = Member.objects.select_related('workspace').filter(
        member_of=request.user, workspace__type='CORPORATE'
    )
    personal_workspaces = Member.objects.select_related('workspace').filter(
        member_of=request.user, workspace__type='PERSONAL'
    )
    
    membership = get_object_or_404(
        Member.objects.select_related('workspace'), 
        member_of=request.user, 
        workspace__slug=workspace_slug
    )

    context = {
        'user':request.user.username,
        'corporate_workspaces': corporate_workspaces,
        'personal_workspaces': personal_workspaces,
        'active_workspace': membership.workspace  
    }
    return render(request, 'dashboard.html', context)

class TaskCard(View):
    def get(self,request,task_slug,workspace_slug,action):
        get_dict={
            'issue':self.get_issue,
            'feedback':self.get_feedback,
            'attachment':self.get_attachment
        }
        return get_dict[action](request,task_slug,workspace_slug)
    
    def get_issue(self,request,task_slug,workspace_slug):
        task=get_object_or_404(Task,slug=task_slug)
        issues=Issue.objects.filter(task=task).all()
        workspace=get_object_or_404(Workspace,slug=workspace_slug)
        member = get_object_or_404(Member, workspace=workspace, member_of=request.user)
        assignments = Assign.objects.filter(task=task).select_related('assigned_to')
        reviewers = [assign.assigned_to for assign in assignments if assign.role == 'REVIEWER']
        workers = [assign.assigned_to for assign in assignments if assign.role == 'WORKER']
        context={
            'role':member.role,
            'issues':issues,
            'reviewers':reviewers,
            'workers':workers,
            'task_slug':task_slug,
        }
        return render(request,'issue.html',context)

    def get_feedback(self,request,task_slug,workspace_slug):
        issues=Issue.objects.filter(task__slug=task_slug).all()
        context={
            'issues':issues,
        }
        return render(request,'LiveFeedback.html',context)

    def get_attachment(self,request,task_slug,workspace_slug):
        return render(request,'attachment.html')



    def post(self,request,task_slug,workspace_slug,action):
        post_dict={
            'task_movement':self.task_movement,
            'addsubtask':self.addsubtask,
            'toggle_subtask':self.toggle_subtask,
        }
        return post_dict[action](request,task_slug,workspace_slug)
    
    def task_movement(self, request, task_slug, workspace_slug):
        try:
            broadcast_data = self.update_task(request, task_slug,workspace_slug)
            if broadcast_data:
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(
                    f"workspace_{broadcast_data['workspace_slug']}",
                    {
                        'type': 'workspace_broadcast',
                        'action': 'card_moved',
                        'sender_channel_name': None,
                        'payload': broadcast_data['payload']
                    }
                )
            return JsonResponse({'success': True, 'message': 'Workflow sync completed'}, status=200)
        except ValueError as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
        
    def update_task(self,request,task_slug,workspace_slug):
        data=json.loads(request.body) if request.body else {}
        new_status=data.get('status')
        # workspace_slug=data.get('workspace_slug')
        role_context=data.get('role')
        task=get_object_or_404(Task,slug=task_slug)
        workspace=get_object_or_404(Workspace,slug=workspace_slug)

        if new_status=='PROGRESS':
            task.status='PROGRESS'
            task.save()

        elif new_status=='REVIEW':
            current_time=timezone.now()
            if task.expires_at and task.expires_at<current_time:
                ActivityLog.objects.create(
                    user=request.user,
                    task=task,
                    workspace=workspace,
                    type= 'REVIEW_REJECTED',
                )
                raise ValueError(f"{task.title} expired on {task.expires_at}")
            
            task.status='REVIEW'
            task.save()
            ActivityLog.objects.create(
                user=request.user,
                task=task,
                workspace=workspace,
                type='REVIEW_APPROVED',
            )
            for reviewer in Assign.objects.filter(task=task,role='REVIEWER'):
                ActivityLog.objects.create(
                    user=reviewer.assigned_to,
                    task=task,
                    workspace=workspace,
                    type='REVIEW_REQUESTED',
                )
        elif new_status=='ISSUE':
            if not Issue.objects.filter(task__slug=task_slug).exists():
                raise ValueError(f"No issue created on this Task yet")
            
            task.status='ISSUE'
            task.save()
            ActivityLog.objects.create(
                    user=request.user,
                    task=task,
                    workspace=workspace,
                    type='ISSUE_CREATED',
                )
            Review.objects.create(
                task=task,
                reviewer=request.user,
                status='ISSUE',
            )
            for rev in Assign.objects.filter(task=task,role='WORKER'):
                ActivityLog.objects.create(
                    user=rev.assigned_to,
                    task=task,
                    workspace=workspace,
                    type='ISSUE_CREATED',
                )
        
        elif new_status=='DONE':
            if Issue.objects.filter(task__slug=task_slug).exists():
                raise ValueError("There is an issue existing for this task to be Done")
            
            task.status='DONE'
            task.save()
            ActivityLog.objects.create(
                user=request.user,
                task=task,
                workspace=workspace,
                type='TASK_COMPLETED',
            )
            Review.objects.create(
                task=task,
                reviewer=rev.assigned_to,
                status= 'DONE',
            )
            for rev in Assign.objects.filter(task=task,role='WORKER'):
                ActivityLog.objects.update_or_create(
                    user=rev.assigned_to,
                    task=task,
                    workspace=workspace,
                    type='TASK_COMPLETED',
                )   

        elif new_status=='TODO':
            task.status = 'TODO'
            task.save()
        
        column_map = {
            'TODO': 'TO DO',
            'PROGRESS': 'IN PROGRESS',
            'REVIEW': 'Apply Review',
            'ISSUE': 'ISSUE FOUND',
            'DONE': 'DONE'
        }

        all_subtasks = list(task.task_subtask.filter(
            Q(type='PUBLIC') | Q(type='PRIVATE', created_by=request.user)
        ))
        list_private = [{'id': s.id, 'title': s.title, 'type': 'private', 'checked': str(s.checked)} for s in all_subtasks if s.type == 'PRIVATE']
        list_public = [{'id': s.id, 'title': s.title, 'type': 'public', 'checked': str(s.checked)} for s in all_subtasks if s.type == 'PUBLIC']

        return {
            'workspace_slug': workspace_slug,
            'payload': {
                'role': role_context,
                'column': column_map.get(task.status, task.status),
                'task_slug': task.slug,
                'priority': str(task.priority),
                'issue_count': Issue.objects.filter(task=task).count(),
                'title': task.title,
                'description': task.description,
                'subtask_private': list_private,
                'subtask_public': list_public,
                'expires_at': str(task.expires_at) if task.expires_at else None,
                'feedback_count': Feedback.objects.filter(task=task).count()
            }
        }

    def addsubtask(self,request,task_slug,workspace_slug):
        try:
            data=json.loads(request.body) if request.body else {}
            title=data.get('title')
            subtask_type = data.get('type', 'PUBLIC')
            task=get_object_or_404(Task,slug=task_slug)
            subtask=Subtask.objects.create(
                task=task,
                created_by=request.user,
                title=title,
                type=subtask_type,
            )
            return JsonResponse({
            'success': True, 
            'message': 'Subtask successfully created!',
            'subtask': {
                'id': subtask.id,
                'title': subtask.title,
                'type': subtask.type,
                'checked': subtask.checked 
            }
        }, status=201)
        except Http404 as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=404)
        except Exception as e:
             return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    def toggle_subtask(self,request,task_slug,workspace_slug):
        try:
            data = json.loads(request.body)
            subtask_id = data.get('subtask_id')
            is_checked = data.get('checked') 

            if subtask_id is None or is_checked is None:
                return JsonResponse({'error': 'Missing required fields (subtask_id or checked)'}, status=400)
            try:
                subtask = Subtask.objects.get(id=subtask_id, task__slug=task_slug)
            except Subtask.DoesNotExist:
                return JsonResponse({'error': f'Subtask {subtask_id} not found for task card {task_slug}'}, status=404)

            if hasattr(subtask, 'type') and subtask.type == 'PRIVATE' and subtask.created_by != request.user:
                return JsonResponse({
                    'error': 'Access Denied: You do not have permission to modify this private subtask.'
                }, status=403)

            subtask.checked = is_checked 
            subtask.save()

            return JsonResponse({
                'status': 'success',
                'message': 'Subtask state synchronized completely.',
                'subtask': {
                    'id': subtask.id,
                    'title': subtask.title,
                    'checked': subtask.checked
                }
            }, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Malformed JSON payload data'}, status=400)
            
        except Exception as e:
            return JsonResponse({'error': f'Server processing error: {str(e)}'}, status=500)



class IssueView(View):
    def get(self, request, issue_slug, task_slug, action):
        get_dict = {
            'create': self.get_create_issue,
            'update': self.get_update_issue,
        }
        return get_dict[action](request, issue_slug, task_slug)
    
    def get_create_issue(self, request, issue_slug, task_slug):
        context = {
            'title': "",
            'description': "",
            'action': 'create',
            'issue_slug': issue_slug, 
            'task_slug': task_slug,
        }
        return render(request, 'curdIssue.html', context)

    def get_update_issue(self, request, issue_slug, task_slug):
        issue = get_object_or_404(Issue, slug=issue_slug)
        context = {
            'title': issue.title,
            'description': issue.description,
            'action': 'update',
            'issue_slug': issue_slug,
            'task_slug': task_slug,
        }
        return render(request, 'curdIssue.html', context)

    def post(self, request, issue_slug, task_slug, action):
        post_dict = {
            'delete': self.post_delete_issue,
            'update': self.post_update_issue,
            'create': self.post_create_issue,
        }
        return post_dict[action](request, issue_slug, task_slug)
    
    def post_delete_issue(self, request, issue_slug, task_slug):
        try:
            issue = get_object_or_404(Issue, slug=issue_slug)
            issue.delete()

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"issue_{task_slug}",
                {
                    "type": "issue_broadcast",
                    "action": "delete"
                }
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def post_update_issue(self, request, issue_slug, task_slug):
        try:
            data = json.loads(request.body)
            new_title = data.get('title')
            new_description = data.get('description')

            issue = get_object_or_404(Issue, slug=issue_slug)
            issue.title = new_title
            issue.description = new_description
            issue.save()

            task = get_object_or_404(Task, slug=task_slug)
            ActivityLog.objects.create(
                user=request.user,
                task=task,
                workspace=task.workspace,
                type='ISSUE_UPDATED'
            )

            for worker in Assign.objects.filter(task=task, role='WORKER'):
                ActivityLog.objects.create(
                    user=worker.assigned_to,
                    task=task,
                    workspace=task.workspace,
                    type='ISSUE_UPDATED'
                )

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"issue_{task_slug}",
                {
                    "type": "issue_broadcast",
                    "action": "update"
                }
            )
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def post_create_issue(self, request, issue_slug, task_slug):
        try:
            data = json.loads(request.body)
            new_title = data.get('title')
            new_description = data.get('description')
            task = get_object_or_404(Task, slug=task_slug)
            
            Issue.objects.create(
                task=task,
                issued_by=request.user,
                title=new_title,
                description=new_description
            )

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"issue_{task_slug}",
                {
                    "type": "issue_broadcast",
                    "action": "create"
                }
            )
            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)





        


        

                 


                

                


                    
        

    
                

                




            
        


