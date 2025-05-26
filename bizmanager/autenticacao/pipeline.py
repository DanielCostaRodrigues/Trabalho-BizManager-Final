from .models import User, Perfil, FreelancerDetalhe, ClienteDetalhe

def guardar_perfil(strategy, backend, user, response, *args, **kwargs):
    """
    Pipeline para processar informações do utilizador após login com Google.
    """
    if backend.name == 'google-oauth2':
        if not kwargs.get('is_new', False):
            return
        request = strategy.request
        tipo_conta = request.session.get('tipo_conta_google', 'cliente') 
        
        user.user_type = tipo_conta
        if not user.first_name and 'given_name' in response:
            user.first_name = response['given_name']
        if not user.last_name and 'family_name' in response:
            user.last_name = response['family_name']
        
        user.save()
        try:
            perfil = Perfil.objects.get(user=user)
        except Perfil.DoesNotExist:
            perfil = Perfil.objects.create(user=user)
        if tipo_conta == 'freelancer':
            if not hasattr(perfil, 'freelancer_detalhe'):
                FreelancerDetalhe.objects.create(perfil=perfil)
        else:  
            if not hasattr(perfil, 'cliente_detalhe'):
                ClienteDetalhe.objects.create(perfil=perfil)
        request.session.pop('tipo_conta_google', None)
        
        return {'user': user}