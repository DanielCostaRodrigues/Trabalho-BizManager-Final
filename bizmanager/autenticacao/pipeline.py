from .models import Perfil, ClienteDetalhe

def guardar_perfil(backend, user, response, *args, **kwargs):
    """
    Pipeline para processar informações do utilizador após login com Google.
    """
    if backend.name == 'google-oauth2':
        # Verificar se o utilizador é novo
        if kwargs.get('is_new', False):
            # Por padrão, definir como cliente 
            user.user_type = 'cliente'
            
            # Preencher nome e apelido
            if not user.first_name and 'given_name' in response:
                user.first_name = response['given_name']
            if not user.last_name and 'family_name' in response:
                user.last_name = response['family_name']
            user.save()