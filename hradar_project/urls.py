from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Rota para o auto-reload do Tailwind
    # path('__reload__/', include('django_browser_reload.urls')),
    path('limpar/', views.limpar_varredura, name='limpar_varredura'),

    # --- AUTENTICAÇÃO ---
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('primeiro-acesso/', views.primeiro_acesso, name='primeiro_acesso'),

    # Rota raiz: direciona para Dashboard ou Login dependendo do status
    path('', views.direcionar_usuario, name='direcionar_usuario'),

    # --- DASHBOARD (RADAR) ---
    path('radar/', views.index, name='index'),
    path('transferencia/', views.processar_transferencia, name='processar_transferencia'),

    # ROTA DE HOMOLOGAÇÃO DO MOTOR V2
    # Rota de teste V2 removida

    # --- GESTÃO DE SERVIDORES ---
    path('servidores/', views.lista_servidores, name='lista_servidores'),
    path('servidores/novo/', views.criar_servidor, name='criar_servidor'), # O link que faltava!
    path('servidores/atualizar-tratamento/', views.atualizar_tratamento_ajax, name='atualizar_tratamento_ajax'),
    path('servidores/editar/<int:id>/', views.editar_servidor, name='editar_servidor'),
    path('servidores/lote/', views.carga_em_lote, name='carga_em_lote'),
    path('remover/<str:tipo>/<int:id>/', views.deletar_alvo, name='deletar_alvo'),

    # --- GESTÃO DE UNIDADES ---
    path('unidades/', views.lista_unidades, name='lista_unidades'),
    path('unidades/nova/', views.criar_unidade, name='criar_unidade'),

    # --- GESTÃO DE PALAVRAS-CHAVE ---
    path('palavras/', views.lista_termos, name='lista_termos'),
    path('palavras/criar/', views.criar_termo, name='criar_termo'),

    # --- ADMINISTRAÇÃO DE USUÁRIOS ---
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/novo/', views.criar_usuario, name='criar_usuario'),
    path('usuarios/editar/<int:id>/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/remover/<int:id>/', views.deletar_usuario, name='deletar_usuario'),

    path('apagar-todos/', views.apagar_todos_servidores, name='apagar_todos_servidores'),
]