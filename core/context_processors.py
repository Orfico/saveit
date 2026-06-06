from django.contrib.auth.models import User


def account_switch(request):
    """Adds switch_from_user to template context when an account switch is active."""
    ctx = {'switch_from_user': None}
    if request.user.is_authenticated:
        switch_from_pk = request.session.get('_switch_from')
        if switch_from_pk:
            try:
                ctx['switch_from_user'] = User.objects.get(pk=switch_from_pk)
            except User.DoesNotExist:
                del request.session['_switch_from']
    return ctx
