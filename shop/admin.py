from django.contrib import admin
from django.contrib.admin import ModelAdmin

from .models import (
    User, Category, Product, Characteristic, ProductCharacteristic,
    Review, Cart, CartItem, DeliverySettings, Order, OrderItem
)


class SoftDeleteAdmin(ModelAdmin):
    """Базовый класс для мягкого удаления в админке."""

    def delete_model(self, request, obj):
        """Мягкое удаление одного объекта."""
        obj.is_deleted = True
        obj.save()

    def delete_queryset(self, request, queryset):
        """Мягкое удаление нескольких объектов."""
        queryset.update(is_deleted=True)

    def get_queryset(self, request):
        """Показываем ВСЕ объекты (включая удаленные)."""
        return super().get_queryset(request)

    def get_list_display(self, request):
        """Добавляем is_deleted в список отображения."""
        list_display = super().get_list_display(request)
        if 'is_deleted' not in list_display:
            list_display = list(list_display) + ['is_deleted']
        return list_display


@admin.register(User)
class UserAdmin(SoftDeleteAdmin):
    list_display = ['email', 'username', 'phone', 'is_active', 'is_deleted']
    list_filter = ['is_active', 'is_deleted']
    search_fields = ['email', 'username', 'phone']
    actions = ['restore_selected']  # Добавляем возможность восстановления

    def restore_selected(self, request, queryset):
        """Восстановление удаленных объектов."""
        queryset.update(is_deleted=False)
        self.message_user(
            request, f"Восстановлено {
                queryset.count()} пользователей.")

    restore_selected.short_description = "Восстановить выбранные"


class ProductCharacteristicInline(admin.TabularInline):
    model = ProductCharacteristic
    extra = 1


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ['name', 'parent', 'is_active', 'is_deleted']
    list_filter = ['is_active', 'is_deleted', 'parent']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    actions = ['restore_selected']

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(
            request, f"Восстановлено {
                queryset.count()} категорий.")

    restore_selected.short_description = "Восстановить выбранные"


@admin.register(Product)
class ProductAdmin(SoftDeleteAdmin):
    list_display = [
        'name',
        'price',
        'purchase_count',
        'is_active',
        'is_limited',
        'is_deleted']
    list_filter = ['is_active', 'is_limited', 'is_deleted', 'categories']
    search_fields = ['name', 'slug', 'manufacturer']
    prepopulated_fields = {'slug': ('name',)}
    actions = ['restore_selected']

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(
            request, f"Восстановлено {
                queryset.count()} товаров.")

    restore_selected.short_description = "Восстановить выбранные"


@admin.register(Characteristic)
class CharacteristicAdmin(admin.ModelAdmin):
    list_display = ['name', 'filter_type', 'is_multiple']
    list_filter = ['filter_type', 'is_multiple']
    search_fields = ['name']


@admin.register(Review)
class ReviewAdmin(SoftDeleteAdmin):
    list_display = ['product', 'user', 'rating', 'is_deleted', 'created_at']
    list_filter = ['rating', 'is_deleted']
    search_fields = ['product__name', 'user__email', 'text']
    actions = ['restore_selected']

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(
            request, f"Восстановлено {
                queryset.count()} отзывов.")

    restore_selected.short_description = "Восстановить выбранные"


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at']
    search_fields = ['user__email']


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']
    search_fields = ['product__name']


@admin.register(DeliverySettings)
class DeliverySettingsAdmin(admin.ModelAdmin):
    list_display = [
        'standard_delivery_cost',
        'free_delivery_threshold',
        'express_delivery_cost']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product_name', 'product_price', 'quantity']


@admin.register(Order)
class OrderAdmin(SoftDeleteAdmin):
    list_display = [
        'id',
        'full_name',
        'email',
        'total_amount',
        'payment_status',
        'is_deleted',
        'created_at']
    list_filter = [
        'payment_status',
        'delivery_method',
        'payment_method',
        'is_deleted']
    search_fields = ['full_name', 'email', 'phone']
    readonly_fields = ['total_amount', 'created_at']
    actions = ['restore_selected']

    def restore_selected(self, request, queryset):
        queryset.update(is_deleted=False)
        self.message_user(
            request, f"Восстановлено {
                queryset.count()} заказов.")

    restore_selected.short_description = "Восстановить выбранные"
