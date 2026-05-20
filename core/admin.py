from django.contrib import admin
from .models import Workspace,Task,Member,Assign,Review,Feedback,Response,ActivityLog,UserEventCursor,Attachment,Issue,Subtask

admin.site.register(Workspace)
admin.site.register(Task)
admin.site.register(Member)
admin.site.register(Assign)
admin.site.register(Review)
admin.site.register(Feedback)
admin.site.register(Response)
admin.site.register(ActivityLog)
admin.site.register(UserEventCursor)
admin.site.register(Attachment)
admin.site.register(Issue)
admin.site.register(Subtask)
