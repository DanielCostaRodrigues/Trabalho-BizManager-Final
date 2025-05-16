from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.db import transaction
from django.db.models import Sum, Count, Q, F, ExpressionWrapper, DecimalField
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.template.exceptions import TemplateDoesNotExist
from django.core.paginator import Paginator
from django.urls import reverse
from django.conf import settings
from django.db.models import Q, Sum, Max
from django.core.paginator import Paginator
import json
import datetime
import stripe
from .models import (
    AreaAtuacao, Servico, Pedido, ServicoImagem, User, Perfil,
    FreelancerDetalhe, ClienteDetalhe, Fatura,
    Comentario, Notificacao
)
from .forms import (
    ClienteFilterForm, FreelancerRegistrationForm, ClienteRegistrationForm, PerfilForm,
    FreelancerDetalheForm, ClienteDetalheForm, ServicoForm, PedidoForm,
    MetodoPagamentoForm, ComentarioForm
)
from .google_calendar import (
    get_google_auth_url, handle_google_callback, add_pedido_to_calendar
)
from .stripe_service import StripeService

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Notificacao
from .utils import (
    notificar_novo_pedido, notificar_pedido_aceite, 
    notificar_pedido_rejeitado, notificar_servico_concluido
)

def criar_notificacao(utilizador, tipo, titulo, texto, link=None):
    """
    Cria uma nova notificação para o utilizador.
    
    Args:
        utilizador: Utilizador que receberá a notificação
        tipo: Tipo de notificação (ex: 'pedido', 'fatura', 'sistema')
        titulo: Título da notificação
        texto: Texto descritivo da notificação
        link: Link opcional para onde a notificação deve direcionar
    """
    notificacao = Notificacao.objects.create(
        utilizador=utilizador,
        tipo=tipo,
        titulo=titulo,
        texto=texto,
        link=link
    )
    return notificacao

def home(request):
    """Página inicial do site."""
    # Tente buscar serviços em destaque e comentários
    try:
        servicos_destaque = Servico.objects.filter(ativo=True).order_by('-data_criacao')[:6]
        comentarios = Comentario.objects.filter(tipo='testemunho', aprovado=True).order_by('-data_criacao')[:3]
    except:
        servicos_destaque = []
        comentarios = []
    
    # Processar o formulário de comentário
    form = ComentarioForm(tipo='testemunho')
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = ComentarioForm(request.POST, tipo='testemunho')
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.utilizador = request.user
            comentario.tipo = 'testemunho'
            comentario.save()
            messages.success(request, "O teu testemunho foi enviado com sucesso e será publicado após moderação.")
            return redirect('home')
    
    context = {
        'servicos_destaque': servicos_destaque,
        'comentarios': comentarios,
        'comentario_form': form
    }
    
    return render(request, 'autenticacao/home.html', context)

def escolher_conta(request):
    """Página para escolher o tipo de conta para registo."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'autenticacao/escolher_conta.html')


def registo_freelancer(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Garantir que as áreas de atuação existam
    if AreaAtuacao.objects.count() == 0:
        areas = [
            ('design', 'Design'),
            ('programacao', 'Programação'),
            ('marketing', 'Marketing'),
            ('redacao', 'Redação'),
            ('traducao', 'Tradução'),
            ('administracao', 'Administração'),
            ('consultoria', 'Consultoria'),
            ('outros', 'Outros'),
        ]
        for codigo, nome in areas:
            AreaAtuacao.objects.create(nome=codigo)
    
    if request.method == 'POST':
        form = FreelancerRegistrationForm(request.POST)
        
        print("\n--- DADOS DO POST ---")
        for key, value in request.POST.items():
            print(f"{key}: {value}")
        
        print("\n--- VERIFICANDO VALIDADE DO FORMULÁRIO ---")
        print("Form is_valid():", form.is_valid())
        
        if not form.is_valid():
            print("\n--- ERROS DETALHADOS DO FORMULÁRIO ---")
            print("Erros globais:", form.non_field_errors())
            for field, errors in form.errors.items():
                print(f"Campo '{field}': {errors}")
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Criar o utilizador
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password1'],  # Mudança aqui
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type='freelancer'
                    )
                    
                    # Criar perfil
                    perfil = Perfil.objects.create(
                        user=user,
                        bio=form.cleaned_data.get('bio', '')
                    )
                    
                    # Obter área de atuação
                    area = form.cleaned_data.get('area')
                    
                    # Criar detalhes de freelancer
                    freelancer_detalhe = FreelancerDetalhe.objects.create(
                        perfil=perfil,
                        area_personalizada=form.cleaned_data.get('area_personalizada', '') if area and area.nome == 'outros' else None
                    )
                    
                    # Adicionar área de atuação
                    if area:
                        freelancer_detalhe.areas_atuacao.add(area)
                    
                    # Fazer login do utilizador
                    login(request, user)
                    
                    messages.success(request, "Conta criada com sucesso! Complete o seu perfil.")
                    return redirect('perfil')
            except Exception as e:
                import traceback
                print(f"Erro detalhado: {traceback.format_exc()}")
                messages.error(request, f"Erro ao criar conta: {str(e)}")
        else:
            # Exibir erros mais claramente para o utilizador
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro no campo {field}: {error}")
    else:
        form = FreelancerRegistrationForm()
    
    return render(request, 'autenticacao/registo_freelancer.html', {'form': form})


def registo_cliente(request):
    """
    View para registo de clientes.
    Processa o formulário e cria o utilizador, perfil e detalhes específicos.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        form = ClienteRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Criar o utilizador
                    user = User.objects.create_user(
                        email=form.cleaned_data['email'],
                        password=form.cleaned_data['password1'],  # Mudança aqui
                        first_name=form.cleaned_data['first_name'],
                        last_name=form.cleaned_data['last_name'],
                        user_type='cliente'
                    )
                    
                    # Criar perfil
                    Perfil.objects.create(user=user)
                    
                    # Criar detalhes de cliente
                    ClienteDetalhe.objects.create(perfil=user.perfil)
                    
                    # Fazer login do utilizador
                    login(request, user)
                    
                    messages.success(request, "Conta criada com sucesso! Complete o seu perfil.")
                    return redirect('perfil')
            except Exception as e:
                messages.error(request, f"Erro ao criar conta: {str(e)}")
        else:
            # Exibir erros mais claramente para o utilizador
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"Erro no campo {field}: {error}")
    else:
        form = ClienteRegistrationForm()
    
    return render(request, 'autenticacao/registo_cliente.html', {'form': form})


def login_view(request):
    """Login de utilizadores."""
    if request.user.is_authenticated:
        return redirect('dashboard')
        
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, email=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Bem-vindo de volta, {user.get_full_name()}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Email ou palavra-passe incorretos.")
    
    return render(request, 'autenticacao/login.html')


@login_required
def logout_view(request):
    """Logout de utilizadores."""
    logout(request)
    messages.success(request, "Logout realizado com sucesso.")
    return redirect('login')


@login_required
def dashboard(request):
    """Dashboard principal do utilizador."""
    
    user = request.user
    context = {
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    # Obter data atual para cálculos
    hoje = timezone.now().date()
    inicio_mes_atual = hoje.replace(day=1)
    
    # Obter os últimos 8 meses para o gráfico
    meses = []
    dados_faturacao = []
    
    for i in range(7, -1, -1):
        # Calcular o mês (atual - i)
        data_mes = (hoje.replace(day=1) - datetime.timedelta(days=i*30)).replace(day=1)
        proximo_mes = (data_mes.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
        
        meses.append(data_mes.strftime("%b"))  # Abreviação do mês
        
        if user.user_type == 'freelancer':
            # Converter datas para datetime com timezone
            data_mes_aware = timezone.make_aware(datetime.datetime.combine(data_mes, datetime.time.min))
            proximo_mes_aware = timezone.make_aware(datetime.datetime.combine(proximo_mes, datetime.time.min))
            
            # Soma das faturas pagas naquele mês
            faturacao_mes = Fatura.objects.filter(
                pedido__servico__freelancer=user,
                pago=True,
                data_pagamento__gte=data_mes_aware,
                data_pagamento__lt=proximo_mes_aware
            ).aggregate(
                total=Sum('valor', default=0)
            )['total'] or 0
        else:
            # Converter datas para datetime com timezone
            data_mes_aware = timezone.make_aware(datetime.datetime.combine(data_mes, datetime.time.min))
            proximo_mes_aware = timezone.make_aware(datetime.datetime.combine(proximo_mes, datetime.time.min))
            
            # Para clientes, quanto gastou em faturas naquele mês
            faturacao_mes = Fatura.objects.filter(
                pedido__cliente=user,
                pago=True,
                data_pagamento__gte=data_mes_aware,
                data_pagamento__lt=proximo_mes_aware
            ).aggregate(
                total=Sum('valor', default=0)
            )['total'] or 0
            
        dados_faturacao.append(float(faturacao_mes))
    
    # Converter listas para JSON para usar no JavaScript
    context['meses'] = json.dumps(meses)
    context['dados_faturacao'] = json.dumps(dados_faturacao)
    
   
    if user.user_type == 'freelancer':
     
        
        # Total faturado (todas as faturas pagas)
        total_faturado = Fatura.objects.filter(
            pedido__servico__freelancer=user,
            pago=True
        ).aggregate(
            total=Sum('valor', default=0)
        )['total'] or 0
        context['total_faturado'] = total_faturado
        
        # Média mensal dos últimos 6 meses
        seis_meses_atras = hoje - datetime.timedelta(days=180)
        # Converter para datetime com timezone
        seis_meses_atras_aware = timezone.make_aware(datetime.datetime.combine(seis_meses_atras, datetime.time.min))
        
        faturas_6_meses = Fatura.objects.filter(
            pedido__servico__freelancer=user,
            pago=True,
            data_pagamento__gte=seis_meses_atras_aware
        ).aggregate(
            total=Sum('valor', default=0)
        )['total'] or 0
        
        # Evitar divisão por zero
        if faturas_6_meses > 0:
            media_mensal = float(faturas_6_meses) / 6
        else:
            media_mensal = 0
        context['media_mensal'] = round(media_mensal, 2) 
        
        # Total de serviços ativos
        context['total_servicos'] = Servico.objects.filter(
            freelancer=user,
            ativo=True
        ).count()
        
        # Total de pedidos recebidos
        context['total_pedidos'] = Pedido.objects.filter(
            servico__freelancer=user
        ).count()
        
        # Pedidos pendentes
        context['pedidos_pendentes'] = Pedido.objects.filter(
            servico__freelancer=user,
            status='pendente'
        ).order_by('-data_pedido')
        
        # Principais clientes que fizeram pedidos
        clientes_destaque = User.objects.filter(
            user_type='cliente',
            pedidos_feitos__servico__freelancer=user
        ).annotate(
            num_pedidos=Count('pedidos_feitos')
        ).order_by('-num_pedidos')[:3]
        
        # Formatar dados para o template
        context['clientes_destaque'] = [
            {
                'nome': cliente.get_full_name(),
                'descricao': f"{cliente.num_pedidos} pedidos realizados",
                'id': cliente.id
            }
            for cliente in clientes_destaque
        ]
        
        # Serviços mais solicitados
        servicos_destaque = Servico.objects.filter(
            freelancer=user
        ).annotate(
            num_pedidos=Count('pedidos')
        ).order_by('-num_pedidos')[:3]
        
        # Formatar dados para o template
        context['servicos_destaque'] = [
            {
                'nome': servico.nome,
                'descricao': f"{servico.num_pedidos} pedidos recebidos",
                'id': servico.id
            }
            for servico in servicos_destaque
        ]
        
        # Faturas recentes
        context['faturas_recentes'] = Fatura.objects.filter(
            pedido__servico__freelancer=user
        ).order_by('-data_emissao')[:5]
        
    elif user.user_type == 'cliente':
        # Calcular estatísticas para clientes
        
        # Total gasto (todas as faturas pagas)
        total_gasto = Fatura.objects.filter(
            pedido__cliente=user,
            pago=True
        ).aggregate(
            total=Sum('valor', default=0)
        )['total'] or 0
        context['total_gasto'] = total_gasto
        
        # Total de pedidos feitos
        context['total_pedidos'] = Pedido.objects.filter(
            cliente=user
        ).count()
        
        # Pedidos aceites
        context['pedidos_aceites'] = Pedido.objects.filter(
            cliente=user,
            status='aceite'
        ).count()
        
        # Para clientes, mostrar serviços recentes e seus pedidos
        context['servicos_recentes'] = Servico.objects.filter(
            ativo=True
        ).order_by('-data_criacao')[:6]
        
        context['pedidos_feitos'] = Pedido.objects.filter(
            cliente=user
        ).order_by('-data_pedido')
    
    return render(request, 'autenticacao/dashboard.html', context)

@login_required
def perfil(request):
    """Visualização e edição do perfil do utilizador."""
    user = request.user
    
    # Tente encontrar o perfil ou crie um se não existir
    try:
        perfil = Perfil.objects.get(user=user)
    except Perfil.DoesNotExist:
        # Criar perfil
        perfil = Perfil.objects.create(user=user)
        
        # Criar detalhes específicos com base no tipo de utilizador
        if user.user_type == 'freelancer':
            FreelancerDetalhe.objects.create(perfil=perfil)
        elif user.user_type == 'cliente':
            ClienteDetalhe.objects.create(perfil=perfil)
    
    # Verificar se o utilizador se autenticou com alguma rede social
    has_social_auth = False
    try:
        from social_django.models import UserSocialAuth
        has_social_auth = UserSocialAuth.objects.filter(user=user).exists()
    except ImportError:
        # Se o social_django não estiver disponível, assume que não há auth social
        pass
    
    if request.method == 'POST':
        # Verificar se há dados para alteração de palavra-passe
        senha_atual = request.POST.get('senha_atual')
        nova_senha = request.POST.get('nova_senha')
        confirmar_senha = request.POST.get('confirmar_senha')
        
        # Processar alteração de palavra-passe se os campos forem preenchidos e não for auth social
        if not has_social_auth and senha_atual and nova_senha and confirmar_senha:
            # Verificar se a palavra-passe atual está correta
            if user.check_password(senha_atual):
                # Verificar se as novas palavras-passe coincidem
                if nova_senha == confirmar_senha:
                    # Verificar requisitos mínimos da palavra-passe
                    if len(nova_senha) >= 8:
                        # Alterar a palavra-passe
                        user.set_password(nova_senha)
                        user.save()
                        
                        # Atualizar a sessão para manter o utilizador autenticado
                        from django.contrib.auth import update_session_auth_hash
                        update_session_auth_hash(request, user)
                        
                        messages.success(request, "Palavra-passe alterada com sucesso!")
                    else:
                        messages.error(request, "A nova palavra-passe deve ter pelo menos 8 caracteres.")
                else:
                    messages.error(request, "As novas palavras-passe não coincidem.")
            else:
                messages.error(request, "Palavra-passe atual incorreta.")
        
        # Atualizar informações básicas
        user.first_name = request.POST.get('nome')
        user.last_name = request.POST.get('sobrenome')
        user.email = request.POST.get('email')
        user.save()
        
        # Atualizar o perfil
        perfil.morada = request.POST.get('morada')
        perfil.bio = request.POST.get('bio', '')
        
        # Upload da foto
        if 'foto' in request.FILES:
            perfil.foto = request.FILES['foto']
        
        perfil.save()
        
        # Atualizar dados específicos por tipo de utilizador
        if user.user_type == 'cliente' and hasattr(perfil, 'cliente_detalhe'):
            perfil.cliente_detalhe.empresa = request.POST.get('empresa', '')
            perfil.cliente_detalhe.save()
        
        messages.success(request, "Perfil atualizado com sucesso!")
        return redirect('perfil')
    
    context = {
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'perfil': perfil,
        'has_social_auth': has_social_auth, 
    }
    
    try:
        return render(request, 'perfil.html', context)
    except TemplateDoesNotExist:
        try:
            return render(request, 'autenticacao/perfil.html', context)
        except TemplateDoesNotExist:
            return render(request, 'autenticacao/autenticacao/perfil.html', context)

@login_required
def servicos(request):
    """Lista de serviços disponíveis."""
    user = request.user
    
    if user.user_type == 'freelancer':
        servicos_list = Servico.objects.filter(freelancer=user).order_by('-data_criacao')
        
        # Adicionar paginação
        paginator = Paginator(servicos_list, 6)  
        page = request.GET.get('page')
        servicos = paginator.get_page(page)
        
        context = {
            'servicos': servicos,  # Objeto paginado
            'nome_completo': user.get_full_name(),
            'user_type': user.user_type,
        }
        return render(request, 'autenticacao/servicos_freelancer.html', context)
    else:
        # Obter parâmetros de pesquisa e filtro
        query = request.GET.get('q', '')
        area_id = request.GET.get('area', '')
        preco_max = request.GET.get('preco_max', '')
        ordem = request.GET.get('ordem', 'recentes')
        
        # Para clientes, mostrar todos os serviços ativos
        servicos_list = Servico.objects.filter(ativo=True)
        
        # Aplicar busca textual se houver
        if query:
            servicos_list = servicos_list.filter(
                Q(nome__icontains=query) | 
                Q(descricao__icontains=query)
            )
        
        # Filtrar por área se especificado
        if area_id:
            try:
                servicos_list = servicos_list.filter(area_id=int(area_id))
            except ValueError:
                pass  # Ignora se o id não for um número válido
        
        # Filtrar por preço máximo se especificado
        if preco_max:
            try:
                servicos_list = servicos_list.filter(orcamento__lte=float(preco_max))
            except ValueError:
                pass  # Ignora se o preço não for um número válido
        
        # Aplicar ordenação
        if ordem == 'preco_asc':
            servicos_list = servicos_list.order_by('orcamento')
        elif ordem == 'preco_desc':
            servicos_list = servicos_list.order_by('-orcamento')
        else:  # Default: recentes
            servicos_list = servicos_list.order_by('-data_criacao')
        
        # Adicionar paginação para clientes também
        paginator = Paginator(servicos_list, 6)  # 6 serviços por página
        page = request.GET.get('page')
        servicos = paginator.get_page(page)
        
        # Obter áreas para filtros
        areas = AreaAtuacao.objects.all()
        
        context = {
            'servicos': servicos,  # Agora é um objeto paginado
            'nome_completo': user.get_full_name(),
            'user_type': user.user_type,
            'areas': areas,
            'query': query,
            'preco_max': preco_max,
            'ordem': ordem
        }
        return render(request, 'autenticacao/servicos_cliente.html', context)
    
@login_required
def criar_servico(request):
    """Criação de novos serviços (apenas para freelancers)."""
    user = request.user
    
    if user.user_type != 'freelancer':
        messages.error(request, "Apenas freelancers podem criar serviços.")
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = ServicoForm(request.POST, request.FILES)
        if form.is_valid():
            # Criar o serviço
            servico = form.save(commit=False)
            servico.freelancer = user
            servico.save()
            
            # Processar múltiplas imagens
            imagens = request.FILES.getlist('imagens')
            
            # Manter a imagem principal (compatibilidade)
            if 'imagem' in request.FILES:
                imagem_principal = request.FILES['imagem']
                ServicoImagem.objects.create(
                    servico=servico,
                    imagem=imagem_principal,
                    ordem=0  # A primeira imagem é a principal
                )
            
            # Adicionar as imagens adicionais
            for ordem, imagem in enumerate(imagens, start=1):  # Começar do 1 pois a principal é 0
                ServicoImagem.objects.create(
                    servico=servico,
                    imagem=imagem,
                    ordem=ordem
                )
            
            messages.success(request, "Serviço criado com sucesso!")
            return redirect('servicos')
    else:
        form = ServicoForm()
    
    context = {
        'form': form,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    return render(request, 'autenticacao/criar_servico.html', context)


@login_required
def editar_servico(request, servico_id):
    """Edição de serviços existentes."""
    user = request.user
    servico = get_object_or_404(Servico, id=servico_id)
    
    # Verificar se o utilizador é o dono do serviço
    if servico.freelancer != user:
        return HttpResponseForbidden("Não tem permissão para editar este serviço.")
    
    # Obter imagens existentes
    imagens_existentes = ServicoImagem.objects.filter(servico=servico).order_by('ordem')
    
    if request.method == 'POST':
        form = ServicoForm(request.POST, request.FILES, instance=servico)
        if form.is_valid():
            servico = form.save(commit=False)
            servico.ativo = 'ativo' in request.POST
            servico.save()
            
            # Processar múltiplas imagens
            imagens = request.FILES.getlist('imagens')
            
            # Processar imagem principal (compatibilidade)
            if 'imagem' in request.FILES:
                imagem_principal = request.FILES['imagem']
                
                # Verificar se já existe uma imagem principal
                try:
                    img_principal = ServicoImagem.objects.get(servico=servico, ordem=0)
                    img_principal.imagem = imagem_principal
                    img_principal.save()
                except ServicoImagem.DoesNotExist:
                    ServicoImagem.objects.create(
                        servico=servico,
                        imagem=imagem_principal,
                        ordem=0
                    )
            
            # Adicionar as novas imagens
            ordem_maxima = imagens_existentes.aggregate(Max('ordem'))['ordem__max'] or 0
            for ordem, imagem in enumerate(imagens, start=ordem_maxima+1):
                ServicoImagem.objects.create(
                    servico=servico,
                    imagem=imagem,
                    ordem=ordem
                )
            
            # Processar imagens para remover
            imagens_para_remover = request.POST.getlist('remover_imagem')
            if imagens_para_remover:
                ServicoImagem.objects.filter(id__in=imagens_para_remover).delete()
            
            messages.success(request, "Serviço atualizado com sucesso!")
            return redirect('servicos')
    else:
        form = ServicoForm(instance=servico)
    
    context = {
        'form': form,
        'servico': servico,
        'imagens_existentes': imagens_existentes,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    return render(request, 'autenticacao/editar_servico.html', context)

@login_required
def remover_imagem_servico(request, imagem_id):
    """Remover uma imagem específica de um serviço."""
    user = request.user
    imagem = get_object_or_404(ServicoImagem, id=imagem_id)
    servico = imagem.servico
    
    # Verificar se o utilizador é o dono do serviço
    if servico.freelancer != user:
        return HttpResponseForbidden("Não tem permissão para modificar este serviço.")
    
    if request.method == 'POST':
        imagem.delete()
        messages.success(request, "Imagem removida com sucesso!")
        
    return redirect('editar_servico', servico_id=servico.id)

@login_required
def ver_servico(request, servico_id):
    """Visualização detalhada de um serviço."""
    user = request.user
    servico = get_object_or_404(Servico, id=servico_id)
    
    # Verificar se o serviço está ativo ou se o utilizador é o dono
    if not servico.ativo and servico.freelancer != user:
        messages.error(request, "Este serviço não está mais disponível.")
        return redirect('servicos')
    
    context = {
        'servico': servico,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    # Se o utilizador for cliente, verificar se já solicitou este serviço
    if user.user_type == 'cliente':
        pedido_existente = Pedido.objects.filter(
            cliente=user,
            servico=servico
        ).exists()
        context['pedido_existente'] = pedido_existente
    
    return render(request, 'autenticacao/ver_servico.html', context)

@login_required
def solicitar_servico(request, servico_id):
    """Solicitar um serviço (apenas para clientes)."""
    request.session['calendar_return_url'] = request.build_absolute_uri()
    user = request.user
    
    if user.user_type != 'cliente':
        messages.error(request, "Apenas clientes podem solicitar serviços.")
        return redirect('dashboard')
    
    servico = get_object_or_404(Servico, id=servico_id, ativo=True)
    
    # Verificar se já existe um pedido para este serviço
    pedido_existente = Pedido.objects.filter(
        cliente=user,
        servico=servico,
        status__in=['pendente', 'aceite']
    ).exists()
    
    if pedido_existente:
        messages.warning(request, "Já solicitou este serviço e aguarda resposta.")
        return redirect('ver_servico_publico', servico_id=servico.id)
    
    if request.method == 'POST':
        form = PedidoForm(request.POST)
        if form.is_valid():
            pedido = form.save(commit=False)
            pedido.cliente = user
            pedido.servico = servico
            
            # Processar os novos campos de agendamento
            pedido.tipo_servico = request.POST.get('tipo_servico', 'imediato')
            
            if pedido.tipo_servico == 'agendado':
                try:
                    # Obter e validar dados de agendamento
                    data_str = request.POST.get('data_agendamento')
                    hora_str = request.POST.get('hora_agendamento')
                    
                    if not data_str or not hora_str:
                        raise ValueError("Data e hora são obrigatórias para serviços agendados.")
                    
                    # Converter strings para objetos de data e hora
                    from datetime import datetime
                    
                    # Converter a data de string para objeto date
                    from datetime import datetime, date
                    year, month, day = map(int, data_str.split('-'))
                    pedido.data_agendamento = date(year, month, day)
                    
                    # Converter a hora de string para objeto time
                    from datetime import time
                    hour, minute = map(int, hora_str.split(':'))
                    pedido.hora_agendamento = time(hour, minute)
                    
                    # Verificar se houve solicitação para sincronizar com o Google Calendar
                    sync_google_calendar = request.POST.get('sync_google_calendar') == 'on'
                    if sync_google_calendar:
                        pedido.google_calendar_sync_requested = True
                        
                except (ValueError, TypeError) as e:
                    messages.error(request, f"Erro no agendamento: {str(e)}")
                    return render(request, 'autenticacao/solicitar_servico.html', {
                        'form': form,
                        'servico': servico,
                        'nome_completo': user.get_full_name(),
                        'user_type': user.user_type,
                        'hoje': timezone.now().date(),
                        'google_calendar_connected': 'google_calendar_tokens' in request.session and user.id in request.session.get('google_calendar_tokens', [])
                    })
            
            # Guardar o pedido
            pedido.save()
            
            # Notificar o cliente de que o pedido foi enviado
            criar_notificacao(
                utilizador=user,
                tipo='pedido',
                titulo='Pedido enviado com sucesso',
                texto=f'O teu pedido para o serviço "{servico.nome}" foi enviado e aguarda aprovação do freelancer.',
                link=reverse('ver_pedido', args=[pedido.id])
            )

            # Notificar o freelancer de que recebeu um novo pedido
            criar_notificacao(
                utilizador=servico.freelancer,
                tipo='pedido',
                titulo='Novo pedido recebido',
                texto=f'{user.get_full_name()} solicitou o teu serviço "{servico.nome}".',
                link=reverse('ver_pedido', args=[pedido.id])
            )
            
            # Se for para sincronizar com o Google Calendar, fazemos isso após guardar o pedido
            if pedido.tipo_servico == 'agendado' and getattr(pedido, 'google_calendar_sync_requested', False):
                try:
                    event_id, event_url = add_pedido_to_calendar(pedido)
                    if event_id:
                        pedido.google_calendar_event_id = event_id
                        pedido.google_calendar_event_url = event_url
                        pedido.save(update_fields=['google_calendar_event_id', 'google_calendar_event_url'])
                        messages.success(request, "Pedido enviado com sucesso e adicionado ao Google Calendar!")
                    else:
                        messages.warning(request, "Pedido enviado com sucesso, mas não foi possível adicionar ao Google Calendar.")
                except Exception as e:
                    messages.warning(request, "Pedido enviado, mas ocorreu um erro ao adicionar ao Google Calendar.")
                    print(f"Erro ao sincronizar com Google Calendar: {str(e)}")
            else:
                messages.success(request, "Pedido enviado com sucesso! Aguarde a resposta do freelancer.")
            
            return redirect('pedidos')
    else:
        form = PedidoForm()
    
    from django.utils import timezone
    
    context = {
        'form': form,
        'servico': servico,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'hoje': timezone.now().date(),
        'google_calendar_connected': 'google_calendar_tokens' in request.session and user.id in request.session.get('google_calendar_tokens', [])
    }
    
    return render(request, 'autenticacao/solicitar_servico.html', context)

@login_required
def toggle_servico_status(request, servico_id):
    """Alternar o status (ativo/inativo) de um serviço."""
    user = request.user
    servico = get_object_or_404(Servico, id=servico_id)
    
    if servico.freelancer != user:
        messages.error(request, "Não tem permissão para modificar este serviço.")
        return redirect('servicos')
    
    if request.method == 'POST':
        # Alternar o status do serviço
        servico.ativo = not servico.ativo
        servico.save()
        
        if servico.ativo:
            messages.success(request, "Serviço ativado com sucesso!")
        else:
            messages.success(request, "Serviço desativado com sucesso!")
        
        # Redirecionar para a página de detalhes do serviço
        return redirect('ver_servico', servico_id=servico.id)
    
    # Se não for POST, redirecionar para a página de detalhes
    return redirect('ver_servico', servico_id=servico.id)

def servicos_publicos(request):
    """Página pública de serviços, acessível a todos os visitantes."""
    # Obter parâmetros de busca e filtro
    query = request.GET.get('q', '')
    area_id = request.GET.get('area', '')
    ordem = request.GET.get('ordem', 'recentes')
    
    # Obter serviços ativos
    servicos_list = Servico.objects.filter(ativo=True)
    
    # Aplicar busca textual
    if query:
        servicos_list = servicos_list.filter(
            Q(nome__icontains=query) | 
            Q(descricao__icontains=query)
        )
    
    # Filtrar por área
    if area_id:
        try:
            servicos_list = servicos_list.filter(area_id=int(area_id))
        except ValueError:
            pass  # Ignora se o id não for um número válido
    
    # Aplicar ordenação
    if ordem == 'preco_asc':
        servicos_list = servicos_list.order_by('orcamento')
    elif ordem == 'preco_desc':
        servicos_list = servicos_list.order_by('-orcamento')
    else:  # Default: recentes
        servicos_list = servicos_list.order_by('-data_criacao')
    
    # Paginação
    paginator = Paginator(servicos_list, 9)  # 9 serviços por página
    page = request.GET.get('page')
    servicos = paginator.get_page(page)
    
    # Obter todas as áreas para o filtro
    areas = AreaAtuacao.objects.all()
    
    context = {
        'servicos': servicos,
        'areas': areas,
        'query': query,
    }
    
    return render(request, 'autenticacao/servicos_publicos.html', context)

def ver_servico_publico(request, servico_id):
    """Visualização pública detalhada de um serviço."""
    # Obter o serviço ou retornar 404
    servico = get_object_or_404(Servico, id=servico_id, ativo=True)
    
    # Obter comentários aprovados deste serviço
    comentarios = Comentario.objects.filter(servico=servico, tipo='servico', aprovado=True).order_by('-data_criacao')
    
    # Processar o formulário de comentário
    form = ComentarioForm(tipo='servico')
    
    if request.method == 'POST' and request.user.is_authenticated:
        form = ComentarioForm(request.POST, tipo='servico')
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.servico = servico
            comentario.utilizador = request.user
            comentario.tipo = 'servico'
            comentario.save()
            messages.success(request, "O teu comentário foi enviado com sucesso e será publicado após moderação.")
            return redirect('ver_servico_publico', servico_id=servico.id)
    
    # Contexto básico
    context = {
        'servico': servico,
        'comentarios': comentarios,
        'comentario_form': form
    }
    
    # Se o utilizador estiver autenticado como cliente, verificar se já solicitou este serviço
    if request.user.is_authenticated and request.user.user_type == 'cliente':
        pedido_existente = Pedido.objects.filter(
            cliente=request.user,
            servico=servico
        ).exists()
        context['pedido_existente'] = pedido_existente
    
    # Obter serviços relacionados (mesma área, excluindo este)
    servicos_relacionados = Servico.objects.filter(
        area=servico.area, 
        ativo=True
    ).exclude(id=servico.id).order_by('?')[:4]
    context['servicos_relacionados'] = servicos_relacionados
    
    # Obter outros serviços do mesmo freelancer
    outros_servicos = Servico.objects.filter(
        freelancer=servico.freelancer, 
        ativo=True
    ).exclude(id=servico.id).order_by('-data_criacao')[:5]
    context['outros_servicos'] = outros_servicos
    
    # Estatísticas do freelancer
    context['servicos_count'] = Servico.objects.filter(freelancer=servico.freelancer).count()
    context['projetos_concluidos'] = Pedido.objects.filter(
        servico__freelancer=servico.freelancer, 
        status='concluido'
    ).count()
    
    return render(request, 'autenticacao/ver_servico_publico.html', context)

@login_required
def pedidos(request):
    """Lista de pedidos do utilizador."""
    user = request.user
    
    status_filter = request.GET.get('status')
    
    if user.user_type == 'freelancer':
        pedidos_list = Pedido.objects.filter(
            servico__freelancer=user
        ).order_by('-data_pedido')
    else:
        pedidos_list = Pedido.objects.filter(
            cliente=user
        ).order_by('-data_pedido')
    
    if status_filter and status_filter != 'all':
        pedidos_list = pedidos_list.filter(status=status_filter)
    
    paginator = Paginator(pedidos_list, 6)
    page = request.GET.get('page')
    pedidos = paginator.get_page(page)
    
    context = {
        'pedidos': pedidos,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'status_atual': status_filter or 'all'
    }
    
    return render(request, 'autenticacao/pedidos.html', context)


@login_required
def ver_pedido(request, pedido_id):
    """Visualização detalhada de um pedido."""
    user = request.user
    
    # Verificar se o utilizador tem acesso ao pedido
    if user.user_type == 'freelancer':
        pedido = get_object_or_404(Pedido, id=pedido_id, servico__freelancer=user)
    else:
        pedido = get_object_or_404(Pedido, id=pedido_id, cliente=user)
    
    context = {
        'pedido': pedido,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    return render(request, 'autenticacao/ver_pedido.html', context)


@login_required
def aceitar_pedido(request, pedido_id):
    """Aceitar um pedido (apenas para freelancers)."""
    user = request.user
    
    if user.user_type != 'freelancer':
        return HttpResponseForbidden("Apenas freelancers podem aceitar pedidos.")
    
    pedido = get_object_or_404(Pedido, id=pedido_id, servico__freelancer=user, status='pendente')
    pedido.status = 'aceite'
    pedido.save()
    
    # Notificar o cliente que o pedido foi aceite
    criar_notificacao(
        utilizador=pedido.cliente,
        tipo='pedido',
        titulo='Pedido aceite',
        texto=f'O teu pedido para o serviço "{pedido.servico.nome}" foi aceite por {user.get_full_name()}.',
        link=reverse('ver_pedido', args=[pedido.id])
    )
    
    messages.success(request, "Pedido aceite com sucesso!")
    return redirect('pedidos')

@login_required
def rejeitar_pedido(request, pedido_id):
    """Rejeitar um pedido (apenas para freelancers)."""
    user = request.user
    
    if user.user_type != 'freelancer':
        return HttpResponseForbidden("Apenas freelancers podem rejeitar pedidos.")
    
    pedido = get_object_or_404(Pedido, id=pedido_id, servico__freelancer=user, status='pendente')
    pedido.status = 'rejeitado'
    pedido.save()
    
    # Notificar o cliente que o pedido foi rejeitado
    criar_notificacao(
        utilizador=pedido.cliente,
        tipo='pedido',
        titulo='Pedido rejeitado',
        texto=f'O teu pedido para o serviço "{pedido.servico.nome}" foi rejeitado pelo freelancer.',
        link=reverse('ver_pedido', args=[pedido.id])
    )
    
    messages.success(request, "Pedido rejeitado.")
    return redirect('pedidos')


@login_required
def concluir_pedido(request, pedido_id):
    """Marcar um pedido como concluído (apenas para freelancers)."""
    user = request.user
    
    if user.user_type != 'freelancer':
        return HttpResponseForbidden("Apenas freelancers podem concluir pedidos.")
    
    pedido = get_object_or_404(Pedido, id=pedido_id, servico__freelancer=user, status='aceite')
    pedido.status = 'concluido'
    pedido.save()
    
    # Criar fatura automaticamente
    fatura = Fatura.objects.create(
        pedido=pedido,
        valor=pedido.servico.orcamento
    )
    
    # Notificar o cliente que o pedido foi concluído e a fatura foi gerada
    criar_notificacao(
        utilizador=pedido.cliente,
        tipo='pedido',
        titulo='Pedido concluído',
        texto=f'O teu pedido para o serviço "{pedido.servico.nome}" foi marcado como concluído. Uma fatura foi gerada.',
        link=reverse('ver_fatura', args=[fatura.id])
    )
    
    messages.success(request, "Pedido marcado como concluído e fatura gerada!")
    return redirect('pedidos')

@login_required
def cancelar_pedido(request, pedido_id):
    """Cancelar um pedido (para clientes ou freelancers, dependendo do status)."""
    user = request.user
    
    # Verificar se o utilizador tem acesso ao pedido
    if user.user_type == 'freelancer':
        pedido = get_object_or_404(Pedido, id=pedido_id, servico__freelancer=user)
        # Freelancers só podem cancelar pedidos aceites
        if pedido.status != 'aceite':
            messages.error(request, "Só pode cancelar pedidos que foram aceites.")
            return redirect('pedidos')
        
        # Destinatário da notificação será o cliente
        destinatario = pedido.cliente
        texto_notificacao = f'O teu pedido para o serviço "{pedido.servico.nome}" foi cancelado pelo freelancer.'
    else:
        pedido = get_object_or_404(Pedido, id=pedido_id, cliente=user)
        # Clientes podem cancelar pedidos pendentes ou aceites
        if pedido.status not in ['pendente', 'aceite']:
            messages.error(request, "Só pode cancelar pedidos pendentes ou aceites.")
            return redirect('pedidos')
        
        # Destinatário da notificação será o freelancer
        destinatario = pedido.servico.freelancer
        texto_notificacao = f'O pedido para o serviço "{pedido.servico.nome}" foi cancelado pelo cliente {user.get_full_name()}.'
    
    pedido.status = 'cancelado'
    pedido.save()
    
    # Notificar a outra parte sobre o cancelamento
    criar_notificacao(
        utilizador=destinatario,
        tipo='pedido',
        titulo='Pedido cancelado',
        texto=texto_notificacao,
        link=reverse('ver_pedido', args=[pedido.id])
    )
    
    messages.success(request, "Pedido cancelado com sucesso.")
    return redirect('pedidos')

@login_required
def faturas(request):
    """Lista de faturas do utilizador e configuração de métodos de pagamento para freelancers."""
    user = request.user
    
    # Processar formulários de métodos de pagamento
    if request.method == 'POST' and user.user_type == 'freelancer':
        action = request.POST.get('action')
        
        try:
            freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=user)
            
            if action == 'update_paypal':
                # Atualizar configurações do PayPal
                paypal_email = request.POST.get('paypal_email')
                
                if paypal_email:
                    freelancer_detalhe.paypal_email = paypal_email
                    freelancer_detalhe.paypal_account_verified = True
                    freelancer_detalhe.save()
                    messages.success(request, "Informações de PayPal atualizadas com sucesso!")
                    return redirect('faturas')
                else:
                    messages.error(request, "Email do PayPal é obrigatório.")
                    
            elif action == 'connect_stripe':
                # Iniciar o processo de conexão com o Stripe Connect
                from .stripe_service import StripeService
                
                # Criar uma conta Stripe Connect para o freelancer
                account_id = StripeService.create_connect_account(user.email)
                
                if account_id:
                    # Salvar o ID da conta no perfil do freelancer
                    freelancer_detalhe.stripe_account_id = account_id
                    freelancer_detalhe.save()
                    
                    # Criar um link de onboarding para o freelancer completar o registro
                    refresh_url = request.build_absolute_uri(reverse('faturas') + '?tab=payment-methods')
                    return_url = request.build_absolute_uri(reverse('stripe_connect_callback'))
                    
                    onboarding_url = StripeService.create_account_link(account_id, refresh_url, return_url)
                    
                    if onboarding_url:
                        # Redirecionar o freelancer para o onboarding do Stripe
                        return redirect(onboarding_url)
                    else:
                        messages.error(request, "Erro ao criar link para configuração do Stripe. Tente novamente.")
                else:
                    messages.error(request, "Erro ao conectar com o Stripe. Tente novamente.")
                    
            elif action == 'update_fee':
                # Atualizar a taxa da plataforma
                try:
                    fee_percentage = float(request.POST.get('platform_fee_percentage', 10))
                    
                    # Limitar a taxa entre 5% e 20%
                    if 5 <= fee_percentage <= 20:
                        freelancer_detalhe.platform_fee_percentage = fee_percentage
                        freelancer_detalhe.save()
                        messages.success(request, f"Taxa da plataforma atualizada para {fee_percentage}%.")
                    else:
                        messages.error(request, "A taxa da plataforma deve estar entre 5% e 20%.")
                except ValueError:
                    messages.error(request, "Valor de taxa inválido.")
                    
        except FreelancerDetalhe.DoesNotExist:
            messages.error(request, "Perfil de freelancer não encontrado.")
    
    # Obter as faturas do utilizador
    if user.user_type == 'freelancer':
        # Para freelancers, mostrar faturas de seus serviços
        faturas_list = Fatura.objects.filter(
            pedido__servico__freelancer=user
        ).order_by('-data_emissao')
        
        # Verificar o status da conta Stripe, se existir
        stripe_account_status = None
        try:
            freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=user)
            if freelancer_detalhe.stripe_account_id:
                from .stripe_service import StripeService
                stripe_account_status = StripeService.check_account_status(freelancer_detalhe.stripe_account_id)
                
                # Atualizar o status de verificação se a conta estiver completa
                if stripe_account_status and stripe_account_status.get('is_complete'):
                    freelancer_detalhe.stripe_account_verified = True
                    freelancer_detalhe.save(update_fields=['stripe_account_verified'])
                    
            # Obter faturas pagas para o histórico
            faturas_pagas_list = Fatura.objects.filter(
                pedido__servico__freelancer=user,
                pago=True
            ).order_by('-data_pagamento')
            
            # Paginar histórico de faturas pagas
            paginator_historico = Paginator(faturas_pagas_list, 10)  # 10 por página
            history_page = request.GET.get('history_page')
            faturas_pagas = paginator_historico.get_page(history_page)
            
        except FreelancerDetalhe.DoesNotExist:
            freelancer_detalhe = None
            faturas_pagas = []
            stripe_account_status = None
            
    else:
        # Para clientes, mostrar faturas de seus pedidos
        faturas_list = Fatura.objects.filter(
            pedido__cliente=user
        ).order_by('-data_emissao')
        
        # Clientes não têm estas variáveis
        freelancer_detalhe = None
        faturas_pagas = None
        stripe_account_status = None
    
    # Filtrar por status se especificado
    status_filter = request.GET.get('status')
    if status_filter == 'pagas':
        faturas_list = faturas_list.filter(pago=True)
    elif status_filter == 'pendentes':
        faturas_list = faturas_list.filter(pago=False)
    
    # Adicionar paginação para todas as faturas
    paginator = Paginator(faturas_list, 10)  # 10 faturas por página
    page = request.GET.get('page')
    faturas = paginator.get_page(page)
    
    # Calcular totais para freelancers
    total_faturado = 0
    total_pago = 0
    total_pendente = 0
    
    if user.user_type == 'freelancer':
        total_faturado = faturas_list.aggregate(
            total=Sum('valor', default=0)
        )['total'] or 0
        
        total_pago = faturas_list.filter(pago=True).aggregate(
            total=Sum('valor', default=0)
        )['total'] or 0
        
        total_pendente = faturas_list.filter(pago=False).aggregate(
            total=Sum('valor', default=0)
        )['total'] or 0
    
    context = {
        'faturas': faturas,  # Agora usa o objeto paginado
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'total_faturado': total_faturado,
        'total_pago': total_pago,
        'total_pendente': total_pendente,
        'freelancer_detalhe': freelancer_detalhe,
        'faturas_pagas': faturas_pagas,  # Já está paginado para freelancers
        'stripe_account_status': stripe_account_status
    }
    
    return render(request, 'autenticacao/faturas.html', context)

@login_required
def ver_fatura(request, fatura_id):
    """Visualização detalhada de uma fatura."""
    user = request.user
    
    # Verificar se o utilizador tem acesso à fatura
    if user.user_type == 'freelancer':
        fatura = get_object_or_404(Fatura, id=fatura_id, pedido__servico__freelancer=user)
    else:
        fatura = get_object_or_404(Fatura, id=fatura_id, pedido__cliente=user)
    
    context = {
        'fatura': fatura,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    return render(request, 'autenticacao/ver_fatura.html', context)


@login_required
def marcar_fatura_paga(request, fatura_id):
    """Marcar uma fatura como paga (apenas para clientes)."""
    user = request.user
    
    if user.user_type != 'cliente':
        return HttpResponseForbidden("Apenas clientes podem marcar faturas como pagas.")
    
    fatura = get_object_or_404(Fatura, id=fatura_id, pedido__cliente=user, pago=False)
    fatura.pago = True
    fatura.data_pagamento = timezone.now()
    fatura.save()
    
    # Notificar o freelancer de que a fatura foi paga
    freelancer = fatura.pedido.servico.freelancer
    criar_notificacao(
        utilizador=freelancer,
        tipo='fatura',
        titulo='Fatura paga',
        texto=f'A fatura do pedido "{fatura.pedido.servico.nome}" foi marcada como paga pelo cliente {user.get_full_name()}.',
        link=reverse('ver_fatura', args=[fatura.id])
    )
    
    messages.success(request, "Fatura marcada como paga. Obrigado!")
    return redirect('faturas')


@login_required
def google_auth(request):
    """Iniciar o fluxo de autenticação do Google Calendar."""
    # URL de redirecionamento após autenticação
    redirect_uri = request.build_absolute_uri('/google-oauth-callback/')
    
    # Obter URL de autenticação
    auth_url = get_google_auth_url(request.user.id, redirect_uri)
    
    # Redirecionar o utilizador para a página de autenticação do Google
    return redirect(auth_url)


def google_oauth_callback(request):
    """Callback para a autenticação OAuth do Google."""
    # Verificar se há erro
    if 'error' in request.GET:
        messages.error(request, f"Erro na autenticação com o Google: {request.GET.get('error')}")
        return redirect('perfil')
    
    # Verificar se temos o código e o estado
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    if not code or not state:
        return HttpResponseBadRequest("Parâmetros inválidos na solicitação.")
    
    # Verificar se o utilizador está autenticado
    if not request.user.is_authenticated:
        messages.error(request, "Precisa estar ligado para concluir a autenticação.")
        return redirect('login')
    
    # Verificar se o estado corresponde ao ID do utilizador (segurança adicional)
    user_id = int(state)
    if user_id != request.user.id:
        return HttpResponseBadRequest("ID de utilizador inválido.")
    
    # Obter o mesmo URI de redirecionamento que foi usado para a autenticação
    redirect_uri = request.build_absolute_uri('/google-oauth-callback/')
    
    # Processar o callback e obter o token, passando o mesmo URI de redirecionamento
    success = handle_google_callback(code, user_id, redirect_uri)
    
    if success:
        # Adicionar à sessão a informação de que o utilizador conectou o Google Calendar
        if 'google_calendar_tokens' not in request.session:
            request.session['google_calendar_tokens'] = []
        
        if request.user.id not in request.session['google_calendar_tokens']:
            request.session['google_calendar_tokens'].append(request.user.id)
            request.session.modified = True
            
        messages.success(request, "Conta do Google Calendar conectada com sucesso!")
    else:
        messages.error(request, "Falha ao conectar com o Google Calendar. Tente novamente.")
    
    # Redirecionar o utilizador para a página do perfil ou da solicitação
    return_url = request.session.get('calendar_return_url', 'perfil')
    request.session.pop('calendar_return_url', None)
    return redirect(return_url)


@login_required
def sync_pedido_to_calendar(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)

    if pedido.cliente != request.user and pedido.servico.freelancer != request.user:
        return HttpResponseForbidden("Não tem permissão para aceder a este pedido.")

    if pedido.tipo_servico != 'agendado':
        messages.error(request, "Apenas pedidos agendados podem ser sincronizados com o Google Calendar.")
        return redirect('ver_pedido', pedido_id=pedido.id)

    # Captura o ID e o LINK do evento
    event_id, event_url = add_pedido_to_calendar(pedido)

    if event_id:
        pedido.google_calendar_event_id = event_id
        pedido.google_calendar_event_url = event_url
        pedido.save(update_fields=['google_calendar_event_id', 'google_calendar_event_url'])

        # Redireciona direto para o evento no Google Calendar
        return redirect(event_url)
    else:
        messages.error(request, "Não foi possível adicionar o serviço ao Google Calendar.")
        return redirect('ver_pedido', pedido_id=pedido.id)



def test_google_auth(request):
    redirect_uri = request.build_absolute_uri('/google-oauth-callback/')
    auth_url = get_google_auth_url(request.user.id, redirect_uri)
    return redirect(auth_url)


def ajuda(request):
    return render(request, 'autenticacao/ajuda.html')


def registar_google(request):
    """Processar registo via Google e definir tipo de conta."""
    tipo_conta = request.GET.get('tipo')
    
    if not request.user.is_authenticated:
        messages.error(request, "Ocorreu um erro durante a autenticação com o Google.")
        return redirect('login')
    
    # Verificar se o perfil já existe
    try:
        perfil = Perfil.objects.get(user=request.user)
        is_novo = False
    except Perfil.DoesNotExist:
        is_novo = True
    
    if is_novo:
        # Definir o tipo de utilizador com base no parâmetro
        if tipo_conta in ['freelancer', 'cliente']:
            request.user.user_type = tipo_conta
            request.user.save()
            
            # Criar perfil
            perfil = Perfil.objects.create(user=request.user)
            
            # Criar detalhes específicos para o tipo de conta
            if tipo_conta == 'freelancer':
                FreelancerDetalhe.objects.create(perfil=perfil)
                messages.success(request, "Conta criada com sucesso! Complete o seu perfil de freelancer.")
            else:
                ClienteDetalhe.objects.create(perfil=perfil)
                messages.success(request, "Conta criada com sucesso! Bem-vindo ao BizManager.")
    
    return redirect('perfil')


@login_required
def selecionar_metodo_pagamento(request, fatura_id):
    """Selecionar o método de pagamento para uma fatura."""
    user = request.user
    
    if user.user_type != 'cliente':
        return HttpResponseForbidden("Apenas clientes podem realizar pagamentos.")
    
    fatura = get_object_or_404(Fatura, id=fatura_id, pedido__cliente=user, pago=False)
    
    if request.method == 'POST':
        form = MetodoPagamentoForm(request.POST)
        if form.is_valid():
            metodo = form.cleaned_data['metodo']
            
            # Atualizar o método de pagamento na fatura
            fatura.metodo_pagamento = metodo
            fatura.save()
            
            # Redirecionar para o fluxo de pagamento apropriado
            if metodo == 'stripe':
                return redirect('iniciar_pagamento_stripe', fatura_id=fatura.id)
            elif metodo == 'paypal':
                return redirect('iniciar_pagamento_paypal', fatura_id=fatura.id)
            elif metodo == 'multibanco':
                messages.info(request, "Pagamento por Multibanco em implementação.")
                return redirect('ver_fatura', fatura_id=fatura.id)
            elif metodo == 'transferencia':
                messages.info(request, "Por favor, realize a transferência bancária e envie o comprovante.")
                return redirect('ver_fatura', fatura_id=fatura.id)
            else:
                messages.error(request, "Método de pagamento inválido.")
                return redirect('ver_fatura', fatura_id=fatura.id)
    else:
        form = MetodoPagamentoForm()
    
    context = {
        'form': form,
        'fatura': fatura,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    }
    
    return render(request, 'autenticacao/selecionar_metodo_pagamento.html', context)

# nao está a funcionar daqui para baixo 
@login_required
def iniciar_pagamento_stripe(request, fatura_id):
    """Iniciar processo de pagamento com Stripe."""
    user = request.user
    
    # Verificar se é cliente
    if user.user_type != 'cliente':
        return HttpResponseForbidden("Apenas clientes podem realizar pagamentos.")
    
    # Obter a fatura
    fatura = get_object_or_404(Fatura, id=fatura_id, pedido__cliente=user, pago=False)
    
    # URLs de sucesso e cancelamento
    success_url = request.build_absolute_uri(reverse('pagamento_sucesso')) + f"?fatura_id={fatura.id}"
    cancel_url = request.build_absolute_uri(reverse('pagamento_cancelado')) + f"?fatura_id={fatura.id}"
    
    # Criar sessão de checkout do Stripe
    from .stripe_service import StripeService  # Certifique-se de importar corretamente
    stripe_session = StripeService.create_checkout_session(fatura, success_url, cancel_url)
    
    if stripe_session:
        # Salvar ID da sessão e URL de pagamento
        fatura.stripe_payment_intent_id = stripe_session.payment_intent
        fatura.stripe_payment_url = stripe_session.url
        fatura.save()
        
        # Redirecionar para a página de pagamento do Stripe
        return redirect(stripe_session.url)
    else:
        messages.error(request, "Erro ao criar sessão de pagamento. Por favor, tente novamente.")
        return redirect('ver_fatura', fatura_id=fatura.id)


@login_required
def pagamento_sucesso(request):
    """Página de sucesso após pagamento."""
    fatura_id = request.GET.get('fatura_id')
    
    if fatura_id:
        try:
            fatura = Fatura.objects.get(id=fatura_id, pedido__cliente=request.user)
            
            # Se o webhook ainda não tiver atualizado (pode acontecer em casos onde o webhook demora)
            if not fatura.pago and fatura.stripe_payment_intent_id:
                payment_intent = StripeService.retrieve_payment_intent(fatura.stripe_payment_intent_id)
                
                if payment_intent and payment_intent.status == 'succeeded':
                    fatura.pago = True
                    fatura.data_pagamento = timezone.now()
                    fatura.save()
            
            messages.success(request, "Pagamento realizado com sucesso! Obrigado.")
            return redirect('ver_fatura', fatura_id=fatura.id)
        except Fatura.DoesNotExist:
            pass
    
    messages.success(request, "Pagamento realizado com sucesso!")
    return redirect('faturas')


@login_required
def pagamento_cancelado(request):
    """Página de cancelamento após pagamento interrompido."""
    fatura_id = request.GET.get('fatura_id')
    
    if fatura_id:
        try:
            fatura = Fatura.objects.get(id=fatura_id, pedido__cliente=request.user)
            messages.warning(request, "Pagamento cancelado. Você pode tentar novamente quando quiser.")
            return redirect('ver_fatura', fatura_id=fatura.id)
        except Fatura.DoesNotExist:
            pass
    
    messages.warning(request, "Pagamento cancelado.")
    return redirect('faturas')


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Webhook para receber eventos do Stripe."""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Payload inválido
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Assinatura inválida
        return HttpResponse(status=400)

    # Processar eventos de pagamento
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        
        # Obter a fatura do metadata
        fatura_id = payment_intent.get('metadata', {}).get('fatura_id')
        
        if fatura_id:
            try:
                fatura = Fatura.objects.get(id=fatura_id)
                
                # Atualizar a fatura como paga
                if not fatura.pago:
                    fatura.pago = True
                    fatura.data_pagamento = timezone.now()
                    fatura.save()
                    
                    # Aqui você pode adicionar lógica adicional,
                    # como enviar um email de confirmação
            except Fatura.DoesNotExist:
                # Fatura não encontrada, registrar erro
                print(f"Fatura ID {fatura_id} não encontrada.")
    
    return HttpResponse(status=200)


@login_required
def listar_notificacoes(request):
    """Listar todas as notificações do utilizador."""
    notificacoes = Notificacao.objects.filter(utilizador=request.user)
    return render(request, 'autenticacao/notificacoes.html', {
        'notificacoes': notificacoes
    })

@login_required
def marcar_como_lida(request, notificacao_id):
    """Marcar uma notificação como lida."""
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, utilizador=request.user)
    notificacao.lida = True
    notificacao.save()
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    # Se tiver um link, redirecione para ele
    if notificacao.link:
        return redirect(notificacao.link)
    
    return redirect('notificacoes')

@login_required
def marcar_todas_como_lidas(request):
    """Marcar todas as notificações como lidas."""
    Notificacao.objects.filter(utilizador=request.user, lida=False).update(lida=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    
    return redirect('notificacoes')

@login_required
def contar_nao_lidas(request):
    """Retorna o número de notificações não lidas."""
    count = Notificacao.objects.filter(utilizador=request.user, lida=False).count()
    return JsonResponse({'count': count})

@login_required
def obter_notificacoes_recentes(request):
    """Retorna as 5 notificações mais recentes em formato JSON."""
    notificacoes = Notificacao.objects.filter(utilizador=request.user).order_by('-criada_em')[:5]
    
    notificacoes_list = []
    for n in notificacoes:
        notificacoes_list.append({
            'id': n.id,
            'tipo': n.tipo,
            'titulo': n.titulo,
            'texto': n.texto,
            'link': n.link,
            'lida': n.lida,
            'criada_em': n.criada_em.strftime('%d/%m/%Y %H:%M')
        })
    
    return JsonResponse({'notificacoes': notificacoes_list})


@login_required
def ver_perfil_utilizador(request, user_id):
    """Visualizar o perfil de outro utilizador."""
    user_profile = get_object_or_404(User, id=user_id)
    
    try:
        perfil = Perfil.objects.get(user=user_profile)
    except Perfil.DoesNotExist:
        # Criar perfil se não existir
        perfil = Perfil.objects.create(user=user_profile)
    
    # Verificar se o utilizador tem detalhes específicos
    has_freelancer_details = hasattr(perfil, 'freelancer_detalhe') if user_profile.user_type == 'freelancer' else False
    has_cliente_details = hasattr(perfil, 'cliente_detalhe') if user_profile.user_type == 'cliente' else False
    
    # Cálculo de estatísticas (movido do template para a view)
    projetos_concluidos = 0
    pedidos_realizados = 0
    
    # Obter serviços do utilizador se for freelancer
    user_services = []
    if user_profile.user_type == 'freelancer':
        user_services = Servico.objects.filter(freelancer=user_profile, ativo=True)
        # Calcular projetos concluídos para freelancers
        projetos_concluidos = Pedido.objects.filter(
            servico__freelancer=user_profile,
            status='concluido'
        ).count()
    elif user_profile.user_type == 'cliente':
        # Calcular pedidos realizados e concluídos para clientes
        pedidos_feitos = Pedido.objects.filter(cliente=user_profile)
        pedidos_realizados = pedidos_feitos.count()
        projetos_concluidos = pedidos_feitos.filter(status='concluido').count()
    
    # Obter avaliações/comentários sobre o utilizador
    user_comments = Comentario.objects.filter(
        Q(servico__freelancer=user_profile) | Q(utilizador=user_profile),
        aprovado=True
    ).order_by('-data_criacao')
    
    context = {
        'profile_user': user_profile,
        'perfil': perfil,
        'nome_completo': request.user.get_full_name(),
        'user_type': request.user.user_type,
        'has_freelancer_details': has_freelancer_details,
        'has_cliente_details': has_cliente_details,
        'user_services': user_services,
        'user_comments': user_comments,
        'is_current_user': request.user.id == user_id,
        # Variáveis calculadas na view para usar no template
        'projetos_concluidos': projetos_concluidos,
        'pedidos_realizados': pedidos_realizados,
    }
    
    return render(request, 'autenticacao/ver_perfil_utilizador.html', context)


@login_required
def enviar_suporte(request):
    """Processa o envio de mensagens de suporte."""
    if request.method == 'POST':
        # Obter dados do formulário
        assunto = request.POST.get('assunto')
        mensagem = request.POST.get('mensagem')
        anexo = request.FILES.get('anexo', None)
        
        # Mapear o valor do assunto para um título mais descritivo
        assunto_mapeado = {
            'conta': 'Problemas com a conta',
            'pagamento': 'Pagamentos e faturas',
            'pedido': 'Problema com um pedido',
            'servico': 'Dúvidas sobre serviços',
            'sugestao': 'Sugestões',
            'outro': 'Outro assunto'
        }.get(assunto, 'Contacto de Suporte')
        
        # Preparar o corpo do e-mail
        corpo_email = f"""
        Nova mensagem de suporte do utilizador:
        
        Nome: {request.user.get_full_name()}
        Email: {request.user.email}
        ID: {request.user.id}
        Tipo de conta: {request.user.user_type}
        
        Assunto: {assunto_mapeado}
        
        Mensagem:
        {mensagem}
        """
        
        # Criar o objeto de e-mail
        from django.core.mail import EmailMessage
        email = EmailMessage(
            subject=f'[Suporte BizManager] {assunto_mapeado}',
            body=corpo_email,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=['suporte@bizmanager.pt'],  # Substitua pelo email correto
            reply_to=[request.user.email]
        )
        
        # Anexar o ficheiro, se fornecido
        if anexo:
            email.attach(anexo.name, anexo.read(), anexo.content_type)
        
        # Enviar o e-mail
        try:
            email.send()
            messages.success(request, "A sua mensagem foi enviada com sucesso! A nossa equipa de suporte entrará em contacto brevemente.")
            
            # Criar notificação para o utilizador
            criar_notificacao(
                utilizador=request.user,
                tipo='sistema',
                titulo='Mensagem de suporte enviada',
                texto='A sua mensagem foi enviada com sucesso para a nossa equipa de suporte.',
                link=None
            )
            
        except Exception as e:
            messages.error(request, f"Ocorreu um erro ao enviar a mensagem. Por favor, tente novamente mais tarde.")
        
        # Redirecionar para a página de ajuda
        return redirect('ajuda')
    
    # Se não for um POST, redirecionar para a página de ajuda
    return redirect('ajuda')

@login_required
def iniciar_pagamento_paypal(request, fatura_id):
    """Iniciar processo de pagamento com PayPal."""
    user = request.user
    
    # Verificar se é cliente
    if user.user_type != 'cliente':
        return HttpResponseForbidden("Apenas clientes podem realizar pagamentos.")
    
    # Obter a fatura
    fatura = get_object_or_404(Fatura, id=fatura_id, pedido__cliente=user, pago=False)
    
    # URLs de sucesso e cancelamento
    success_url = request.build_absolute_uri(reverse('pagamento_paypal_sucesso')) + f"?fatura_id={fatura.id}"
    cancel_url = request.build_absolute_uri(reverse('pagamento_paypal_cancelado')) + f"?fatura_id={fatura.id}"
    
    # Criar pagamento do PayPal
    from .paypal_service import PayPalService
    payment, checkout_url = PayPalService.create_payment(fatura, success_url, cancel_url)
    
    if checkout_url:
        # Guardar URL de pagamento na fatura
        fatura.paypal_payment_url = checkout_url
        fatura.save()
        
        # Redirecionar para a página de pagamento do PayPal
        return redirect(checkout_url)
    else:
        messages.error(request, "Erro ao criar sessão de pagamento PayPal. Por favor, tente novamente.")
        return redirect('ver_fatura', fatura_id=fatura.id)
    

@login_required
def pagamento_paypal_sucesso(request):
    """Página de sucesso após pagamento com PayPal."""
    fatura_id = request.GET.get('fatura_id')
    
    if fatura_id:
        try:
            fatura = Fatura.objects.get(id=fatura_id, pedido__cliente=request.user)
            
            # Se o webhook ainda não tiver atualizado (pode acontecer em casos onde o webhook demora)
            if not fatura.pago and fatura.paypal_payment_url:
                # Verificar o status do pagamento usando a API do PayPal
                from .paypal_service import PayPalService
                payment_status = PayPalService.verify_payment_status(fatura)
                
                if payment_status == 'completed':
                    fatura.pago = True
                    fatura.data_pagamento = timezone.now()
                    fatura.save()
                    
                    # Notificar o freelancer de que a fatura foi paga
                    freelancer = fatura.pedido.servico.freelancer
                    criar_notificacao(
                        utilizador=freelancer,
                        tipo='fatura',
                        titulo='Fatura paga via PayPal',
                        texto=f'A fatura do pedido "{fatura.pedido.servico.nome}" foi paga pelo cliente {request.user.get_full_name()} através do PayPal.',
                        link=reverse('ver_fatura', args=[fatura.id])
                    )
            
            messages.success(request, "Pagamento realizado com sucesso via PayPal! Obrigado.")
            return redirect('ver_fatura', fatura_id=fatura.id)
        except Fatura.DoesNotExist:
            pass
    
    messages.success(request, "Pagamento via PayPal realizado com sucesso!")
    return redirect('faturas')

@login_required
def pagamento_paypal_cancelado(request):
    """Página de cancelamento após pagamento interrompido no PayPal."""
    fatura_id = request.GET.get('fatura_id')
    
    if fatura_id:
        try:
            fatura = Fatura.objects.get(id=fatura_id, pedido__cliente=request.user)
            messages.warning(request, "Pagamento via PayPal cancelado. Podes tentar novamente quando quiseres.")
            return redirect('ver_fatura', fatura_id=fatura.id)
        except Fatura.DoesNotExist:
            pass
    
    messages.warning(request, "Pagamento via PayPal cancelado.")
    return redirect('faturas')

@login_required
def metodos_pagamento_freelancer(request):
    """
    View para freelancers configurarem seus métodos de pagamento.
    """
    user = request.user
    
    # Verificar se é freelancer
    if user.user_type != 'freelancer':
        messages.error(request, "Apenas freelancers podem configurar métodos de pagamento.")
        return redirect('dashboard')
    
    # Obter detalhes do freelancer
    try:
        freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=user)
    except FreelancerDetalhe.DoesNotExist:
        messages.error(request, "Perfil de freelancer não encontrado.")
        return redirect('dashboard')
    
    # Processar formulário POST
    if request.method == 'POST':
        # Determinar qual tipo de configuração está sendo atualizada
        action = request.POST.get('action')
        
        if action == 'update_paypal':
            # Atualizar configurações do PayPal
            paypal_email = request.POST.get('paypal_email')
            
            if paypal_email:
                freelancer_detalhe.paypal_email = paypal_email
                freelancer_detalhe.save(update_fields=['paypal_email'])
                
                # Em um sistema real, aqui seria feita uma verificação com a API do PayPal
                # Por simplicidade, estamos apenas marcando como verificado
                freelancer_detalhe.paypal_account_verified = True
                freelancer_detalhe.save(update_fields=['paypal_account_verified'])
                
                messages.success(request, "Informações de PayPal atualizadas com sucesso!")
            else:
                messages.error(request, "Email do PayPal é obrigatório.")
                
        elif action == 'connect_stripe':
            # Iniciar o processo de conexão com o Stripe Connect
            from .stripe_service import StripeService
            
            # Criar uma conta Stripe Connect para o freelancer
            account_id = StripeService.create_connect_account(user.email)
            
            if account_id:
                # Salvar o ID da conta no perfil do freelancer
                freelancer_detalhe.stripe_account_id = account_id
                freelancer_detalhe.save(update_fields=['stripe_account_id'])
                
                # Criar um link de onboarding para o freelancer completar o registro
                refresh_url = request.build_absolute_uri(reverse('metodos_pagamento_freelancer'))
                return_url = request.build_absolute_uri(reverse('stripe_connect_callback'))
                
                onboarding_url = StripeService.create_account_link(account_id, refresh_url, return_url)
                
                if onboarding_url:
                    # Redirecionar o freelancer para o onboarding do Stripe
                    return redirect(onboarding_url)
                else:
                    messages.error(request, "Erro ao criar link para configuração do Stripe. Tente novamente.")
            else:
                messages.error(request, "Erro ao conectar com o Stripe. Tente novamente.")
                
        elif action == 'update_fee':
            # Atualizar a taxa da plataforma
            try:
                fee_percentage = float(request.POST.get('platform_fee_percentage', 10))
                
                # Limitar a taxa entre 5% e 20%
                if 5 <= fee_percentage <= 20:
                    freelancer_detalhe.platform_fee_percentage = fee_percentage
                    freelancer_detalhe.save(update_fields=['platform_fee_percentage'])
                    messages.success(request, f"Taxa da plataforma atualizada para {fee_percentage}%.")
                else:
                    messages.error(request, "A taxa da plataforma deve estar entre 5% e 20%.")
            except ValueError:
                messages.error(request, "Valor de taxa inválido.")
    
    # Verificar o status da conta Stripe, se existir
    stripe_account_status = None
    if freelancer_detalhe.stripe_account_id:
        from .stripe_service import StripeService
        stripe_account_status = StripeService.check_account_status(freelancer_detalhe.stripe_account_id)
        
        # Atualizar o status de verificação se a conta estiver completa
        if stripe_account_status and stripe_account_status.get('is_complete'):
            freelancer_detalhe.stripe_account_verified = True
            freelancer_detalhe.save(update_fields=['stripe_account_verified'])
    
    context = {
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'freelancer_detalhe': freelancer_detalhe,
        'stripe_account_status': stripe_account_status
    }
    
    return render(request, 'autenticacao/metodos_pagamento_freelancer.html', context)

@login_required
def stripe_connect_callback(request):
    """
    Callback após o onboarding do Stripe Connect.
    """
    user = request.user
    
    if user.user_type != 'freelancer':
        messages.error(request, "Apenas freelancers podem configurar métodos de pagamento.")
        return redirect('dashboard')
    
    try:
        freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=user)
        
        # Verificar o status da conta
        if freelancer_detalhe.stripe_account_id:
            from .stripe_service import StripeService
            status = StripeService.check_account_status(freelancer_detalhe.stripe_account_id)
            
            if status and status.get('is_complete'):
                freelancer_detalhe.stripe_account_verified = True
                freelancer_detalhe.save(update_fields=['stripe_account_verified'])
                messages.success(request, "A tua conta Stripe foi conectada com sucesso!")
            else:
                # A conta foi criada, mas não está completamente configurada
                messages.warning(request, "A tua conta Stripe foi criada, mas ainda precisa de informações adicionais.")
        else:
            messages.warning(request, "Não foi possível verificar a tua conta Stripe.")
    except FreelancerDetalhe.DoesNotExist:
        messages.error(request, "Perfil de freelancer não encontrado.")
    
    return redirect('faturas')

@login_required
def redirect_to_faturas_payment_tab(request):
    """
    Redirecionamento da URL de métodos de pagamento para a aba correspondente na página de faturas.
    """
    return redirect(reverse('faturas') + '?tab=payment-methods')


@login_required
def listar_clientes(request):
    """
    Lista clientes com opções de filtro para freelancers.
    Permite filtrar por nome, email, status e última compra.
    """
    user = request.user
    
    # Verificar se é um freelancer
    if user.user_type != 'freelancer':
        messages.error(request, "Apenas freelancers podem aceder à lista de clientes.")
        return redirect('dashboard')
    
    # Inicializar o formulário de filtro
    form = ClienteFilterForm(request.GET)
    
    # Obter todos os clientes que fizeram pedidos para os serviços deste freelancer
    clientes = User.objects.filter(
        user_type='cliente',
        pedidos_feitos__servico__freelancer=user
    ).distinct()
    
    # Aplicar filtros se o formulário for válido
    if form.is_valid():
        # Filtro por texto (nome ou email)
        if form.cleaned_data['search']:
            search_query = form.cleaned_data['search']
            clientes = clientes.filter(
                Q(first_name__icontains=search_query) | 
                Q(last_name__icontains=search_query) | 
                Q(email__icontains=search_query)
            )
        
        # Filtro por status (ativo/inativo)
        if form.cleaned_data['status']:
            # Aqui estamos a considerar um cliente "inativo" se não tiver feito pedidos nos últimos 6 meses
            hoje = timezone.now().date()
            seis_meses_atras = hoje - datetime.timedelta(days=180)
            seis_meses_atras_aware = timezone.make_aware(datetime.datetime.combine(seis_meses_atras, datetime.time.min))
            
            if form.cleaned_data['status'] == 'ativo':
                # Clientes com pedidos nos últimos 6 meses
                clientes = clientes.filter(
                    pedidos_feitos__data_pedido__gte=seis_meses_atras_aware
                ).distinct()
            else:
                # Clientes sem pedidos nos últimos 6 meses
                clientes_ativos_ids = User.objects.filter(
                    user_type='cliente',
                    pedidos_feitos__servico__freelancer=user,
                    pedidos_feitos__data_pedido__gte=seis_meses_atras_aware
                ).values_list('id', flat=True)
                
                clientes = clientes.exclude(id__in=clientes_ativos_ids)
        
        # Filtro por última contratação
        if form.cleaned_data['ultimo_servico']:
            days = form.cleaned_data['ultimo_servico']
            hoje = timezone.now().date()
            
            if days == 'inactive':
                # Clientes inativos há mais de 6 meses
                data_limite = hoje - datetime.timedelta(days=180)
                data_limite_aware = timezone.make_aware(datetime.datetime.combine(data_limite, datetime.time.min))
                
                # Obter IDs de clientes com pedidos recentes
                clientes_recentes_ids = User.objects.filter(
                    user_type='cliente',
                    pedidos_feitos__servico__freelancer=user,
                    pedidos_feitos__data_pedido__gte=data_limite_aware
                ).values_list('id', flat=True)
                
                # Excluir esses IDs da query
                clientes = clientes.exclude(id__in=clientes_recentes_ids)
            else:
                # Clientes ativos no período selecionado
                data_limite = hoje - datetime.timedelta(days=int(days))
                data_limite_aware = timezone.make_aware(datetime.datetime.combine(data_limite, datetime.time.min))
                
                clientes = clientes.filter(
                    pedidos_feitos__servico__freelancer=user,
                    pedidos_feitos__data_pedido__gte=data_limite_aware
                ).distinct()
        
        # Filtro por tipo de serviço
        if form.cleaned_data['servico_tipo']:
            area = form.cleaned_data['servico_tipo']
            clientes = clientes.filter(
                pedidos_feitos__servico__freelancer=user,
                pedidos_feitos__servico__area=area
            ).distinct()
        
        # Ordenação
        ordem = form.cleaned_data.get('ordenar_por', 'nome')
        
        if ordem == 'nome':
            clientes = clientes.order_by('first_name', 'last_name')
        elif ordem == 'nome_desc':
            clientes = clientes.order_by('-first_name', '-last_name')
        elif ordem == 'data_registo':
            clientes = clientes.order_by('date_joined')
        elif ordem == 'data_registo_desc':
            clientes = clientes.order_by('-date_joined')
        elif ordem == 'ultima_compra':
            # Isto requer uma anotação para ordenar por data do último pedido
            clientes = clientes.annotate(
                ultima_compra=Max('pedidos_feitos__data_pedido')
            ).order_by('ultima_compra')
        elif ordem == 'ultima_compra_desc':
            clientes = clientes.annotate(
                ultima_compra=Max('pedidos_feitos__data_pedido')
            ).order_by('-ultima_compra')
    
    # Adicionar estatísticas para cada cliente
    hoje = timezone.now().date()
    
    for cliente in clientes:
        # Total gasto pelo cliente nos serviços deste freelancer
        total_gasto = Pedido.objects.filter(
            cliente=cliente,
            servico__freelancer=user,
            status='concluido'
        ).aggregate(
            total=Sum('servico__orcamento', default=0)
        )['total'] or 0
        cliente.total_gasto = total_gasto
        
        # Número de pedidos feitos
        cliente.num_pedidos = Pedido.objects.filter(
            cliente=cliente,
            servico__freelancer=user
        ).count()
        
        # Data do último pedido
        try:
            ultimo_pedido = Pedido.objects.filter(
                cliente=cliente,
                servico__freelancer=user
            ).latest('data_pedido')
            cliente.ultimo_pedido_data = ultimo_pedido.data_pedido
            
            # Verificar se o cliente está inativo (último pedido > 180 dias)
            if hasattr(ultimo_pedido.data_pedido, 'date'):
                data_ultimo_pedido = ultimo_pedido.data_pedido.date()
            else:
                data_ultimo_pedido = ultimo_pedido.data_pedido
                
            diferenca = hoje - data_ultimo_pedido
            cliente.is_inactive = diferenca.days > 180
            
        except Pedido.DoesNotExist:
            cliente.ultimo_pedido_data = None
            cliente.is_inactive = True
    
    # Paginação
    paginator = Paginator(clientes, 10)  # 10 clientes por página
    page = request.GET.get('page')
    clientes_paginados = paginator.get_page(page)
    
    context = {
        'form': form,
        'clientes': clientes_paginados,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'num_total_clientes': clientes.count(),
    }
    
    return render(request, 'autenticacao/listar_clientes.html', context)

@login_required
def enviar_proposta_cliente(request, cliente_id):
    """
    Permite ao freelancer enviar uma proposta comercial para um cliente.
    """
    user = request.user
    
    # Verificar se é um freelancer
    if user.user_type != 'freelancer':
        messages.error(request, "Apenas freelancers podem enviar propostas para clientes.")
        return redirect('dashboard')
    
    # Obter o cliente
    cliente = get_object_or_404(User, id=cliente_id, user_type='cliente')
    
    # Obter serviços ativos do freelancer para incluir na proposta
    servicos_ativos = Servico.objects.filter(freelancer=user, ativo=True)
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descricao = request.POST.get('descricao')
        servicos_ids = request.POST.getlist('servicos')
        validade = request.POST.get('validade')
        
        if not titulo or not descricao or not servicos_ids or not validade:
            messages.error(request, "Por favor, preenche todos os campos e seleciona pelo menos um serviço.")
            return render(request, 'autenticacao/enviar_proposta_cliente.html', {
                'cliente': cliente,
                'servicos': servicos_ativos,
                'nome_completo': user.get_full_name(),
                'user_type': user.user_type,
            })
        
        # Obter os serviços selecionados
        servicos_selecionados = Servico.objects.filter(id__in=servicos_ids, freelancer=user, ativo=True)
        
        # Calcular o valor total da proposta
        valor_total = sum(servico.orcamento for servico in servicos_selecionados)
        
        # Criar o texto da notificação
        servicos_texto = ", ".join(servico.nome for servico in servicos_selecionados)
        
        # Criar notificação para o cliente
        notificacao = criar_notificacao(
            utilizador=cliente,
            tipo='proposta',
            titulo=f'Nova proposta comercial de {user.get_full_name()}: {titulo}',
            texto=f'{descricao}\n\nServiços incluídos: {servicos_texto}\n\nValor total: {valor_total}€\n\nValidade: {validade}',
            link=None  # Será atualizado depois
        )
        
        # Atualizar o link para apontar para a visualização da proposta
        if notificacao:
            notificacao.link = reverse('ver_notificacao_proposta', args=[notificacao.id])
            notificacao.save(update_fields=['link'])
        
        # Enviar email ao cliente (opcional)
        try:
            from django.core.mail import send_mail
            message_body = f"""
            Olá {cliente.get_full_name()},
            
            {user.get_full_name()} enviou-te uma proposta comercial.
            
            **{titulo}**
            
            {descricao}
            
            **Serviços incluídos:**
            {servicos_texto}
            
            **Valor total:** {valor_total}€
            **Validade:** {validade}
            
            Para ver todos os detalhes, acede à tua conta no BizManager.
            
            Cumprimentos,
            Equipa BizManager
            """
            
            send_mail(
                f'[BizManager] Nova proposta comercial de {user.get_full_name()}',
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                [cliente.email],
                fail_silently=True,
            )
        except Exception as e:
            # Registar erro, mas não mostrar ao utilizador
            print(f"Erro ao enviar email: {str(e)}")
        
        messages.success(request, f"Proposta enviada com sucesso para {cliente.get_full_name()}.")
        return redirect('listar_clientes')
    
    return render(request, 'autenticacao/enviar_proposta_cliente.html', {
        'cliente': cliente,
        'servicos': servicos_ativos,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
    })

@login_required
def exportar_dados_cliente(request, cliente_id):
    """
    Exporta os dados de histórico de um cliente específico em formato CSV.
    """
    user = request.user
    
    # Verificar se é um freelancer
    if user.user_type != 'freelancer':
        messages.error(request, "Apenas freelancers podem exportar dados de clientes.")
        return redirect('dashboard')
    
    # Obter o cliente
    cliente = get_object_or_404(User, id=cliente_id, user_type='cliente')
    
    # Verificar se o cliente já contratou algum serviço deste freelancer
    if not Pedido.objects.filter(cliente=cliente, servico__freelancer=user).exists():
        messages.error(request, "Só podes exportar dados de clientes que já solicitaram os teus serviços.")
        return redirect('listar_clientes')
    
    # Obter pedidos deste cliente relacionados a este freelancer
    pedidos = Pedido.objects.filter(
        cliente=cliente,
        servico__freelancer=user
    ).order_by('-data_pedido')
    
    # Gerar o CSV
    import csv
    from django.http import HttpResponse
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="cliente_{cliente.id}_{datetime.datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['ID Pedido', 'Serviço', 'Data Pedido', 'Status', 'Valor', 'Pago', 'Data Pagamento'])
    
    for pedido in pedidos:
        try:
            fatura = Fatura.objects.get(pedido=pedido)
            valor = fatura.valor
            pago = 'Sim' if fatura.pago else 'Não'
            data_pagamento = fatura.data_pagamento.strftime('%d/%m/%Y') if fatura.data_pagamento else '-'
        except Fatura.DoesNotExist:
            valor = pedido.servico.orcamento
            pago = 'Não'
            data_pagamento = '-'
        
        writer.writerow([
            pedido.id,
            pedido.servico.nome,
            pedido.data_pedido.strftime('%d/%m/%Y'),
            pedido.get_status_display(),
            valor,
            pago,
            data_pagamento
        ])
    
    # Registar a exportação (opcional)
    try:
        # Criar notificação para o próprio freelancer
        criar_notificacao(
            utilizador=user,
            tipo='sistema',
            titulo='Exportação de dados concluída',
            texto=f'Exportaste com sucesso os dados do cliente {cliente.get_full_name()} em {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}.',
            link=None
        )
    except Exception as e:
        # Registar erro, mas não mostrar ao utilizador
        print(f"Erro ao criar notificação: {str(e)}")
    
    return response

@login_required
def ver_notificacao_proposta(request, notificacao_id):
    """
    Visualizar os detalhes de uma proposta a partir de uma notificação.
    """
    user = request.user
    
    # Obter a notificação e verificar se o utilizador tem acesso
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, utilizador=user, tipo='proposta')
    
    # Marcar a notificação como lida se ainda não estiver
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.save()
    
    # Extrair informações da proposta a partir do texto da notificação
    texto_partes = notificacao.texto.split('\n\n')
    descricao = texto_partes[0] if texto_partes else ""
    
    # Extrair informações sobre serviços e valores
    servicos_info = ""
    valor_total_info = ""
    validade_info = ""
    
    for parte in texto_partes[1:]:
        if parte.startswith("Serviços incluídos:"):
            servicos_info = parte
        elif parte.startswith("Valor total:"):
            valor_total_info = parte
        elif parte.startswith("Validade:"):
            validade_info = parte
    
    # Tentar encontrar o freelancer (para clientes visualizando propostas)
    freelancer = None
    if user.user_type == 'cliente':
        # Buscar o freelancer através do título da notificação
        # Isso assume que o título contém "de [nome do freelancer]"
        try:
            import re
            match = re.search(r'de ([^\:]+):', notificacao.titulo)
            if match:
                freelancer_name = match.group(1).strip()
                # Primeiro tentar encontrar pelo nome completo
                freelancer = User.objects.filter(
                    first_name__icontains=freelancer_name.split()[0],
                    user_type='freelancer'
                ).first()
                
                # Se não encontrar, tentar pelo email (username)
                if not freelancer:
                    # Verificar se existe algum freelancer com email na notificação
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+', notificacao.texto)
                    if email_match:
                        email = email_match.group(0)
                        freelancer = User.objects.filter(
                            email=email,
                            user_type='freelancer'
                        ).first()
        except Exception as e:
            print(f"Erro ao tentar encontrar o freelancer: {str(e)}")
    
    # Contexto para o template
    context = {
        'notificacao': notificacao,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'descricao': descricao,
        'servicos_info': servicos_info,
        'valor_total_info': valor_total_info,
        'validade_info': validade_info,
        'freelancer': freelancer
    }
    
    return render(request, 'autenticacao/ver_notificacao_proposta.html', context)

@login_required
def ver_notificacao_proposta(request, notificacao_id):
    """
    Visualiza os detalhes de uma proposta a partir de uma notificação.
    """
    user = request.user
    
    # Obter a notificação e verificar se o utilizador tem acesso
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, utilizador=user, tipo='proposta')
    
    # Marcar a notificação como lida se ainda não estiver
    if not notificacao.lida:
        notificacao.lida = True
        notificacao.save()
    
    # Extrair informações da proposta a partir do texto da notificação
    texto_partes = notificacao.texto.split('\n\n')
    descricao = texto_partes[0] if texto_partes else ""
    
    # Extrair informações sobre serviços e valores
    servicos_info = ""
    valor_total_info = ""
    validade_info = ""
    
    for parte in texto_partes[1:]:
        if parte.startswith("Serviços incluídos:"):
            servicos_info = parte
        elif parte.startswith("Valor total:"):
            valor_total_info = parte
        elif parte.startswith("Validade:"):
            validade_info = parte
    
    # Tentar encontrar o freelancer (para clientes visualizando propostas)
    freelancer = None
    if user.user_type == 'cliente':
        # Buscar o freelancer através do título da notificação
        # Isso assume que o título contém "de [nome do freelancer]"
        try:
            import re
            match = re.search(r'de ([^\:]+):', notificacao.titulo)
            if match:
                freelancer_name = match.group(1).strip()
                # Primeiro tentar encontrar pelo nome completo
                freelancer = User.objects.filter(
                    first_name__icontains=freelancer_name.split()[0],
                    user_type='freelancer'
                ).first()
                
                # Se não encontrar, tentar pelo email (username)
                if not freelancer:
                    # Verificar se existe algum freelancer com email na notificação
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+', notificacao.texto)
                    if email_match:
                        email = email_match.group(0)
                        freelancer = User.objects.filter(
                            email=email,
                            user_type='freelancer'
                        ).first()
        except Exception as e:
            print(f"Erro ao tentar encontrar o freelancer: {str(e)}")
    
    # Contexto para o template
    context = {
        'notificacao': notificacao,
        'nome_completo': user.get_full_name(),
        'user_type': user.user_type,
        'descricao': descricao,
        'servicos_info': servicos_info,
        'valor_total_info': valor_total_info,
        'validade_info': validade_info,
        'freelancer': freelancer
    }
    
    return render(request, 'autenticacao/ver_notificacao_proposta.html', context)


@login_required
def responder_proposta(request, notificacao_id):
    """
    Processa a resposta (aceitar/recusar) a uma proposta.
    """
    user = request.user
    
    # Verificar se é um cliente
    if user.user_type != 'cliente':
        messages.error(request, "Apenas clientes podem responder a propostas.")
        return redirect('notificacoes')
    
    # Obter a notificação e verificar se o utilizador tem acesso
    notificacao = get_object_or_404(Notificacao, id=notificacao_id, utilizador=user, tipo='proposta')
    
    if request.method == 'POST':
        acao = request.POST.get('acao')
        comentario = request.POST.get('comentario', '')
        
        # Extrair informações do freelancer a partir do título da notificação
        import re
        freelancer_name = None
        freelancer = None
        match = re.search(r'de ([^\:]+):', notificacao.titulo)
        if match:
            freelancer_name = match.group(1).strip()
            # Tentar encontrar o freelancer pelo nome
            freelancer = User.objects.filter(
                first_name__icontains=freelancer_name.split()[0],
                user_type='freelancer'
            ).first()
        
        if acao == 'aceitar':
            # Notificar o freelancer que a proposta foi aceite
            if freelancer:
                criar_notificacao(
                    utilizador=freelancer,
                    tipo='aceitacao',
                    titulo=f'Proposta aceite por {user.get_full_name()}',
                    texto=f'A tua proposta comercial foi aceite por {user.get_full_name()}.' +
                          (f'\n\nComentário: {comentario}' if comentario else ''),
                    link=None  # No futuro, pode ser o link para um pedido gerado
                )
            
            messages.success(request, "Proposta aceite com sucesso! O freelancer foi notificado.")
            return redirect('notificacoes')
            
        elif acao == 'recusar':
            # Notificar o freelancer que a proposta foi recusada
            if freelancer:
                criar_notificacao(
                    utilizador=freelancer,
                    tipo='rejeicao',
                    titulo=f'Proposta recusada por {user.get_full_name()}',
                    texto=f'A tua proposta comercial foi recusada por {user.get_full_name()}.' +
                          (f'\n\nComentário: {comentario}' if comentario else ''),
                    link=None
                )
            
            messages.info(request, "Proposta recusada. O freelancer foi notificado.")
            return redirect('notificacoes')
    
    # Se não for POST ou ação inválida, redirecionar para a visualização da proposta
    return redirect('ver_notificacao_proposta', notificacao_id=notificacao_id)