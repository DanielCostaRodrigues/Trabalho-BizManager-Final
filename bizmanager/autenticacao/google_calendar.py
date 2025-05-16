import os
import datetime
import pickle
import sys
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.profile', 
    'https://www.googleapis.com/auth/userinfo.email',
    'openid']


possible_paths = [
    'credentials.json', 
    os.path.join(os.path.dirname(__file__), 'credentials.json'),  
    os.path.join(os.path.dirname(os.path.dirname(__file__)), 'credentials.json'),  
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'credentials.json'), 
    'C:\\Users\\kikon\\bizmanager\\credentials.json',   
    'C:\\Users\\kikon\\bizmanager\\bizmanager\\credentials.json',  
]

CREDENTIALS_FILE = None
for path in possible_paths:
    if os.path.exists(path):
        CREDENTIALS_FILE = path
        print(f"Encontrado ficheiro de credenciais em: {path}")
        break

if not CREDENTIALS_FILE:
    print("ERRO: Ficheiro de credenciais não encontrado. Caminhos verificados:")
    for path in possible_paths:
        print(f"- {path}")
    raise FileNotFoundError("Não foi possível encontrar o ficheiro credentials.json em nenhum dos caminhos verificados")

TOKEN_DIR = os.path.join(os.path.dirname(CREDENTIALS_FILE), 'tokens')


def get_google_auth_url(user_id, redirect_uri):
    """
    Gera o URL de autenticação do Google OAuth2 para o utilizador.
    
    Args:
        user_id (int): ID do utilizador para identificação do token
        redirect_uri (str): URL de redirecionamento após autenticação
        
    Returns:
        str: URL para autorização OAuth2
    """
  
    os.makedirs(TOKEN_DIR, exist_ok=True)
    
    
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    
    # Gerar URL de autorização
    auth_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        state=str(user_id)  
    )
    
    return auth_url


def handle_google_callback(code, user_id, redirect_uri=None):
    """
    Processa o retorno da autenticação OAuth2 e guarda o token de acesso.
    
    Args:
        code (str): Código de autorização retornado pelo Google
        user_id (int): ID do utilizador para guardar o token
        redirect_uri (str, optional): URL de redirecionamento para o callback
        
    Returns:
        bool: Verdadeiro se a autenticação foi bem-sucedida
    """
    try:
        
        if redirect_uri is None:
            redirect_uri = 'http://127.0.0.1:8000/google-oauth-callback/'
            
        print(f"A usar redirect_uri: {redirect_uri}")
        
       
        flow = Flow.from_client_secrets_file(
            CREDENTIALS_FILE,
            scopes=SCOPES,
            redirect_uri=redirect_uri
        )
        
       
        flow.fetch_token(code=code)
        
        
        credentials = flow.credentials
        token_path = os.path.join(TOKEN_DIR, f'token_{user_id}.pickle')
        
        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)
            
        return True
        
    except Exception as e:
        print(f"Erro ao processar callback do Google: {str(e)}")
        return False


def get_calendar_service(user_id):
    """
    Obtém um serviço autenticado da API do Google Calendar.
    
    Args:
        user_id (int): ID do utilizador para buscar o token guardado
        
    Returns:
        service: Serviço da API do Google Calendar autenticado
        None: Se falhar ao obter o serviço
    """
    try:
        # Verificar se o token existe
        token_path = os.path.join(TOKEN_DIR, f'token_{user_id}.pickle')
        credentials = None
        
        # Carregar credenciais do ficheiro se existir
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                credentials = pickle.load(token)
        
        # Verificar se as credenciais expiram ou são inválidas
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
            else:
                
                return None
            
            # Guardar as credenciais atualizadas
            with open(token_path, 'wb') as token:
                pickle.dump(credentials, token)
        
        # Construir o serviço
        service = build('calendar', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        print(f"Erro ao obter serviço do Google Calendar: {str(e)}")
        return None


def create_calendar_event(user_id, summary, description, start_datetime, end_datetime):
    """
    Cria um evento no Google Calendar do utilizador.
    
    Args:
        user_id (int): ID do utilizador
        summary (str): Título do evento
        description (str): Descrição do evento
        start_datetime (datetime): Data e hora de início
        end_datetime (datetime): Data e hora de término
        
    Returns:
        event_id (str): ID do evento criado
        None: Se falhar ao criar o evento
    """
    try:
        service = get_calendar_service(user_id)
        if not service:
            return None
        
        # Formatar datas para o formato da API
        start = start_datetime.isoformat()
        end = end_datetime.isoformat()
        
        # Criar o evento
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start,
                'timeZone': 'Europe/Lisbon',  # Fuso horário de Portugal
            },
            'end': {
                'dateTime': end,
                'timeZone': 'Europe/Lisbon',  # Fuso horário de Portugal
            },
            'reminders': {
                'useDefault': True,
            },
        }
        
        # Inserir o evento no calendário primário do utilizador
        event = service.events().insert(calendarId='primary', body=event).execute()
        return event.get('id')
        
    except Exception as e:
        print(f"Erro ao criar evento no Google Calendar: {str(e)}")
        return None


def add_pedido_to_calendar(pedido):
    """
    Adiciona um pedido como evento no Google Calendar e retorna o event_id e URL.
    
    Args:
        pedido: Instância do modelo Pedido
        
    Returns:
        tuple: (event_id, event_url) ou (None, None) se falhar
    """
    try:
        if pedido.tipo_servico != 'agendado' or not pedido.data_agendamento or not pedido.hora_agendamento:
            return None, None
        
        service = get_calendar_service(pedido.cliente.id)
        if not service:
            return None, None
        
        # Combinar data e hora para criar datetime de início
        from datetime import datetime, timedelta
        from django.utils import timezone
        
        # Usar timezone para criar datetimes com fuso horário
        start_datetime = timezone.make_aware(datetime.combine(
            pedido.data_agendamento, 
            pedido.hora_agendamento
        ))
        
        # Por padrão, definimos a duração como 1 hora
        end_datetime = start_datetime + timedelta(hours=1)
        
        # Criar título e descrição
        summary = f"Serviço: {pedido.servico.nome}"
        description = f"""
        Serviço solicitado via BizManager
        
        Cliente: {pedido.cliente.get_full_name()}
        Freelancer: {pedido.servico.freelancer.get_full_name()}
        Valor: €{pedido.servico.orcamento}
        
        Descrição do serviço: {pedido.servico.descricao}
        
        Comentários adicionais: {pedido.comentario or 'Nenhum'}
        """
        
        # Criar o evento
        event = {
            'summary': summary,
            'description': description,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'Europe/Lisbon',  # Fuso horário de Portugal
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'Europe/Lisbon',  # Fuso horário de Portugal
            },
            'reminders': {
                'useDefault': True,
            },
        }
        
        # Inserir o evento no calendário primário do utilizador
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        event_id = created_event.get('id')
        
        # Construir o link para o evento no Google Calendar
        event_html_link = created_event.get('htmlLink')
        
        return event_id, event_html_link
        
    except Exception as e:
        print(f"Erro ao adicionar pedido ao Google Calendar: {str(e)}")
        return None, None