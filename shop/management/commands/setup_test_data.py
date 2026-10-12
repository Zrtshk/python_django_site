from django.core.management.base import BaseCommand
from django.core.files import File
from django.contrib.auth import get_user_model
from shop.models import (
    Category, Product, Characteristic, ProductCharacteristic,
    Review, DeliverySettings
)
from decimal import Decimal
from io import BytesIO
from PIL import Image, ImageDraw
import os
import random

User = get_user_model()


class Command(BaseCommand):
    help = 'Полная настройка проекта: создание всех тестовых данных'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Начинаем настройку тестовых данных...'))

        # 1. Создаем папки
        os.makedirs('media/products', exist_ok=True)
        os.makedirs('media/placeholders', exist_ok=True)
        os.makedirs('static/images', exist_ok=True)

        # 2. Создаем суперпользователя
        self.create_superuser()

        # 3. Создаем настройки доставки
        self.create_delivery_settings()

        # 4. Создаем категории
        categories = self.create_categories()

        # 5. Создаем характеристики
        characteristics = self.create_characteristics()

        # 6. Создаем пользователей
        users = self.create_users()

        # 7. Создаем товары
        products = self.create_products(categories, characteristics)

        # 8. Создаем отзывы
        self.create_reviews(products, users)

        # 9. Создаем заглушку для изображений
        self.create_placeholder()

        self.stdout.write(self.style.SUCCESS('✅ Все тестовые данные успешно созданы!'))
        self.stdout.write(self.style.SUCCESS('📋 Администратор: admin@example.com / admin123'))
        self.stdout.write(self.style.SUCCESS('📋 Пользователи: user1@example.com ... user5@example.com / 123456'))

    def create_superuser(self):
        User = get_user_model()
        admin_email = 'admin@example.com'
        admin_username = 'admin'

        if not User.objects.filter(email=admin_email).exists() and not User.objects.filter(
                username=admin_username).exists():
            User.objects.create_superuser(
                email=admin_email,
                username=admin_username,
                password='admin123',
                first_name='Admin',
                last_name='Adminovich'
            )
            self.stdout.write('✅ Суперпользователь создан')

    def create_delivery_settings(self):
        if not DeliverySettings.objects.exists():
            DeliverySettings.objects.create(
                standard_delivery_cost=200.00,
                free_delivery_threshold=2000.00,
                express_delivery_cost=500.00
            )
            self.stdout.write('✅ Настройки доставки созданы')

    def create_categories(self):
        categories_data = [
            {'name': 'Смартфоны', 'slug': 'smartfony'},
            {'name': 'Ноутбуки', 'slug': 'noutbuki'},
            {'name': 'Планшеты', 'slug': 'planshety'},
            {'name': 'Аксессуары', 'slug': 'aksessuary'},
        ]

        subcategories = [
            {'name': 'Игровые ноутбуки', 'slug': 'game-noutbuki', 'parent': 'noutbuki'},
            {'name': 'Чехлы', 'slug': 'chehly', 'parent': 'aksessuary'},
        ]

        categories = {}
        for cat_data in categories_data:
            cat, _ = Category.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={'name': cat_data['name'], 'is_active': True}
            )
            categories[cat_data['slug']] = cat

        for sub_data in subcategories:
            parent = categories.get(sub_data['parent'])
            if parent:
                Category.objects.get_or_create(
                    slug=sub_data['slug'],
                    defaults={'name': sub_data['name'], 'parent': parent, 'is_active': True}
                )

        self.stdout.write(f'✅ Создано {len(categories)} категорий')
        return categories

    def create_characteristics(self):
        characteristics_data = [
            {'name': 'Цвет', 'filter_type': 'dropdown', 'is_multiple': True},
            {'name': 'Объем памяти', 'filter_type': 'dropdown', 'is_multiple': False},
            {'name': 'В наличии', 'filter_type': 'checkbox', 'is_multiple': False},
            {'name': 'Процессор', 'filter_type': 'text', 'is_multiple': False},
        ]

        characteristics = {}
        for char_data in characteristics_data:
            char, _ = Characteristic.objects.get_or_create(
                name=char_data['name'],
                defaults={'filter_type': char_data['filter_type'], 'is_multiple': char_data['is_multiple']}
            )
            characteristics[char_data['name']] = char

        self.stdout.write(f'✅ Создано {len(characteristics)} характеристик')
        return characteristics

    def create_users(self):
        users = []
        for i in range(5):
            user, _ = User.objects.get_or_create(
                email=f'user{i + 1}@example.com',
                defaults={
                    'username': f'user{i + 1}',
                    'first_name': f'Имя{i + 1}',
                    'last_name': f'Фамилия{i + 1}',
                    'phone': f'+7900000000{i + 1}',
                }
            )
            user.set_password('123456')
            user.save()
            users.append(user)

        self.stdout.write('✅ Создано 5 пользователей')
        return users

    def create_products(self, categories, characteristics):
        products_data = [
            {
                'name': 'iPhone 15 Pro',
                'slug': 'iphone-15-pro',
                'short_description': 'Флагманский смартфон Apple',
                'full_description': 'Самый мощный смартфон Apple с титановым корпусом',
                'price': 999.99,
                'categories': ['smartfony'],
                'manufacturer': 'Apple',
                'sort_index': 10,
                'is_limited': True,
                'characteristics': {'Цвет': 'Титановый', 'Объем памяти': '256 ГБ', 'В наличии': 'Да',
                                    'Процессор': 'A17 Pro'}
            },
            {
                'name': 'MacBook Pro 16',
                'slug': 'macbook-pro-16',
                'short_description': 'Мощный ноутбук для профессионалов',
                'full_description': 'Ноутбук с процессором M3 Max и экраном 16 дюймов',
                'price': 2499.99,
                'categories': ['noutbuki', 'game-noutbuki'],
                'manufacturer': 'Apple',
                'sort_index': 9,
                'is_limited': False,
                'characteristics': {'Цвет': 'Серый', 'Объем памяти': '1 ТБ', 'В наличии': 'Да', 'Процессор': 'M3 Max'}
            },
            {
                'name': 'Samsung Galaxy S24',
                'slug': 'samsung-galaxy-s24',
                'short_description': 'Флагманский Android смартфон',
                'full_description': 'Смартфон с искусственным интеллектом и камерой 200 МП',
                'price': 899.99,
                'categories': ['smartfony'],
                'manufacturer': 'Samsung',
                'sort_index': 8,
                'is_limited': False,
                'characteristics': {'Цвет': 'Фиолетовый', 'Объем памяти': '256 ГБ', 'В наличии': 'Да',
                                    'Процессор': 'Exynos 2400'}
            },
            {
                'name': 'iPad Pro 12.9',
                'slug': 'ipad-pro-12-9',
                'short_description': 'Профессиональный планшет',
                'full_description': 'Планшет с экраном Liquid Retina XDR',
                'price': 1099.99,
                'categories': ['planshety'],
                'manufacturer': 'Apple',
                'sort_index': 7,
                'is_limited': True,
                'characteristics': {'Цвет': 'Серебристый', 'Объем памяти': '512 ГБ', 'В наличии': 'Да',
                                    'Процессор': 'M2'}
            },
            {
                'name': 'Samsung Galaxy Tab S9',
                'slug': 'samsung-galaxy-tab-s9',
                'short_description': 'Мощный Android планшет',
                'full_description': 'Планшет с S Pen и Dynamic AMOLED экраном',
                'price': 799.99,
                'categories': ['planshety'],
                'manufacturer': 'Samsung',
                'sort_index': 6,
                'is_limited': False,
                'characteristics': {'Цвет': 'Бежевый', 'Объем памяти': '256 ГБ', 'В наличии': 'Нет',
                                    'Процессор': 'Snapdragon 8 Gen 2'}
            },
            {
                'name': 'ASUS ROG Zephyrus G16',
                'slug': 'asus-rog-zephyrus-g16',
                'short_description': 'Игровой ноутбук премиум класса',
                'full_description': 'Ноутбук с Intel Core i9 и RTX 4090',
                'price': 3299.99,
                'categories': ['noutbuki', 'game-noutbuki'],
                'manufacturer': 'ASUS',
                'sort_index': 3,
                'is_limited': True,
                'characteristics': {'Цвет': 'Черный', 'Объем памяти': '2 ТБ', 'В наличии': 'Да',
                                    'Процессор': 'Intel Core i9'}
            },
        ]

        # Дополнительные товары
        extra_products = [
            {'name': 'Sony WH-1000XM5', 'price': 349.99, 'manufacturer': 'Sony'},
            {'name': 'Apple AirPods Pro 2', 'price': 249.99, 'manufacturer': 'Apple'},
            {'name': 'DJI Mini 3 Pro', 'price': 759.99, 'manufacturer': 'DJI'},
            {'name': 'Kindle Paperwhite', 'price': 139.99, 'manufacturer': 'Amazon'},
            {'name': 'Apple Watch Series 8', 'price': 399.99, 'manufacturer': 'Apple'},
            {'name': 'Nanoleaf Shapes', 'price': 199.99, 'manufacturer': 'Nanoleaf'},
            {'name': 'Logitech MX Master 3S', 'price': 99.99, 'manufacturer': 'Logitech'},
            {'name': 'JBL Charge 5', 'price': 179.99, 'manufacturer': 'JBL'},
            {'name': 'Nothing Phone 2', 'price': 699.99, 'manufacturer': 'Nothing'},
            {'name': 'Google Pixel 7 Pro', 'price': 899.99, 'manufacturer': 'Google'},
            {'name': 'OnePlus 11', 'price': 799.99, 'manufacturer': 'OnePlus'},
            {'name': 'Xiaomi 13 Pro', 'price': 999.99, 'manufacturer': 'Xiaomi'},
        ]

        colors = [
            (255, 100, 100), (100, 100, 255), (100, 255, 100),
            (255, 200, 100), (200, 100, 255), (100, 255, 200),
            (255, 150, 200), (150, 200, 255), (200, 255, 150),
        ]

        products = []

        # Создаем основные товары
        for prod_data in products_data:
            product = self._create_single_product(prod_data, categories, characteristics, colors)
            if product:
                products.append(product)

        # Создаем дополнительные товары
        for i, prod_data in enumerate(extra_products):
            cat = random.choice(list(categories.values()))
            product_data = {
                'name': prod_data['name'],
                'slug': prod_data['name'].lower().replace(' ', '-') + f'-{i + 100}',
                'short_description': f'{prod_data["name"]} - отличный выбор!',
                'full_description': f'Полное описание {prod_data["name"]}. Высокое качество, надежность и стильный дизайн.',
                'price': prod_data['price'],
                'categories': [cat.slug],
                'manufacturer': prod_data['manufacturer'],
                'sort_index': random.randint(0, 100),
                'is_limited': True,
                'characteristics': {'Цвет': random.choice(['Красный', 'Синий', 'Зеленый', 'Черный', 'Белый', 'Серый'])},
            }
            product = self._create_single_product(product_data, categories, characteristics, colors, i)
            if product:
                products.append(product)

        self.stdout.write(f'✅ Создано {len(products)} товаров')
        return products

    def _create_single_product(self, prod_data, categories, characteristics, colors, index=0):
        color = colors[index % len(colors)]

        product, created = Product.objects.get_or_create(
            slug=prod_data['slug'],
            defaults={
                'name': prod_data['name'],
                'short_description': prod_data['short_description'],
                'full_description': prod_data['full_description'],
                'price': Decimal(str(prod_data['price'])),
                'manufacturer': prod_data.get('manufacturer', ''),
                'sort_index': prod_data.get('sort_index', 0),
                'is_limited': prod_data.get('is_limited', False),
                'is_active': True,
            }
        )

        if created:
            for cat_slug in prod_data.get('categories', []):
                if cat_slug in categories:
                    product.categories.add(categories[cat_slug])

            for char_name, value in prod_data.get('characteristics', {}).items():
                if char_name in characteristics:
                    ProductCharacteristic.objects.create(
                        product=product,
                        characteristic=characteristics[char_name],
                        value=value
                    )

            # Создаем изображение
            img = Image.new('RGB', (300, 300), color=color)
            draw = ImageDraw.Draw(img)
            text = prod_data['name'][:12]
            try:
                draw.text((50, 140), text, fill='white')
            except Exception:
                draw.text((50, 140), "Product", fill='white')

            img_io = BytesIO()
            img.save(img_io, 'PNG')
            img_io.seek(0)

            filename = f"product_{product.id}.png"
            product.image.save(filename, File(img_io), save=True)
            return product
        return None

    def create_reviews(self, products, users):
        review_texts = [
            'Отличный товар! Рекомендую всем!',
            'Хорошее качество, доволен покупкой',
            'Супер! Быстрая доставка, отличный продукт',
            'Неплохо, но есть над чем поработать',
            'Лучшая покупка в этом году!',
        ]

        for product in products[:8]:
            for i, user in enumerate(users[:3]):
                if i < len(review_texts):
                    Review.objects.get_or_create(
                        product=product,
                        user=user,
                        defaults={
                            'text': review_texts[i],
                            'rating': random.randint(3, 5),
                        }
                    )
        self.stdout.write('✅ Созданы отзывы')

    def create_placeholder(self):
        img = Image.new('RGB', (300, 300), color=(128, 128, 128))
        draw = ImageDraw.Draw(img)
        try:
            draw.text((80, 140), "No Image", fill='white')
        except Exception:
            pass

        img_io = BytesIO()
        img.save(img_io, 'PNG')
        img_io.seek(0)

        with open('media/placeholders/no-image.png', 'wb') as f:
            f.write(img_io.getvalue())

        # Также создаем в static
        with open('static/images/no-image.png', 'wb') as f:
            f.write(img_io.getvalue())

        self.stdout.write('✅ Создана заглушка для изображений')
