from .models import Notificacao

def criar_notificacao(utilizador, tipo, titulo, texto, link=None):
    """
    Cria uma nova notificação para um utilizador.
    
    Args:
        utilizador: Utilizador que receberá a notificação
        tipo: Tipo de notificação (conforme TIPOS no modelo)
        titulo: Título curto da notificação
        texto: Texto detalhado da notificação
        link: Link opcional para redirecionar (URL)
    
    Returns:
        Objeto Notificacao criado
    """
    notificacao = Notificacao.objects.create(
        utilizador=utilizador,
        tipo=tipo,
        titulo=titulo,
        texto=texto,
        link=link
    )
    return notificacao

def notificar_nova_mensagem(utilizador, remetente, sala):
    """Notifica o utilizador sobre uma nova mensagem."""
    titulo = f"Nova mensagem de {remetente.get_full_name() or remetente.email}"
    texto = "Recebeu uma nova mensagem no chat."
    link = f"/chat/room/{sala.name}/"
    return criar_notificacao(utilizador, 'mensagem', titulo, texto, link)

def notificar_novo_pedido(freelancer, cliente, servico):
    """Notifica o freelancer sobre um novo pedido de serviço."""
    titulo = f"Novo pedido de {cliente.get_full_name() or cliente.email}"
    texto = f"Recebeu um novo pedido para o serviço: {servico.nome}"
    link = f"/pedidos/"
    return criar_notificacao(freelancer, 'pedido', titulo, texto, link)

def notificar_pedido_aceite(cliente, freelancer, servico):
    """Notifica o cliente que seu pedido foi aceite."""
    titulo = f"Pedido aceite por {freelancer.get_full_name() or freelancer.email}"
    texto = f"O seu pedido para o serviço '{servico.nome}' foi aceite!"
    link = f"/pedidos/"
    return criar_notificacao(cliente, 'aceitacao', titulo, texto, link)

def notificar_pedido_rejeitado(cliente, freelancer, servico):
    """Notifica o cliente que seu pedido foi rejeitado."""
    titulo = f"Pedido rejeitado por {freelancer.get_full_name() or freelancer.email}"
    texto = f"O seu pedido para o serviço '{servico.nome}' foi rejeitado."
    link = f"/pedidos/"
    return criar_notificacao(cliente, 'rejeicao', titulo, texto, link)

def notificar_servico_concluido(cliente, freelancer, servico):
    """Notifica o cliente que o serviço foi concluído."""
    titulo = f"Serviço concluído por {freelancer.get_full_name() or freelancer.email}"
    texto = f"O serviço '{servico.nome}' foi marcado como concluído. Por favor, faça a avaliação."
    link = f"/pedidos/"
    return criar_notificacao(cliente, 'conclusao', titulo, texto, link)