from django.db import models
from django.contrib.auth.models import User
from core.utils import generate_unique_slug

class Workspace(models.Model):
    TYPE_CHOICES = [
        ('PERSONAL', 'Personal'),
        ('CORPORATE', 'Corporate'),
    ]
    name=models.CharField(max_length=255)
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    type=models.CharField(max_length=100,choices=TYPE_CHOICES,default='PERSONAL')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Workspace)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name

class Task(models.Model):
    STATUS_CHOICES = [
        ('TO_DO', 'To Do'),
        ('IN_PROGRESS', 'In Progress'),
        ('REVIEWING', 'Reviewing'),
        ('ISSUE_FOUND', 'Issue Found'),
        ('APPLY_REVIEW', 'Apply Review'),
        ('DONE', 'Done'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
    ]
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name='workspace_task')
    assigned_by=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_task')
    title=models.CharField(max_length=255)
    description=models.TextField(null=True,blank=True)
    status=models.CharField(max_length=100,choices=STATUS_CHOICES,default='TO_DO')
    priority=models.CharField(max_length=100,choices=PRIORITY_CHOICES,default='MEDIUM')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['workspace', 'assigned_by']),
        ]

    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Task)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.title} Task assigned by {self.assigned_by.username} on workspace : {self.workspace.name}"


class Member(models.Model): # Junction of Workspace and User 
    ROLE_CHOICES = [
        ('OWNER', 'Owner'),
        ('REVIEWER', 'Reviewer'),
        ('WORKER', 'Worker'),
    ]
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    workspace=models.ForeignKey(Workspace,on_delete=models.CASCADE,related_name='workspace_member')
    member_of=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_member')
    role=models.CharField(max_length=100,choices=ROLE_CHOICES,default='OWNER')
    joined_at=models.DateTimeField(auto_now_add=True)
    leaved_at=models.DateTimeField(null=True, blank=True)
    class Meta:
        indexes = [
            models.Index(fields=['workspace', 'member_of']),
        ]
    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Member)
        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.member_of.username} joined at workspace : {self.workspace.name}"


class Assign(models.Model): # Junction Task and user
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    task=models.ForeignKey(Task,on_delete=models.CASCADE,related_name='task_assign')
    assigned_to=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_assign')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['task', 'assigned_to']),
        ]

    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Assign)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.task.title} assigned to {self.assigned_to.username}"
    
class Subtask(models.Model):
    TYPE_CHOICES = [
        ('PRIVATE', 'private'),
        ('PUBLIC', 'public'),
    ]
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    task=models.ForeignKey(Task,on_delete=models.CASCADE,related_name='task_subtask')
    created_by=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_subtask')
    title=models.CharField(max_length=255)
    type=models.CharField(max_length=100,choices=TYPE_CHOICES,default='PRIVATE')
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['task', 'created_by']),
            models.Index(fields=['task', 'type']),
        ]
    
    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Subtask)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} subtask created for Task {self.task.title} by {self.created_by.username}"
    
class Review(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    task=models.ForeignKey(Task,on_delete=models.CASCADE,related_name='task_review')
    reviewer=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_review')
    status=models.CharField(max_length=100,choices=STATUS_CHOICES,default='PENDING')
    found_issue=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['task', 'reviewer']),
        ]
    
    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Review)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.task.title} reviewed by {self.reviewer.username}"
    
class Issue(models.Model):
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    review=models.ForeignKey(Review,on_delete=models.CASCADE,related_name='review_issue')
    issued_by=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_issue')
    title=models.CharField(max_length=255)
    description=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    
    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Issue)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.title} issued by {self.issued_by.username}"

class Feedback(models.Model):
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    issue=models.ForeignKey(Issue,on_delete=models.CASCADE,related_name='issue_feedback')
    feedback_by=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_feedback')
    content=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['issue', 'feedback_by']),
        ]
    
    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Feedback)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Feedback on issue : {self.issue.title} by {self.feedback_by.username}"

class Response(models.Model):
    slug=models.SlugField(max_length=255,unique=True,editable=False)
    issue=models.ForeignKey(Issue,on_delete=models.CASCADE,related_name='issue_response')
    feedback=models.ForeignKey(Feedback,on_delete=models.CASCADE,related_name='feedback_response')
    response_by=models.ForeignKey(User,on_delete=models.CASCADE,related_name='user_response')
    content=models.TextField()
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['issue', 'feedback','response_by']),
        ]
    
    def save(self, *args,**kwargs):
        if not self.slug:
            self.slug=generate_unique_slug(Response)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Response on feedback : {self.feedback.slug} by {self.response_by.username}"
    

    
class ActivityLog(models.Model):

    TYPE_CHOICES = [
        ('TASK_CREATED', 'Task Created'),
        ('TASK_UPDATED', 'Task Updated'),
        ('TASK_MOVED', 'Task Moved'),

        ('REVIEW_REQUESTED', 'Review Requested'),
        ('REVIEW_APPROVED', 'Review Approved'),
        ('REVIEW_REJECTED', 'Review Rejected'),

        ('ISSUE_CREATED', 'Issue Created'),
        ('ISSUE_UPDATED', 'Issue Updated'),

        ('FEEDBACK_CREATED', 'Feedback Created'),
        ('FEEDBACK_RESPONSE', 'Feedback Response'),

        ('WORKSPACE_JOINED', 'Workspace Joined'),
        ('TASK_ASSIGNED', 'Task Assigned'),

        ('EXPIRE_ALERT', 'Expire Alert'),
    ]

    slug = models.SlugField(
        max_length=255,
        unique=True,
        editable=False
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='user_activity'
    )

    workspace = models.ForeignKey(
        'Workspace',
        on_delete=models.CASCADE,
        related_name='workspace_activity',
        null=True,
        blank=True
    )

    task = models.ForeignKey(
        'Task',
        on_delete=models.CASCADE,
        related_name='task_activity',
        null=True,
        blank=True
    )

    issue = models.ForeignKey(
        'Issue',
        on_delete=models.CASCADE,
        related_name='issue_activity',
        null=True,
        blank=True
    )

    review = models.ForeignKey(
        'Review',
        on_delete=models.CASCADE,
        related_name='review_activity',
        null=True,
        blank=True
    )

    type = models.CharField(
        max_length=100,
        choices=TYPE_CHOICES
    )

    payload = models.JSONField(default=dict)

    is_processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'type']),
            models.Index(fields=['workspace']),
            models.Index(fields=['task']),
            models.Index(fields=['issue']),
            models.Index(fields=['review']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_processed']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = generate_unique_slug(ActivityLog)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.type} by {self.actor.username}"
    

class UserEventCursor(models.Model):

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='event_cursor'
    )

    workspace = models.ForeignKey(
        'Workspace',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    last_event_id = models.BigIntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'workspace']),
        ]

    def __str__(self):
        return f"{self.user.username} → {self.last_event_id}"
    

class Attachment(models.Model):

    TYPE_CHOICES = [
        ('FILE', 'File'),
        ('URL', 'URL'),
        ('IMAGE', 'Image'),
        ('DOCUMENT', 'Document'),
        ('REPOSITORY', 'Repository'),
    ]

    task=models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='task_attachment'
    )

    uploaded_by=models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    file=models.FileField(
        upload_to='attachments/',
        null=True,
        blank=True
    )

    external_url=models.URLField(
        null=True,
        blank=True
    )

    type=models.CharField(
        max_length=100,
        choices=TYPE_CHOICES
    )

    created_at=models.DateTimeField(auto_now_add=True)