import re
from django.db import models
from django.contrib.auth.models import User

class PerfilAgente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    primeiro_acesso = models.BooleanField(default=True)
    data_aceite_termo = models.DateTimeField(null=True, blank=True)

class ServidorMonitorado(models.Model):
    TRATAMENTOS = [
        ('', 'Nenhum'),
        ('Dr.', 'Dr.'),
        ('Drª.', 'Drª.'),
    ]

    agente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='servidores')
    tratamento = models.CharField(max_length=10, choices=TRATAMENTOS, default='', blank=True)
    nome = models.CharField(max_length=255)
    id_funcional = models.CharField(max_length=20)
    id_funcional_limpo = models.CharField(max_length=20)
    unidade = models.CharField(max_length=100, default='PENDENTE')

    def save(self, *args, **kwargs):
        # 1. Força Nome em Maiúsculo
        self.nome = self.nome.upper()

        # 2. Limpeza total do ID: Mantém apenas os algarismos
        self.id_funcional = re.sub(r'\D', '', str(self.id_funcional))
        self.id_funcional_limpo = self.id_funcional

        # 3. Força Unidade em Maiúsculo se existir
        if self.unidade:
            self.unidade = self.unidade.upper()

        super().save(*args, **kwargs)

    @property
    def id_formatado(self):
        val = self.id_funcional
        # Máscara para 8 dígitos: 0.000.000-0
        if len(val) == 8:
            return f"{val[0]}.{val[1:4]}.{val[4:7]}-{val[7]}"
        # Máscara para 7 dígitos: 000.000-0
        elif len(val) == 7:
            return f"{val[:3]}.{val[3:6]}-{val[6]}"
        return val

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return f"{self.nome} ({self.unidade})"

class OrgaoMonitorado(models.Model):
    agente = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orgaos')
    sigla_orgao = models.CharField(max_length=50)

class RegraClassificacao(models.Model):
    CORES = [
        ('slate', 'Cinza Neutro (Sem Classificação)'),
        ('rose', 'Vermelho (Ex: Exoneração, Convocação)'),
        ('amber', 'Amarelo (Ex: Promoção, Elogio)'),
        ('emerald', 'Verde (Ex: Férias, Licença)'),
        ('blue', 'Azul (Ex: Majoração)'),
        ('violet', 'Roxo (Ex: Designação)'),
        ('stone', 'Preto (Ex: Falecimento)'),
        ('orange', 'Laranja (Ex: Atenção)'),
        ('pink', 'Rosa (Ex: Destaque Especial)'),
        ('indigo', 'Índigo (Ex: Transferência)'),
        ('teal', 'Verde-Água (Ex: Órgãos/Departamentos)'),
        ('fuchsia', 'Fúcsia (Ex: Saúde/PPCJCM)'),
        ('lime', 'Limão (Ex: Extraquadro)'),
        ('sky', 'Azul Celeste (Ex: Administrativo)'),
        ('yellow', 'Amarelo Vivo (Ex: Alerta/Atenção)'),
        ('zinc', 'Cinza Industrial (Ex: Edital/Transcrições)'),
    ]
    gatilho = models.CharField(max_length=100, help_text="Palavra lida no BI (Ex: CONVOCAÇÃO)")
    etiqueta = models.CharField(max_length=100, help_text="Nome do Card (Ex: CONVOCAÇÃO PARA DEPOR)")
    cor = models.CharField(max_length=20, choices=CORES, default='slate')

    def __str__(self):
        return f"{self.gatilho} -> {self.etiqueta}"

class TermoMonitorado(models.Model):
    agente = models.ForeignKey(User, on_delete=models.CASCADE)
    termo = models.CharField(max_length=100)

    def __str__(self):
        return self.termo