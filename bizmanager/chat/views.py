from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Count
from django.http import JsonResponse
from .models import ChatRoom, Message
from autenticacao.models import User

@login_required
def index(request):
    user_rooms = ChatRoom.objects.filter(participants=request.user)
    
    
    rooms_with_info = []
    for room in user_rooms:
        # Obter a última mensagem
        last_message = room.messages.order_by('-timestamp').first()
        
        # Contar mensagens não lidas
        unread_count = room.messages.filter(is_read=False).exclude(sender=request.user).count()
        
        # Obter outros participantes (exceto o próprio utilizador)
        other_participants = room.participants.exclude(id=request.user.id)
        
        rooms_with_info.append({
            'room': room,
            'last_message': last_message,
            'unread_count': unread_count,
            'other_participants': other_participants
        })
    
    rooms_with_info.sort(
        key=lambda x: x['last_message'].timestamp if x['last_message'] else room.created_at, 
        reverse=True
    )
    
    return render(request, 'chat/index.html', {
        'rooms_with_info': rooms_with_info,
    })

@login_required
def room(request, room_name):
    # Obter ou criar a sala
    room, created = ChatRoom.objects.get_or_create(name=room_name)
    
    if request.user not in room.participants.all():
        room.participants.add(request.user)
    unread_messages = Message.objects.filter(room=room, is_read=False).exclude(sender=request.user)
    for message in unread_messages:
        message.is_read = True
        message.save()
    
    other_participants = room.participants.exclude(id=request.user.id)
    
    return render(request, 'chat/room.html', {
        'room_name': room_name,
        'room': room,
        'other_participants': other_participants
    })

@login_required
def start_chat(request, username):
    other_user = get_object_or_404(User, email=username)
    
    existing_rooms = ChatRoom.objects.annotate(
        participant_count=Count('participants')
    ).filter(
        participants=request.user
    ).filter(
        participants=other_user
    ).filter(
        participant_count=2  
    )
    
    if existing_rooms.exists():
        room = existing_rooms.first()
        return redirect('chat:room', room_name=room.name)
    
    room_name = f"dm_{min(request.user.id, other_user.id)}_{max(request.user.id, other_user.id)}"
    room, created = ChatRoom.objects.get_or_create(name=room_name)
    room.participants.add(request.user, other_user)
    
    return redirect('chat:room', room_name=room.name)

@login_required
def contacts(request):
    users = User.objects.exclude(id=request.user.id)
    
    return render(request, 'chat/contacts.html', {
        'users': users
    })

@login_required
def unread_count(request):
    count = Message.objects.filter(
        room__participants=request.user,
        is_read=False
    ).exclude(sender=request.user).count()
    
    return JsonResponse({'unread_count': count})