from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import Comentario
from .models import (
    User, Perfil, FreelancerDetalhe, ClienteDetalhe,
    AreaAtuacao, Servico, Pedido, Fatura
)


class CustomUserAdmin(UserAdmin):
    """Configuração do admin para o modelo User personalizado."""
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'user_type')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser',
                                       'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'user_type'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'user_type', 'is_staff')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    list_filter = ('user_type', 'is_staff', 'is_superuser', 'is_active')


class FreelancerDetalheInline(admin.StackedInline):
    """Inline para FreelancerDetalhe no admin de Perfil."""
    model = FreelancerDetalhe
    can_delete = False
    filter_horizontal = ('areas_atuacao',)


class ClienteDetalheInline(admin.StackedInline):
    """Inline para ClienteDetalhe no admin de Perfil."""
    model = ClienteDetalhe
    can_delete = False


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    """Configuração do admin para o modelo Perfil."""
    list_display = ('user', 'get_user_type', 'get_user_email')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    list_filter = ('user__user_type',)
    
    def get_inlines(self, request, obj=None):
        """Mostra inlines diferentes dependendo do tipo de utilizador."""
        if obj is None:
            return []
        
        if obj.user.user_type == 'freelancer':
            return [FreelancerDetalheInline]
        elif obj.user.user_type == 'cliente':
            return [ClienteDetalheInline]
        
        return []
    
    def get_user_type(self, obj):
        return obj.user.get_user_type_display()
    get_user_type.short_description = 'Tipo de utilizador'
    
    def get_user_email(self, obj):
        return obj.user.email
    get_user_email.short_description = 'Email'


@admin.register(AreaAtuacao)
class AreaAtuacaoAdmin(admin.ModelAdmin):
    """Configuração do admin para o modelo AreaAtuacao."""
    list_display = ('get_nome_display',)
    search_fields = ('nome',)


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    """Configuração do admin para o modelo Servico."""
    list_display = ('nome', 'freelancer', 'orcamento', 'area', 'data_criacao', 'ativo')
    list_filter = ('ativo', 'area', 'data_criacao')
    search_fields = ('nome', 'descricao', 'freelancer__email', 'freelancer__first_name', 'freelancer__last_name')
    date_hierarchy = 'data_criacao'
    list_editable = ('ativo',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Configuração do admin para o modelo Pedido."""
    list_display = ('servico', 'cliente', 'status', 'data_pedido')
    list_filter = ('status', 'data_pedido')
    search_fields = ('servico__nome', 'cliente__email', 'cliente__first_name', 'cliente__last_name')
    date_hierarchy = 'data_pedido'
    list_editable = ('status',)


@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    """Configuração do admin para o modelo Fatura."""
    list_display = ('id', 'pedido', 'valor', 'pago', 'data_emissao', 'data_pagamento')
    list_filter = ('pago', 'data_emissao', 'data_pagamento')
    search_fields = ('pedido__servico__nome', 'pedido__cliente__email')
    date_hierarchy = 'data_emissao'
    list_editable = ('pago',)
    readonly_fields = ('pedido', 'valor', 'data_emissao')



admin.site.register(User, CustomUserAdmin)



from .models import Comentario

@admin.register(Comentario)
class ComentarioAdmin(admin.ModelAdmin):
    list_display = ['utilizador', 'tipo', 'servico', 'avaliacao', 'data_criacao', 'aprovado']
    list_filter = ['tipo', 'aprovado', 'avaliacao', 'data_criacao']
    search_fields = ['texto', 'utilizador__email', 'servico__nome']
    actions = ['aprovar_comentarios']

    def aprovar_comentarios(self, request, queryset):
        queryset.update(aprovado=True)
    aprovar_comentarios.short_description = "Aprovar comentários selecionados"