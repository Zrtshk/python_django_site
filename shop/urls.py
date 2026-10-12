from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Регистрация ViewSet'ов для автоматической генерации маршрутов
router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet, basename='category')
router.register(r'products', views.ProductViewSet, basename='product')
router.register(r'reviews', views.ReviewViewSet, basename='review')
router.register(r'cart', views.CartViewSet, basename='cart')
router.register(r'orders', views.OrderViewSet, basename='order')
router.register(r'users', views.UserViewSet, basename='user')
router.register(r'auth', views.AuthViewSet, basename='auth')

urlpatterns = [
    # ==================== КАТАЛОГ И ТОВАРЫ ====================

    # Акции (скидки)
    path('sales/', views.SalesView.as_view(), name='sales'),

    # Теги для фильтрации
    path('tags/', views.TagsView.as_view(), name='tags'),

    # Каталог товаров
    path('catalog/', views.CatalogView.as_view(), name='catalog'),

    # Популярные товары
    path(
        'products/popular/',
        views.ProductViewSet.as_view({'get': 'popular'}),
        name='popular'
    ),

    # Ограниченный тираж
    path(
        'products/limited/',
        views.ProductViewSet.as_view({'get': 'limited'}),
        name='limited'
    ),

    # Баннеры для главной страницы
    path('banners/', views.BannersView.as_view(), name='banners'),

    # Детальная страница товара
    path('product/<int:pk>/',
         views.ProductViewSet.as_view({'get': 'retrieve'}),
         name='product_detail'),

    # Отзывы на товар
    path('product/<int:pk>/reviews', views.ReviewViewSet.as_view({'post': 'create'}), name='product_review'),

    # ==================== КОРЗИНА ====================

    # Получение и добавление товаров в корзину
    path('basket', views.CartViewSet.as_view(
        {'get': 'list', 'post': 'add'}),
         name='basket_no_slash'
         ),

    # Удаление товара из корзины
    path('basket/delete',
         views.CartViewSet.as_view({'delete': 'delete'}),
         name='basket_delete'
         ),

    # ==================== ПОЛЬЗОВАТЕЛИ И ПРОФИЛЬ ====================

    # Профиль пользователя (получение, обновление)
    path('profile', views.UserViewSet.as_view({
        'get': 'current',
        'put': 'update_profile',
        'patch': 'update_profile',
        'post': 'update_profile',
    }), name='profile'),

    # Аватар пользователя (обновление, удаление)
    path('profile/avatar', views.UserViewSet.as_view({
        'post': 'update_avatar',
        'delete': 'delete_avatar'
    }), name='profile_avatar'),

    # Смена пароля
    path('profile/password',
         views.UserViewSet.as_view({'post': 'change_password'}),
         name='change_password_no_slash'
         ),

    # ==================== АУТЕНТИФИКАЦИЯ ====================

    # Вход
    path('sign-in',
         views.AuthViewSet.as_view({'post': 'login'}),
         name='sign_in_no_slash'
         ),

    # Выход
    path('sign-out',
         views.AuthViewSet.as_view({'post': 'logout'}),
         name='sign_out'
         ),

    # Регистрация
    path('sign-up', views.RegistrationView.as_view(), name='sign_up'),

    # ==================== ЗАКАЗЫ ====================

    # Список заказов и создание
    path('orders', views.OrderViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='orders_no_slash'),

    path('orders/', views.OrderViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='orders'),

    # Детали заказа (получение, подтверждение)
    path('order/<int:pk>/', views.OrderViewSet.as_view({
        'get': 'retrieve',
        'post': 'update'
    }), name='order_detail'),

    path('order/<int:pk>', views.OrderViewSet.as_view({
        'get': 'retrieve',
        'post': 'update'
    }), name='order_detail_no_slash'),

    # ==================== ОПЛАТА ====================

    # Оплата заказа (с ID в URL)
    path('payment/<int:order_id>',
         views.OrderViewSet.as_view({'post': 'pay'}),
         name='payment_with_id_no_slash'
         ),

    # Оплата заказа (без ID в URL — берется из тела запроса)
    path('payment/',
         views.OrderViewSet.as_view({'post': 'pay'}),
         name='payment'
         ),

    # ==================== ВСЕ ОСТАЛЬНЫЕ МАРШРУТЫ ====================

    # Подключаем все маршруты от router
    path('', include(router.urls)),
]