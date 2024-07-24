from django.contrib import admin
from apps.accessories.models import *
# Register your models here.

admin.site.register(Advertisement)
admin.site.register(ChargeAmount)
admin.site.register(PaymentTable)
admin.site.register(AmbassadorsDetails)

admin.site.register(Notifications)


admin.site.register(MerchandiseStoreCategory)
admin.site.register(MerchandiseStoreProduct)
admin.site.register(MerchandiseStoreProductBuy)
admin.site.register(AmbassadorsPost)
admin.site.register(ProductDeliveryAddress)

admin.site.register(AdvertiserFacility)
admin.site.register(CouponCode)