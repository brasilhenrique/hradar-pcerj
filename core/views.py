from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
import json
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.utils import timezone
import re
from .models import PerfilAgente, ServidorMonitorado, OrgaoMonitorado, TermoMonitorado, RegraClassificacao
from .services.parser import extrair_dados_bi, cruzar_dados

def eh_admin(user):
    return user.is_superuser

# =============================================================================
# ACESSO E PERFIL
# =============================================================================
@login_required
def direcionar_usuario(request):
    perfil, _ = PerfilAgente.objects.get_or_create(user=request.user)
    if perfil.primeiro_acesso:
        return redirect('primeiro_acesso')
    return redirect('index')

@login_required
def primeiro_acesso(request):
    perfil, _ = PerfilAgente.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        nova = request.POST.get('password')
        confirma = request.POST.get('confirm_password')
        aceita = request.POST.get('disclaimer')
        if aceita and nova and nova == confirma:
            request.user.set_password(nova)
            request.user.save()
            update_session_auth_hash(request, request.user)
            perfil.primeiro_acesso = False
            perfil.save()
            return redirect('index')
        messages.error(request, "Erro ao validar termos ou senhas.")
    return render(request, 'primeiro_acesso.html')

# =============================================================================
# DASHBOARD PRINCIPAL
# =============================================================================
@login_required
def index(request):
    servidores = ServidorMonitorado.objects.filter(agente=request.user).order_by('nome')
    orgaos = OrgaoMonitorado.objects.filter(agente=request.user)
    termos = TermoMonitorado.objects.filter(agente=request.user)
    regras_admin = RegraClassificacao.objects.all()

    alertas = request.session.get('alertas_salvos', None)

    if request.method == 'POST' and request.FILES:
        try:
            arquivo_pdf = list(request.FILES.values())[0]
            texto_extraido = extrair_dados_bi(arquivo_pdf)
            alertas = cruzar_dados(arquivo_pdf, texto_extraido, servidores, orgaos, termos, regras_admin)

            request.session['alertas_salvos'] = alertas

            encontrou = any([
                alertas.get('convocacoes'), alertas.get('servidores'), alertas.get('elogios'),
                alertas.get('alvos_transferidos'), alertas.get('entradas'), alertas.get('saidas'),
                alertas.get('movimentacoes_internas'), alertas.get('unidades'), alertas.get('termos_encontrados')
            ])

            if encontrou:
                messages.success(request, "Varredura concluída! Ocorrências detectadas.")
            else:
                messages.info(request, "Varredura concluída. Nenhuma citação encontrada.")
        except Exception as e:
            messages.error(request, f"Erro ao processar: {str(e)}")

    return render(request, 'index.html', {
        'servidores': servidores, 'orgaos': orgaos, 'alertas': alertas, 'hoje': timezone.now(),
    })

@login_required
def limpar_varredura(request):
    if 'alertas_salvos' in request.session:
        del request.session['alertas_salvos']
    return redirect('index')

# =============================================================================
# WATCHLIST — SERVIDORES E UNIDADES
# =============================================================================
@login_required
def lista_servidores(request):
    lista = ServidorMonitorado.objects.filter(agente=request.user).order_by('unidade', 'nome')
    return render(request, 'meus_servidores.html', {'servidores': lista})

@login_required
def criar_servidor(request):
    if request.method == 'POST':
        nome = request.POST.get('nome', '').upper().strip()
        id_func_raw = request.POST.get('id_funcional', '').strip()
        id_func = re.sub(r'\D', '', id_func_raw).lstrip('0')
        # Captura a unidade do form, se não tiver nada, joga pra PENDENTE
        unidade = request.POST.get('unidade', '').upper().strip() or 'PENDENTE'

        if nome and id_func:
            srv, criado = ServidorMonitorado.objects.get_or_create(agente=request.user, nome=nome, id_funcional=id_func)

            # Se a lotação informada for diferente da que está no banco, atualiza
            if srv.unidade != unidade and unidade != 'PENDENTE':
                srv.unidade = unidade
                srv.save()

            if criado:
                messages.success(request, f"{nome} adicionado à monitorização com sucesso.")
            else:
                messages.warning(request, f"Servidor {nome} já constava na lista e foi atualizado.")
        else:
            messages.error(request, "Nome e ID funcional são obrigatórios.")
    return redirect('lista_servidores')

@login_required
def editar_servidor(request, id):
    servidor = get_object_or_404(ServidorMonitorado, id=id, agente=request.user)
    if request.method == 'POST':
        nome = request.POST.get('nome', '').upper().strip()
        id_func_raw = request.POST.get('id_funcional', '').strip()
        id_func = re.sub(r'\D', '', id_func_raw).lstrip('0')
        # Captura a unidade do form; se vier vazio, coloca 'PENDENTE'
        unidade = request.POST.get('unidade', '').upper().strip() or 'PENDENTE'

        if nome and id_func:
            servidor.nome = nome
            servidor.id_funcional = id_func
            servidor.unidade = unidade
            servidor.save()
            messages.success(request, f"Dados de {nome} atualizados com sucesso.")
            return redirect('lista_servidores')
        else:
            messages.error(request, "Nome e ID funcional são obrigatórios.")

    return render(request, 'servidor_form.html', {'servidor': servidor})

@login_required
def deletar_alvo(request, tipo, id):
    if tipo == 'servidor':
        get_object_or_404(ServidorMonitorado, id=id, agente=request.user).delete()
        messages.success(request, "Servidor removido da monitorização.")
        return redirect('lista_servidores')
    elif tipo == 'unidade':
        get_object_or_404(OrgaoMonitorado, id=id, agente=request.user).delete()
        messages.success(request, "Unidade removida da monitorização.")
        return redirect('lista_unidades')
    elif tipo == 'termo':
        get_object_or_404(TermoMonitorado, id=id, agente=request.user).delete()
        messages.success(request, "Palavra-chave removida do radar.")
        return redirect('lista_termos')
    return redirect('index')


# =============================================================================
# WATCHLIST — PALAVRAS-CHAVE (ACOMPANHAMENTO ESPECIAL)
# =============================================================================

@login_required
def lista_termos(request):
    lista = TermoMonitorado.objects.filter(agente=request.user).order_by('termo')
    return render(request, 'minhas_palavras.html', {'termos': lista})

@login_required
def criar_termo(request):
    if request.method == 'POST':
        termo = request.POST.get('termo', '').upper().strip()
        if termo:
            _, criado = TermoMonitorado.objects.get_or_create(agente=request.user, termo=termo)
            if criado:
                messages.success(request, f"A palavra-chave '{termo}' foi adicionada.")
            else:
                messages.warning(request, f"A palavra-chave '{termo}' já estava na sua lista.")
        else:
            messages.error(request, "A palavra é obrigatória.")
    return redirect('lista_termos')

@login_required
def lista_unidades(request):
    lista = OrgaoMonitorado.objects.filter(agente=request.user).order_by('sigla_orgao')
    return render(request, 'minhas_unidades.html', {'unidades': lista})

@login_required
def criar_unidade(request):
    if request.method == 'POST':
        sigla = request.POST.get('sigla', '').upper().strip()
        if sigla:
            _, criado = OrgaoMonitorado.objects.get_or_create(agente=request.user, sigla_orgao=sigla)
            if criado:
                messages.success(request, f"Unidade '{sigla}' adicionada.")
            else:
                messages.warning(request, f"Unidade '{sigla}' já monitorada.")
    return redirect('lista_unidades')

# =============================================================================
# AÇÕES DE TRANSFERÊNCIA E DELEÇÃO EM MASSA
# =============================================================================
@login_required
def processar_transferencia(request):
    if request.method == 'POST':
        acao = request.POST.get('acao')
        nome = request.POST.get('nome', '').upper().strip()
        id_func_raw = request.POST.get('id_funcional', '').strip()
        servidor_id = request.POST.get('servidor_id')

        id_func = re.sub(r'\D', '', id_func_raw).lstrip('0')
        novo_db_id = None

        if acao == 'remover' and servidor_id:
            ServidorMonitorado.objects.filter(id=servidor_id, agente=request.user).delete()
            messages.success(request, f"{nome} removido da Watchlist.")

        elif acao == 'adicionar' and nome and id_func:
            srv, criado = ServidorMonitorado.objects.get_or_create(agente=request.user, nome=nome, id_funcional=id_func)
            novo_db_id = srv.id
            if criado:
                messages.success(request, f"{nome} adicionado à Watchlist.")
            else:
                messages.warning(request, f"{nome} já está na Watchlist.")

        elif acao == 'atualizar':
            messages.success(request, f"Lotação de {nome} reconhecida e atualizada.")

        if 'alertas_salvos' in request.session:
            alertas = request.session['alertas_salvos']
            for cat in ['entradas', 'saidas', 'movimentacoes_internas', 'alvos_transferidos']:
                for t in alertas.get(cat, []):
                    if t.get('ID_LIMPO') == id_func:
                        if acao == 'adicionar' and novo_db_id:
                            t['DB_ID'] = novo_db_id
                        elif acao == 'remover':
                            t.pop('DB_ID', None)
            request.session['alertas_salvos'] = alertas
            request.session.modified = True

    return redirect('index')

@login_required
def apagar_todos_servidores(request):
    if request.method == 'POST':
        count, _ = ServidorMonitorado.objects.filter(agente=request.user).delete()
        messages.success(request, f"Base zerada! {count} servidores foram removidos da Watchlist.")
    return redirect('lista_servidores')

# =============================================================================
# CARGA EM LOTE E ADMINISTRAÇÃO (MANTIDOS)
# =============================================================================
@login_required
@login_required
def carga_em_lote(request):
    if request.method == 'POST':
        # 1. Correção do nome do campo: agora bate exatamente com o HTML
        texto = request.POST.get('lista_servidores', '').strip()

        if not texto:
            return redirect('carga_em_lote')

        adicionados, ignorados, erros = 0, 0, 0

        for linha in texto.splitlines():
            if not linha.strip():
                continue

            # 2. Lendo o ponto-e-vírgula da sua lista
            partes = linha.split(';')

            if len(partes) < 2:
                erros += 1
                continue

            nome_bruto = partes[0].strip().upper()
            id_func = re.sub(r'\D', '', partes[1].strip()).lstrip('0')

            # 3. Capturando a lotação (se houver um terceiro item na linha)
            unidade = partes[2].strip().upper() if len(partes) > 2 else 'PENDENTE'

            if not nome_bruto or not id_func:
                erros += 1
                continue

            # 4. Separando o tratamento protocolar do nome (se vier escrito na lista)
            tratamento = ''
            if nome_bruto.startswith('DR.'):
                tratamento = 'Dr.'
                nome = re.sub(r'^DR\.\s*', '', nome_bruto).strip()
            elif nome_bruto.startswith('DRA.') or nome_bruto.startswith('DRª.'):
                tratamento = 'Drª.'
                nome = re.sub(r'^DR[Aª]\.\s*', '', nome_bruto).strip()
            else:
                nome = nome_bruto

            # 5. Salvando ou atualizando no banco de dados
            srv, criado = ServidorMonitorado.objects.get_or_create(
                agente=request.user,
                id_funcional=id_func,
                defaults={'nome': nome, 'tratamento': tratamento, 'unidade': unidade}
            )

            if criado:
                adicionados += 1
            else:
                # Atualiza os dados de quem já existe caso a nova lista traga informações mais frescas
                atualizou = False
                if srv.nome != nome:
                    srv.nome = nome
                    atualizou = True
                if srv.tratamento != tratamento:
                    srv.tratamento = tratamento
                    atualizou = True
                if unidade != 'PENDENTE' and srv.unidade != unidade:
                    srv.unidade = unidade
                    atualizou = True

                if atualizou:
                    srv.save()

                ignorados += 1

        messages.success(request, f"Lote processado: {adicionados} novos, {ignorados} atualizados/existentes, {erros} erros na leitura.")
        return redirect('lista_servidores')

    return render(request, 'carga_lote_form.html')

@user_passes_test(eh_admin)
def lista_usuarios(request):
    users = User.objects.all().order_by('-is_superuser', 'first_name')
    return render(request, 'usuarios_lista.html', {'usuarios': users})

@user_passes_test(eh_admin)
def criar_usuario(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()

        # Evita travar na tela preta se o usuário já existir
        if User.objects.filter(username=username).exists():
            messages.error(request, f"O acesso para {username} já existe!")
            return redirect('lista_usuarios')

        # O pulo do gato: tenta pegar a senha. Se vier vazia, usa o próprio ID como senha!
        senha_bruta = request.POST.get('password', '').strip()
        if not senha_bruta:
            senha_bruta = username

        # O create_user já faz o hash de segurança automaticamente
        u = User.objects.create_user(
            username=username,
            password=senha_bruta,
            first_name=request.POST.get('first_name', '').strip()
        )

        if request.POST.get('is_admin') == 'on':
            u.is_superuser = u.is_staff = True
            u.save()

        messages.success(request, f"Acesso criado! Login: {username} | Senha: {senha_bruta}")
        return redirect('lista_usuarios')

    return render(request, 'usuarios_form.html')

@user_passes_test(eh_admin)
def editar_usuario(request, id):
    u = get_object_or_404(User, id=id)
    if request.method == 'POST':
        u.username = request.POST.get('username', '').strip()
        if request.POST.get('password'): u.set_password(request.POST.get('password', ''))
        u.save()
        return redirect('lista_usuarios')
    return render(request, 'usuarios_form.html', {'usuario': u})

@user_passes_test(eh_admin)
def deletar_usuario(request, id):
    u = get_object_or_404(User, id=id)
    if not u.is_superuser: u.delete()
    return redirect('lista_usuarios')

@login_required
def atualizar_tratamento_ajax(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            servidor = get_object_or_404(ServidorMonitorado, id=data.get('servidor_id'), agente=request.user)
            servidor.tratamento = data.get('tratamento', '')
            servidor.save()
            return JsonResponse({'status': 'sucesso'})
        except Exception as e:
            return JsonResponse({'status': 'erro', 'mensagem': str(e)}, status=400)
    return JsonResponse({'status': 'invalido'}, status=400)