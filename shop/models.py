from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Кастомная модель пользователя"""
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Телефон')
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватарка')
    is_deleted = models.BooleanField(default=False, verbose_name='Удален')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Category(models.Model):
    """Категория товаров"""
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(max_length=255, unique=True, verbose_name='Слаг')
    icon = models.ImageField(
        upload_to='category_icons/',
        blank=True,
        null=True,
        verbose_name='Иконка')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='children',
        verbose_name='Родительская категория'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    is_deleted = models.BooleanField(default=False, verbose_name='Удалена')
    sort_order = models.PositiveIntegerField(
        default=0, verbose_name='Порядок сортировки')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар"""
    name = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(max_length=255, unique=True, verbose_name='Слаг')
    short_description = models.CharField(
        max_length=500, verbose_name='Краткое описание')
    full_description = models.TextField(verbose_name='Полное описание')
    image = models.ImageField(
        upload_to='products/',
        verbose_name='Изображение')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Цена')
    categories = models.ManyToManyField(
        Category,
        related_name='products',
        verbose_name='Категории')
    manufacturer = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Производитель')
    sort_index = models.PositiveIntegerField(
        default=0, verbose_name='Индекс сортировки')
    purchase_count = models.PositiveIntegerField(
        default=0, verbose_name='Количество покупок')
    is_limited = models.BooleanField(
        default=False, verbose_name='Ограниченный тираж')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_deleted = models.BooleanField(default=False, verbose_name='Удален')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-sort_index', '-purchase_count', 'name']

    def __str__(self):
        return self.name


class Characteristic(models.Model):
    """Характеристика товара (справочник)"""
    name = models.CharField(max_length=255,
                            verbose_name='Название характеристики')
    filter_type = models.CharField(
        max_length=20,
        choices=[
            ('dropdown', 'Выпадающий список'),
            ('checkbox', 'Галочка'),
            ('text', 'Текст'),
        ],
        default='text',
        verbose_name='Тип фильтра'
    )
    is_multiple = models.BooleanField(
        default=False, verbose_name='Множественный выбор')

    class Meta:
        verbose_name = 'Характеристика'
        verbose_name_plural = 'Характеристики'

    def __str__(self):
        return self.name


class ProductCharacteristic(models.Model):
    """Значение характеристики для конкретного товара"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='characteristics',
        verbose_name='Товар')
    characteristic = models.ForeignKey(
        Characteristic,
        on_delete=models.CASCADE,
        verbose_name='Характеристика')
    value = models.CharField(max_length=500, verbose_name='Значение')

    class Meta:
        verbose_name = 'Характеристика товара'
        verbose_name_plural = 'Характеристики товаров'
        unique_together = ['product', 'characteristic']

    def __str__(self):
        return f"{self.product.name} - {self.characteristic.name}: {self.value}"


class Review(models.Model):
    """Отзыв на товар"""
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар')
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Пользователь')
    text = models.TextField(verbose_name='Текст отзыва')
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)],
        verbose_name='Рейтинг'
    )
    is_deleted = models.BooleanField(default=False, verbose_name='Удален')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.product.name}"


class Cart(models.Model):
    """Корзина пользователя"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='cart',
        verbose_name='Пользователь',
        null=True,
        blank=True)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')
    session_key = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Ключ сессии')

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

    def __str__(self):
        if self.user:
            return f"Корзина {self.user.email}"
        return f"Корзина (сессия: {self.session_key})"

    def get_total_price(self):
        """Общая стоимость корзины"""
        return sum(item.get_total_price() for item in self.items.all())


class CartItem(models.Model):
    """Позиция в корзине"""
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Корзина')
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        verbose_name='Товар')
    quantity = models.PositiveIntegerField(
        default=1, verbose_name='Количество')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Позиция корзины'
        verbose_name_plural = 'Позиции корзины'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    def get_total_price(self):
        """Стоимость позиции"""
        return self.product.price * self.quantity


class DeliverySettings(models.Model):
    """Настройки доставки"""
    standard_delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=200.00,
        verbose_name='Стоимость стандартной доставки'
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=2000.00,
        verbose_name='Порог бесплатной доставки'
    )
    express_delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500.00,
        verbose_name='Стоимость экспресс-доставки'
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Настройка доставки'
        verbose_name_plural = 'Настройки доставки'

    def __str__(self):
        return "Настройки доставки"


class Order(models.Model):
    """Заказ"""
    DELIVERY_CHOICES = [
        ('standard', 'Стандартная доставка'),
        ('express', 'Экспресс-доставка'),
    ]

    PAYMENT_CHOICES = [
        ('card', 'Онлайн картой'),
        ('random_account', 'Онлайн со случайного чужого счёта'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('failed', 'Ошибка оплаты'),
        ('processing', 'В обработке'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='orders',
                             verbose_name='Пользователь')
    full_name = models.CharField(max_length=255, verbose_name='ФИО')
    email = models.EmailField(verbose_name='Email')
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        verbose_name='Способ доставки')
    delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Стоимость доставки')
    city = models.CharField(max_length=255, verbose_name='Город')
    address = models.CharField(max_length=500, verbose_name='Адрес')

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        verbose_name='Способ оплаты')
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending',
                                      verbose_name='Статус оплаты')
    payment_error = models.TextField(
        blank=True, null=True, verbose_name='Текст ошибки оплаты')

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Общая сумма',
        null=True)
    comment = models.TextField(
        blank=True,
        null=True,
        verbose_name='Комментарий к заказу')

    is_deleted = models.BooleanField(default=False, verbose_name='Удален')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} - {self.full_name}"

    def save(self, *args, **kwargs):
        if not self.total_amount and self.pk:
            total = 0
            for item in self.items.all():
                total += item.product_price * item.quantity
            self.total_amount = total + (self.delivery_cost or 0)
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Позиция заказа"""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Заказ')
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name='Товар')
    product_name = models.CharField(
        max_length=255, verbose_name='Название товара')
    product_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Цена товара')
    quantity = models.PositiveIntegerField(
        verbose_name='Количество', default=0.00)
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    def get_total_price(self):
        """Стоимость позиции"""
        return self.product_price * self.quantity
