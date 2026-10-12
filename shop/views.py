from datetime import timedelta
import json
from decimal import Decimal, InvalidOperation

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q, Count, Avg
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets, generics, status
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView

from .models import (
    Category, Product, Review, ProductCharacteristic,
    Cart, CartItem, Order, OrderItem, DeliverySettings
)
from .serializers import (
    CategorySerializer, ProductListSerializer,
    ReviewSerializer, CartSerializer,
    OrderSerializer, DeliverySettingsSerializer,
    UserProfileSerializer, UserRegistrationSerializer,
    ProductFullSerializer, CategoryItemSerializer
)

User = get_user_model()


# ==================== ГЛАВНАЯ СТРАНИЦА ====================

def home_view(request):
    """
    Представление для главной страницы.
    Передает в шаблон популярные товары, ограниченный тираж и категории.
    """
    popular_products = Product.objects.filter(
        is_active=True, is_deleted=False
    ).order_by('-sort_index', '-purchase_count')[:8]

    limited_products = Product.objects.filter(
        is_active=True, is_deleted=False, is_limited=True
    )[:16]

    categories = Category.objects.filter(
        is_active=True, is_deleted=False, parent__isnull=True
    )

    context = {
        'popularCards': popular_products,
        'limitedCards': limited_products,
        'categories': categories,
        'banners': [
            {'title': 'Скидка 50%', 'subtitle': 'На все смартфоны', 'image': '/static/images/banner1.jpg'},
            {'title': 'Новинки', 'subtitle': 'Лучшие товары сезона', 'image': '/static/images/banner2.jpg'}
        ]
    }

    return render(request, 'shop/index.html', context)


# ==================== КАТЕГОРИИ ====================

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для получения категорий.
    Возвращает только корневые категории (без родителей).
    """
    queryset = Category.objects.filter(is_active=True, is_deleted=False)
    serializer_class = CategoryItemSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Возвращаем только корневые категории."""
        return self.queryset.filter(parent__isnull=True)

    def list(self, request, *args, **kwargs):
        """Список всех корневых категорий."""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class CategoriesListView(APIView):
    """
    Список категорий для меню (без /api/).
    Используется для отображения категорий в шапке сайта.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем все активные корневые категории."""
        categories = Category.objects.filter(
            is_active=True, is_deleted=False, parent__isnull=True
        )
        serializer = CategoryItemSerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)


class FeaturedCategoriesView(APIView):
    """
    Избранные категории для главной страницы.
    Возвращает первые 3 активные корневые категории.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        categories = Category.objects.filter(
            is_active=True, is_deleted=False, parent__isnull=True
        )[:3]
        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)


# ==================== ТОВАРЫ ====================

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для товаров.
    Поддерживает фильтрацию по категории, цене, производителю,
    поиск по названию и сортировку.
    """
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Формируем queryset с учетом фильтров и сортировки."""
        queryset = Product.objects.filter(is_active=True, is_deleted=False)

        # Фильтрация по категории
        category_slug = self.request.query_params.get('category')
        if category_slug:
            category = get_object_or_404(Category, slug=category_slug)
            queryset = queryset.filter(categories=category)

        # Поиск по названию
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Фильтрация по цене
        price_min = self.request.query_params.get('price_min')
        price_max = self.request.query_params.get('price_max')
        if price_min:
            queryset = queryset.filter(price__gte=Decimal(price_min))
        if price_max:
            queryset = queryset.filter(price__lte=Decimal(price_max))

        # Фильтрация по производителю
        manufacturer = self.request.query_params.get('manufacturer')
        if manufacturer:
            queryset = queryset.filter(manufacturer__icontains=manufacturer)

        # Сортировка
        sort_by = self.request.query_params.get('sort_by', '-sort_index')
        if sort_by == 'popularity':
            queryset = queryset.order_by('-purchase_count')
        elif sort_by == 'price':
            queryset = queryset.order_by('price')
        elif sort_by == '-price':
            queryset = queryset.order_by('-price')
        elif sort_by == 'reviews':
            queryset = queryset.annotate(reviews_count=Count('reviews')).order_by('-reviews_count')
        elif sort_by == 'new':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-sort_index', '-purchase_count')

        return queryset

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия."""
        if self.action == 'retrieve':
            return ProductFullSerializer
        return ProductListSerializer

    @action(detail=False, methods=['get'], url_path='popular', url_name='popular')
    def popular(self, request):
        """Получение популярных товаров (8 штук)."""
        products = self.get_queryset()[:8]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def manufacturers(self, request):
        """Получение списка производителей для фильтра."""
        manufacturers = Product.objects.filter(
            is_active=True, is_deleted=False
        ).exclude(manufacturer__isnull=True).exclude(manufacturer=''
        ).values_list('manufacturer', flat=True).distinct()
        return Response(sorted(list(manufacturers)))

    @action(detail=False, methods=['get'])
    def top(self, request):
        """Получение топ-товаров (8 штук)."""
        products = self.get_queryset()[:8]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='limited', url_name='limited')
    def limited(self, request):
        """Получение товаров ограниченного тиража (до 16)."""
        products = self.get_queryset().filter(is_limited=True)[:16]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class ProductsListView(APIView):
    """
    Список товаров с фильтрацией и пагинацией (без /api/).
    """
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем список товаров с пагинацией."""
        products = Product.objects.filter(is_active=True, is_deleted=False)

        # Фильтрация
        category = request.GET.get('category')
        if category:
            products = products.filter(categories__slug=category)

        search = request.GET.get('search')
        if search:
            products = products.filter(name__icontains=search)

        price_min = request.GET.get('price_min')
        price_max = request.GET.get('price_max')
        if price_min:
            products = products.filter(price__gte=price_min)
        if price_max:
            products = products.filter(price__lte=price_max)

        # Сортировка
        sort = request.GET.get('sort')
        if sort == 'popular':
            products = products.order_by('-purchase_count')
        elif sort == 'price':
            products = products.order_by('price')
        elif sort == '-price':
            products = products.order_by('-price')
        elif sort == 'reviews':
            products = products.annotate(review_count=Count('reviews')).order_by('-review_count')
        elif sort == 'new':
            products = products.order_by('-created_at')
        else:
            products = products.order_by('-sort_index', '-purchase_count')

        # Пагинация
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 12))
        start = (page - 1) * page_size
        end = start + page_size

        total = products.count()
        products_page = products[start:end]

        serializer = ProductListSerializer(products_page, many=True, context={'request': request})

        return Response({
            'results': serializer.data,
            'count': total,
            'next': f'?page={page + 1}' if end < total else None,
            'previous': f'?page={page - 1}' if page > 1 else None,
        })


class PopularProductsView(APIView):
    """Популярные товары для главной страницы (без /api/)."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем 8 популярных товаров."""
        products = Product.objects.filter(
            is_active=True, is_deleted=False
        ).order_by('-sort_index', '-purchase_count')[:8]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


class LimitedProductsView(APIView):
    """Ограниченный тираж для главной страницы (без /api/)."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем до 16 товаров ограниченного тиража."""
        products = Product.objects.filter(
            is_active=True, is_deleted=False, is_limited=True
        )[:16]
        serializer = ProductListSerializer(products, many=True, context={'request': request})
        return Response(serializer.data)


# ==================== ОТЗЫВЫ ====================

class ReviewViewSet(viewsets.ModelViewSet):
    """API для отзывов на товары."""
    serializer_class = ReviewSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        product_id = self.request.query_params.get('product')
        if product_id:
            return Review.objects.filter(product_id=product_id, is_deleted=False)
        return Review.objects.filter(is_deleted=False)

    def create(self, request, *args, **kwargs):
        """Создание отзыва на товар."""
        product_id = self.kwargs.get('pk')
        if not product_id:
            return Response(
                {'error': 'Не указан ID товара'},
                status=status.HTTP_400_BAD_REQUEST
            )

        product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)

        if not request.user.is_authenticated:
            return Response(
                {'error': 'Только авторизованные пользователи могут оставлять отзывы'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        data = request.data.copy()
        data['product'] = product_id
        data['user'] = request.user.id

        # Проверяем, есть ли уже отзыв от этого пользователя на этот товар
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response(
                {'error': 'Вы уже оставили отзыв на этот товар'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save(user=request.user, product=product)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request, *args, **kwargs):
        """Получение отзывов на товар."""
        product_id = self.kwargs.get('pk')
        if product_id:
            reviews = Review.objects.filter(product_id=product_id, is_deleted=False)
            serializer = self.get_serializer(reviews, many=True)
            return Response(serializer.data)
        return Response({'error': 'Не указан ID товара'}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# ==================== КОРЗИНА ====================

class CartViewSet(viewsets.ViewSet):
    """API для работы с корзиной."""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [AllowAny]

    def get_cart(self, user=None, session_key=None):
        """Получение корзины по пользователю или сессии."""
        if user and user.is_authenticated:
            cart, created = Cart.objects.get_or_create(user=user)
            return cart
        if session_key:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
            return cart
        return None

    def get_or_create_cart(self, request):
        """Получение или создание корзины для текущего запроса."""
        if request.user.is_authenticated:
            return self.get_cart(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart = self.get_cart(session_key=session_key)
            if not cart:
                cart = Cart.objects.create(session_key=session_key)
            return cart

    def list(self, request):
        """Получение корзины."""
        cart = self.get_or_create_cart(request)
        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data['items'])

    @method_decorator(csrf_exempt)
    @action(detail=False, methods=['post'])
    def add(self, request, product_id=None):
        """Добавление товара в корзину."""
        product_id = request.data.get('id') or request.data.get('product_id')

        if not product_id:
            return Response(
                {'error': 'Не указан ID товара', 'received_data': request.data},
                status=status.HTTP_400_BAD_REQUEST
            )

        quantity = request.data.get('count', request.data.get('quantity', 1))

        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
        except (TypeError, ValueError):
            quantity = 1

        product = get_object_or_404(Product, id=product_id, is_active=True, is_deleted=False)
        cart = self.get_or_create_cart(request)

        cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def update_quantity(self, request):
        """Обновление количества товара в корзине."""
        item_id = request.data.get('item_id')
        quantity = request.data.get('quantity', 1)

        if not item_id:
            return Response({'error': 'Не указан ID позиции'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            quantity = 1

        if request.user.is_authenticated:
            cart = self.get_cart(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)
            cart = self.get_cart(session_key=session_key)

        if not cart:
            return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)

        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)

        if quantity <= 0:
            cart_item.delete()
        else:
            cart_item.quantity = quantity
            cart_item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    def delete(self, request):
        """Удаление товара из корзины (DELETE /basket)."""
        product_id = request.data.get('id')
        quantity = request.data.get('count', 1)

        if not product_id:
            return Response({'error': 'Не указан ID товара'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            quantity = int(quantity)
            if quantity < 1:
                quantity = 1
        except (TypeError, ValueError):
            quantity = 1

        if request.user.is_authenticated:
            cart = self.get_cart(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)
            cart = self.get_cart(session_key=session_key)

        if not cart:
            return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)

        cart_item = CartItem.objects.filter(cart=cart, product_id=product_id).first()
        if not cart_item:
            return Response({'error': 'Товар не найден в корзине'}, status=status.HTTP_404_NOT_FOUND)

        if quantity >= cart_item.quantity:
            cart_item.delete()
        else:
            cart_item.quantity -= quantity
            cart_item.save()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def remove(self, request):
        """Удаление товара из корзины (POST /cart/remove/)."""
        item_id = request.data.get('item_id')

        if not item_id:
            return Response({'error': 'Не указан ID позиции'}, status=status.HTTP_400_BAD_REQUEST)

        if request.user.is_authenticated:
            cart = self.get_cart(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)
            cart = self.get_cart(session_key=session_key)

        if not cart:
            return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)

        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()

        serializer = CartSerializer(cart, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def clear(self, request):
        """Очистка корзины."""
        if request.user.is_authenticated:
            cart = self.get_cart(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({'error': 'Корзина не найдена'}, status=status.HTTP_404_NOT_FOUND)
            cart = self.get_cart(session_key=session_key)

        if cart:
            cart.items.all().delete()

        serializer = CartSerializer(cart, context={'request': request}) if cart else CartSerializer({'items': []}, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def count(self, request):
        """Количество товаров в корзине."""
        if request.user.is_authenticated:
            cart = self.get_cart(user=request.user)
        else:
            session_key = request.session.session_key
            if not session_key:
                return Response({'count': 0})
            cart = self.get_cart(session_key=session_key)

        if cart:
            count = sum(item.quantity for item in cart.items.all())
            return Response({'count': count})
        return Response({'count': 0})


class BasketView(APIView):
    """Получение корзины для фронтенда (без /api/)."""
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()

        if cart:
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        return Response({'items': [], 'total_price': 0, 'total_items': 0})


# ==================== ЗАКАЗЫ ====================

class OrderViewSet(viewsets.ViewSet):
    """API для управления заказами."""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Список заказов пользователя."""
        orders = Order.objects.filter(user=request.user, is_deleted=False)
        serializer = OrderSerializer(orders, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        """Детали заказа."""
        order = get_object_or_404(Order, id=pk, user=request.user, is_deleted=False)
        serializer = OrderSerializer(order, context={'request': request})
        return Response(serializer.data)

    def create(self, request):
        """Создание заказа из корзины."""
        # Получаем корзину пользователя или сессии
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()

        if not cart or not cart.items.exists():
            return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

        # Создаем заказ
        order = Order.objects.create(
            user=request.user if request.user.is_authenticated else None,
            full_name=request.user.get_full_name() or request.user.username if request.user.is_authenticated else '',
            email=request.user.email if request.user.is_authenticated else '',
            phone=request.user.phone or '' if request.user.is_authenticated else '',
            delivery_method='standard',
            delivery_cost=0,
            city='',
            address='',
            payment_method='card',
            total_amount=cart.get_total_price(),
            comment=''
        )

        # Создаем позиции заказа
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_price=cart_item.product.price,
                quantity=cart_item.quantity
            )

        # Очищаем корзину
        cart.items.all().delete()

        return Response({'orderId': order.id}, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        """Обновление данных заказа (подтверждение)."""
        order = get_object_or_404(Order, id=pk, user=request.user, is_deleted=False)

        if 'full_name' in request.data:
            order.full_name = request.data['full_name']
        if 'email' in request.data:
            order.email = request.data['email']
        if 'phone' in request.data:
            order.phone = request.data['phone']
        if 'delivery_method' in request.data:
            order.delivery_method = request.data['delivery_method']
        if 'city' in request.data:
            order.city = request.data['city']
        if 'address' in request.data:
            order.address = request.data['address']
        if 'payment_method' in request.data:
            order.payment_method = request.data['payment_method']
        if 'comment' in request.data:
            order.comment = request.data['comment']

        order.save()

        return Response({'orderId': order.id}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='payment/(?P<order_id>[0-9]+)', url_name='payment_with_id')
    def pay(self, request, order_id=None):
        """Оплата заказа (POST /api/payment/<order_id>/)."""
        if order_id:
            order = get_object_or_404(Order, id=order_id, user=request.user, is_deleted=False)
        else:
            order_id = request.data.get('order_id') or request.data.get('id')
            if not order_id:
                return Response({'error': 'Не указан ID заказа'}, status=status.HTTP_400_BAD_REQUEST)
            order = get_object_or_404(Order, id=order_id, user=request.user, is_deleted=False)

        card_number = request.data.get('number')
        month = request.data.get('month')
        year = request.data.get('year')

        if not card_number:
            return Response({'error': 'Необходимо указать номер карты или счета'}, status=status.HTTP_400_BAD_REQUEST)

        card_number_str = str(card_number).replace(' ', '')

        # Валидация номера карты
        if not card_number_str.isdigit():
            return Response({'error': 'Номер должен содержать только цифры'}, status=status.HTTP_400_BAD_REQUEST)

        if len(card_number_str) > 8:
            return Response({'error': 'Номер не может быть длиннее 8 цифр'}, status=status.HTTP_400_BAD_REQUEST)

        if int(card_number_str) % 2 != 0:
            return Response({'error': 'Номер должен быть четным'}, status=status.HTTP_400_BAD_REQUEST)

        # ===== ВАЛИДАЦИЯ ДАТЫ =====
        from datetime import datetime

        if month and year:
            try:
                month = int(month)
                year = int(year)

                # Проверяем, что месяц от 1 до 12
                if month < 1 or month > 12:
                    return Response(
                        {'error': 'Неверный месяц. Используйте значение от 1 до 12'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Проверяем, что год корректный (2 или 4 цифры)
                # Если год 2-значный (например 25), преобразуем в 4-значный (2025)
                if year < 100:
                    # Если год < 50, считаем что это 20XX, иначе 19XX
                    if year < 50:
                        full_year = 2000 + year
                    else:
                        full_year = 1900 + year
                else:
                    full_year = year

                # Проверяем, что год не слишком старый и не слишком далекий
                if full_year < 2000 or full_year > 2100:
                    return Response(
                        {'error': 'Неверный год. Используйте 2-значное число (например, 25 для 2025)'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # ПОЛУЧАЕМ ТЕКУЩУЮ ДАТУ
                now = datetime.now()
                current_year = now.year
                current_month = now.month

                # Проверяем, что карта не просрочена
                # Если год меньше текущего года — просрочена
                if full_year < current_year:
                    return Response(
                        {'error': f'Срок действия карты истек (год {full_year})'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                # Если год равен текущему, проверяем месяц
                if full_year == current_year and month < current_month:
                    return Response(
                        {'error': f'Срок действия карты истек (месяц {month})'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            except (ValueError, TypeError):
                return Response(
                    {'error': 'Неверный формат даты. Укажите месяц (1-12) и год (2 цифры)'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Симуляция оплаты
        if int(card_number_str) % 2 == 0 and not card_number_str.endswith('0'):
            order.payment_status = 'paid'
            order.save()

            for item in order.items.all():
                if item.product:
                    item.product.purchase_count += item.quantity
                    item.product.save()

            return Response({
                'status': 'success',
                'message': 'Ждём подтверждения оплаты от платёжной системы',
                'order_id': order.id
            })
        else:
            order.payment_status = 'failed'
            order.payment_error = 'Ошибка при обработке платежа'
            order.save()

            return Response({
                'status': 'error',
                'message': 'Ошибка при обработке платежа',
                'order_id': order.id
            }, status=status.HTTP_400_BAD_REQUEST)


class OrderHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """История заказов пользователя."""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        """Возвращаем только заказы текущего пользователя."""
        return Order.objects.filter(user=self.request.user, is_deleted=False)


class OrderDetailViewSet(viewsets.ReadOnlyModelViewSet):
    """Детали заказа (для неавторизованных)."""
    permission_classes = [AllowAny]
    serializer_class = OrderSerializer

    def get_queryset(self):
        """Возвращаем все активные заказы."""
        return Order.objects.filter(is_deleted=False)


# ==================== ПОЛЬЗОВАТЕЛИ / ПРОФИЛЬ ====================

class UserViewSet(viewsets.ViewSet):
    """API для управления профилем пользователя."""
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        """Получение профиля пользователя."""
        user = request.user
        if pk and str(pk) != str(user.id):
            return Response({'error': 'Доступ запрещен'}, status=status.HTTP_403_FORBIDDEN)
        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['put', 'patch', 'post'])
    def update_profile(self, request):
        """Обновление профиля пользователя."""
        user = request.user
        data = request.data.copy()

        if 'avatar' in data:
            del data['avatar']

        if 'fullName' in data:
            full_name = data.pop('fullName', '').strip()
            if full_name:
                parts = full_name.split(' ', 1)
                data['first_name'] = parts[0]
                data['last_name'] = parts[1] if len(parts) > 1 else ''

        serializer = UserProfileSerializer(user, data=data, partial=True, context={'request': request})

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], url_path='avatar', url_name='delete_avatar')
    def delete_avatar(self, request):
        """Удаление аватара пользователя."""
        user = request.user

        if not user.avatar:
            return Response({'error': 'Аватар не найден'}, status=status.HTTP_404_NOT_FOUND)

        user.avatar.delete()
        user.avatar = None
        user.save()

        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Профиль текущего пользователя."""
        serializer = UserProfileSerializer(request.user, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['post'], url_path='password', url_name='change_password')
    def change_password(self, request):
        """Смена пароля пользователя."""
        user = request.user
        current_password = request.data.get('currentPassword')
        new_password = request.data.get('newPassword')

        if not current_password or not new_password:
            return Response({'error': 'Не указан текущий или новый пароль'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({'error': 'Неверный текущий пароль'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        return Response({'status': 'success', 'message': 'Пароль успешно изменен'})

    @action(detail=False, methods=['post'], url_path='avatar', url_name='update_avatar')
    def update_avatar(self, request):
        """Обновление аватара пользователя."""
        user = request.user

        if 'avatar' not in request.FILES:
            return Response({'error': 'Файл аватара не передан'}, status=status.HTTP_400_BAD_REQUEST)

        avatar_file = request.FILES['avatar']

        if avatar_file.size > 2 * 1024 * 1024:
            return Response({'error': 'Размер аватара не должен превышать 2 МБ'}, status=status.HTTP_400_BAD_REQUEST)

        user.avatar = avatar_file
        user.save()

        serializer = UserProfileSerializer(user, context={'request': request})
        return Response(serializer.data)


class RegistrationView(APIView):
    """Регистрация нового пользователя по Swagger."""
    permission_classes = [AllowAny]

    def post(self, request):
        data = request.data

        # Если data пустой, пробуем парсить body
        if not data or isinstance(data, dict) and len(data) == 0:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except BaseException:
                pass

        # Если data все еще QueryDict с ключом JSON, извлекаем его
        if isinstance(data, dict) and len(data) == 1:
            for key, value in data.items():
                if key.startswith('{') and key.endswith('}'):
                    try:
                        data = json.loads(key)
                    except BaseException:
                        pass
                    break

        name = data.get('name')
        username = data.get('username')
        password = data.get('password')

        if not name or not username or not password:
            return Response(
                {'error': 'Не указаны name, username или password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Проверяем, существует ли пользователь
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Пользователь с таким username уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Разбиваем name на first_name и last_name
        name_parts = name.strip().split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Создаем пользователя
        user = User.objects.create(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=data.get('email') or f'{username}@example.com'
        )
        user.set_password(password)
        user.save()

        # Авторизуем пользователя
        from django.contrib.auth import login
        login(request, user)

        serializer = UserProfileSerializer(user, context={'request': request})
        return Response({
            'status': 'success',
            'user': serializer.data
        }, status=status.HTTP_201_CREATED)



# ==================== АУТЕНТИФИКАЦИЯ ====================

class AuthViewSet(viewsets.ViewSet):
    """API для аутентификации (вход/выход)."""
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'], url_path='login', url_name='login')
    def login(self, request):
        """Вход пользователя с переносом корзины."""
        data = request.data

        if not data or isinstance(data, dict) and len(data) == 0:
            try:
                data = json.loads(request.body.decode('utf-8'))
            except BaseException:
                pass

        if isinstance(data, dict) and len(data) == 1:
            for key, value in data.items():
                if key.startswith('{') and key.endswith('}'):
                    try:
                        data = json.loads(key)
                    except BaseException:
                        pass
                    break

        email = data.get('email') or data.get('username')
        password = data.get('password')

        if not email or not password:
            return Response({'error': 'Не указаны email и/или пароль'}, status=status.HTTP_400_BAD_REQUEST)

        from django.contrib.auth import authenticate, login
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # === ПЕРЕНОС КОРЗИНЫ ===
            session_key = request.session.session_key
            if session_key:
                # Находим гостевую корзину по сессии
                guest_cart = Cart.objects.filter(session_key=session_key).first()
                if guest_cart:
                    # Находим или создаем корзину пользователя
                    user_cart, created = Cart.objects.get_or_create(user=user)

                    # Переносим товары из гостевой корзины в корзину пользователя
                    for guest_item in guest_cart.items.all():
                        # Проверяем, есть ли такой товар уже в корзине пользователя
                        user_item = user_cart.items.filter(product=guest_item.product).first()
                        if user_item:
                            user_item.quantity += guest_item.quantity
                            user_item.save()
                        else:
                            guest_item.cart = user_cart
                            guest_item.save()

                    # Удаляем гостевую корзину
                    guest_cart.delete()

            # Выполняем вход
            login(request, user)
            serializer = UserProfileSerializer(user, context={'request': request})
            return Response({'status': 'success', 'user': serializer.data})

        return Response({'error': 'Неверный email или пароль'}, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """Выход пользователя."""
        from django.contrib.auth import logout
        logout(request)
        return Response({'status': 'success'})


# ==================== НАСТРОЙКИ ====================

class DeliverySettingsView(generics.RetrieveAPIView):
    """Настройки доставки."""
    permission_classes = [AllowAny]
    queryset = DeliverySettings.objects.all()
    serializer_class = DeliverySettingsSerializer

    def get_object(self):
        """Возвращаем единственный объект настроек."""
        return DeliverySettings.objects.first()


# ==================== БАННЕРЫ ====================

class BannersView(APIView):
    """Баннеры для главной страницы."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем список баннеров."""
        return Response([
            {
                'id': 1,
                'title': 'Скидка 50%',
                'price': 999,
                'images': [{
                    'src': '/static/images/banners/banner1.jpeg',
                    'alt': 'Скидка 50%'
                }],
                'category': 1
            },
            {
                'id': 2,
                'title': 'Новинки',
                'price': 499,
                'images': [{
                    'src': '/static/images/banners/banner2.jpeg',
                    'alt': 'Новинки'
                }],
                'category': 2
            }
        ])


# ==================== АКЦИИ (SALES) ====================

class SalesView(APIView):
    """Товары со скидкой (акции)."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем товары со скидкой с пагинацией."""
        page = int(request.GET.get('currentPage', 1))
        per_page = int(request.GET.get('limit', 12))

        products = Product.objects.filter(
            is_active=True, is_deleted=False, is_limited=True
        ).order_by('-created_at')

        paginator = Paginator(products, per_page)

        try:
            page_obj = paginator.page(page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        items = []
        for product in page_obj:
            sale_price = product.price * Decimal('0.7')
            items.append({
                'id': str(product.id),
                'title': product.name,
                'price': float(product.price),
                'salePrice': float(sale_price),
                'dateFrom': product.created_at.strftime('%d.%m') if product.created_at else '01-01',
                'dateTo': (product.created_at + timedelta(days=31)).strftime('%d.%m') if product.created_at else '02-01',
                'images': [{
                    'src': request.build_absolute_uri(product.image.url) if product.image else '/static/images/no-image.png',
                    'alt': product.name
                }]
            })

        return Response({
            'items': items,
            'currentPage': page_obj.number,
            'lastPage': paginator.num_pages,
        })


# ==================== КАТАЛОГ ====================

class CatalogView(APIView):
    """
    Каталог товаров с фильтрацией, сортировкой и пагинацией.
    Полностью соответствует Swagger спецификации.
    """
    permission_classes = [AllowAny]

    @staticmethod
    def _to_bool(value, default=False):
        """Преобразование значения в булево."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ('1', 'true', 'yes', 'on')

    @staticmethod
    def _to_int(value, default, min_value=1, max_value=None):
        """Преобразование значения в целое число с валидацией."""
        try:
            result = int(value)
        except (TypeError, ValueError):
            return default
        if result < min_value:
            return default
        if max_value is not None:
            result = min(result, max_value)
        return result

    @staticmethod
    def _to_decimal(value):
        """Преобразование значения в Decimal."""
        if value in (None, ''):
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _get_filter_data(self, request):
        """Получение данных фильтрации."""
        filter_data = {
            'name': request.GET.get('filter[name]', ''),
            'minPrice': request.GET.get('filter[minPrice]'),
            'maxPrice': request.GET.get('filter[maxPrice]'),
            'freeDelivery': request.GET.get('filter[freeDelivery]'),
            'available': request.GET.get('filter[available]'),
        }

        raw_filter = request.GET.get('filter')
        if raw_filter:
            try:
                json_filter = json.loads(raw_filter)
                if isinstance(json_filter, dict):
                    for key, value in json_filter.items():
                        if value is not None:
                            filter_data[key] = value
            except (TypeError, ValueError, json.JSONDecodeError):
                pass

        return filter_data

    def get(self, request):
        """Обработка GET-запроса для каталога."""
        current_page = self._to_int(request.GET.get('currentPage'), default=1)
        limit = self._to_int(request.GET.get('limit'), default=20, max_value=100)
        category_id = request.GET.get('category')
        sort = request.GET.get('sort', 'date')
        sort_type = request.GET.get('sortType', 'dec')

        if sort not in ('rating', 'price', 'reviews', 'date'):
            sort = 'date'
        if sort_type not in ('inc', 'dec'):
            sort_type = 'dec'

        filter_data = self._get_filter_data(request)
        search = filter_data.get('name', '')
        min_price = self._to_decimal(filter_data.get('minPrice'))
        max_price = self._to_decimal(filter_data.get('maxPrice'))
        free_delivery = self._to_bool(filter_data.get('freeDelivery'), default=False)
        available = self._to_bool(filter_data.get('available'), default=True)

        products = Product.objects.filter(
            is_active=True, is_deleted=False
        ).prefetch_related('categories', 'characteristics', 'reviews')

        if category_id:
            try:
                products = products.filter(categories__id=int(category_id))
            except (TypeError, ValueError):
                products = products.none()

        if search:
            products = products.filter(name__icontains=search.strip())

        if min_price is not None:
            products = products.filter(price__gte=min_price)
        if max_price is not None:
            products = products.filter(price__lte=max_price)

        if free_delivery:
            products = products.filter(price__gt=Decimal('1000'))

        if available:
            pass

        tag_ids = request.GET.getlist('tags') or request.GET.getlist('tags[]')
        if len(tag_ids) == 1:
            raw_tags = tag_ids[0]
            if raw_tags.startswith('['):
                try:
                    tag_ids = json.loads(raw_tags)
                except (ValueError, json.JSONDecodeError):
                    pass

        valid_tag_ids = []
        for tag_id in tag_ids:
            try:
                valid_tag_ids.append(int(tag_id))
            except (TypeError, ValueError):
                continue

        if valid_tag_ids:
            for tag_id in valid_tag_ids:
                products = products.filter(characteristics__characteristic__id=tag_id)

        products = products.distinct()

        products = products.annotate(
            reviews_count=Count('reviews', filter=Q(reviews__is_deleted=False), distinct=True),
            average_rating=Avg('reviews__rating', filter=Q(reviews__is_deleted=False))
        )

        if sort == 'price':
            order_by = '-price' if sort_type == 'dec' else 'price'
            products = products.order_by(order_by, 'id')
        elif sort == 'reviews':
            order_by = '-reviews_count' if sort_type == 'dec' else 'reviews_count'
            products = products.order_by(order_by, 'id')
        elif sort == 'rating':
            order_by = '-average_rating' if sort_type == 'dec' else 'average_rating'
            products = products.order_by(order_by, 'id')
        else:
            order_by = '-created_at' if sort_type == 'dec' else 'created_at'
            products = products.order_by(order_by, 'id')

        paginator = Paginator(products, limit)

        try:
            page_obj = paginator.page(current_page)
        except PageNotAnInteger:
            page_obj = paginator.page(1)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        items = []
        for product in page_obj.object_list:
            category = next(iter(product.categories.all()), None)

            items.append({
                'id': product.id,
                'category': category.id if category else None,
                'title': product.name,
                'price': float(product.price),
                'count': product.purchase_count or 0,
                'date': product.created_at.strftime('%a %b %d %Y %H:%M:%S GMT+0100') if product.created_at else None,
                'description': product.short_description or '',
                'freeDelivery': product.price > Decimal('1000'),
                'images': [{
                    'src': request.build_absolute_uri(product.image.url) if product.image else '/static/images/no-image.png',
                    'alt': product.name
                }],
                'tags': [
                    {'id': char.id, 'name': char.value}
                    for char in product.characteristics.all()[:5]
                ],
                'reviews': product.reviews_count,
                'rating': round(float(product.average_rating or 0), 1),
            })

        return Response({
            'items': items,
            'currentPage': page_obj.number,
            'lastPage': paginator.num_pages,
        })


# ==================== ТЕГИ ====================

class TagsView(APIView):
    """Получение тегов (характеристик) для фильтрации."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем список характеристик для фильтрации."""
        category_id = request.GET.get('category')

        if category_id:
            characteristics = ProductCharacteristic.objects.filter(
                product__categories__id=category_id,
                product__is_active=True,
                product__is_deleted=False
            ).values('characteristic__id', 'characteristic__name').distinct()
        else:
            characteristics = ProductCharacteristic.objects.filter(
                product__is_active=True,
                product__is_deleted=False
            ).values('characteristic__id', 'characteristic__name').distinct()

        return Response([
            {'id': char['characteristic__id'], 'name': char['characteristic__name']}
            for char in characteristics
        ])


# ==================== КОРЗИНА API ====================

class BasketAPIView(APIView):
    """Корзина для фронтенда через /api/basket."""
    permission_classes = [AllowAny]

    def get(self, request):
        """Возвращаем корзину текущего пользователя или сессии."""
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).first()
        else:
            session_key = request.session.session_key
            if not session_key:
                request.session.create()
                session_key = request.session.session_key
            cart = Cart.objects.filter(session_key=session_key).first()

        if cart:
            serializer = CartSerializer(cart)
            return Response(serializer.data)
        return Response({'items': [], 'total_price': 0, 'total_items': 0})