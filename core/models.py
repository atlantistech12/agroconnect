# models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify

# Modelo para Fornecedores, Transportadores e Compradores
class Perfil(models.Model):
    TIPO_USUARIO = (
        ('fornecedor', 'Fornecedor'),
        ('comprador', 'Comprador'),
    )
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=20, choices=TIPO_USUARIO)
    telefone = models.CharField(max_length=15)
    endereco = models.TextField()
    imagem = models.ImageField(upload_to='perfis/', default='perfis/default.jpg')

    def __str__(self):
        return f"{self.usuario.username} - {self.tipo}"

# Modelo para Produtos
class Categoria(models.Model):
    TIPOS_MEDIDA = [
        ('kg', 'Quilograma (kg)'),
        ('g', 'Grama (g)'),
        ('L', 'Litro (L)'),
        ('ml', 'Mililitro (ml)'),
        ('un', 'Unidade (un)'),
        ('cx', 'Caixa (cx)'),
        ('sc', 'Saco (sc)'),
        ('mt', 'Metro (m)'),
    ]
    
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)  # Novo campo
    tipo_medida = models.CharField(
        max_length=3,
        choices=TIPOS_MEDIDA,
        default='un',
        verbose_name="Unidade de Medida"
    )
    descricao = models.TextField(blank=True)
    sistema = models.BooleanField(default=False)
    icone = models.CharField(max_length=50, default='fas fa-seedling', blank=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)
    
    @property
    def unidade_medida(self):
        return self.get_tipo_medida_display()

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

    imagem = models.ImageField(
        upload_to='produtos/',
        blank=True,
        null=True,
        verbose_name="Foto do Produto"
    )

    def __str__(self):
        return self.nome

# Modelo para Pedidos
class Pedido(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('aceito', 'Aceito'),
        ('recusado', 'Recusado'),
        ('cancelado', 'Cancelado'), 
        ('concluido', 'Concluido'),
    ]

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')

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
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.produto.nome}"

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

