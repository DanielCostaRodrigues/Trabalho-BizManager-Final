import paypalrestsdk
from django.conf import settings
from django.urls import reverse
from .models import Fatura, FreelancerDetalhe

class PayPalService:
    @staticmethod
    def setup_paypal(client_id=None, client_secret=None):
        """
        Configura a API do PayPal com as credenciais.
        Usa credenciais específicas se fornecidas, ou as credenciais padrão do sistema.
        """
        paypalrestsdk.configure({
            "mode": settings.PAYPAL_MODE,
            "client_id": client_id or settings.PAYPAL_CLIENT_ID,
            "client_secret": client_secret or settings.PAYPAL_CLIENT_SECRET
        })

    @staticmethod
    def create_payment(fatura, success_url, cancel_url):
        """
        Cria um pagamento no PayPal.
        
        Args:
            fatura: Objeto da fatura a ser paga
            success_url: URL para redirecionamento após pagamento bem-sucedido
            cancel_url: URL para redirecionamento após cancelamento
            
        Returns:
            O objeto de pagamento criado e a URL de checkout, ou (None, None) em caso de erro
        """
        # Verificar se o freelancer tem conta PayPal própria
        freelancer = fatura.pedido.servico.freelancer
        use_freelancer_account = False
        
        try:
            freelancer_detalhe = FreelancerDetalhe.objects.get(perfil__user=freelancer)
            if freelancer_detalhe.paypal_email and freelancer_detalhe.paypal_account_verified:
                use_freelancer_account = True
                
        except FreelancerDetalhe.DoesNotExist:
            pass
        
       
        PayPalService.setup_paypal()
        
       
        valor_total = float(fatura.valor)
        
       
        recipient_email = None
        if use_freelancer_account:
            recipient_email = freelancer_detalhe.paypal_email
            platform_fee_percentage = float(freelancer_detalhe.platform_fee_percentage)
            platform_fee = round(valor_total * (platform_fee_percentage / 100), 2)
            valor_freelancer = valor_total - platform_fee
        
        # Formatar valor para duas casas decimais
        valor_formatado = "{:.2f}".format(valor_total)
        
        # Preparar dados de pagamento
        payment_data = {
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": success_url,
                "cancel_url": cancel_url
            },
            "transactions": [{
                "amount": {
                    "total": valor_formatado,
                    "currency": "EUR"  # Moeda em euros
                },
                "description": f"Pagamento da fatura #{fatura.id} - {fatura.pedido.servico.nome}",
                "custom": f"fatura_{fatura.id}",  # Campo personalizado para identificar a fatura
            }]
        }
        
      
        if recipient_email:
            
            payment_data["transactions"][0]["payee"] = {
                "email": recipient_email
            }
            
           
            payment_data["transactions"][0]["platform_fee"] = {
                "percentage": float(freelancer_detalhe.platform_fee_percentage)
            }
        
        payment = paypalrestsdk.Payment(payment_data)
        
        try:
            if payment.create():
                # Guardar ID do pagamento na fatura
                fatura.paypal_payment_id = payment.id
                fatura.save(update_fields=['paypal_payment_id'])
                
                if recipient_email:
                    fatura.paypal_recipient_email = recipient_email
                    fatura.save(update_fields=['paypal_recipient_email'])
                
                for link in payment.links:
                    if link.rel == "approval_url":
                        return payment, link.href
                        
                return None, None
            else:
                print(f"Erro ao criar pagamento: {payment.error}")
                return None, None
        except Exception as e:
            print(f"Exceção ao criar pagamento PayPal: {str(e)}")
            return None, None

    @staticmethod
    def execute_payment(payment_id, payer_id):
        """
        Executa um pagamento aprovado pelo comprador.
        
        Args:
            payment_id: ID do pagamento aprovado
            payer_id: ID do pagador
            
        Returns:
            True se o pagamento foi executado com sucesso, False caso contrário
        """
        PayPalService.setup_paypal()
        
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            return True
        else:
            print(f"Erro ao executar pagamento: {payment.error}")
            return False
    
    @staticmethod
    def verify_payment_status(fatura):
        """
        Verifica o status de um pagamento existente.
        
        Args:
            fatura: Objeto da fatura com o ID do pagamento PayPal
            
        Returns:
            O status do pagamento (completed, pending, etc.) ou None se não encontrado
        """
        PayPalService.setup_paypal()
        
        if not fatura.paypal_payment_id:
            return None
        
        try:
            payment = paypalrestsdk.Payment.find(fatura.paypal_payment_id)
            
            # Obter o status da transação
            if hasattr(payment, 'transactions') and payment.transactions:
                for transaction in payment.transactions:
                    if hasattr(transaction, 'related_resources') and transaction.related_resources:
                        for resource in transaction.related_resources:
                            if hasattr(resource, 'sale') and resource.sale:
                                return resource.sale.state
            
            return payment.state
        except Exception as e:
            print(f"Erro ao verificar status do pagamento PayPal: {str(e)}")
            return None