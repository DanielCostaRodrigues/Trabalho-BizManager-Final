import json
import base64
import os
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.conf import settings
from .models import ChatRoom, Message
from django.contrib.auth import get_user_model
from autenticacao.utils import notificar_nova_mensagem
import uuid

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'
        
        # Verificar se o utilizador está autenticado
        if self.scope['user'].is_anonymous:
            await self.close()
            return
        
        self.user = self.scope['user']
        
        # Verificar se a sala existe e se o utilizador tem permissão
        room_exists = await self.get_room()
        if not room_exists:
            await self.close()
            return
        
        # Juntar-se ao grupo da sala
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        # Enviar histórico de mensagens quando alguém se conecta
        await self.send_message_history()
        
        # Notificar outros utilizadores que este utilizador entrou
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'user_joined',
                'user': self.user.get_full_name() or self.user.email,
                'message': f'{self.user.get_full_name() or self.user.email} entrou no chat.'
            }
        )
    
    async def disconnect(self, close_code):
        # Notificar outros utilizadores que este utilizador saiu
        if hasattr(self, 'room_group_name') and hasattr(self, 'user'):
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'user_left',
                    'user': self.user.get_full_name() or self.user.email,
                    'message': f'{self.user.get_full_name() or self.user.email} saiu do chat.'
                }
            )
            
            # Sair do grupo da sala
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    # Receber mensagem do WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type', 'message')
        
        if message_type == 'file':
            # Processar ficheiro
            file_name = text_data_json.get('file_name')
            file_type = text_data_json.get('file_type')
            file_data = text_data_json.get('file_data')
            
            # Gerar um nome de ficheiro único
            unique_filename = f"{uuid.uuid4().hex}_{file_name}"
            
            # Extrair os dados de base64
            format, filestr = file_data.split(';base64,')
            file_content = base64.b64decode(filestr)
            
            # Criar um caminho para salvar o ficheiro
            file_dir = os.path.join(settings.MEDIA_ROOT, 'chat_files')
            os.makedirs(file_dir, exist_ok=True)
            file_path = os.path.join(file_dir, unique_filename)
            
            # Salvar o ficheiro
            with open(file_path, 'wb') as f:
                f.write(file_content)
            
            # Criar uma URL relativa para o ficheiro
            file_url = f'/media/chat_files/{unique_filename}'
            
            # Guardar a mensagem na base de dados
            await self.save_file_message(file_name, file_url)
            
            # Enviar mensagem para o grupo da sala
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'file_message',
                    'file_name': file_name,
                    'file_type': file_type,
                    'file_url': file_url,
                    'user': self.user.get_full_name() or self.user.email,
                    'user_id': self.user.id,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            # Notificar outros participantes
            await self.notify_other_participants(f"Enviou um ficheiro: {file_name}")
        else:
            # Processar mensagem de texto normal
            message = text_data_json.get('message', '')
            
            # Guardar a mensagem na base de dados
            await self.save_message(message)
            
            # Enviar mensagem para o grupo da sala
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'user': self.user.get_full_name() or self.user.email,
                    'user_id': self.user.id,
                    'timestamp': timezone.now().isoformat(),
                }
            )
            
            # Notificar outros participantes sobre a nova mensagem
            await self.notify_other_participants(message)
    
    # Receber mensagem do grupo da sala
    async def chat_message(self, event):
        # Enviar mensagem para o WebSocket
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'user': event['user'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp'],
        }))
    
    # Processar mensagem de ficheiro
    async def file_message(self, event):
        # Enviar mensagem para o WebSocket
        await self.send(text_data=json.dumps({
            'type': 'file',
            'file_name': event['file_name'],
            'file_type': event['file_type'],
            'file_url': event['file_url'],
            'user': event['user'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp'],
        }))
    
    # Notificar quando um utilizador entrar
    async def user_joined(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
        }))
    
    # Notificar quando um utilizador sair
    async def user_left(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'message': event['message'],
        }))
    
    @database_sync_to_async
    def get_room(self):
        try:
            room = ChatRoom.objects.get(name=self.room_name)
            # Verificar se o utilizador é participante
            if self.user not in room.participants.all():
                room.participants.add(self.user)
            return True
        except ChatRoom.DoesNotExist:
            # Criar a sala se ela não existir
            room = ChatRoom.objects.create(name=self.room_name)
            room.participants.add(self.user)
            return True
    
    @database_sync_to_async
    def save_message(self, message):
        room = ChatRoom.objects.get(name=self.room_name)
        Message.objects.create(
            room=room,
            sender=self.user,
            content=message
        )
    
    @database_sync_to_async
    def save_file_message(self, file_name, file_url):
        room = ChatRoom.objects.get(name=self.room_name)
        Message.objects.create(
            room=room,
            sender=self.user,
            content=f"[Ficheiro: {file_name}]",
            file_url=file_url
        )
    
    # Método para notificar outros participantes
    @database_sync_to_async
    def notify_other_participants(self, message):
        """Notifica outros participantes da sala sobre a nova mensagem."""
        room = ChatRoom.objects.get(name=self.room_name)
        for participant in room.participants.exclude(id=self.user.id):
            notificar_nova_mensagem(participant, self.user, room)
    
    @database_sync_to_async
    def get_message_history(self):
        room = ChatRoom.objects.get(name=self.room_name)
        messages = list(room.messages.order_by('-timestamp')[:50])
        
        # Criar uma lista de dicionários com os dados das mensagens
        message_list = []
        for message in messages:
            message_dict = {
                'content': message.content,
                'sender_id': message.sender_id,
                'sender_name': message.sender.get_full_name() or message.sender.email,
                'timestamp': message.timestamp.isoformat(),
            }
            
            # Verificar se é uma mensagem de ficheiro
            if hasattr(message, 'file_url') and message.file_url:
                message_dict['type'] = 'file'
                message_dict['file_url'] = message.file_url
                import re
                file_match = re.search(r'\[Ficheiro: (.*?)\]', message.content)
                if file_match:
                    message_dict['file_name'] = file_match.group(1)
                else:
                    message_dict['file_name'] = "Ficheiro"
            
            message_list.append(message_dict)
        
        return message_list
    
    async def send_message_history(self):
        messages = await self.get_message_history()
        
        message_history = []
        for message in reversed(messages):  
            if message.get('type') == 'file':
                message_history.append({
                    'type': 'file',
                    'file_name': message['file_name'],
                    'file_url': message['file_url'],
                    'user': message['sender_name'],
                    'user_id': message['sender_id'],
                    'timestamp': message['timestamp'],
                })
            else:
                message_history.append({
                    'type': 'chat_message',
                    'message': message['content'],
                    'user': message['sender_name'],
                    'user_id': message['sender_id'],
                    'timestamp': message['timestamp'],
                })
        
        if message_history:
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': message_history,
            }))