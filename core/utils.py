import secrets
from django.utils.text import slugify
from django.utils import timezone

def generate_unique_slug(model_name,field_name='slug',length=8):
    timestamp=timezone.now().strftime("%Y%m%d-%H%M")
    while True:
        random_suffix=secrets.token_hex(length // 2)
        candidate_slug=f"{random_suffix}-{timestamp}"
        lookup_kwargs={field_name : candidate_slug} # Dictionary Unpacking
        if not model_name.objects.filter(**lookup_kwargs).exists():
            return candidate_slug
        
def Notif_Event(event="dummy",task_title="dummy",workspace_name="dummy",username="dummy"):
    notif={
        "TASK_ASSIGNED":f"New Task Has Been Assigned on {workspace_name}",
        "REVIEW_REQUESTED":f"New Review Request on {workspace_name}",
        "REVIEW_REJECTED":f"Your Review Request on Task : [ {task_title} ]Has been Rejected",
        "REVIEW_APPROVED":f"Your Review Request on Task :[ {task_title} ] Has been Approved",
        "ISSUE_CREATED":f"New Issue Created at Task :[ {task_title} ]",
        "ISSUE_UPDATED":f"Issue Updated at Task :[ {task_title} ]",
        "FEEDBACK_CREATED":f"New Feedback has been created on Task : [ {task_title} ]",
        "FEEDBACK_RESPONSE":f"New Response has been created on Task : [ {task_title} ]",
        "WORKSPACE_JOINED":f"You been added to {workspace_name}",
        "TASK_COMPLETED":f"Task : [ {task_title} ] has been completed",
        "dummy":"dummy"
    }
    return notif[event]