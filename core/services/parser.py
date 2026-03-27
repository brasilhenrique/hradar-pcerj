import pypdf
import pdfplumber
import re
import time
from io import BytesIO

# ==========================================
# ÍMÃS DE EXTRAÇÃO (REGEX BLINDADAS)
# ==========================================

# Captura horas simples e intervalos flexíveis: 14:00, 14h30m, 14.00h, 09:00h às 17:00h
REGEX_HORA = re.compile(r'(?i)\b\d{1,2}[:h;]\d{2}[mh]?(?:\s*(?:às|as|-|/|a|e)\s*\d{1,2}[:h;]\d{2}[mh]?)?\b')

# Captura datas em múltiplos formatos: 12/12/2012, 24-03-26, 10.05.24
REGEX_DATA = re.compile(r'\b\d{2,4}[-./]\d{2}[-./]\d{2,4}\b')

# Captura CNJ (Tribunais), padrão SAD/PAD e internos da CGPOL
REGEX_PROCESSO = re.compile(
    r'(\*?\s*\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}|' # CNJ com ou sem asterisco (TJ-RJ, TJ-SP, etc)
    r'SEI-\d{6}/\d{6}/\d{4}|' # Processos SEI
    r'(?:SAD|PAD)\s*\d{2,3}[-/]\d{2,5}/\d{2,4}|' # Ex: SAD 404-00197/2023
    r'PAD\s+\d{2,4}/\d{2,4}|' # Ex: PAD 30/23
    r'\d{3}-\d{5}/\d{4}|' # Ex: 404-00069/2022 ou 411-00062/2026
    r'\d{4,6}[-/]\d{4,6}/\d{4}' # Ex: 9179-1404/2025 ou 006053/1404/2024
    r')', re.IGNORECASE
)

# --- BANCO DE LOCAIS (Comarcas do RJ + Nomes Compostos, Abreviações e Outros Estados) ---
COMARCAS = (
    r'(?:Rio de Janeiro|Capital|F[óo]rum|1ª Vara Especializada|'
    r'(?:Regional\s+)?(?:Bangu|Barra da Tijuca|Campo Grande|Ilha do Governador|Jacarepagu[áa]|Leopoldina|Madureira|M[ée]ier|Pavuna|Santa Cruz|Vila Inhomirim|Itaipava|Alc[âa]ntara|Regi[ãa]o Oce[âa]nica)|'
    r'Angra dos Reis|Araruama|Arraial do Cabo|Barra do Pira[íi]|Barra Mansa|Belford Roxo|Bom Jardim|'
    r'Bom Jesus d[eo] Itabapoana|B\.\s*J\.\s*do\s*Itabapoana|B[úu]zios|(?:Arma[çc][ãa]o\s+dos\s+)?B[úu]zios|Cabo Frio|Cachoeiras de Macacu|'
    r'Cambuci(?:\s*/\s*S[ãa]o\s*Jos[ée]\s*de\s*Ub[áa])?|Campos dos Goytacazes|Cantagalo|Carapebus(?:\s*/\s*Quissam[ãa])?|Quissam[ãa]|Carmo|'
    r'Casimiro de Abreu|Concei[çc][ãa]o de Macabu|Cordeiro|Duas Barras|Duque de Caxias|'
    r'Engenheiro Paulo de Frontin|Eng\.\s*Paulo de Frontin|Guapimirim|Iguaba Grande|Itabora[íi]|'
    r'Itagua[íi]|Italva(?:\s*/\s*Cardoso\s*Moreira)?|Itaocara|Itaperuna|Itatiaia|Japeri|Laje do Muria[ée]|Maca[ée]|Mag[ée]|'
    r'Mangaratiba|Maric[áa]|Mendes|Mesquita|Miguel Pereira|Miracema|Natividade|Nil[óo]polis|Niter[óo]i|'
    r'Nova Friburgo|Nova Igua[çc]u(?:/Mesquita)?|Paracambi|Para[íi]ba do Sul|Paraty|Paty do Alferes|'
    r'Petr[óo]polis|Pinheiral|Pira[íi]|Porci[úu]ncula|Porto Real(?:(?:\s*/\s*|\s+e\s+)Quatis)?|Queimados|Resende|Rio Bonito|'
    r'Rio Claro|Rio das Flores|Rio das Ostras|Santa Maria Madalena|(?:Santo\s*Ant[ôo]nio|S\.\s*A\.)\s*de\s*P[áa]dua|'
    r'S[ãa]o Fid[ée]lis|S[ãa]o Francisco d[eo] Itabapoana|S\.\s*F\.\s*de\s*Itabapoana|S[ãa]o Gon[çc]alo|'
    r'S[ãa]o Jo[ãa]o da Barra|S[ãa]o Jo[ãa]o de Meriti|S\.\s*J\.\s*de\s*Meriti|S[ãa]o Jos[ée] do Vale do Rio Preto|'
    r'S[ãa]o Pedro da Aldeia|S[ãa]o Sebasti[ãa]o do Alto|Sapucaia|Saquarema|Serop[ée]dica|Silva Jardim|'
    r'Sumidouro|Teres[óo]polis|Trajano de Moraes|Tr[êe]s Rios|Valen[çc]a|Vassouras|Volta Redonda|Cruzeiro\s*[-/]?\s*SP)'
)

TIPO_VARA = r'(?:Vara|VCrs?|V\.\s*[UÚ]nica|Unica|Juizado|Juiz\.?|JECrim|JEACrim|ORCRIM|Auditoria\s+Militar|CRP|CPIA|Central\s*de\s*Processamento(?:Criminal)?|SRF|Carteira\s*Funcional)'

# O \b antes do \d garante que ele não pegue o final de um ano (ex: 026 de 2026)
REGEX_LOCAL = re.compile(
    rf'({COMARCAS}[a-zA-ZÀ-ÿ\.\s\-/]*(?:-\s*)?(?:(?:[IVX]+|\b\d{{1,3}}[ªº°aAoO]?)\s*)?{TIPO_VARA}[a-zA-ZÀ-ÿ\.\s\-\/\*]*|'
    rf'(?:(?:[IVX]+|\b\d{{1,3}}[ªº°aAoO]?)\s*)?{TIPO_VARA}[a-zA-ZÀ-ÿ\.\s\-\/\*]*|'
    rf'[Cc][Gg][Pp][Oo][Ll].{{0,20}}?Sl\s*\d+)',
    re.IGNORECASE
)

REGEX_TITULOS_MOV = re.compile(r'(REMOÇ|LOTAÇ)(ÃO|ÕES)\s+DE\s+(AGENTE|AUTORIDADE)(S)?', re.IGNORECASE)
REGEX_PALAVRAS_CONVOCACAO = re.compile(
    r'\b(Vara|VCr|Juizado|[UuÚú]nica|JECrim|JEACrim|F[óo]rum|Auditoria|Justi[çc]a|CGPOL|CRP|SAD|PAD|Sindic[âa]ncia|Corregedoria|MP|Minist[é]rio P[úu]blico|Audi[êe]ncia|Depor|Central|Processamento|Criminal|Juventude|Mulher|Militar|PMERJ|ORCRIM|DEAC|Idoso|VIJCAP|Crian[çc]a|CPIA|SRF|DHBF|V[UÚúu])\b',
    re.IGNORECASE
)

# ==========================================
# FUNÇÕES CORE E PRÉ-PROCESSAMENTO
# ==========================================

def extrair_com_prioridade(regex, contexto_foco, contexto_amplo):
    matches_foco = regex.findall(contexto_foco)
    if matches_foco:
        unicos_foco = list(dict.fromkeys(matches_foco))
        if len(unicos_foco) == 1: return unicos_foco[0]

    matches_amplo = regex.findall(contexto_amplo)
    if matches_amplo:
        unicos_amplo = list(dict.fromkeys(matches_amplo))
        if len(unicos_amplo) == 1: return unicos_amplo[0]

    return "Verificar no BI"

def gerar_mensagem_whatsapp_convocacao(nome_servidor, tratamento, contexto_foco, contexto_amplo, num_bi):
    # Extração primária usando os Ímãs (Regex)
    hora = extrair_com_prioridade(REGEX_HORA, contexto_foco, contexto_amplo)
    data = extrair_com_prioridade(REGEX_DATA, contexto_foco, contexto_amplo)
    local = extrair_com_prioridade(REGEX_LOCAL, contexto_foco, contexto_amplo)
    processo = extrair_com_prioridade(REGEX_PROCESSO, contexto_foco, contexto_amplo)

    # --- O FALLBACK SUPREMO (A TÉCNICA DO SANDUÍCHE EVOLUÍDO) ---
    # Se o Ímã de Local falhou (ou deu conflito) e temos o Processo, ativamos o plano B.
    if local == "Verificar no BI" and processo != "Verificar no BI":
        proc_esc = re.escape(processo)

        # Tentativa 1: O Sanduíche Tradicional (Fatia de cima: Processo | Fatia de baixo: Data)
        if data != "Verificar no BI":
            data_esc = re.escape(data)
            match_sanduiche = re.search(rf'{proc_esc}\s+(.+?)\s+{data_esc}', contexto_amplo)
            if match_sanduiche:
                local = match_sanduiche.group(1).strip()

        # Tentativa 2: O Sanduíche Aberto (Fatia de cima: Processo | Fatia de baixo: Hora) -> A SALVAÇÃO DO HÉRIK!
        if local == "Verificar no BI" and hora != "Verificar no BI":
            hora_esc = re.escape(hora)
            match_sanduiche_hora = re.search(rf'{proc_esc}\s+(.+?)\s+{hora_esc}', contexto_amplo)
            if match_sanduiche_hora:
                local = match_sanduiche_hora.group(1).strip()
    # ----------------------------------------------------

    # Formatação do texto final para o WhatsApp
    texto_bi = f" no BI nº {num_bi}" if num_bi else " no BI"
    prefixo = f"{tratamento} " if tratamento else ""

    return (
        f"🚨 *COMPARECIMENTO PARA DEPOR*\n\n"
        f"👮‍♂️ *Servidor:* {prefixo}{nome_servidor}\n"
        f"🏛️ *Local:* {local.strip()}\n"
        f"📄 *Processo:* {processo}\n"
        f"📅 *Data:* {data}\n"
        f"⏰ *Horário:* {hora}\n\n"
        f"📌 *Por favor, confira os dados da convocação{texto_bi}.*\n\n"
        f"✅ *FAVOR RESPONDER COM O \"CIENTE\".*"
    )

def extrair_dados_bi(arquivo_pdf):
    arquivo_pdf.seek(0)
    texto_acumulado = []

    def processar_texto(conteudo_pagina):
        if not conteudo_pagina: return
        linhas = conteudo_pagina.split('\n')
        for l in linhas:
            l_clean = l.strip()
            if not l_clean: continue
            if "BOLETIM INFORMATIVO" in l_clean.upper(): continue
            if "RIO DE JANEIRO" in l_clean.upper(): continue
            if re.match(r'^\d{3}/\d{1,2}$', l_clean): continue
            texto_acumulado.append(l_clean)

    try:
        reader = pypdf.PdfReader(arquivo_pdf)
        for page in reader.pages:
            processar_texto(page.extract_text())
    except Exception as e:
        print(f"[HRADAR AVISO] PyPDF falhou ({e}). Acionando Motor Blindado (Plumber)...")
        arquivo_pdf.seek(0)
        try:
            with pdfplumber.open(arquivo_pdf) as pdf:
                for page in pdf.pages:
                    processar_texto(page.extract_text())
        except Exception as e2:
            raise Exception(f"Arquivo severamente corrompido: {e2}")

    # Retorna o texto cru linha a linha para ser varrido pela Janela Deslizante
    return "\n".join(texto_acumulado)

def limpar_nome_dr(nome):
    if not nome: return ""
    return re.sub(r'^(Dr[aª]?\.?\s*)', '', nome.strip(), flags=re.IGNORECASE)

def limpar_id(id_texto):
    if not id_texto: return ""
    return re.sub(r'\D', '', str(id_texto)).lstrip('0')

def criar_regex_id(id_limpo):
    separadores = r'[\.\-\s]*'
    return r'(?<!\d)0*' + separadores.join(list(id_limpo)) + r'(?!\d)'

def criar_regex_unidade(sigla):
    sigla_base = re.sub(r'(\d+)[ªº°aAoO]?', r'\1', sigla.strip().upper())
    partes = sigla_base.split()
    regex_parts = []
    for p in partes:
        if p.isdigit(): regex_parts.append(rf"0*{p}(?:[ªº°aAoO])?")
        else: regex_parts.append(re.escape(p))
    padrao = r'\s*'.join(regex_parts)
    return re.compile(rf'\b{padrao}\b', re.IGNORECASE)

def gerar_mensagem_whatsapp_mencao(nome_servidor, tratamento, id_servidor, contexto, num_bi, etiqueta):
    texto_bi = f" {num_bi}" if num_bi else ""
    prefixo = f"{tratamento} " if tratamento else ""
    return f"🚨 *ALERTA:* CITAÇÃO NO BI{texto_bi}\n👤 *SERVIDOR:* {prefixo}{nome_servidor}, ID nº {id_servidor}\n📌 *CATEGORIA:* {etiqueta}"

def realcar_html(texto, termo):
    if not termo or not texto: return texto
    pattern = re.compile(re.escape(str(termo)), re.IGNORECASE)
    return pattern.sub(lambda m: f'<span class="bg-yellow-200 text-black font-bold px-1 rounded">{m.group(0)}</span>', texto)

def extrair_remocoes_estruturadas(arquivo_pdf):
    arquivo_pdf.seek(0)
    transferencias = []
    cargos = [
        r'Oficial de Pol[íi]cia Civil', r'Delegado de Pol[íi]cia', r'Comiss[áa]rio de Pol[íi]cia',
        r'Perito Criminal', r'Perito Legista', r'Perito Papiloscopista', r'Inspetor de Pol[íi]cia',
        r'Investigador de Pol[íi]cia', r'T[é]cnico Policial de Necropsia', r'Auxiliar Policial de Necropsia',
        r'Piloto Policial', r'Oficial de Cart[óo]rio Policial', r'Agente de Pol[íi]cia Cient[íi]fica'
    ]
    regex_cargos_str = r'(' + '|'.join(cargos) + r')'
    reg_completo = re.compile(r'^(.*?)\s+' + regex_cargos_str + r'\s+([\d\.\-]+)\s+(.*?)\s+(SEI-\d{6}/\d{6}/\d{4})$', re.IGNORECASE)
    reg_lotacao = re.compile(r'^(.*?)\s+' + regex_cargos_str + r'\s+([\d\.\-]+)\s+(SEI-\d{6}/\d{6}/\d{4})$', re.IGNORECASE)
    padrao_destino = re.compile(r'^(\d{1,3}[ªº°aAoO]?\s*[A-Za-z]+|DEAM\s+[A-Za-zÀ-ÿ]+|DH-?[A-Za-zÀ-ÿ]+|DC-[A-Za-zÀ-ÿ]+|[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?)\s+(.*)$', re.IGNORECASE)

    pdf_para_plumber = None
    try:
        paginas_alvo = []
        reader = pypdf.PdfReader(arquivo_pdf)
        total_paginas = len(reader.pages)
        for i, page in enumerate(reader.pages):
            txt = page.extract_text()
            if txt and REGEX_TITULOS_MOV.search(txt):
                paginas_alvo.append(i)
                if i + 1 < total_paginas: paginas_alvo.append(i + 1)

        if not paginas_alvo: return []
        paginas_alvo = sorted(list(set(paginas_alvo)))

        writer = pypdf.PdfWriter()
        for idx in paginas_alvo:
            writer.add_page(reader.pages[idx])

        pdf_para_plumber = BytesIO()
        writer.write(pdf_para_plumber)
        pdf_para_plumber.seek(0)
    except Exception as e:
        print(f"[HRADAR AVISO] PyPDF falhou no fatiamento ({e}). Plumber fará a varredura profunda.")
        arquivo_pdf.seek(0)
        pdf_para_plumber = arquivo_pdf

    try:
        with pdfplumber.open(pdf_para_plumber) as pdf:
            lendo_movimentacao = False
            for pagina in pdf.pages:
                texto_layout = pagina.extract_text(layout=True)
                if not texto_layout: continue
                linhas = texto_layout.split('\n')
                for linha in linhas:
                    l_limpa = linha.strip()
                    if not l_limpa: continue
                    if REGEX_TITULOS_MOV.search(l_limpa):
                        lendo_movimentacao = True
                        continue
                    parada = ["ATOS DA", "ATOS DO", "DESIGNAÇÃO", "COMPARECIMENTO", "DESIGNAÇÕES"]
                    if lendo_movimentacao and any(p in l_limpa.upper() for p in parada):
                        if not re.search(regex_cargos_str, l_limpa, re.IGNORECASE):
                            lendo_movimentacao = False
                            continue
                    if lendo_movimentacao:
                        m_comp = reg_completo.search(l_limpa)
                        m_lota = reg_lotacao.search(l_limpa)
                        match = m_comp or m_lota
                        if match:
                            if match == m_comp:
                                dn, cargo, id_f, orig, sei = match.groups()
                            else:
                                dn, cargo, id_f, sei = match.groups()
                                orig = "1ª LOTAÇÃO"
                            m_dest = padrao_destino.search(dn.strip())
                            if m_dest:
                                destino, nome = m_dest.groups()
                            else:
                                p = dn.strip().split(' ')
                                destino, nome = p[0], " ".join(p[1:])
                            transferencias.append({
                                "DESTINO": destino.strip(), "NOME": limpar_nome_dr(nome), "CARGO": cargo.strip(),
                                "ID": id_f.strip(), "ID_LIMPO": limpar_id(id_f), "ORIGEM": orig.strip(), "SEI": sei.strip()
                            })
    except Exception as e:
        print(f"[HRADAR PERF] Erro no Plumber: {e}")
        pass

    return transferencias

def cruzar_dados(arquivo_pdf, texto_pypdf, servidores, orgaos, termos=None, regras=None):
    if termos is None: termos = []
    if regras is None: regras = []

    t_inicio = time.time()
    res = {'convocacoes': [], 'servidores': [], 'unidades': [], 'entradas': [], 'saidas': [], 'alvos_transferidos': [], 'movimentacoes_internas': [], 'elogios': [], 'termos_encontrados': []}

    nome_arq = getattr(arquivo_pdf, 'name', '')
    match_bi = re.search(r'(\d{1,3})\D*?(\d{4})', nome_arq)
    num_bi = f"{match_bi.group(1).zfill(3)}/{match_bi.group(2)}" if match_bi else ""

    watchlist = []
    mapa_servidores = {}
    for s in servidores:
        id_limpo = limpar_id(s.id_funcional)
        if id_limpo:
            watchlist.append({'obj': s, 'regex': re.compile(criar_regex_id(id_limpo))})
            mapa_servidores[id_limpo] = s

    mapa_orgaos_regex = {o.sigla_orgao.upper(): criar_regex_unidade(o.sigla_orgao) for o in orgaos}
    regex_termos = {t.termo.upper(): re.compile(rf'\b{re.escape(t.termo)}\b', re.IGNORECASE) for t in termos}

    regras_db = {}
    for r in regras:
        # 1. Troca qualquer pipe (|) por vírgula para padronizar o separador
        gatilho_normalizado = r.gatilho.replace('|', ',')

        # 2. Divide os termos e arranca fora qualquer espaço invisível nas pontas
        termos_separados = [t.strip() for t in gatilho_normalizado.split(',') if t.strip()]

        # 3. Monta a Regex blindada e case-insensitive
        padrao_regex_regra = r'\b(' + '|'.join(termos_separados) + r')\b'

        regras_db[r.gatilho.upper()] = {
            'regex': re.compile(padrao_regex_regra, re.IGNORECASE),
            'etiqueta': r.etiqueta.upper(),
            'cor': r.cor
        }

    # Aqui as linhas são as linhas originais do PDF
    linhas = texto_pypdf.split('\n')
    total = len(linhas)

    MAPA_CORES_CSS = {
        'slate': {"bg": "bg-slate-200", "border": "border-slate-300", "text": "text-slate-700", "icon": "📄"},
        'rose': {"bg": "bg-rose-100", "border": "border-rose-400", "text": "text-rose-900", "icon": "🚨"},
        'amber': {"bg": "bg-amber-100", "border": "border-amber-400", "text": "text-amber-900", "icon": "⭐"},
        'emerald': {"bg": "bg-emerald-100", "border": "border-emerald-400", "text": "text-emerald-900", "icon": "🟢"},
        'blue': {"bg": "bg-blue-100", "border": "border-blue-400", "text": "text-blue-900", "icon": "🔵"},
        'violet': {"bg": "bg-violet-100", "border": "border-violet-400", "text": "text-violet-900", "icon": "📋"},
        'stone': {"bg": "bg-stone-200", "border": "border-stone-500", "text": "text-stone-900", "icon": "⚫"},
        'cyan': {"bg": "bg-cyan-100", "border": "border-cyan-400", "text": "text-cyan-900", "icon": "🎯"},
        'orange': {"bg": "bg-orange-100", "border": "border-orange-400", "text": "text-orange-900", "icon": "🟠"},
        'pink': {"bg": "bg-pink-100", "border": "border-pink-400", "text": "text-pink-900", "icon": "🌸"},
        'indigo': {"bg": "bg-indigo-100", "border": "border-indigo-400", "text": "text-indigo-900", "icon": "🟣"},
        'teal': {"bg": "bg-teal-100", "border": "border-teal-400", "text": "text-teal-900", "icon": "🌊"},
        'fuchsia': {"bg": "bg-fuchsia-100", "border": "border-fuchsia-400", "text": "text-fuchsia-900", "icon": "🦩"},
        'lime': {"bg": "bg-lime-100", "border": "border-lime-400", "text": "text-lime-900", "icon": "🍋"},
        'sky': {"bg": "bg-sky-100", "border": "border-sky-400", "text": "text-sky-900", "icon": "☁️"},
        'yellow': {"bg": "bg-yellow-100", "border": "border-yellow-400", "text": "text-yellow-900", "icon": "⚡"},
        'zinc': {"bg": "bg-zinc-200", "border": "border-zinc-400", "text": "text-zinc-800", "icon": "⚙️"},
    }

    COR_GERAL = MAPA_CORES_CSS['slate']
    etiqueta_atual = "GERAL"
    cor_atual = COR_GERAL

    for i in range(total):
        linha_atual = linhas[i].strip()
        if not linha_atual: continue

        linha_upper = linha_atual.upper()
        ultimo_indice = -1
        regra_vencedora = None

        for gatilho, dados_regra in regras_db.items():
            matches = list(dados_regra['regex'].finditer(linha_upper))
            if matches:
                posicao_match = matches[-1].start()
                if posicao_match > ultimo_indice:
                    ultimo_indice = posicao_match
                    regra_vencedora = dados_regra

        if regra_vencedora:
            etiqueta_atual = regra_vencedora['etiqueta']
            cor_atual = MAPA_CORES_CSS.get(regra_vencedora['cor'], COR_GERAL)

        for termo_str, regex_t in regex_termos.items():
            if regex_t.search(linha_upper):
                res['termos_encontrados'].append({
                    'alvo': termo_str,
                    'contexto': realcar_html(linha_atual, termo_str),
                    'cor_css': MAPA_CORES_CSS['cyan']
                })

        for item in watchlist:
            match_id = item['regex'].search(linha_atual)

            if match_id:
                s = item['obj']
                id_no_bi = match_id.group(0)

                # --- A VERDADEIRA JANELA DESLIZANTE ---
                # Pega a linha do ID + 4 linhas acima e 4 abaixo para garantir processos e datas
                inicio_janela = max(0, i - 4)
                fim_janela = min(total, i + 5)
                contexto_amplo = " ".join([linhas[idx].strip() for idx in range(inicio_janela, fim_janela)])

                contexto_puro = linha_atual # Para a tabela, a linha pura exibe a escala perfeita

                nome_com_titulo = f"{s.tratamento} {s.nome}" if s.tratamento else s.nome

                alerta = {
                    'alvo': nome_com_titulo,
                    'identificador': getattr(s, 'id_formatado', s.id_funcional),
                    'contexto': realcar_html(contexto_puro, id_no_bi),
                    'contexto_puro': contexto_puro,
                    'contexto_amplo': contexto_amplo,
                    'servidor_id': s.id,
                    'etiqueta': etiqueta_atual,
                    'cor_css': cor_atual
                }

                # A Guilhotina agora busca os dados dentro da JANELA inteira
                tem_hora = REGEX_HORA.search(contexto_amplo)
                tem_processo = REGEX_PROCESSO.search(contexto_amplo)

                # A vacina anti-escala mantida para blindar a CFD
                contexto_upper = contexto_amplo.upper()
                eh_escala_cfd = "DIURNO" in contexto_upper or "NOTURNO" in contexto_upper

                if tem_hora and tem_processo and not eh_escala_cfd:
                    alerta['etiqueta'] = 'COMPARECIMENTO PARA DEPOR'
                    alerta['cor_css'] = MAPA_CORES_CSS.get('rose', COR_GERAL)
                    # Passamos o contexto_amplo para as Regex do WhatsApp acharem os dados do depoimento
                    alerta['whatsapp'] = gerar_mensagem_whatsapp_convocacao(s.nome, s.tratamento, contexto_puro, contexto_amplo, num_bi)
                    res['convocacoes'].append(alerta)
                else:
                    alerta['whatsapp'] = gerar_mensagem_whatsapp_mencao(s.nome, s.tratamento, s.id_funcional, contexto_puro, num_bi, etiqueta_atual)
                    res['servidores'].append(alerta)

    padrao_pessoal = re.compile(r'\d{1,2}\.?\d{3}\.?\d{3}-\d')
    for linha in linhas:
        if padrao_pessoal.search(linha):
            continue
        for sigla, regex_unidade in mapa_orgaos_regex.items():
            if regex_unidade.search(linha):
                res['unidades'].append({'alvo': sigla, 'contexto': realcar_html(linha, sigla), 'contexto_puro': linha, 'tipo': 'UNIDADE'})

    remocoes = extrair_remocoes_estruturadas(arquivo_pdf)
    for t in remocoes:
        dest = t['DESTINO'].upper()
        orig = t['ORIGEM'].upper()
        id_l = t['ID_LIMPO']
        is_alvo = id_l in mapa_servidores

        if is_alvo:
            s_obj = mapa_servidores[id_l]
            t['NOME'] = f"{s_obj.tratamento} {s_obj.nome}" if s_obj.tratamento else s_obj.nome
            t['DB_ID'] = s_obj.id
        is_ent = any(regex_unidade.search(dest) for regex_unidade in mapa_orgaos_regex.values())
        is_sai = any(regex_unidade.search(orig) for regex_unidade in mapa_orgaos_regex.values())

        if is_ent and is_sai: res['movimentacoes_internas'].append(t)
        elif is_ent: res['entradas'].append(t)
        elif is_sai: res['saidas'].append(t)
        elif is_alvo: res['alvos_transferidos'].append(t)

    res['limite_atingido'] = False
    LIMITE_GERAL = 100
    for chave in ['convocacoes', 'servidores', 'unidades', 'entradas', 'saidas', 'alvos_transferidos', 'movimentacoes_internas', 'elogios', 'termos_encontrados']:
        if len(res[chave]) > LIMITE_GERAL:
            res[chave] = res[chave][:LIMITE_GERAL]
            res['limite_atingido'] = True

    return res