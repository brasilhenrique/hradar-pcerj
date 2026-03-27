import os
from pathlib import Path

# Caminho base do projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# SEGURANÇA: Chave secreta para produção
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-2eii!_-ufabygkwj+36t*7b9hpvs^5a*a0sv5392g2&3@8ncmh')

# DESATIVADO EM PRODUÇÃO
DEBUG = True

# Domínio do seu site no PythonAnywhere
ALLOWED_HOSTS = ['*']

# Definição dos Apps (Removido o browser_reload que só funciona localmente)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Seus apps principais
    'core',
    'tailwind',
    'theme',
]

# Middlewares (Removido o browser_reload)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'hradar_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'hradar_project.wsgi.application'

# Banco de Dados SQLite na raiz para o PythonAnywhere
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Internacionalização
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# --- CONFIGURAÇÃO DE ARQUIVOS ESTÁTICOS (PRODUÇÃO) ---
STATIC_URL = 'static/'

# Pasta onde os arquivos estáticos ficam durante o desenvolvimento
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Pasta para onde o Django enviará todos os estáticos no comando collectstatic
# É este caminho que você deve colocar na aba "Web" do PythonAnywhere
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Configuração do Tailwind
TAILWIND_APP_NAME = 'theme'

# Redirecionamento de Login
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = 'direcionar_usuario'
LOGOUT_REDIRECT_URL = '/login/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# O usuário será deslogado ao fechar o navegador/aba
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 600  # Expira em 10 min de inatividade para segurança extra
SESSION_SAVE_EVERY_REQUEST = True

# --- CONFIGURAÇÕES DE SEGURANÇA DE SESSÃO ---

# 1. Derruba o login assim que o navegador é fechado
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# 2. (Bônus de Segurança) Derruba o login por inatividade após 1 hora (3600 segundos)
SESSION_COOKIE_AGE = 3600