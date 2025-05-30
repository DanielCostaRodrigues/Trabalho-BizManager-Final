from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('autenticacao.urls')),  # Rotas do aplicação da autenticação 
    path('chat/', include('chat.urls', namespace='chat')),  
]

# Adicionar URLs para arquivos de mídia em ambiente de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)