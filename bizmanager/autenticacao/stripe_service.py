import stripe
from django.conf import settings
from decimal import Decimal
from .models import FreelancerDetalhe

stripe.api_key = settings.STRIPE_SECRET_KEY

class StripeService:
    @staticmethod
    def create_checkout_session(fatura, success_url, cancel_url):
        """
        Cria uma sessão de checkout do Stripe para a fatura.
        Se o freelancer tiver uma conta Stripe conectada, usa o Connect para transfer payments.
        """
        try:
            # Verificar se o freelancer tem conta Stripe conectada
            freelancer = fatura.pedido.servico.freelancer
            use_connect_account = False
            connect_account_id = None
            application_fee_amount = 0
            
            try:
                freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=freelancer)
                if freelancer_detalhe.stripe_account_id and freelancer_detalhe.stripe_account_verified:
                    use_connect_account = True
                    connect_account_id = freelancer_detalhe.stripe_account_id
                    
                    # Calcular a taxa da plataforma
                    platform_fee_percentage = float(freelancer_detalhe.platform_fee_percentage)
                    application_fee_amount = int((fatura.valor * Decimal(platform_fee_percentage / 100)) * 100)
            except FreelancerDetalhe.DoesNotExist:
                pass
            
            # Converter decimal para centavos (Stripe usa inteiros)
            valor_em_centavos = int(fatura.valor * 100)
            
            # Preparar dados básicos da sessão
            session_data = {
                'payment_method_types': ['card'],
                'line_items': [
                    {
                        'price_data': {
                            'currency': 'eur',
                            'product_data': {
                                'name': f"Pagamento - {fatura.pedido.servico.nome}",
                                'description': f"Fatura #{fatura.id} para o serviço {fatura.pedido.servico.nome}",
                            },
                            'unit_amount': valor_em_centavos,
                        },
                        'quantity': 1,
                    },
                ],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'client_reference_id': str(fatura.id),
                'metadata': {
                    'fatura_id': fatura.id,
                    'pedido_id': fatura.pedido.id,
                    'cliente_id': fatura.pedido.cliente.id,
                }
            }
            
            
            if use_connect_account:
                session_data['payment_intent_data'] = {
                    'application_fee_amount': application_fee_amount,
                    'transfer_data': {
                        'destination': connect_account_id,
                    }
                }
                
                fatura.stripe_connected_account = connect_account_id
                fatura.stripe_application_fee = application_fee_amount / 100  
                fatura.save(update_fields=['stripe_connected_account', 'stripe_application_fee'])
            
            checkout_session = stripe.checkout.Session.create(**session_data)
            
            return checkout_session
        except Exception as e:
            print(f"Erro ao criar sessão de checkout do Stripe: {str(e)}")
            return None
    
    @staticmethod
    def retrieve_payment_intent(payment_intent_id):
        """
        Recupera um Payment Intent do Stripe pelo ID.
        """
        try:
            return stripe.PaymentIntent.retrieve(payment_intent_id)
        except Exception as e:
            print(f"Erro ao recuperar Payment Intent do Stripe: {str(e)}")
            return None
    
    @staticmethod
    def create_account_link(account_id, refresh_url, return_url):
        """
        Cria um link para o onboarding da conta Stripe Connect de um freelancer.
        
        Args:
            account_id: ID da conta Stripe Connect
            refresh_url: URL para atualizar a sessão se expirar
            return_url: URL para retornar após completar o onboarding
            
        Returns:
            URL do link de onboarding ou None em caso de erro
        """
        try:
            account_link = stripe.AccountLink.create(
                account=account_id,
                refresh_url=refresh_url,
                return_url=return_url,
                type='account_onboarding',
            )
            return account_link.url
        except Exception as e:
            print(f"Erro ao criar link de conta Stripe: {str(e)}")
            return None
    
    @staticmethod
    def create_connect_account(freelancer_email, country='PT'):
        """
        Cria uma conta Stripe Connect para um freelancer.
        
        Args:
            freelancer_email: Email do freelancer
            country: Código ISO do país (padrão: Portugal)
            
        Returns:
            O ID da conta criada ou None em caso de erro
        """
        try:
            account = stripe.Account.create(
                type='express',
                country=country,
                email=freelancer_email,
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
            )
            return account.id
        except Exception as e:
            print(f"Erro ao criar conta Stripe Connect: {str(e)}")
            return None
    
    @staticmethod
    def check_account_status(account_id):
        """
        Verifica o status de uma conta Stripe Connect.
        
        Args:
            account_id: ID da conta Stripe Connect
            
        Returns:
            Um dicionário com informações de status ou None em caso de erro
        """
        try:
            account = stripe.Account.retrieve(account_id)
            
            is_complete = False
            if account.details_submitted and account.payouts_enabled:
                is_complete = True
                
            return {
                'is_complete': is_complete,
                'details_submitted': account.details_submitted,
                'charges_enabled': account.charges_enabled,
                'payouts_enabled': account.payouts_enabled
            }
        except Exception as e:
            print(f"Erro ao verificar status da conta Stripe: {str(e)}")
            return None