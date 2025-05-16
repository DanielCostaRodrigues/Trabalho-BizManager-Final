from django.db import migrations

def atualizar_status_pedidos(apps, schema_editor):
    # Obter o modelo Pedido do estado atual das migrações
    Pedido = apps.get_model('autenticacao', 'Pedido')
    
    # Atualizar todos os pedidos com status 'aceito' para 'aceite'
    for pedido in Pedido.objects.filter(status='aceito'):
        pedido.status = 'aceite'
        pedido.save()
        
    # Imprimir informação sobre as atualizações
    print(f"Pedidos atualizados de 'aceito' para 'aceite': {Pedido.objects.filter(status='aceite').count()}")

class Migration(migrations.Migration):

    dependencies = [
        ('autenticacao', '0004_alter_pedido_status'),  # Substitua pelo nome da última migração
    ]

    operations = [
        migrations.RunPython(atualizar_status_pedidos),
    ]