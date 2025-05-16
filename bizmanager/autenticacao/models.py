from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('O email é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """User model."""

    username = None
    email = models.EmailField(_('email address'), unique=True)
    user_type = models.CharField(max_length=20, choices=[
        ('freelancer', 'Freelancer'),
        ('cliente', 'Cliente'),
    ], default='cliente')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    # Adicionar related_name para resolver os conflitos
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='user_set_custom',  # Nome personalizado para evitar conflito
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='user_set_custom',  # Nome personalizado para evitar conflito
        related_query_name='user',
    )

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()


class AreaAtuacao(models.Model):
    """Área de atuação do freelancer."""
    AREAS_CHOICES = [
        ('design', 'Design'),
        ('programacao', 'Programação'),
        ('marketing', 'Marketing'),
        ('redacao', 'Redação'),
        ('traducao', 'Tradução'),
        ('administracao', 'Administração'),
        ('consultoria', 'Consultoria'),
        ('outros', 'Outros'),
    ]
    
    nome = models.CharField(max_length=50, choices=AREAS_CHOICES)
    
    def __str__(self):
        return self.get_nome_display()


class Perfil(models.Model):
    """Perfil do utilizador."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    foto = models.ImageField(upload_to='perfil/', null=True, blank=True)
    morada = models.CharField(max_length=200, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"


class FreelancerDetalhe(models.Model):
    """Detalhes específicos do freelancer."""
    perfil = models.OneToOneField(Perfil, on_delete=models.CASCADE, related_name='freelancer_detalhe')
    areas_atuacao = models.ManyToManyField(AreaAtuacao)
    area_personalizada = models.CharField(max_length=50, null=True, blank=True)
    
    paypal_email = models.EmailField(blank=True, null=True, verbose_name="Email PayPal")
    paypal_account_verified = models.BooleanField(default=False, verbose_name="Conta PayPal Verificada")
    
    stripe_account_id = models.CharField(max_length=255, blank=True, null=True, verbose_name="ID da Conta Stripe")
    stripe_account_verified = models.BooleanField(default=False, verbose_name="Conta Stripe Verificada")
    
    platform_fee_percentage = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00, 
        verbose_name="Taxa da Plataforma (%)"
    )
    
    def __str__(self):
        return f"Perfil freelancer de {self.perfil.user.get_full_name()}"

class ClienteDetalhe(models.Model):
    """Detalhes específicos do cliente."""
    perfil = models.OneToOneField(Perfil, on_delete=models.CASCADE, related_name='cliente_detalhe')
    empresa = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        return f"Perfil cliente de {self.perfil.user.get_full_name()}"


class Servico(models.Model):
    """Serviço oferecido pelo freelancer."""
    freelancer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servicos')
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    orcamento = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    prazo = models.CharField(max_length=50)  # Ex: "5 dias", "1 semana"
    area = models.ForeignKey(AreaAtuacao, on_delete=models.SET_NULL, null=True, related_name='servicos')
    data_criacao = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)
    # Novo campo para imagem do serviço
    imagem = models.ImageField(upload_to='servicos/', null=True, blank=True)
    
    def __str__(self):
        return self.nome
    
class ServicoImagem(models.Model):
    """Imagens de um serviço."""
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='imagens')
    imagem = models.ImageField(upload_to='servicos/')
    ordem = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['ordem']
        verbose_name = 'Imagem do Serviço'
        verbose_name_plural = 'Imagens dos Serviços'
    
    def __str__(self):
        return f"Imagem {self.id} do serviço {self.servico.nome}"
    

class Pedido(models.Model):
    """Pedido de serviço feito por um cliente."""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceite', 'Aceite'),
        ('rejeitado', 'Rejeitado'),
        ('concluido', 'Concluído'),
        ('cancelado', 'Cancelado'),
    ]
    
    TIPO_SERVICO_CHOICES = [
        ('imediato', 'Imediato'),
        ('agendado', 'Agendado'),
    ]
    
    cliente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pedidos_feitos')
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='pedidos')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    data_pedido = models.DateTimeField(auto_now_add=True)
    comentario = models.TextField(null=True, blank=True)
    
    # Campos para agendamento
    tipo_servico = models.CharField(max_length=20, choices=TIPO_SERVICO_CHOICES, default='imediato')
    data_agendamento = models.DateField(null=True, blank=True)
    hora_agendamento = models.TimeField(null=True, blank=True)
    google_calendar_event_id = models.CharField(max_length=255, null=True, blank=True)
    google_calendar_event_url = models.URLField(max_length=500, null=True, blank=True)  # Novo campo
    
    def __str__(self):
        return f"Pedido de {self.cliente.get_full_name()} para {self.servico.nome}"


class Fatura(models.Model):
    """Fatura gerada após a conclusão de um pedido."""
    pedido = models.OneToOneField(Pedido, on_delete=models.CASCADE, related_name='fatura')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_emissao = models.DateTimeField(auto_now_add=True)
    pago = models.BooleanField(default=False)
    data_pagamento = models.DateTimeField(null=True, blank=True)
    
    # Campos para Stripe
    stripe_payment_intent_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_url = models.CharField(max_length=255, null=True, blank=True)
    stripe_connected_account = models.CharField(max_length=255, null=True, blank=True)
    stripe_application_fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Campos para PayPal
    paypal_payment_id = models.CharField(max_length=255, null=True, blank=True)
    paypal_payment_url = models.CharField(max_length=500, null=True, blank=True)
    paypal_recipient_email = models.EmailField(null=True, blank=True)
    
    metodo_pagamento = models.CharField(max_length=50, choices=[
        ('stripe', 'Cartão de Crédito/Débito'),
        ('multibanco', 'Multibanco'),
        ('transferencia', 'Transferência Bancária'),
        ('paypal', 'PayPal'),
    ], default='stripe')
    
    # Informações de cobrança adicionais
    valor_plataforma = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, 
                                          help_text="Valor cobrado pela plataforma (taxa)")
    valor_freelancer = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                          help_text="Valor líquido para o freelancer")
    
    def __str__(self):
        return f"Fatura {self.id} - {self.pedido.servico.nome}"
    
    def save(self, *args, **kwargs):
        # Calcular os valores da plataforma e do freelancer, se ainda não definidos
        if self.valor and not self.valor_plataforma:
            # Obter a taxa da plataforma do perfil do freelancer
            try:
                freelancer = self.pedido.servico.freelancer
                freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=freelancer)
                platform_fee_percentage = float(freelancer_detalhe.platform_fee_percentage)
                
                # Calcular a taxa e o valor líquido
                self.valor_plataforma = round(float(self.valor) * (platform_fee_percentage / 100), 2)
                self.valor_freelancer = float(self.valor) - float(self.valor_plataforma)
            except (FreelancerDetalhe.DoesNotExist, Exception) as e:
                # Se houver erro, definir valores padrão
                print(f"Erro ao calcular valores da fatura: {str(e)}")
                self.valor_plataforma = 0
                self.valor_freelancer = self.valor
                
        super().save(*args, **kwargs)
    

class Comentario(models.Model):
    TIPO_CHOICES = [
        ('testemunho', 'Testemunho Geral'),
        ('servico', 'Comentário de Serviço'),
    ]
    
    utilizador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comentarios')
    texto = models.TextField()
    data_criacao = models.DateTimeField(auto_now_add=True)
    aprovado = models.BooleanField(default=False)  # Para moderação
    
    # Novos campos
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='testemunho')
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE, related_name='comentarios', null=True, blank=True)
    avaliacao = models.IntegerField(choices=[(1, '1 Estrela'), (2, '2 Estrelas'), (3, '3 Estrelas'), 
                                           (4, '4 Estrelas'), (5, '5 Estrelas')], null=True, blank=True)
    
    class Meta:
        ordering = ['-data_criacao']
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
    
    def __str__(self):
        if self.tipo == 'servico' and self.servico:
            return f'Comentário de {self.utilizador.get_full_name()} sobre {self.servico.nome}'
        return f'Testemunho de {self.utilizador.get_full_name()}'
        
class Notificacao(models.Model):
    TIPOS = [
        ('mensagem', 'Nova Mensagem'),
        ('pedido', 'Novo Pedido'),
        ('aceitacao', 'Pedido Aceite'),
        ('rejeicao', 'Pedido Rejeitado'),
        ('conclusao', 'Serviço Concluído'),
        ('pagamento', 'Pagamento Recebido'),
        ('sistema', 'Notificação do Sistema'),
        ('proposta', 'Nova Proposta'),
    ]
    
    utilizador = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    titulo = models.CharField(max_length=100)
    texto = models.TextField()
    link = models.CharField(max_length=200, blank=True, null=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'
    
    def __str__(self):
        return f"{self.get_tipo_display()} para {self.utilizador.email}"
    

