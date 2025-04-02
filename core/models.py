# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

# Modelo para Fornecedores, Transportadores e Compradores
class Perfil(models.Model):
    TIPO_USUARIO = (
        ('fornecedor', 'Fornecedor'),
        ('transportador', 'Transportador'),
        ('comprador', 'Comprador'),
    )
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_USUARIO)
    telefone = models.CharField(max_length=15)
    endereco = models.TextField()

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo}"

# Modelo para Produtos
class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

class Produto(models.Model):
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True
    )
    fornecedor = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        limit_choices_to={'tipo': 'fornecedor'}
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.IntegerField()
    estoque_minimo = models.IntegerField(
        default=10,
        verbose_name="Estoque Mínimo",
        help_text="Quantidade mínima para alertas de reposição"
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome

# Modelo para Pedidos
class Pedido(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceito', 'Aceito'),
        ('recusado', 'Recusado'),
        ('entregue', 'Entregue'),
    ]
    produto = models.ForeignKey(  # ← Deve ser ForeignKey
        'Produto',
        on_delete=models.CASCADE,
        related_name='pedidos'
    )
    comprador = models.ForeignKey(
        'Perfil',
        on_delete=models.CASCADE,
        related_name='pedidos_feitos'
    )
    quantidade = models.IntegerField()
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    data_pedido = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

    def __str__(self):
        return f"Pedido #{self.id} - {self.produto.nome}"


# Modelo para Transporte
class Transporte(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    transportador = models.ForeignKey(Perfil, on_delete=models.CASCADE, limit_choices_to={'tipo': 'transportador'})
    status = models.CharField(max_length=20, default='aguardando')
    data_inicio = models.DateTimeField(null=True, blank=True)
    data_entrega = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Transporte para {self.pedido}"


class Mensagem(models.Model):
    remetente = models.ForeignKey(
        'Perfil',
        on_delete=models.CASCADE,
        related_name='mensagens_enviadas'
    )
    destinatario = models.ForeignKey(
        'Perfil',
        on_delete=models.CASCADE,
        related_name='mensagens_recebidas'
    )
    conteudo = models.TextField()
    data_envio = models.DateTimeField(auto_now_add=True)
    lida = models.BooleanField(default=False)

    def __str__(self):
        return f"De {self.remetente} para {self.destinatario} - {self.data_envio}"
    class Meta:
        ordering = ['-data_envio']
        
    def mark_as_read(self):
        if not self.lida:
            self.lida = True
            self.save()
    
    @classmethod
    def get_conversations(cls, user):
        return cls.objects.filter(
            Q(remetente=user) | Q(destinatario=user)
        ).distinct('remetente', 'destinatario')
    

class Avaliacao(models.Model):
    class Meta:
        unique_together = ('pedido', 'avaliador')  # Uma avaliação por pedido
    
    NOTA_CHOICES = [
        (1, '★☆☆☆☆'),
        (2, '★★☆☆☆'),
        (3, '★★★☆☆'),
        (4, '★★★★☆'),
        (5, '★★★★★'),
    ]

    pedido = models.ForeignKey(
        'Pedido',
        on_delete=models.CASCADE,
        related_name='avaliacoes'
    )
    avaliador = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name='avaliacoes_feitas',
        limit_choices_to={'tipo': 'comprador'}
    )
    fornecedor = models.ForeignKey(
        Perfil,
        on_delete=models.CASCADE,
        related_name='avaliacoes_recebidas',
        limit_choices_to={'tipo': 'fornecedor'}
    )
    nota = models.PositiveSmallIntegerField(
        choices=NOTA_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comentario = models.TextField(max_length=500, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Avaliação de {self.avaliador} para {self.fornecedor} - {self.get_nota_display()}"

    @property
    def nota_estrelas(self):
        return '★' * self.nota + '☆' * (5 - self.nota)

