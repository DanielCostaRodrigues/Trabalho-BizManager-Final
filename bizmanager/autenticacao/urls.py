from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
      
    # Páginas de autenticação
    path('', views.home, name='home'),
    path('escolher-conta/', views.escolher_conta, name='escolher_conta'),
    path('registo-freelancer/', views.registo_freelancer, name='registo_freelancer'),
    path('registo-cliente/', views.registo_cliente, name='registo_cliente'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Páginas principais
    path('dashboard/', views.dashboard, name='dashboard'),
    path('perfil/', views.perfil, name='perfil'),
    
    # Serviços
    path('servicos/', views.servicos, name='servicos'),
    path('servicos/criar/', views.criar_servico, name='criar_servico'),
    path('servicos/editar/<int:servico_id>/', views.editar_servico, name='editar_servico'),
    path('servicos/ver/<int:servico_id>/', views.ver_servico, name='ver_servico'),
    path('servicos/solicitar/<int:servico_id>/', views.solicitar_servico, name='solicitar_servico'),
    path('servicos/toggle-status/<int:servico_id>/', views.toggle_servico_status, name='toggle_servico_status'),
    
    # Pedidos
    path('pedidos/', views.pedidos, name='pedidos'),
    path('pedidos/ver/<int:pedido_id>/', views.ver_pedido, name='ver_pedido'),
    path('pedidos/aceitar/<int:pedido_id>/', views.aceitar_pedido, name='aceitar_pedido'),
    path('pedidos/rejeitar/<int:pedido_id>/', views.rejeitar_pedido, name='rejeitar_pedido'),
    path('pedidos/concluir/<int:pedido_id>/', views.concluir_pedido, name='concluir_pedido'),
    path('pedidos/cancelar/<int:pedido_id>/', views.cancelar_pedido, name='cancelar_pedido'),
    
    # Faturas
    path('faturas/', views.faturas, name='faturas'),
    path('faturas/ver/<int:fatura_id>/', views.ver_fatura, name='ver_fatura'),
    path('faturas/pagar/<int:fatura_id>/', views.marcar_fatura_paga, name='marcar_fatura_paga'),
    
    # Serviços públicos
    path('servicos-disponiveis/', views.servicos_publicos, name='servicos_publicos'),
    path('servicos-disponiveis/ver/<int:servico_id>/', views.ver_servico_publico, name='ver_servico_publico'),
    
    # Google Calendar API Integration
    path('google-auth/', views.google_auth, name='google_auth'),
    path('google-oauth-callback/', views.google_oauth_callback, name='google_oauth_callback'),
    path('pedidos/sync-calendar/<int:pedido_id>/', views.sync_pedido_to_calendar, name='sync_pedido_to_calendar'),
    path('test-google-auth/', views.test_google_auth, name='test_google_auth'),
    
    # Página de Ajuda
    path('ajuda/', views.ajuda, name='ajuda'),

    # URL para o registo com Google
    path('registar-google/', views.registar_google, name='registar_google'),
    path('', include('social_django.urls', namespace='social')),

    # URLs para pagamentos
    path('faturas/pagar/<int:fatura_id>/stripe/', views.iniciar_pagamento_stripe, name='iniciar_pagamento_stripe'),
    path('pagamentos/sucesso/', views.pagamento_sucesso, name='pagamento_sucesso'),
    path('pagamentos/cancelado/', views.pagamento_cancelado, name='pagamento_cancelado'),
    path('webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('faturas/selecionar-metodo/<int:fatura_id>/', views.selecionar_metodo_pagamento, name='selecionar_metodo_pagamento'),

    # Novas URLs para recuperação de palavra-passe
    path('recuperar-palavra-passe/', auth_views.PasswordResetView.as_view(
        email_template_name='email/recuperacao_password.html',
        subject_template_name='email/assunto_recuperacao.txt',
        extra_context={'title': 'Recuperar Palavra-passe'}
    ), name='password_reset'),
    
    path('recuperar-palavra-passe/enviado/', auth_views.PasswordResetDoneView.as_view(
        extra_context={'title': 'Email Enviado'}
    ), name='password_reset_done'),
    
    path('redefinir-palavra-passe/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        extra_context={'title': 'Definir Nova Palavra-passe'}
    ), name='password_reset_confirm'),
    
    path('redefinir-palavra-passe/concluido/', auth_views.PasswordResetCompleteView.as_view(
        extra_context={'title': 'Palavra-passe Redefinida'}
    ), name='password_reset_complete'),

    # URLs para notificações
    path('notificacoes/', views.listar_notificacoes, name='notificacoes'),
    path('notificacoes/marcar-lida/<int:notificacao_id>/', views.marcar_como_lida, name='marcar_notificacao_lida'),
    path('notificacoes/marcar-todas-lidas/', views.marcar_todas_como_lidas, name='marcar_todas_notificacoes_lidas'),
    path('notificacoes/contar-nao-lidas/', views.contar_nao_lidas, name='contar_notificacoes_nao_lidas'),
    path('notificacoes/recentes/', views.obter_notificacoes_recentes, name='obter_notificacoes_recentes'),
    
    # URLs para ver perfil 
    path('perfil/<int:user_id>/', views.ver_perfil_utilizador, name='ver_perfil_utilizador'),
    
    # URLs para o suporte
    path('enviar-suporte/', views.enviar_suporte, name='enviar_suporte'),
    
    # URLs para PayPal
    path('faturas/pagar/<int:fatura_id>/paypal/', views.iniciar_pagamento_paypal, name='iniciar_pagamento_paypal'),
    path('pagamentos/paypal/sucesso/', views.pagamento_paypal_sucesso, name='pagamento_paypal_sucesso'),
    path('pagamentos/paypal/cancelado/', views.pagamento_paypal_cancelado, name='pagamento_paypal_cancelado'),
    
    # URLs para métodos de pagamento do freelancer
    path('metodos-pagamento/', views.redirect_to_faturas_payment_tab, name='metodos_pagamento_freelancer'),
    path('stripe-connect-callback/', views.stripe_connect_callback, name='stripe_connect_callback'),

    # listagem de clientes 
    path('clientes/', views.listar_clientes, name='listar_clientes'),
    path('clientes/enviar-proposta/<int:cliente_id>/', views.enviar_proposta_cliente, name='enviar_proposta_cliente'),
    path('clientes/exportar-dados/<int:cliente_id>/', views.exportar_dados_cliente, name='exportar_dados_cliente'),
    
    # URLs para propostas
    path('notificacoes/proposta/<int:notificacao_id>/', views.ver_notificacao_proposta, name='ver_notificacao_proposta'),
    path('notificacoes/proposta/<int:notificacao_id>/responder/', views.responder_proposta, name='responder_proposta'),    
    
]