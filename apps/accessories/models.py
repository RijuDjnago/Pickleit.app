from django.db import models
from apps.user.models import *
from apps.team.models import *
import uuid


# Create your models here.

SCREEN_TYPE = (
    # ("Team Create", "Team Create"),
    # ("Leauge Register", "Leauge Register"),
    ("Player List", "Player List"),
    ("User Team List", "User Team List"),
    ("Leauge List", "Leauge List"),
    ("Home", "Home"),
    ("stats", "Stats"),
    ("sponsor_view", "Sponsor View"),
    ("sponsor_add", "Sponsor Add"),
)

ADD_TYPE = (
    ("Image", "Image"),
    ("Script", "Script"),
)

class Advertisement(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, unique=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    image = models.ImageField(upload_to='advertisement_image/', null=True, blank=True)
    script_text = models.TextField(null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    approved_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='advertisementCreatedBy')
    description = models.TextField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    def __str__(self) :
        return f"{self.name} [{self.start_date} to {self.end_date}]"
    
CHARGE_TYPE = (
    ("Organizer", "To Become an Organizer"),
    ("Sponsors", "To Become a Sponsors"),
    ("Ambassador", "To Become a Ambassador"),
)
class ChargeAmount(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, unique=True)
    charge_for = models.CharField(choices=CHARGE_TYPE, max_length=250, null=True, blank=True, unique=True)
    charge_amount = models.PositiveIntegerField(help_text="subscription amount ($)", null=True, blank=True)
    effective_time = models.DurationField(help_text="subscription duration of month number,i.e. [days hours:minutes:seconds], for 1 month [30 00:00:00]", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='chargeAmountCreatedBy')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='chargeAmountUpdatedBy')

    def __str__(self) :
        return f"{self.charge_for} - Amount : {self.charge_amount}$ - Time for {self.effective_time} months"
        
class Notifications(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    screen = models.CharField(max_length=250,choices=SCREEN_TYPE, null=True, blank=True)
    url = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self) :
        return f"{self.user.username} - Message : {self.message}$ - Status : {self.is_read}"


class MerchandiseStoreCategory(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, null=True, blank=True, unique=True)
    name = models.CharField(max_length=250, null=True, blank=True)
    image = models.ImageField(upload_to='store_category/', null=True, blank=True)
    size = models.JSONField(null=True, blank=True)    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='categoryCreatedBy')
    
    def __str__(self) :
        return f"{self.name}"

class MerchandiseStoreProduct(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, null=True, blank=True, unique=True)
    category = models.ForeignKey(MerchandiseStoreCategory,on_delete=models.SET_NULL, null=True, blank=True, related_name='category')
    name = models.CharField(max_length=250, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    specifications = models.TextField(null=True, blank=True)
    old_price = models.PositiveIntegerField(null=True, blank=True)
    percent_off = models.PositiveIntegerField(null=True, blank=True)
    price = models.PositiveIntegerField(null=True, blank=True)
    image = models.ImageField(upload_to='store_product/', null=True, blank=True)
    leagues_for = models.ManyToManyField(Leagues)
    size = models.JSONField(null=True, blank=True)
    is_love = models.ManyToManyField(User)
    rating = models.PositiveIntegerField(null=True, blank=True,default=0)
    rating_count = models.PositiveIntegerField(null=True, blank=True, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='productCreatedBy')
    
    def __str__(self) :
        return f"{self.name}, Price : $ {self.price}, Category : {self.category.name}"

    def get_leagues_names(self):
        leagues_for_id = self.leagues_for.all()
        leagues_name = [i.name for i in leagues_for_id]
        return leagues_name
    
    def update_rating(self):
        total_rating = sum(rating.rating for rating in self.ratings.all())
        self.rating_count = self.ratings.count()
        self.rating = round(total_rating / self.rating_count, 1) if self.rating_count > 0 else 0
        self.save()

class ProductRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_ratings')
    product = models.ForeignKey(MerchandiseStoreProduct, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField(help_text="Rate between 1 and 5.")  # Ensure this is within a valid range, e.g., 1-5
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product')  # Ensure a user can rate a product only once

    def __str__(self):
        return f'{self.user} rated {self.product} as {self.rating}'
    
class MerchandiseProductImages(models.Model):
    product = models.ForeignKey(MerchandiseStoreProduct, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='store_product/images/')

    def __str__(self):
        return f"Images of {self.product.name}"

BUYING_STATUS = (
    ("CART", "CART"),
    ("BuyNow", "BUY NOW"),
    ("ORDER PLACED", "ORDER PLACED"),
    ("CANCEL", "CANCEL"),
    ("DELIVERED", "DELIVERED"),
)

class ProductDeliveryAddress(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, null=True, blank=True, unique=True)
    street = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    default_address = models.BooleanField(default=False)
    complete_address = models.TextField(null=True, blank=True,help_text="street, city, state, country, PIN-postal_code")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return f"{self.created_by.username} {self.complete_address}"
    
    def save(self, *args, **kwargs):
        # Check if any of the address components are not None
        if self.street and self.city and self.state and self.postal_code and self.country:
            # Concatenate the address components to form the complete_address
            self.complete_address = f"{self.street}, {self.city}, {self.state}, {self.country}, PIN-{self.postal_code}"
        super().save(*args, **kwargs)
    
class MerchandiseStoreProductBuy(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, null=True, blank=True, unique=True)
    cart_idd = models.CharField(max_length=250, null=True, blank=True)
    product = models.ForeignKey(MerchandiseStoreProduct,on_delete=models.SET_NULL, null=True, blank=True, related_name='product')
    price_per_product = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField()
    total_product = models.PositiveIntegerField()
    status = models.CharField(choices=BUYING_STATUS, max_length=250, null=True, blank=True)
    size = models.CharField(max_length=250, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    delivery_address_main = models.ForeignKey(ProductDeliveryAddress,on_delete=models.SET_NULL, null=True, blank=True)
    delivery_address = models.TextField(null=True, blank=True,help_text="street, city, state, country, PIN-postal_code")
    delivered_at = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='productBuyby')
    def __str__(self) :
        return f"{self.created_by.email}, Product - {self.product.name}"
    
    
class AmbassadorsPost(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, null=True, blank=True, unique=True)
    file = models.URLField(null=True, blank=True)
    thumbnail = models.URLField(null=True, blank=True)
    post_text = models.TextField(null=True, blank=True)
    approved_by_admin = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='postby')
    likes = models.ManyToManyField(User)
    
    
CHARGE_FOR = (
    ("product_buy", "product_buy"),
    ("for_advertisement", "for_advertisement"),
)

 
class PaymentTable(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, unique=True)
    chargeamount = models.ForeignKey(ChargeAmount,on_delete=models.SET_NULL, null=True, blank=True, related_name='chargeamount')
    var_chargeamount = models.PositiveIntegerField() 
    payment_for = models.CharField(max_length=250, choices=CHARGE_FOR, null=True, blank=True)
    payment_for_id = models.TextField(null=True, blank=True)
    payment_by = models.CharField(max_length=250, null=True, blank=True)
    payment_amount = models.PositiveIntegerField()
    payment_status = models.BooleanField(default=False)
    stripe_response = models.JSONField(null=True, blank=True)
    expires_at  = models.DateTimeField(null=True, blank=True)
    payment_for_product = models.ManyToManyField(MerchandiseStoreProductBuy)
    payment_for_ad = models.ForeignKey(Advertisement, on_delete=models.SET_NULL, null=True, blank=True, related_name="payForAd")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='paymentTableCreatedBy')

    def __str__(self) :
        return f"{self.created_by.username} - Amount : {self.var_chargeamount}$ - Status : {self.payment_status}"
  
class AmbassadorsDetails(models.Model):
    ambassador = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='ambassador')
    follower = models.ManyToManyField(User,related_name='ambassador_follower')
    following = models.ManyToManyField(User,related_name='ambassador_following')


FACILITY_TYPE = (
    ("Pickleball Facility", "Pickleball Facility"),
    ("Sports Facility", "Sports Facility"),
    ("Country Club", "Country Club"),
    ("Neighborhood Courts", "Neighborhood Courts"),
    ("Public Area", "Public Area"),
    ("Other", "Other"),
)

COURT_TYPE = (
    ("Outdoor Court Only","Outdoor Court Only"),
    ("Indoor Court Only", "Indoor Court Only"),
    ("Both Outdoor and Indoor","Both Outdoor and Indoor"),
)

MEMBERSHIP_TYPE = (
    ("Open to Public","Open to Public"),
    ("Members only", "Members only"),
    ("Pay to Play", "Pay to Play"),
)


class AdvertiserFacility(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    secret_key = models.CharField(max_length=250, null=True, blank=True, unique=True)
    facility_name = models.CharField(max_length=200, null=True, blank=True)
    facility_type = models.CharField(choices=FACILITY_TYPE, max_length=200, null=True, blank=True)
    court_type = models.CharField(choices=COURT_TYPE, max_length=200, null=True, blank=True)
    membership_type = models.CharField(choices=MEMBERSHIP_TYPE, max_length=200, null=True, blank=True)
    complete_address = models.TextField(null=True, blank=True,help_text="street, city, state, country, PIN-postal_code")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    number_of_courts = models.PositiveIntegerField()
    response = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='facilityCreatedBy')
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, blank=True, related_name='facilityUpdatedBy')
    acknowledgement = models.BooleanField(default=False)
    # For not physically deleting
    is_view = models.BooleanField(default=False) 

    def __str__(self):
        return f"{self.facility_name} - {self.facility_type}"
    

class CouponCode(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4)
    percentage = models.IntegerField(help_text="This Input Count As A Discount Percentage", default=0)
    coupon_code = models.CharField(max_length=20, unique=True)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.coupon_code} || {self.percentage} ({self.start_date.date()} to {self.end_date.date()})"
