from django.conf import settings

def stripe_context(request):
    """Contexto para adicionar configurações do Stripe aos templates."""
    return {
        'settings': {
            'STRIPE_PUBLIC_KEY': settings.STRIPE_PUBLIC_KEY,
        }
    }