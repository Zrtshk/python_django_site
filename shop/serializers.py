from django.db.models import Avg
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    Category, Product, Characteristic, ProductCharacteristic,
    Review, CartItem, Order, OrderItem, DeliverySettings
)

User = get_user_model()


# ==================== КАТЕГОРИИ ====================

class CategorySerializer(serializers.ModelSerializer):
    """
    Сериализатор категорий.
    Используется для отображения категорий с дочерними элементами.
    """
    children = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'icon', 'parent', 'children', 'is_active']

    def get_children(self, obj):
        """Получение дочерних категорий (максимум 2 уровня)."""
        if obj.children.exists():
            return CategorySerializer(
                obj.children.filter(is_active=True, is_deleted=False),
                many=True
            ).data
        return []


class CharacteristicSerializer(serializers.ModelSerializer):
    """Сериализатор характеристик товаров."""

    class Meta:
        model = Characteristic
        fields = ['id', 'name', 'filter_type', 'is_multiple']


class ProductCharacteristicSerializer(serializers.ModelSerializer):
    """Сериализатор значений характеристик товара."""
    characteristic = CharacteristicSerializer(read_only=True)
    characteristic_id = serializers.PrimaryKeyRelatedField(
        source='characteristic',
        queryset=Characteristic.objects.all(),
        write_only=True
    )

    class Meta:
        model = ProductCharacteristic
        fields = ['id', 'characteristic', 'characteristic_id', 'value']


# ==================== ОТЗЫВЫ ====================

class ReviewSerializer(serializers.ModelSerializer):
    """Сериализатор отзывов."""
    author = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    rate = serializers.IntegerField(source='rating')
    date = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ['author', 'email', 'text', 'rate', 'date', 'product']
        read_only_fields = ['product']

    def get_author(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip() or obj.user.username

    def get_email(self, obj):
        return obj.user.email

    def get_date(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M') if obj.created_at else None




# ==================== ТОВАРЫ ====================

class ProductListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка товаров (для фронтенда).
    Используется на главной странице и в каталоге.
    """
    title = serializers.CharField(source='name', read_only=True)
    images = serializers.SerializerMethodField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = Product
        fields = ['id', 'title', 'price', 'images']

    def get_images(self, obj):
        """
        Возвращает массив с изображением товара.
        Если изображение отсутствует, возвращает заглушку.
        """
        request = self.context.get('request')

        if obj and obj.image and hasattr(obj.image, 'url') and obj.image.url:
            try:
                if request:
                    return [{
                        'src': request.build_absolute_uri(obj.image.url),
                        'alt': obj.name
                    }]
                return [{
                    'src': obj.image.url,
                    'alt': obj.name
                }]
            except BaseException:
                pass

        return [{
            'src': '/static/images/no-image.png',
            'alt': obj.name if obj else 'No Image'
        }]


class ProductDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной страницы товара.
    Возвращает полную информацию о товаре.
    """
    categories = CategorySerializer(many=True, read_only=True)
    characteristics = ProductCharacteristicSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    reviews_count = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'short_description', 'full_description',
            'price', 'image', 'image_url', 'categories', 'manufacturer',
            'characteristics', 'reviews', 'reviews_count', 'rating',
            'is_limited', 'purchase_count', 'sort_index'
        ]

    def get_reviews_count(self, obj):
        return obj.reviews.count()

    def get_rating(self, obj):
        avg = obj.reviews.aggregate(avg=Avg('rating'))['avg']
        return round(avg, 1) if avg else 0

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return None


class ProductShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для краткого представления товара (ProductShort).
    Соответствует Swagger спецификации.
    """
    id = serializers.IntegerField()
    category = serializers.SerializerMethodField()
    title = serializers.CharField(source='name')
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    description = serializers.CharField(source='short_description')
    freeDelivery = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'title', 'price', 'count', 'date',
            'description', 'freeDelivery', 'images', 'tags',
            'reviews', 'rating',
        ]

    def get_category(self, obj):
        first_category = obj.categories.first()
        return first_category.id if first_category else None

    def get_count(self, obj):
        return obj.purchase_count or 0

    def get_date(self, obj):
        return obj.created_at.strftime('%a %b %d %Y %H:%M:%S GMT+0100') if obj.created_at else None

    def get_freeDelivery(self, obj):
        return obj.price > 1000

    def get_images(self, obj):
        request = self.context.get('request')
        if obj and obj.image and hasattr(obj.image, 'url') and obj.image.url:
            try:
                if request:
                    return [{
                        'src': request.build_absolute_uri(obj.image.url),
                        'alt': obj.name
                    }]
                return [{
                    'src': obj.image.url,
                    'alt': obj.name
                }]
            except BaseException:
                pass

        return [{
            'src': '/static/images/no-image.png',
            'alt': obj.name if obj else 'No Image'
        }]

    def get_tags(self, obj):
        characteristics = obj.characteristics.all()
        return [{'id': char.id, 'name': char.value} for char in characteristics[:5]]

    def get_reviews(self, obj):
        return obj.reviews.filter(is_deleted=False).count()

    def get_rating(self, obj):
        reviews = obj.reviews.filter(is_deleted=False)
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0


class ProductFullSerializer(serializers.ModelSerializer):
    """
    Сериализатор для полной информации о товаре (ProductFull).
    Соответствует Swagger спецификации.
    """
    id = serializers.IntegerField()
    category = serializers.SerializerMethodField()
    title = serializers.CharField(source='name')
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    description = serializers.CharField(source='short_description')
    fullDescription = serializers.CharField(source='full_description')
    freeDelivery = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    reviews = serializers.SerializerMethodField()
    specifications = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'category', 'title', 'price', 'count', 'date',
            'description', 'fullDescription', 'freeDelivery',
            'images', 'tags', 'reviews', 'specifications', 'rating',
        ]

    def get_category(self, obj):
        first_category = obj.categories.first()
        return first_category.id if first_category else None

    def get_count(self, obj):
        return obj.purchase_count or 0

    def get_date(self, obj):
        return obj.created_at.strftime('%a %b %d %Y %H:%M:%S GMT+0100') if obj.created_at else None

    def get_freeDelivery(self, obj):
        return obj.price > 1000

    def get_images(self, obj):
        request = self.context.get('request')
        if obj and obj.image and hasattr(obj.image, 'url') and obj.image.url:
            try:
                if request:
                    return [{
                        'src': request.build_absolute_uri(obj.image.url),
                        'alt': obj.name
                    }]
                return [{
                    'src': obj.image.url,
                    'alt': obj.name
                }]
            except BaseException:
                pass

        return [{
            'src': '/static/images/no-image.png',
            'alt': obj.name if obj else 'No Image'
        }]

    def get_tags(self, obj):
        return [str(char.id) for char in obj.characteristics.all()]

    def get_reviews(self, obj):
        reviews = obj.reviews.filter(is_deleted=False)
        return [{
            'author': f"{r.user.first_name} {r.user.last_name}".strip() or r.user.email,
            'email': r.user.email,
            'text': r.text,
            'rate': r.rating,
            'date': r.created_at.strftime('%Y-%m-%d %H:%M')
        } for r in reviews]

    def get_specifications(self, obj):
        return [{
            'name': char.characteristic.name,
            'value': char.value
        } for char in obj.characteristics.all()]

    def get_rating(self, obj):
        reviews = obj.reviews.filter(is_deleted=False)
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return 0


# ==================== КОРЗИНА ====================

class CartItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции корзины."""
    product = ProductListSerializer(read_only=True)
    product_id = serializers.PrimaryKeyRelatedField(
        source='product',
        queryset=Product.objects.filter(is_active=True, is_deleted=False),
        write_only=True
    )
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_id', 'quantity', 'total_price']

    def get_total_price(self, obj):
        return obj.get_total_price()


class CartSerializer(serializers.Serializer):
    """Сериализатор корзины."""

    def to_representation(self, instance):
        """Возвращаем объект с ключом items."""
        cart_items = instance.items.all()
        items = []

        for cart_item in cart_items:
            product = cart_item.product
            if not product or not product.is_active:
                continue

            category = product.categories.first()
            request = self.context.get('request')
            image_url = '/static/images/no-image.png'

            if product.image and hasattr(product.image, 'url') and product.image.url:
                if request:
                    image_url = request.build_absolute_uri(product.image.url)
                else:
                    image_url = product.image.url

            items.append({
                'id': product.id,
                'category': category.id if category else None,
                'title': product.name,
                'price': float(product.price),
                'count': cart_item.quantity,
                'date': product.created_at.strftime('%a %b %d %Y %H:%M:%S GMT+0100') if product.created_at else None,
                'description': product.short_description or '',
                'freeDelivery': product.price > 1000,
                'images': [{
                    'src': image_url,
                    'alt': product.name
                }],
                'tags': [
                    {'id': char.id, 'name': char.value}
                    for char in product.characteristics.all()[:5]
                ],
                'reviews': product.reviews.filter(is_deleted=False).count(),
                'rating': round(product.reviews.filter(is_deleted=False).aggregate(avg=Avg('rating'))['avg'] or 0, 1),
            })

        return {'items': items}


# ==================== ЗАКАЗЫ ====================

class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции заказа."""

    class Meta:
        model = OrderItem
        fields = ['id', 'product_name', 'product_price', 'quantity', 'get_total_price']


class OrderCreateSerializer(serializers.Serializer):
    """Сериализатор для создания заказа."""
    full_name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    phone = serializers.CharField(max_length=20)
    delivery_method = serializers.ChoiceField(choices=Order.DELIVERY_CHOICES)
    city = serializers.CharField(max_length=255)
    address = serializers.CharField(max_length=500)
    payment_method = serializers.ChoiceField(choices=Order.PAYMENT_CHOICES)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, data):
        """Валидация данных заказа."""
        return data


class OrderSerializer(serializers.ModelSerializer):
    """
    Сериализатор заказа.
    Соответствует Swagger спецификации.
    """
    id = serializers.IntegerField()
    createdAt = serializers.DateTimeField(source='created_at')
    fullName = serializers.CharField(source='full_name')
    email = serializers.EmailField()
    phone = serializers.CharField()
    deliveryType = serializers.CharField(source='delivery_method')
    paymentType = serializers.CharField(source='payment_method')
    totalCost = serializers.DecimalField(source='total_amount', max_digits=10, decimal_places=2)
    status = serializers.CharField(source='payment_status')
    city = serializers.CharField()
    address = serializers.CharField()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'createdAt', 'fullName', 'email', 'phone',
            'deliveryType', 'paymentType', 'totalCost', 'status',
            'city', 'address', 'products'
        ]

    def get_products(self, obj):
        items = obj.items.all()
        result = []
        request = self.context.get('request')

        for item in items:
            product = item.product
            image_url = '/static/images/no-image.png'

            if product and product.image and hasattr(product.image, 'url') and product.image.url:
                if request:
                    image_url = request.build_absolute_uri(product.image.url)
                else:
                    image_url = product.image.url

            result.append({
                'id': item.product.id if item.product else None,
                'category': item.product.categories.first().id if item.product and item.product.categories.first() else None,
                'title': item.product_name,
                'price': float(item.product_price),
                'count': item.quantity,
                'images': [{
                    'src': image_url,
                    'alt': item.product_name
                }]
            })
        return result


class OrderProductSerializer(ProductShortSerializer):
    """Сериализатор товара в заказе."""
    count = serializers.IntegerField(source='quantity')
    price = serializers.DecimalField(max_digits=10, decimal_places=2, source='product_price')

    class Meta(ProductShortSerializer.Meta):
        fields = ['id', 'category', 'title', 'price', 'count']


# ==================== ПОЛЬЗОВАТЕЛИ ====================

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор профиля пользователя.
    Соответствует Swagger спецификации.
    """
    fullName = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['fullName', 'email', 'phone', 'avatar', 'first_name', 'last_name']

    def get_fullName(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip() or obj.username

    def get_avatar(self, obj):
        request = self.context.get('request')
        if obj.avatar and hasattr(obj.avatar, 'url'):
            return {
                'src': request.build_absolute_uri(obj.avatar.url) if request else obj.avatar.url,
                'alt': obj.username
            }
        return None

    def to_internal_value(self, data):
        """Преобразуем fullName в first_name и last_name при валидации."""
        data = data.copy()
        if 'fullName' in data:
            full_name = data.pop('fullName', '').strip()
            if full_name:
                parts = full_name.split(' ', 1)
                data['first_name'] = parts[0]
                data['last_name'] = parts[1] if len(parts) > 1 else ''
            else:
                data['first_name'] = ''
                data['last_name'] = ''
        return super().to_internal_value(data)

    def validate_first_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError('Имя должно содержать минимум 2 символа')
        return value.strip() if value else ''

    def validate_last_name(self, value):
        if value and len(value.strip()) < 2:
            raise serializers.ValidationError('Фамилия должна содержать минимум 2 символа')
        return value.strip() if value else ''

    def validate_phone(self, value):
        if value:
            import re
            phone_clean = re.sub(r'[^\d+]', '', value)
            if not re.match(r'^\+?\d{10,15}$', phone_clean):
                raise serializers.ValidationError(
                    'Некорректный номер телефона. Используйте формат: +79001234567'
                )
        return value

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            if attr in ['first_name', 'last_name']:
                setattr(instance, attr, value.strip() if value else '')
            else:
                setattr(instance, attr, value)
        instance.save()
        return instance


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    password_confirm = serializers.CharField(write_only=True, min_length=6)
    name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['email', 'username', 'first_name', 'last_name', 'phone', 'password', 'password_confirm', 'name']

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Пароли не совпадают'})

        # Если передан name, разбиваем на first_name и last_name
        if 'name' in data:
            full_name = data.pop('name', '').strip()
            if full_name:
                parts = full_name.split(' ', 1)
                data['first_name'] = parts[0]
                data['last_name'] = parts[1] if len(parts) > 1 else ''

        return data

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


# ==================== ИЗОБРАЖЕНИЯ И ТЕГИ ====================

class ImageSerializer(serializers.Serializer):
    """Сериализатор изображения."""
    src = serializers.SerializerMethodField()
    alt = serializers.SerializerMethodField()

    def __init__(self, instance=None, **kwargs):
        self.alt_text = kwargs.pop('alt_text', '')
        super().__init__(instance, **kwargs)

    def get_src(self, obj):
        request = self.context.get('request')
        if obj and hasattr(obj, 'url'):
            if request:
                return request.build_absolute_uri(obj.url)
            return obj.url
        return None

    def get_alt(self, obj):
        return self.alt_text or 'Image'


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор тегов (характеристик)."""
    id = serializers.IntegerField(source='pk')
    name = serializers.CharField(source='value')

    class Meta:
        model = ProductCharacteristic
        fields = ['id', 'name']


# ==================== КАТЕГОРИИ ДЛЯ МЕНЮ ====================

class CategoryItemSerializer(serializers.Serializer):
    """
    Сериализатор категорий для меню.
    Возвращает категории с иконками и подкатегориями.
    """
    id = serializers.IntegerField()
    title = serializers.CharField(source='name')
    image = serializers.SerializerMethodField()
    subcategories = serializers.SerializerMethodField()

    def get_image(self, obj):
        """Возвращаем иконку категории."""
        request = self.context.get('request')
        if obj.icon and hasattr(obj.icon, 'url') and obj.icon.url:
            return {
                'src': request.build_absolute_uri(obj.icon.url) if request else obj.icon.url,
                'alt': obj.name
            }
        return {
            'src': '/static/images/no-image.png',
            'alt': obj.name
        }

    def get_subcategories(self, obj):
        """Возвращаем подкатегории с иконками."""
        request = self.context.get('request')
        children = obj.children.filter(is_active=True, is_deleted=False)
        result = []

        for child in children:
            icon_url = '/static/images/no-image.png'
            if child.icon and hasattr(child.icon, 'url') and child.icon.url:
                icon_url = request.build_absolute_uri(child.icon.url) if request else child.icon.url

            result.append({
                'id': child.id,
                'title': child.name,
                'image': {
                    'src': icon_url,
                    'alt': child.name
                }
            })
        return result


# ==================== КОРЗИНА (ДОПОЛНИТЕЛЬНО) ====================

class BasketItemSerializer(serializers.Serializer):
    """Сериализатор товара в корзине (формат ProductShort)."""
    id = serializers.IntegerField()
    category = serializers.SerializerMethodField()
    title = serializers.CharField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    count = serializers.IntegerField()
    date = serializers.SerializerMethodField()
    description = serializers.CharField()
    freeDelivery = serializers.BooleanField()
    images = serializers.ListField(child=ImageSerializer())
    tags = serializers.ListField(child=TagSerializer())
    reviews = serializers.IntegerField()
    rating = serializers.DecimalField(max_digits=3, decimal_places=1)

    def get_category(self, obj):
        product = obj.get('product') or obj.get('product_obj')
        if product and hasattr(product, 'categories'):
            first_category = product.categories.first()
            return first_category.id if first_category else None
        return obj.get('category')

    def get_date(self, obj):
        product = obj.get('product') or obj.get('product_obj')
        if product and hasattr(product, 'created_at'):
            return product.created_at.strftime('%a %b %d %Y %H:%M:%S GMT+0100')
        return None


class BasketRequestSerializer(serializers.Serializer):
    """Сериализатор для добавления/удаления товара из корзины."""
    id = serializers.IntegerField(required=True)
    count = serializers.IntegerField(required=True, min_value=1)


# ==================== НАСТРОЙКИ ====================

class DeliverySettingsSerializer(serializers.ModelSerializer):
    """Сериализатор настроек доставки."""

    class Meta:
        model = DeliverySettings
        fields = ['standard_delivery_cost', 'free_delivery_threshold', 'express_delivery_cost']