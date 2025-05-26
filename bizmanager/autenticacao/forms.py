from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from .models import User, Perfil, FreelancerDetalhe, ClienteDetalhe, AreaAtuacao, Servico, Pedido, Comentario

class FreelancerRegistrationForm(UserCreationForm):
    """Formulário de registo para freelancers com validação aprimorada."""
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        label='Nome',
        widget=forms.TextInput(attrs={
            'placeholder': 'O seu nome', 
            'class': 'form-control'
        })
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        label='Apelido',
        widget=forms.TextInput(attrs={
            'placeholder': 'O seu apelido', 
            'class': 'form-control'
        })
    )
    email = forms.EmailField(
        max_length=100, 
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'seu@email.com', 
            'class': 'form-control'
        })
    )
    password1 = forms.CharField(
        label="Palavra-passe",
        widget=forms.PasswordInput(attrs={
            'placeholder': '********', 
            'class': 'form-control'
        }),
        help_text="A palavra-passe deve ter no mínimo 8 caracteres."
    )
    password2 = forms.CharField(
        label="Confirmar palavra-passe",
        widget=forms.PasswordInput(attrs={
            'placeholder': '********', 
            'class': 'form-control'
        })
    )
    bio = forms.CharField(
        widget=forms.Textarea(attrs={
            'placeholder': 'Conte-nos um pouco sobre si e as suas competências', 
            'rows': 4,
            'class': 'form-control'
        }),
        required=False,
        label='Sobre si'
    )
    area = forms.ModelChoiceField(
        queryset=AreaAtuacao.objects.all(),
        empty_label="Selecione a sua área principal",
        required=True,
        label='Área de atuação',
        to_field_name='nome',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    area_personalizada = forms.CharField(
        max_length=50, 
        required=False,
        label='Área personalizada',
        widget=forms.TextInput(attrs={
            'placeholder': 'Digite a sua área de atuação', 
            'class': 'form-control'
        })
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este email já está registado.")
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if not password1:
            raise ValidationError("A palavra-passe é obrigatória.")
        
        if not password2:
            raise ValidationError("A confirmação da palavra-passe é obrigatória.")
        
        if password1 != password2:
            raise ValidationError("As palavras-passe não coincidem.")
        
        if len(password1) < 8:
            raise ValidationError("A palavra-passe deve ter no mínimo 8 caracteres.")
        
        if not any(char.isdigit() for char in password1):
            raise ValidationError("A palavra-passe deve conter pelo menos um número.")
        
        if not any(char.isalpha() for char in password1):
            raise ValidationError("A palavra-passe deve conter pelo menos uma letra.")
        
        return password2

    def clean(self):
        cleaned_data = super().clean()
        
        area = cleaned_data.get('area')
        area_personalizada = cleaned_data.get('area_personalizada', '')
        
        if area and area.nome == 'outros' and not area_personalizada:
            self.add_error('area_personalizada', 'Por favor, especifique a sua área de atuação.')
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'freelancer'
        
        if commit:
            user.save()
            
            perfil = Perfil.objects.create(
                user=user,
                bio=self.cleaned_data.get('bio', '')
            )
            
            area_nome = self.cleaned_data.get('area')
            area = AreaAtuacao.objects.get(nome=area_nome)
            
            freelancer_detalhe = FreelancerDetalhe.objects.create(
                perfil=perfil,
                area_personalizada=self.cleaned_data.get('area_personalizada') if area_nome == 'outros' else None
            )
            
            freelancer_detalhe.areas_atuacao.add(area)
        
        return user


class ClienteRegistrationForm(UserCreationForm):
    """Formulário de registo para clientes."""
    first_name = forms.CharField(
        max_length=30, 
        required=True, 
        label='Nome',
        widget=forms.TextInput(attrs={'placeholder': 'O seu nome'})
    )
    last_name = forms.CharField(
        max_length=30, 
        required=True,
        label='Apelido',
        widget=forms.TextInput(attrs={'placeholder': 'O seu apelido'})
    )
    email = forms.EmailField(
        max_length=100, 
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={'placeholder': 'seu@email.com'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '********'}),
        label="Palavra-passe",
        required=True
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '********'}),
        label="Confirmar palavra-passe",
        required=True
    )

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'password1', 'password2')

    def clean_email(self):
        """Validar se o email já existe."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este email já está registado.")
        return email

    def clean_password2(self):
        """Validar se as palavras-passe coincidem e têm requisitos mínimos."""
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        
        if not password1:
            raise ValidationError("A palavra-passe é obrigatória.")
        
        if not password2:
            raise ValidationError("A confirmação da palavra-passe é obrigatória.")
        
        if password1 != password2:
            raise ValidationError("As palavras-passe não coincidem.")
        
        # Validações de força de palavra-passe
        if len(password1) < 8:
            raise ValidationError("A palavra-passe deve ter no mínimo 8 caracteres.")
        
        # Verificar se a palavra-passe contém letras e números
        if not any(char.isdigit() for char in password1):
            raise ValidationError("A palavra-passe deve conter pelo menos um número.")
        
        if not any(char.isalpha() for char in password1):
            raise ValidationError("A palavra-passe deve conter pelo menos uma letra.")
        
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'cliente'
        if commit:
            user.save()
            
            # Criar perfil
            Perfil.objects.create(user=user)
            
            # Criar detalhes de cliente
            ClienteDetalhe.objects.create(perfil=user.perfil)
            
        return user

class PerfilForm(forms.ModelForm):
    """Formulário para atualização do perfil base."""
    class Meta:
        model = Perfil
        fields = ['foto', 'morada', 'bio']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = False


class FreelancerDetalheForm(forms.ModelForm):
    """Formulário para atualização dos detalhes do freelancer."""
    class Meta:
        model = FreelancerDetalhe
        fields = ['area_personalizada']


class ClienteDetalheForm(forms.ModelForm):
    """Formulário para atualização dos detalhes do cliente."""
    class Meta:
        model = ClienteDetalhe
        fields = ['empresa']


class ServicoForm(forms.ModelForm):
    """Formulário para criação/edição de serviços."""
    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'orcamento', 'prazo', 'area', 'imagem']
        widgets = {
            'nome': forms.TextInput(attrs={'placeholder': 'Nome do serviço'}),
            'descricao': forms.Textarea(attrs={'placeholder': 'Descrição detalhada do serviço', 'rows': 4}),
            'orcamento': forms.NumberInput(attrs={'placeholder': '0.00', 'min': '0', 'step': '0.01'}),
            'prazo': forms.TextInput(attrs={'placeholder': 'Ex: 5 dias, 1 semana...'}),
            'imagem': forms.FileInput(attrs={'class': 'form-control'}),
        }


class PedidoForm(forms.ModelForm):
    """Formulário para criação de um pedido."""
    class Meta:
        model = Pedido
        fields = ['comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={
                'placeholder': 'Descreva o que precisa...',
                'rows': 4,
                'class': 'form-control'
            }),
        }


class MetodoPagamentoForm(forms.Form):
    """Formulário para escolher o método de pagamento."""
    metodo = forms.ChoiceField(
        choices=[
            ('stripe', 'Cartão de Crédito/Débito'),
            ('multibanco', 'Multibanco'),
            ('transferencia', 'Transferência Bancária'),
            ('paypal', 'PayPal'),
        ],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
        initial='stripe',
        required=True,
        label="Método de Pagamento"
    )

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto', 'avaliacao']
        widgets = {
            'texto': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4, 
                'placeholder': 'Deixa aqui o teu comentário sobre este serviço...',
                'required': True
            }),
            'avaliacao': forms.HiddenInput()  # Campo escondido controlado pelo JavaScript
        }
    
    def __init__(self, *args, tipo='servico', **kwargs):
        super().__init__(*args, **kwargs)
        self.tipo = tipo
        
        # Para comentários de serviços, a avaliação é obrigatória
        if tipo == 'servico':
            self.fields['avaliacao'].required = True
        elif tipo == 'testemunho':
            # Para testemunhos, remover o campo avaliação
            self.fields.pop('avaliacao', None)
    
    def clean_avaliacao(self):
        """Validar se a avaliação está entre 1 e 5"""
        avaliacao = self.cleaned_data.get('avaliacao')
        
        if self.tipo == 'servico':
            if not avaliacao:
                raise ValidationError("Por favor, seleciona uma avaliação de 1 a 5 estrelas.")
            
            if avaliacao not in [1, 2, 3, 4, 5]:
                raise ValidationError("A avaliação deve ser entre 1 e 5 estrelas.")
        
        return avaliacao
    
    def clean_texto(self):
        """Validar se o texto não está vazio"""
        texto = self.cleaned_data.get('texto')
        
        if not texto or not texto.strip():
            raise ValidationError("Por favor, escreve um comentário.")
        
        if len(texto.strip()) < 10:
            raise ValidationError("O comentário deve ter pelo menos 10 caracteres.")
        
        return texto.strip()
    
class ClienteFilterForm(forms.Form):
    """Formulário para filtrar clientes com base em diferentes critérios."""
    search = forms.CharField(
        required=False, 
        label="Pesquisar",
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome ou email', 
            'class': 'form-control'
        })
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Todos'), ('ativo', 'Ativos'), ('inativo', 'Inativos')],
        required=False,
        label="Estado",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    ultimo_servico = forms.ChoiceField(
        choices=[
            ('', 'Todos'),
            ('30', 'Últimos 30 dias'),
            ('90', 'Últimos 90 dias'),
            ('180', 'Últimos 6 meses'),
            ('365', 'Último ano'),
            ('inactive', 'Inativos > 6 meses')
        ],
        required=False,
        label="Última contratação",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    servico_tipo = forms.ModelChoiceField(
        queryset=AreaAtuacao.objects.all(),
        required=False,
        empty_label="Todos os serviços",
        label="Tipo de Serviço",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    ordenar_por = forms.ChoiceField(
        choices=[
            ('nome', 'Nome (A-Z)'),
            ('nome_desc', 'Nome (Z-A)'),
            ('data_registo', 'Data de Registo (Antiga-Nova)'),
            ('data_registo_desc', 'Data de Registo (Nova-Antiga)'),
            ('ultima_compra', 'Última Compra (Antiga-Nova)'),
            ('ultima_compra_desc', 'Última Compra (Nova-Antiga)')
        ],
        required=False,
        initial='nome',
        label="Ordenar por",
        widget=forms.Select(attrs={'class': 'form-select'})
    )