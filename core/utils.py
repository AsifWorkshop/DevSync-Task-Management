import secrets
from django.utils.text import slugify
from django.utils import timezone

def generate_unique_slug(model_name,field_name='slug',length=8):
    timestamp=timezone.now().strftime("%Y%m%d-%H%M")
    while True:
        random_suffix=secrets.token_hex(length // 2)
        candidate_slug=f"{random_suffix}-{timestamp}"
        lookup_kwargs={field_name : candidate_slug} # Dictionary Unpacking
        if not model_name.obejcts.filter(**lookup_kwargs).exists():
            return candidate_slug
        
