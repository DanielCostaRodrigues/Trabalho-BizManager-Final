# BizManager - Documentação Técnica

## Visão Geral
BizManager é uma plataforma web all-in-one para freelancers e pequenos empreendedores, desenvolvida com Django. A aplicação oferece funcionalidades como gestão de serviços, pedidos, pagamentos e comunicação em tempo real.

## Requisitos do Sistema
- Python 3.8+
- Redis Server (para WebSockets)
- Navegador moderno com suporte a HTML5/CSS3/JavaScript

## ⚠️ Estrutura de Diretórios e Execução
**IMPORTANTE**: O projeto está organizado numa estrutura de pastas aninhadas. Para o correto funcionamento, deverá:
1. Navegar primeiro para a pasta `bizmanager`
2. Em seguida, navegar para a segunda pasta `bizmanager` onde está o ficheiro `manage.py`
3. Executar todos os comandos a partir deste segundo diretório

Esta estrutura de diretório duplo é essencial para o funcionamento do projeto!

## Instalação

### 1. Clonar o Repositório
```bash
git clone https://github.com/seu-utilizador/bizmanager.git
```

### 2. Navegar para o Diretório Correto
A estrutura do projeto requer uma navegação específica devido à organização dos diretórios. O projeto está dentro de uma pasta "bizmanager" que por sua vez contém outra pasta "bizmanager" com os ficheiros do projeto.

```bash
# Primeiro, entre na pasta principal
cd bizmanager

# Depois, entre na pasta do projeto
cd bizmanager
```

⚠️ **IMPORTANTE**: A navegação correta dos diretórios é essencial para o funcionamento do projeto. Deverá estar dentro do segundo diretório "bizmanager" para executar o projeto corretamente, onde estão localizados os ficheiros manage.py, db.sqlite3 e as pastas da aplicação.

### 3. Configurar Ambiente Virtual
```bash
# Criar ambiente virtual (dentro do segundo diretório bizmanager)
python -m venv venv

# Ativar ambiente virtual
# No Windows:
venv\Scripts\activate
# No Linux/macOS:
source venv/bin/activate
```

### 4. Instalar Dependências
```bash
# Instalar todas as dependências necessárias
pip install django daphne channels channels-redis social-auth-app-django stripe paypalrestsdk
```

Alternativamente, pode usar o ficheiro requirements.txt:
```bash
pip install -r requirements.txt
```

### 5. Configurar a Base de Dados
```bash
# Executar migrações
python manage.py makemigrations
python manage.py migrate
```

### 6. Criar Superutilizador (Opcional)
```bash
python manage.py createsuperuser
```

### 7. Iniciar o Redis Server
```bash
# No Ubuntu/Debian
sudo service redis-server start

# No macOS (com Homebrew)
brew services start redis

# No Windows (usando Redis para Windows)
# Iniciar o executável redis-server.exe
```

### 8. Executar o Servidor de Desenvolvimento
```bash
# Certifique-se de estar no diretório correto (segundo diretório bizmanager)
# onde está localizado o ficheiro manage.py
python manage.py runserver
```

O projeto estará disponível em: http://127.0.0.1:8000/

⚠️ **IMPORTANTE**: Se encontrar erros ao executar o servidor, verifique se:
1. Está no diretório correto (o segundo diretório "bizmanager" onde está o manage.py)
2. Todas as dependências foram instaladas corretamente
3. O Redis Server está em execução (necessário para o chat em tempo real)

## Guia Rápido para Execução

1. Navegue até ao diretório do projeto:
   ```bash
   cd bizmanager
   cd bizmanager
   ```

2. Ative o ambiente virtual:
   ```bash
   # Windows
   venv\Scripts\activate
   # Linux/macOS
   source venv/bin/activate
   ```

3. Execute o servidor:
   ```bash
   python manage.py runserver
   ```

## Estrutura de Diretórios
```
bizmanager/                      # Diretório principal do projeto
└── bizmanager/                  # Diretório da aplicação Django
    ├── autenticacao/            # App de autenticação e gestão de utilizadores
    ├── chat/                    # App para comunicação em tempo real
    ├── config/                  # Configurações principais do projeto
    │   ├── settings.py          # Configurações Django
    │   ├── urls.py              # URLs do projeto
    │   ├── asgi.py              # Configuração ASGI (WebSockets)
    │   └── wsgi.py              # Configuração WSGI
    ├── media/                   # Ficheiros carregados pelos utilizadores
    ├── static/                  # Ficheiros estáticos
    ├── templates/               # Templates HTML
    ├── venv/                    # Ambiente virtual (será criado durante a instalação)
    ├── bizmanager              # Ficheiro executável do projeto
    ├── credentials              # Ficheiro de credenciais
    ├── db.sqlite3               # Base de dados SQLite
    ├── debug.log                # Ficheiro de log para debugging
    ├── google-oauth-credentials.json  # Credenciais do Google OAuth
    └── manage.py                # Script de gestão Django
└── tokens/                      # Diretório para tokens (se aplicável)
```

⚠️ **NOTA**: Certifique-se de que está a trabalhar no diretório correto. Todas as operações devem ser realizadas dentro do segundo diretório "bizmanager" onde está o ficheiro manage.py.

## Configurações Adicionais

### Credenciais Google OAuth
1. Coloque o ficheiro `google-oauth-credentials.json` na raiz do projeto
2. Verifique se os URIs de redirecionamento estão configurados:
   - `http://localhost:8000/complete/google-oauth2/`
   - `http://127.0.0.1:8000/complete/google-oauth2/`

### Configuração do Stripe e PayPal
As chaves API para serviços de pagamento já estão configuradas em `settings.py` para ambiente de desenvolvimento.

## Dados de Acesso
- **Admin Django**: http://127.0.0.1:8000/admin/
  - Utilizador: kikonunes.2004@hotmail.com
  - Palavra-passe: 1212

- **Conta de Teste Freelancer**:
  - Email: admin@gmail.com
  - Palavra-passe: @Bizmanager

- **Conta de Teste Cliente**:
  - Email: kikonunes.2004@hotmail.com
  - Palavra-passe: 1212

## Resolução de Problemas

### Problemas com WebSockets
Se encontrar problemas com o chat em tempo real:
1. Verifique se o Redis Server está em execução
2. Reinicie o serviço Daphne: `daphne -p 8001 config.asgi:application`

### Erros de Autenticação Social
Verifique o ficheiro de log `debug.log` na raiz do projeto para detalhes sobre erros de autenticação.

## Notas de Desenvolvimento
- O projeto utiliza a base de dados SQLite para facilitar o desenvolvimento, mas está preparado para migração para PostgreSQL em produção.
- As chaves API de teste para Stripe e PayPal estão incluídas no settings.py apenas para fins de desenvolvimento.

## Implantação em Produção
Para implantação em ambiente de produção, considere:
1. Alterar DEBUG para False em settings.py
2. Configurar uma base de dados PostgreSQL
3. Usar Nginx como proxy reverso
4. Utilizar Gunicorn ou uWSGI para servir a aplicação Django
5. Configurar certificados SSL
6. Atualizar as chaves API para produção

---

**Desenvolvido por:**
- Francisco Nunes (2022147843)
- Daniel Rodrigues (2022103386)

*Projeto e Desenvolvimento Informático - 2025*