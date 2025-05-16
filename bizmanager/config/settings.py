"""
Configurações do Django para o projeto BizManager.
"""

import os
import json
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-chave-secreta-para-desenvolvimento'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'daphne',  
    'channels',  
    'chat',  # Adicionada a vírgula aqui
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social_django',
    
    # Aplicações do projeto
    'autenticacao',  # A sua aplicação principal
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'social_django.middleware.SocialAuthExceptionMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social_django.context_processors.backends',
                'social_django.context_processors.login_redirect',
                'config.context_processors.stripe_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Europe/Lisbon'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files (Uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Custom User Model
AUTH_USER_MODEL = 'autenticacao.User'

# Authentication URLs
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'

# Mensagens
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
        },
        'autenticacao': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Configurações de Email 
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'kikonuesnnene@gmail.com' 
EMAIL_HOST_PASSWORD = 'isjl yyxj twfl cwna'  
DEFAULT_FROM_EMAIL = 'BizManager <kikonuesnnene@gmail.com>'  

# Configurações de sessão
SESSION_COOKIE_AGE = 86400  # 1 dia
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Configurações de segurança para desenvolvimento
CSRF_COOKIE_SECURE = False
SESSION_COOKIE_SECURE = False

# Configuração para autenticação social
AUTHENTICATION_BACKENDS = [
    'social_core.backends.google.GoogleOAuth2',
    'django.contrib.auth.backends.ModelBackend',
]

# Encontrar o ficheiro de credenciais OAuth
OAUTH_CREDENTIALS_FILE = None
possible_paths = [
    'google-oauth-credentials.json', 
    os.path.join(BASE_DIR, 'google-oauth-credentials.json'),
    os.path.join(os.path.dirname(BASE_DIR), 'google-oauth-credentials.json'),
]

for path in possible_paths:
    if os.path.exists(path):
        OAUTH_CREDENTIALS_FILE = path
        break

if OAUTH_CREDENTIALS_FILE:
    with open(OAUTH_CREDENTIALS_FILE, 'r') as f:
        google_oauth_config = json.load(f)
    
    # Obter credenciais do ficheiro
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = google_oauth_config['web']['client_id']
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = google_oauth_config['web']['client_secret']
else:
    print("AVISO: Ficheiro de credenciais OAuth não encontrado.")
    SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = ''
    SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = ''

# Âmbitos necessários
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']

# URLs de redirecionamento
SOCIAL_AUTH_LOGIN_REDIRECT_URL = '/dashboard/'
SOCIAL_AUTH_URL_NAMESPACE = 'social'

# Pipeline personalizado
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.user.create_user',
    'autenticacao.pipeline.guardar_perfil',  
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)

# Configurações do Stripe
STRIPE_PUBLIC_KEY = 'pk_test_51RDXwz2ZbcsqplEMFqF6Kr8Q1adEI83LyCSZ6yzZIf4lrlsOcTTUPAoaiCmsh4vb06yWfbKnWre9Kn2CWL5ORn4I00cqPFl6TW'
STRIPE_SECRET_KEY = 'sk_test_51RDXwz2ZbcsqplEMOveRcXCgqE804jiU9dFb5vdvXIe9JIV3Wajdabzs88Xdq0fOCYjXja1a5OT72TOf6cwAumsW00rYgqUZdR'

ALLOWED_HOSTS = ['192.168.1.95', 'localhost', '127.0.0.1']

# Configuração ASGI para WebSockets
ASGI_APPLICATION = 'config.asgi.application'

# Configuração do Canal Layer com Redis
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [('127.0.0.1', 6379)],
        },
    },
}

# Configurações do PayPal
PAYPAL_MODE = 'sandbox' 
PAYPAL_CLIENT_ID = 'AaftjgZYosOT-LW0QT3x1SVYGpkkChJsCaoM28zK-9FL4j44G0kgYtLyL-1_cY2hngkCOp_iaMcTFvcr'
PAYPAL_CLIENT_SECRET = 'EABmeZe1ACdRf1fps74cbEOCA-g_42kfv7ZMAQhjwkPcL5Me5Ei7Y3RrhSverIf7_gJiNDTmzwmWAmz_'