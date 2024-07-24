from django.shortcuts import render, redirect, HttpResponse
from rest_framework.decorators import api_view
from apps.user.helpers import *
from apps.team.models import *
from apps.accessories.models import *
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import stripe, time, json
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Sum, F
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
stripe.api_key = settings.STRIPE_PUBLIC_KEY
protocol = settings.PROTOCALL
api_key = settings.MAP_API_KEY


#sponsor part start
@api_view(('GET',))
def screen_type_list(request):
    """
    Displays the screens.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            screen_type = []
            added_screen_lst = [i["screen"] for i in Advertisement.objects.all().values("screen")]

            for _, value in SCREEN_TYPE:
                if value in added_screen_lst :
                    pass
                else:
                    screen_type.append(value)
            # data["data"] = {"screen_type":["Team Create","Leauge Register"],"advertisement_type":["Image","Script"]}
            data["data"] = {"screen_type":screen_type,"advertisement_type":["Image","Script"]}
            data['status'], data['message'] = status.HTTP_200_OK, "Role Admin"
            
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# Not using anymore
@api_view(('POST',))
def add_advertisement(request):
    try:
        data = {'status':'', 'message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        advertisement_name = request.data.get('advertisement_name')
        description = request.data.get('description')
        image = request.FILES.get('image')
        script_text = request.data.get('script_text')
        url = request.data.get('url')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')

        start_date = datetime.strptime(start_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%m/%d/%Y').strftime('%Y-%m-%d')

        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin or get_user.is_sponsor:
                obj = GenerateKey()
                advertisement_key = obj.gen_advertisement_key()
                Advertisement.objects.create(
                    secret_key=advertisement_key,
                    name=advertisement_name,
                    image=image,
                    url=url,
                    created_by_id=get_user.id,
                    script_text=script_text,
                    description = description,
                    start_date=start_date,
                    end_date=end_date
                    )
                data["status"], data["message"] = status.HTTP_200_OK,"Advertisement created successfully"
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND,"User is not Admin or Sponsor"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# Updated for payment gateway
from datetime import datetime
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import base64


@api_view(('POST',))
def create_advertisement(request):
    """
    Creates an advertisement and charges fees for creating it. 
    Only admin user or sponsor user can create an advertisement.
    """
    try:
        data = {'status':'', 'message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        advertisement_name = request.data.get('advertisement_name')
        description = request.data.get('description')
        image = request.FILES.get('image')
        script_text = request.data.get('script_text')
        url = request.data.get('url')
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        start_date = datetime.strptime(start_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin or get_user.is_sponsor:
                obj = GenerateKey()
                advertisement_key = obj.gen_advertisement_key()
                image_path = default_storage.save(image.name, ContentFile(image.read()))
                make_request_data = {"secret_key":advertisement_key,"name":advertisement_name,"image":image_path,
                                     "url":url,"created_by_id":get_user.id,"description":description,
                                     "script_text":script_text,"start_date":start_date,"end_date":end_date}
        
                #json bytes
                json_bytes = json.dumps(make_request_data).encode('utf-8')
                
                # Encode bytes to base64
                my_data = base64.b64encode(json_bytes).decode('utf-8')
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
                date_gap = end_date - start_date
                gap_in_days = date_gap.days
                duration = gap_in_days
                charge_amount = int(duration)*int(settings.PER_DAY_CHARGE_FOR_AD)*100  
                charge_for = "for_advertisement"          
                product_name = "Payment For Adding Advertisement"
                product_description = "Payment received by Pickleit"
                stripe.api_key = settings.STRIPE_SECRET_KEY
                
                if get_user.stripe_customer_id :
                    stripe_customer_id = get_user.stripe_customer_id
                else:
                    customer = stripe.Customer.create(email=get_user.email).to_dict()
                    stripe_customer_id = customer["id"]
                    get_user.stripe_customer_id = stripe_customer_id
                    get_user.save() 
                host = request.get_host()
                current_site = f"{protocol}://{host}"
                main_url = f"{current_site}/accessories/9671103725bb2e332ec083861133f7c0dad8e72b039e76bcdff4a102d453b66a/{charge_for}/{my_data}/"
                product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
                price = stripe.Price.create(unit_amount=charge_amount,currency='usd',product=product["id"],).to_dict()
                checkout_session = stripe.checkout.Session.create(
                    customer=stripe_customer_id,
                    line_items=[
                        {
                            # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                            'price': price["id"],
                            'quantity': 1,
                        },
                    ],
                    mode='payment',
                    success_url= main_url + "{CHECKOUT_SESSION_ID}" + "/",
                    cancel_url="https://example.com/success" + '/cancel.html',
                )
                return Response({"strip_url":checkout_session.url})
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND,"User is not Admin or Sponsor"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


def payment_for_advertisement(request,charge_for,my_data,checkout_session_id):
    """
    Take care of the payment part for creating an advertisement.
    """
    try:
        context ={}
        stripe.api_key = settings.STRIPE_SECRET_KEY
        pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()    
        stripe_customer_id = pay["customer"]
        payment_status = pay["payment_status"]
        expires_at = pay["expires_at"]
        amount_total = float(pay["amount_total"]) / 100
        payment_method_types = pay["payment_method_types"]
        json_bytes = base64.b64decode(my_data)
        request_data = json.loads(json_bytes.decode('utf-8'))
        print(request_data)
        expiry_date = request_data["end_date"]
        payment_status = True if payment_status == "paid" else False
       
        check_customer = User.objects.filter(stripe_customer_id=stripe_customer_id).first()
        obj = GenerateKey ()
        secret_key = obj.gen_payment_key()
        check_same_payment = PaymentTable.objects.filter(payment_for_id=checkout_session_id,payment_for=charge_for)
        if check_same_payment.exists() :
            
            get_same_payment = check_same_payment.first()
            if get_same_payment.payment_status :
                context["charge_for"] = get_same_payment.payment_for
                context["expires_time"] = get_same_payment.expires_at
                return render(request,"success_payment.html",context)

            else:
                
                context["charge_for"] = get_same_payment.payment_for
                return render(request,"failed_payment.html",context)
        if not check_same_payment.exists(): 
            save_payment = PaymentTable(secret_key=secret_key,payment_for=charge_for,payment_for_id=checkout_session_id,payment_by=payment_method_types,
                                        payment_amount=amount_total,payment_status=payment_status,stripe_response=pay,var_chargeamount=amount_total,
                                        created_by_id=check_customer.id,expires_at=expiry_date)
            save_payment.save()
        
        if payment_status is True:
            ad = Advertisement.objects.create(
                    secret_key=request_data["secret_key"],
                    name=request_data["name"],
                    image=request_data["image"],
                    url=request_data["url"],
                    created_by_id=request_data["created_by_id"],
                    description=request_data["description"],
                    script_text=request_data["script_text"],
                    start_date=request_data["start_date"],
                    end_date=request_data["end_date"],
                    approved_by_admin=True)
            save_payment.payment_for_ad = ad
            save_payment.save()
            context["charge_for"] = save_payment.payment_for
            context["expires_time"] = save_payment.expires_at
    
            return render(request,"success_payment.html", context)
        else: 
            return render(request,"failed_payment.html")
    except:
        return render(request,"failed_payment.html")


@api_view(('GET',))
def view_advertisement(request):
    """
    Displays the details of an advertisement.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        ad_uuid = request.GET.get('ad_uuid')
        ad_secret_key = request.GET.get('ad_secret_key')
        host = request.get_host()
        base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_ad = Advertisement.objects.filter(uuid=ad_uuid,secret_key=ad_secret_key)
        if check_user.exists() and check_ad.exists():
            get_user = check_user.first()
            if get_user.is_admin or get_user.is_sponsor or get_user.is_organizer:
                ad_data = Advertisement.objects.filter(id=check_ad.first().id).values("id","uuid","secret_key","name","image","script_text"
                                                                                            ,"url","approved_by_admin","description","start_date",
                                                                                            "end_date","created_by__first_name","created_by__last_name")
                if ad_data[0]["image"] != "":
                    ad_data[0]["image"] = base_url + ad_data[0]["image"]
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, ad_data,"data found"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","You are not a Sponsor"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def list_advertisement(request):
    """
    Fetches the list of all advertisements ordered by their name.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)       
        host = request.get_host()
        base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_admin:
                all_add = Advertisement.objects.all().order_by("name").values()
                for ad in all_add:
                    ad['image'] = base_url + ad['image']
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_add,"Data Found"
            else:
                all_add = Advertisement.objects.filter(created_by=get_user).order_by("name").values("id","uuid","secret_key","name","image","script_text"
                                                                                            ,"url","approved_by_admin","description","start_date","end_date","created_by__first_name","created_by__last_name")
                for ad in all_add:
                    ad['image'] = base_url + ad['image']
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_add,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


import ast
import random
@api_view(('GET',))
def list_advertisement_for_app(request):
    """
    Displays the shuffled advertisement list.
    """
    data = {'status': '', 'data': '', 'message': ''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        host = request.get_host()
        base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
        
        if check_user.exists():
            get_user = check_user.first()
            today_date = datetime.now()
            all_ads = Advertisement.objects.filter(approved_by_admin=True, end_date__gte=today_date).order_by("-id")
            
            # Convert queryset to list of dictionaries
            data_list = list(all_ads.values())
            
            # Shuffle the list
            random.shuffle(data_list)
            
            # Update image URLs
            for ad in data_list:
                ad['image'] = base_url + ad['image']
            
            data["status"] = status.HTTP_200_OK
            data["data"] = data_list
            data["message"] = "Data Found"
        else:
            data["status"] = status.HTTP_404_NOT_FOUND
            data["message"] = "User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def advertisement_approved_by_admin(request):
    """
    Allows admin user to approve or not approve the advertisements.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        advertisement_id = request.data.get('advertisement_id')
        advertisement_status = request.data.get('advertisement_status')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_advertisement = Advertisement.objects.filter(id=advertisement_id)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin and check_advertisement.exists() :
                get_advertisement = check_advertisement.first()
                advertisement_status = True if advertisement_status == "True" else False
                get_advertisement.approved_by_admin = advertisement_status
                get_advertisement.save()
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{get_advertisement.name} is updated successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not admin or Advertisement is undefined"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)
#sponsor part end


# Not using
@api_view(('POST','GET'))
def add_charge_amount(request):
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin :
                check_charge_for = ChargeAmount.objects.all().values("charge_for")
                
                charge_for_data = {"Organizer":"Organizer","Sponsors":"Sponsors"}
                for i in check_charge_for :
                    if i["charge_for"] in charge_for_data.values() :
                        charge_for_data.pop(i["charge_for"])

                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, charge_for_data,"charge for"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
        if request.method == "POST":
            user_uuid = request.data.get('user_uuid')
            user_secret_key = request.data.get('user_secret_key')
            charge_for = request.data.get('charge_for')
            charge_amount = request.data.get('charge_amount')
            effective_time = request.data.get('effective_time')
            check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
            if check_user.exists() :
                get_user = check_user.first()
                if get_user.is_admin :
                    obj = GenerateKey()
                    c_amount_key = obj.gen_charge_amount()
                    check_charge_for = ChargeAmount.objects.filter(charge_for=charge_for).values("charge_for")
                    if not charge_for or not charge_amount or not effective_time :
                        data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "",f"charge amount,charge for, effective time  is required"
                        return Response(data)
                    if check_charge_for.exists():
                        data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "",f"{charge_for} charge amount is already exists"
                        return Response(data)
                    var_effective_time = f"{effective_time} 00:00:00"
                    save_ca = ChargeAmount(secret_key=c_amount_key,charge_for=charge_for,charge_amount=charge_amount,
                                 effective_time=var_effective_time,created_by_id=get_user.id)
                    save_ca.save()
                    data["status"], data["data"], data["message"] = status.HTTP_201_CREATED, "",f"{charge_for} charge amount is added successfully"
                else:
                    data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"

    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


def format_duration(duration):
    days, seconds = duration.days, duration.seconds
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"


# Not using
@api_view(('GET',))
def list_charge_amount(request):
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin :
                check_charge_for = ChargeAmount.objects.all().values("id","uuid","secret_key","charge_for","charge_amount","effective_time",)
                for i in check_charge_for :
                    var = format_duration(i["effective_time"])
                    i["effective_time"] = var
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, check_charge_for,"Data found"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# Not using
@api_view(('GET',))
def view_charge_amount(request):
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        charge_id = request.GET.get('charge_id')
        check_charge_for = ChargeAmount.objects.filter(id=charge_id).values("id","uuid","secret_key","charge_for","charge_amount","effective_time",)
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() and check_charge_for.exists() :
            get_user = check_user.first()
            if get_user.is_admin :
                for i in check_charge_for :
                    var = format_duration(i["effective_time"])
                    i["effective_time"] = var
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, check_charge_for,"Data found"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User or ChargeAmount not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# Not using
@api_view(('POST',))
def edit_charge_amount(request):
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        charge_id = request.data.get('charge_id')

        charge_amount = request.data.get('charge_amount')
        effective_time = request.data.get('effective_time')
        check_charge_for = ChargeAmount.objects.filter(id=charge_id)
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() and check_charge_for.exists() :
            get_user = check_user.first()
            get_ca = check_charge_for.first()
            if get_user.is_admin :
                if not charge_amount or not effective_time :
                    data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "",f"charge id, charge amount, charge for, effective time  is required"
                    return Response(data)
                
                var_effective_time = f"{effective_time} 00:00:00"
                get_ca.charge_amount = charge_amount
                get_ca.effective_time = var_effective_time
                get_ca.save()
                data["status"], data["data"], data["message"] = status.HTTP_201_CREATED, "",f"{get_ca.charge_for} charge amount is updated successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User or ChargeAmount not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def allow_to_make_organizer(request):
    """
    Allows user to become organizer.
    """
    try:
        data={'status':'', 'message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            get_user.is_organizer = True
            get_user.save()
            data['status'], data['message'] = status.HTTP_200_OK, f"Now you are an organizer."
        else:
            data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# Not using
def payment(request,charge_for,checkout_session_id):
    context ={}
    stripe.api_key = settings.STRIPE_SECRET_KEY
    context['stripe_api_key'] = settings.STRIPE_PUBLIC_KEY
    pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()    
    stripe_customer_id = pay["customer"]
    payment_status = pay["payment_status"]
    expires_at = pay["expires_at"]
    amount_total = float(pay["amount_total"]) / 100

    payment_method_types = pay["payment_method_types"]
    
    payment_status = True if payment_status == "paid" else False
    check_customer = User.objects.filter(stripe_customer_id=stripe_customer_id).first()
    obj = GenerateKey ()
    secret_key = obj.gen_payment_key()
    check_charge = ChargeAmount.objects.filter(charge_for=charge_for)
    check_same_paymnet = PaymentTable.objects.filter(payment_for_id=checkout_session_id,payment_for=charge_for)
    if check_same_paymnet.exists() :
        get_same_paymnet = check_same_paymnet.first()
        if get_same_paymnet.payment_status :
            context["charge_for"] = get_same_paymnet.payment_for
            context["expires_time"] = get_same_paymnet.expires_at
            return render(request,"success_payment.html",context)
        else:
            context["charge_for"] = get_same_paymnet.payment_for
            return render(request,"failed_payment.html",context)
        
    elif check_charge.exists() and not check_same_paymnet.exists():
        get_charge = check_charge.first()
        expires_duration = get_charge.effective_time.days
        current_time = datetime.now()
        expires_time = current_time + timedelta(days=expires_duration)
        save_payment = PaymentTable(secret_key=secret_key,chargeamount_id=get_charge.id,var_chargeamount=get_charge.charge_amount,
                                    payment_for=charge_for,payment_for_id=checkout_session_id,payment_by=payment_method_types,
                                    payment_amount=amount_total,payment_status=payment_status,stripe_response=pay,
                                    created_by_id=check_customer.id,expires_at=expires_time)
        save_payment.save()
        if charge_for == "Organizer" :
            check_customer.is_organizer = True
            check_customer.is_organizer_expires_at = expires_time
            check_customer.save()
            
        elif charge_for == "Sponsors" :
            check_customer.is_sponsor = True
            check_customer.is_sponsor_expires_at = expires_time
            check_customer.save()
            
        elif charge_for == "Ambassador" :
            check_customer.is_ambassador = True
            check_customer.is_ambassador_expires_at = expires_time
            check_customer.save()
        context["charge_for"] = save_payment.payment_for
        context["expires_time"] = save_payment.expires_at
        return render(request,"success_payment.html",context)
    else: 
        message = f"error .."
        return render(request,"failed_payment.html")

# Not using
@api_view(('POST','GET'))
def checkout(request):
    context={}
    stripe.api_key = settings.STRIPE_SECRET_KEY
    context['stripe_api_key'] = settings.STRIPE_PUBLIC_KEY
    if request.method == 'POST':
        charge_for = request.data.get('charge_for')
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        # This is for Organizer
        if charge_for == "Organizer" and check_user.exists():
            check_product = ChargeAmount.objects.filter(charge_for = "Organizer")
            if check_product.exists():
                get_user = check_user.first()
                get_product = check_product.first()
                product_name = f"To Become an Organizer"
                get_days = str(get_product.effective_time).split(" ")[0]
                product_description = f"This is a subscription for {get_days} days"
                unit_amount = (get_product.charge_amount) * 100
            else:
                return HttpResponse("Not a vaild request")
        # This is for Sponsors
        elif charge_for == "Sponsors" and check_user.exists() :
            check_product = ChargeAmount.objects.filter(charge_for = "Sponsors")
            if check_product.exists():
                get_user = check_user.first()
                get_product = check_product.first()
                product_name = f"To Become a Sponsors"
                get_days = str(get_product.effective_time).split(" ")[0]
                product_description = f"This is a subscription for {get_days} days"
                unit_amount = (get_product.charge_amount) * 100
            else:
                return HttpResponse("Not a vaild request")
        # This is for Sponsors
        elif charge_for == "Ambassador" and check_user.exists() :
            check_product = ChargeAmount.objects.filter(charge_for = "Ambassador")
            if check_product.exists():
                get_user = check_user.first()
                get_product = check_product.first()
                product_name = f"To Become an Ambassador"
                get_days = str(get_product.effective_time).split(" ")[0]
                product_description = f"This is a subscription for {get_days} days"
                unit_amount = (get_product.charge_amount) * 100
            else:
                return HttpResponse("Not a vaild request")
        else:
            return HttpResponse("Not a vaild request")
        # creating customer 
        if get_user.stripe_customer_id :
            stripe_customer_id = get_user.stripe_customer_id
        else:
            customer = stripe.Customer.create(email=get_user.email).to_dict()
            stripe_customer_id = customer["id"]
            get_user.stripe_customer_id = stripe_customer_id
            get_user.save()
        
        host = request.get_host()
        current_site = f"{protocol}://{host}"
        main_url = f"{current_site}/accessories/040ffd5925d40e11c67b7238a7fc9957850b8b9a46e9729fab88c24d6a98aff2/{charge_for}/"
        
        product = stripe.Product.create(name=product_name,description=product_description,).to_dict()

        price = stripe.Price.create(unit_amount=unit_amount,currency='usd',product=product["id"],).to_dict()
                    
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': price["id"],
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url= main_url + "{CHECKOUT_SESSION_ID}" + "/",
            cancel_url="https://example.com/success" + '/cancel.html',
        )
        return Response({"strip_url":checkout_session.url})
        
    return HttpResponse("Get method not supported")


# Not using
@api_view(('GET',))
def list_payments(request):
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin :
                all_payment = PaymentTable.objects.all().order_by('-id').values("created_by__first_name","created_by__last_name",
                                                        "created_by__email","payment_status","created_at","payment_for","payment_for_id",
                                                        "payment_by","payment_amount")
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_payment,"Data found"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def store_category_add(request):
    """
    Adds a new merchandise category for product.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        category_name = request.data.get('category_name')
        category_image = request.FILES.get('category_image')
        print("category_image",category_image)
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin :
                if category_name and len(category_name) > 0 :
                    obj = GenerateKey()
                    category_key = obj.gen_category_key()
                    cat = MerchandiseStoreCategory(secret_key=category_key,name=category_name,created_by_id=get_user.id,
                                                   image=category_image)
                    cat.save()
                    data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{category_name} created successfully"
                else:
                    data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","Category name is undefined"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def store_category_edit(request):
    """
    Is used to edit the details of merchandise category for product.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        category_id = request.data.get('category_id')
        category_name = request.data.get('category_name')
        category_image = request.FILES.get('category_image')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_cat = MerchandiseStoreCategory.objects.filter(id=category_id)
        if check_user.exists() :
            get_user = check_user.first()
            if get_user.is_admin :
                get_cat = check_cat.first()
                get_cat.name = category_name
                get_cat.image = category_image
                get_cat.save()
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{category_name} edited successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","Category undefined or User is not Admin"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def store_category_view(request):
    """
    Displays the details of a merchandise category.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        cat_id = request.GET.get('cat_id')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            all_cal = MerchandiseStoreCategory.objects.filter(id=cat_id).order_by("name").values("id","uuid","secret_key","name","created_by__first_name","created_by__last_name","image","size")
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_cal,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def store_category_list(request):
    """
    Displays the list of all merchandise category.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            all_cal = MerchandiseStoreCategory.objects.all().order_by("name").values("id","uuid","secret_key","name","created_by__first_name","created_by__last_name","image","size")
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_cal,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def store_product_add(request):
    """
    An admin or an organizer can add a store product.
    """
    try:        
        data = {'status':'','data':'','message':''} 
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        category_id = request.data.get('category_id')
        product_name = request.data.get('product_name')        
        leagues_for_id = request.data.get('leagues_for_id')        
        product_description = request.data.get('product_description')
        product_specifications = request.data.get('product_specifications')
        product_old_price = request.data.get('product_old_price')
        product_price = request.data.get('product_price')
        product_image = request.FILES.getlist('product_image')
        product_size = request.data.get('product_size')      
        product_size = json.loads(product_size)

        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            
            ### send the merchantdice request
            check_pro = MerchandiseStoreProduct.objects.filter(created_by = get_user)
            if not check_pro.exists():
                check_req = ProductSellerRequest.objects.create(user=get_user)
            else:
                pass

            
            check_category = MerchandiseStoreCategory.objects.filter(id=category_id)
            check_leagues_for = Leagues.objects.filter(id=leagues_for_id)
            if get_user.is_admin or get_user.is_organizer :                
                percent_price = ((float(product_old_price) - float(product_price)) / float(product_old_price)) * 100
                    
                obj = GenerateKey()
                product_key = obj.gen_product_key()
                get_category = check_category.first()
                get_leagues = check_leagues_for.first()
                
                save_product = MerchandiseStoreProduct.objects.create(secret_key=product_key,category_id=get_category.id,name=product_name,
                                        description=product_description,specifications=product_specifications,
                                        price=product_price,size=product_size,created_by_id=get_user.id,
                                        percent_off = round(percent_price,2),old_price=product_old_price)
                save_product.image = product_image[0]
                save_product.save()
                for image in product_image[1:]:
                    MerchandiseProductImages.objects.create(product=save_product, image=image)
                save_product.leagues_for.add(get_leagues.id)
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{product_name} created successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin or Organizer"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def store_product_list(request):
    """
    Displays the list of all store products.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            all_cal = MerchandiseStoreProduct.objects.filter(created_by__is_merchant = True).order_by("name").values("id","uuid","secret_key",
                    "category__name","name","description","specifications","price","size","rating",
                    "created_by__first_name","created_by__last_name","image")
            for i in list(all_cal) :
                get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                i["leagues_name"] = get_p.get_leagues_names()
            
            data["top_card_3"] = all_cal.order_by("-rating")[:3]
            for i in list(data["top_card_3"]) :
                get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                i["leagues_name"] = get_p.get_leagues_names()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_cal,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def my_store_product_list(request):
    """
    Displays the list of store products added by the user itself.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            data["is_merchant"] = get_user.is_merchant
            all_cal = MerchandiseStoreProduct.objects.filter(created_by=get_user).order_by("name").values("id","uuid","secret_key",
                    "category__name","name","description","specifications","price","size","rating",
                    "created_by__first_name","created_by__last_name","image")
            for i in list(all_cal) :
                get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                i["leagues_name"] = get_p.get_leagues_names()
            
            data["top_card_3"] = all_cal.order_by("-rating")[:3]
            for i in list(data["top_card_3"]) :
                get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                i["leagues_name"] = get_p.get_leagues_names()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, all_cal,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def store_product_delete(request):
    """
    Allows an admin or an organizer to delete a store product.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        product_id = request.data.get('product_id')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            check_product = MerchandiseStoreProduct.objects.filter(id=product_id)
            if get_user.is_admin or get_user.is_organizer:
                if not check_product.exists():
                    data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","Product is not found"
                    return Response(data) 
                else:
                    check_product.delete()
                    data["status"], data["message"] = status.HTTP_200_OK, "Product deleted successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin or Organizer"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def store_product_view(request):
    """
    Displays the details of a particular store product.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        product_uuid = request.GET.get('product_uuid')
        product_secret_key = request.GET.get('product_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_product = MerchandiseStoreProduct.objects.filter(uuid=product_uuid,secret_key=product_secret_key)       
        if check_user.exists() :
            if check_product.exists() :
                get_product = check_product.values("id","uuid","secret_key",
                    "category__name","name","description","specifications","price","size","rating",
                    "created_by__first_name","created_by__last_name","image","old_price","percent_off")
                
                additional_images = list(MerchandiseProductImages.objects.filter(product=check_product.first()).values_list("image", flat=True))
                if additional_images:
                    for item in get_product:
                        item["additional_images"] = additional_images
                for i in get_product :
                    get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                    i["leagues_name"] = get_p.get_leagues_names()
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, get_product,"Data Found"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","Product is undefined"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def category_wise_product_filter(request):
    """
    Filters out the store products for a given category.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        category_id = request.GET.get('category_id')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_product = MerchandiseStoreProduct.objects.filter(category_id=category_id).order_by("name").values("id","uuid","secret_key",
                    "category__name","name","description","specifications","price","size","rating",
                    "created_by__first_name","created_by__last_name","image")
            for i in get_product :
                get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                i["leagues_name"] = get_p.get_leagues_names()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, get_product,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def search_wise_product_filter(request):
    """
    Filters the list of products according to search.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_name = request.GET.get('search_name')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_product = MerchandiseStoreProduct.objects.filter(
                Q(category__name__icontains=search_name) | Q(name__icontains=search_name) |
                Q(leagues_for__name__icontains=search_name) | Q(price__icontains=search_name) |
                Q(description__icontains=search_name) | Q(specifications__icontains=search_name) |
                Q(size__icontains=search_name) | Q(rating__icontains=search_name)
                ).order_by("name").values("id","uuid","secret_key",
                    "category__name","name","description","specifications","price","size","rating",
                    "created_by__first_name","created_by__last_name","image")
            for i in get_product :
                get_p = MerchandiseStoreProduct.objects.filter(id=i["id"]).first()
                i["leagues_name"] = get_p.get_leagues_names()
            
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, get_product,"Data Found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def store_product_edit(request):
    """
    An admin or an organizer can edit the details of a product.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        category_id = request.data.get('category_id')
        product_id = request.data.get('product_id')
        product_name = request.data.get('product_name')
        
        product_description = request.data.get('product_description')
        product_specifications = request.data.get('product_specifications')
        product_price = request.data.get('product_price')
        product_image = request.FILES.get('product_image')
        product_size = request.data.get('product_size')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            check_category = MerchandiseStoreCategory.objects.filter(id=category_id)
            check_product = MerchandiseStoreProduct.objects.filter(id=product_id)
            if get_user.is_admin or get_user.is_organizer:
                if not check_product.exists() or not check_category.exists() or not product_name or not product_price :
                    data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","Category name or Product Name or Product Price is undefined"
                    return Response(data) 
                else:
                    get_product = check_product.first()
                    get_product.category_id = category_id
                    get_product.name = product_name
                    get_product.description = product_description
                    get_product.specifications = product_specifications
                    get_product.price = product_price
                    get_product.image = product_image
                    get_product.size = product_size
                    get_product.save()
                    
                    data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{product_name} updated successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User is not Admin or Organizer"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)      


@api_view(('POST',))
def store_product_love_byUser(request):
    """
    Allows a user to add a product to his wishlist.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        product_id = request.data.get('product_id')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_product = MerchandiseStoreProduct.objects.filter(id=product_id)
        if check_user.exists() and check_product.exists() :
            get_user = check_user.first()
            get_product = check_product.first()
            check_love = check_product.filter(is_love__id=get_user.id)
            product_name = get_product.name
            if check_love.exists() :
                get_product.is_love.remove(get_user.id)
                data["message"] = f"You removed the {product_name} from your wishlist"
            else:
                get_product.is_love.add(get_user.id)
                data["message"] = f"You added the {product_name} in your wishlist"
                
            data["status"], data["data"],  = status.HTTP_200_OK, ""
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User or Product not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


class ProductRatingSerializer(serializers.ModelSerializer):
    user = serializers.SerializerMethodField()
    class Meta:
        model = ProductRating
        fields = ['user', 'product', 'rating', 'created_at']
    
    def get_user(self, obj):
        name = f"{obj.user.first_name}" if obj.user.first_name else "Annonymous User"
        return name

@api_view(['POST'])
def rate_product(request):
    data = {'status':'','data':[],'message':''} 
    try:
        user_uuid = request.data.get("user_uuid")
        user_secret_key = request.data.get("user_secret_key")
        product_uuid = request.data.get("product_uuid")
        product_secret_key = request.data.get("product_secret_key")
        rating_value = request.data.get('rating')
      
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)  
        check_product = MerchandiseStoreProduct.objects.filter(uuid=product_uuid, secret_key=product_secret_key)
        if check_user and check_product:
            user = check_user.first()
            product = check_product.first()

            if not 1 <= float(rating_value) <= 5:
                data["status"], data["data"], data["message"] = status.HTTP_400_BAD_REQUEST, [], "Rating must be between 1 and 5."
                return Response(data)

            rating, created = ProductRating.objects.update_or_create(
                user=user,
                product=product,
                defaults={'rating': rating_value}
            )

            product.update_rating()  # Update the average rating and count

            serializer = ProductRatingSerializer(rating)
            data["status"] = status.HTTP_200_OK if not created else status.HTTP_201_CREATED
            data["data"] = serializer.data
            data["message"] = "Product is rated successfully."
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, [], "User or Product not found"
    except Exception as e :
        data['status'], data["data"], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"{e}"
 
   
@api_view(("GET",))
def wishlisted_products(request):
    try:
        data = {"status":"","message":"","data":[]}
        user_uuid = request.GET.get("user_uuid")
        user_secret_key = request.GET.get("user_secret_key")
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            wishlisted_products = []
            all_products = MerchandiseStoreProduct.objects.all()
            for product in all_products:
                if get_user in product.is_love.all():
                    product_details = {
                        "id":product.id,
                        "uuid":product.uuid,
                        "secret_key":product.secret_key,
                        "name":product.name,
                        "image":product.image.url,
                        "price":product.price,
                        "old_price":product.old_price,
                        "category":product.category.name,
                        "percent_off":product.percent_off,
                        "leagues_for":list(product.leagues_for.all().values("id","name")),
                        "size":product.size,
                        "rating":product.rating,
                        "description":product.description,
                        "specifications":product.specifications,
                        "created_by":product.created_by.first_name
                    }
                    wishlisted_products.append(product_details)
            paginator = PageNumberPagination()
            paginator.page_size = 5 # Set the page size to 20
            products_data = paginator.paginate_queryset(wishlisted_products, request)
            paginated_response = paginator.get_paginated_response(products_data)
            data["status"] = status.HTTP_200_OK
            data["message"] = "Wishlisted products fetched successfully."
            data["count"] = paginated_response.data["count"]
            data["previous"] = paginated_response.data["previous"]
            data["next"] = paginated_response.data["next"]
            data["data"] = paginated_response.data["results"]
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(("GET",))
def check_store_product_liked_or_not(request):
    """
    Displays if a product is in the wishlist of a user or not.
    """
    try:
        data = {}
        user_uuid = request.GET.get("user_uuid")
        user_secret_key = request.GET.get("user_secret_key")
        product_id = request.GET.get("product_id")
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            check_product = MerchandiseStoreProduct.objects.filter(id=product_id)
            if check_product.exists():
                get_product = check_product.first()
                liked_status = False
                if get_user in get_product.is_love.all():
                    liked_status = True
                    data["status"], data["message"], data["liked_status"] = status.HTTP_200_OK, "", liked_status
                else:
                    data["status"], data["message"], data["liked_status"] = status.HTTP_200_OK, "", liked_status
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"Product not found."
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def user_add_delivery_address(request):
    """
    Allows a user to add delivery address.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        street = request.data.get('street')
        city = request.data.get('city')
        state = request.data.get('state')
        postal_code = request.data.get('postal_code')
        country = request.data.get('country')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            if street and city and state and postal_code and country :
                obj = GenerateKey()
                delivery_address_key = obj.gen_delivery_address_sk()
                # complete_address = f'{street}, {city}, {state}, {country}, PIN-{postal_code}'
                save_delivery_address = ProductDeliveryAddress(secret_key=delivery_address_key,
                                        street=street,city=city,state=state,postal_code=postal_code,
                                        country=country,created_by_id=get_user.id)
                                        
                save_delivery_address.save()            
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, "","New address added successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_403_FORBIDDEN, "","Street, City, State, Postal Code are mandatory"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def user_edit_delivery_address(request):
    """
    Allows a user to edit his delivery address.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        address_id = request.data.get('address_id')
        street = request.data.get('street')
        city = request.data.get('city')
        state = request.data.get('state')
        postal_code = request.data.get('postal_code')
        country = request.data.get('country')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_delivery_address = ProductDeliveryAddress.objects.filter(id=address_id)
        if check_user.exists() and check_delivery_address.exists():
            # get_user = check_user.first()
            get_delivery_address= check_delivery_address.first()
            if street and city and state and postal_code and country :
                # complete_address = f'{street}, {city}, {state}, {country}, PIN-{postal_code}'
                get_delivery_address.street = street
                get_delivery_address.city = city
                get_delivery_address.state = state
                get_delivery_address.postal_code = postal_code
                # get_delivery_address.complete_address = complete_address
                get_delivery_address.save()
                data["status"], data["data"], data["message"] = status.HTTP_200_OK, "","Address updated successfully"
            else:
                data["status"], data["data"], data["message"] = status.HTTP_403_FORBIDDEN, "","Street, City, State, Postal Code are mandatory"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def user_delivery_address(request):
    """
    Displays the details of delivery address of a user.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            addresses = ProductDeliveryAddress.objects.filter(created_by_id=get_user.id)
            valid_addresses = []
            for address in addresses:
                if address.street != "null" and address.city != "null" and address.state != "null" and address.postal_code != "null" and address.country != "null":
                    valid_addresses.append({
                        "id": address.id,
                        "street": address.street,
                        "city": address.city,
                        "state": address.state,
                        "postal_code": address.postal_code,
                        "country": address.country,
                        "complete_address": address.complete_address,
                        "default_address": address.default_address,
                        "created_by__first_name": address.created_by.first_name,
                        "created_by__last_name": address.created_by.last_name
                    })

            data['status'] = status.HTTP_200_OK
            data['data'] = valid_addresses
            data['message'] = 'Data Found'
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def user_delivery_address_change(request):
    """
    Allows user to change delivery address.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        address_id = request.data.get('address_id')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_delivery_address = ProductDeliveryAddress.objects.filter(id=address_id)
        if check_user.exists() and check_delivery_address.exists():
            get_delivery_address= check_delivery_address.first()
            get_delivery_address.default_address = True
            get_delivery_address.save()
            all_delivery_address = ProductDeliveryAddress.objects.filter(created_by_id=get_delivery_address.created_by.id).exclude(id=address_id)
            for i in all_delivery_address:
                i.default_address = False
                i.save()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, "","Address updated successfully"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_403_FORBIDDEN, "","User or Address not found"
                
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def product_add_to_cart(request):
    """
    Allows user to add a product to his cart.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_product = MerchandiseStoreProduct.objects.filter(id=product_id)
        size = request.data.get('size')

        if check_user.exists() and check_product.exists() :
            get_user = check_user.first()
            get_product = check_product.first()                
            obj2 = GenerateKey()
            p_sk = obj2.gen_buy_product_sk()
            total_product = round(int(quantity) * round(float(get_product.price),2),2)
            create_cart = MerchandiseStoreProductBuy(secret_key=p_sk,product_id=product_id,price_per_product=get_product.price,
                                       quantity=quantity,total_product=total_product,status="CART",
                                       created_by_id=get_user.id,size=size)
            create_cart.save()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{get_product.name} successfully added to cart"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User or Product not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)  


@api_view(('GET',))
def cart_list(request):
    """
    Displays the cart list of a user.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        coupon_code = request.GET.get('coupon_code')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            check_coupon = CouponCode.objects.filter(coupon_code=coupon_code)           
            if check_coupon.exists():   
                card_products = MerchandiseStoreProductBuy.objects.filter(created_by_id=get_user.id,status="CART").order_by("-id").annotate(
                    total_price=F('product__price') * F('quantity')
                ).values("id", "uuid", "secret_key", "product__name", "product__price", "quantity", "product__image", "total_price","size")

                total_price = card_products.aggregate(total_prices=Sum("total_price", default=0))['total_prices']
                get_coupon = check_coupon.first().percentage
                price_after_discount = int(total_price - (total_price*get_coupon/100))
                data["coupon_status"] = "Successfully applied."
                data["discount"] = int(total_price*get_coupon/100)
                data["total_price"] = price_after_discount
            else:
                card_products = MerchandiseStoreProductBuy.objects.filter(created_by_id=get_user.id,status="CART").order_by("-id").annotate(
                    total_price=F('product__price') * F('quantity')
                ).values("id", "uuid", "secret_key", "product__name", "product__price", "quantity", "product__image", "total_price","size")

                total_price = card_products.aggregate(total_prices=Sum("total_price", default=0))['total_prices']
                data["coupon_status"] = "Coupon code does not exist."
                data["discount"] = 0
                data["total_price"] = total_price
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, card_products,f"Data found"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)  


@api_view(('POST',))
def cart_edit(request):
    """
    Allows a user to edit his cart.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        cart_id = request.data.get('cart_id')
        quantity = request.data.get('quantity')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_cart = MerchandiseStoreProductBuy.objects.filter(id=cart_id)
        if check_user.exists() and check_cart.exists():
            get_cart = check_cart.first()
            get_cart.quantity = int(quantity)
            get_cart.save()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, "","Cart updated successfully"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User or Cart Product not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def cart_delete(request):
    """
    Allows a user to delete product from his cart.
    """
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        cart_id = request.data.get('cart_id')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_cart = MerchandiseStoreProductBuy.objects.filter(id=cart_id)
        if check_user.exists() and check_cart.exists():
            get_cart = check_cart.first()
            get_cart.delete()
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, "",f"{get_cart.product.name} is removed from cart."
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User or Cart Product not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# ################################## payement part start #############################################
# directly buy the product
@api_view(('POST',))
def buy_now_product(request):
    """
    Allows a user to directly buy any product from product list.
    """
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        delivery_address_main = None
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        delivery_address_main = request.data.get('delivery_address_main_id')
        product_id = request.data.get('product_id')
        quantity = int(request.data.get('quantity'))
        size = request.data.get('size')

        price = MerchandiseStoreProduct.objects.filter(id=int(product_id)).first().price
        if not check_user.exists():
            data = {}
            data['message'] = "User not exists"
            return Response(data)
        if delivery_address_main is None:
            user_street = check_user.first().street
            user_city = check_user.first().city
            user_state = check_user.first().state
            user_postal_code = check_user.first().postal_code
            delivery_address = f"{user_street},{user_city},{user_state},{user_postal_code}"
        else:
            
            delivery_address = ProductDeliveryAddress.objects.filter(id=delivery_address_main,created_by=check_user.first()).first().complete_address
        obj = GenerateKey ()
        secret_key = obj.gen_payment_key()
        unit_amount = (quantity*price)*100
        add_buy = MerchandiseStoreProductBuy.objects.create(
            secret_key = secret_key,
            # cart_idd = ,
            product_id = product_id,
            price_per_product = price,
            quantity = quantity,
            status = "BuyNow",
            total_product = (quantity*price),
            delivery_address_main_id = delivery_address_main,
            delivery_address = delivery_address,
            created_by = check_user.first(),
            size = size
        )
        charge_for = "product_buy"
        card_id = add_buy.id
        product_name_ = add_buy.product.name
        product_name = f"Your merchandise product {product_name_}"
               
        product_description = "Payment received by Pickleit"
        get_user = check_user.first()
        if get_user.stripe_customer_id :
            stripe_customer_id = get_user.stripe_customer_id
        else:
            customer = stripe.Customer.create(email=get_user.email).to_dict()
            stripe_customer_id = customer["id"]
            get_user.stripe_customer_id = stripe_customer_id
            get_user.save()
        
        host = request.get_host()
        current_site = f"{protocol}://{host}"

        main_url = f"{current_site}/accessories/694b0ce98afc6fa28631622bc70971b3ca40d25490634a60dcd53a5ff04843f3/{charge_for}/{card_id}/"
        product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
        price = stripe.Price.create(unit_amount=unit_amount,currency='usd',product=product["id"],).to_dict()
        checkout_session = stripe.checkout.Session.create(
            customer=stripe_customer_id,
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': price["id"],
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url= main_url + "{CHECKOUT_SESSION_ID}" + "/",
            cancel_url="https://example.com/success" + '/cancel.html',
        )
        return Response({"strip_url":checkout_session.url})
    except Exception as e :
        data = {}
        data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
        return Response(data)


# store buy product payment details store.
def buy_now_product_payment(request,charge_for,cart_id,checkout_session_id):
    """
    Handles the payment part for directly buying any product.
    """
    context ={}
    stripe.api_key = settings.STRIPE_SECRET_KEY
    # context['stripe_api_key'] = settings.STRIPE_PUBLIC_KEY
    pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()    
    stripe_customer_id = pay["customer"]
    payment_status = pay["payment_status"]
    expires_at = pay["expires_at"]
    amount_total = float(pay["amount_total"]) / 100

    payment_method_types = pay["payment_method_types"]
    
    payment_status = True if payment_status == "paid" else False
    check_customer = User.objects.filter(stripe_customer_id=stripe_customer_id).first()
    obj = GenerateKey ()
    secret_key = obj.gen_payment_key()
    check_charge = MerchandiseStoreProductBuy.objects.filter(id=cart_id, status="BuyNow", is_paid=False)
    if check_charge.exists():
        get_charge = check_charge.first()
        per_product_amount = int(get_charge.price_per_product)
        total_product = int(get_charge.quantity)
        charge_amount = (per_product_amount*total_product)
        expires_time = None
        save_payment = PaymentTable(
            secret_key=secret_key,
            var_chargeamount=charge_amount,              
            payment_for=charge_for,
            payment_for_id=checkout_session_id,
            payment_by=payment_method_types,
            payment_amount=amount_total,
            payment_status=payment_status,
            stripe_response=pay,
            created_by_id=check_customer.id,
            expires_at=expires_time
            )
        save_payment.save()
        product_ = MerchandiseStoreProductBuy.objects.get(pk=cart_id)
        save_payment.payment_for_product.add(product_)
        obj = GenerateKey ()
        genarate_cart_id = obj.generate_cart_unique_id()
        
        if payment_status is True:
            MerchandiseStoreProductBuy.objects.filter(id=cart_id).update(is_paid=True,status="ORDER PLACED",cart_idd=genarate_cart_id)
            return render(request,"success_payment_for_buy.html",context)
        else:
            MerchandiseStoreProductBuy.objects.filter(id=cart_id).update(status="CANCEL",cart_idd=genarate_cart_id)
            message = f"error .."
            return render(request,"failed_payment.html")
    else: 
        return render(request,"success_payment_for_buy.html",context)


#buy all cart product
@api_view(('POST',))
def buy_all_cart_product(request):
    """
    Allows a user to buy all his cart products.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY
    user_uuid = request.data.get('user_uuid')
    user_secret_key = request.data.get('user_secret_key')
    coupon_code = request.data.get('coupon_code')
    check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
    if not check_user.exists():
        data = {}
        data['message'] = "User not exists"
        return Response(data)
    charge_for = "product_buy"
    get_user = check_user.first()
    user_id = get_user.id
    all_cart_product = MerchandiseStoreProductBuy.objects.filter(created_by_id=user_id, status="CART", is_paid=False)
    # print(all_cart_product.values("quantity","total_product","price_per_product"))
    if all_cart_product.exists():
        card_id_list = []
        all_product_string = "Your merchandise product "
        total_price = 0
        delivery_address_main = ProductDeliveryAddress.objects.filter(created_by=get_user,default_address=True).first()
        obj = GenerateKey ()
        genarate_cart_id = obj.generate_cart_unique_id()
        for cpd in all_cart_product:
            card_id_list.append(cpd.id)
            p_name = cpd.product.name
            total_price += (cpd.price_per_product * cpd.quantity)
            all_product_string += p_name + ", "
            try:
                complete_address = f"{delivery_address_main.street}, {delivery_address_main.city}, {delivery_address_main.state}, {delivery_address_main.country}, PIN-{delivery_address_main.postal_code}"
            except:
                complete_address = f""
            MerchandiseStoreProductBuy.objects.filter(id=cpd.id).update(delivery_address_main=delivery_address_main,
                                                    delivery_address=complete_address,cart_idd=genarate_cart_id)            

        all_product_string = all_product_string.rstrip(", ")
    else:
        return Response({"message":"No item in Cart"}) 

    if get_user.stripe_customer_id :
        stripe_customer_id = get_user.stripe_customer_id
    else:
        customer = stripe.Customer.create(email=get_user.email).to_dict()
        stripe_customer_id = customer["id"]
        get_user.stripe_customer_id = stripe_customer_id
        get_user.save()
    
    # product_name = all_product_string
    product_name = all_product_string
    product_description = f"Payment received by Pickleit"
    unit_amount = total_price*100
    today= datetime.now()
    discount_obj = CouponCode.objects.filter(coupon_code=coupon_code, start_date__lte=today, end_date__gte=today)
    if discount_obj.exists():
        get_discount = discount_obj.first().percentage
        unit_amount = int(unit_amount - (unit_amount * (get_discount/100)))
    
    host = request.get_host()
    current_site = f"{protocol}://{host}"
    main_url = f"{current_site}/accessories/7417d36367fa2fab97cf476a626b989b2fb842eddc47f55b50e877bd57c97a00/{charge_for}/"
    product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
    price = stripe.Price.create(unit_amount=unit_amount,currency='usd',product=product["id"],).to_dict()
    checkout_session = stripe.checkout.Session.create(
        customer=stripe_customer_id,
        line_items=[
            {
                # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                'price': price["id"],
                'quantity': 1,
            },
        ],
        mode='payment',
        success_url= main_url + "{CHECKOUT_SESSION_ID}" + "/",
        cancel_url="https://example.com/success" + '/cancel.html',
    )
    return Response({"strip_url":checkout_session.url})


#payment for buy all cart product details
def buy_all_cart_product_payment(request,charge_for,checkout_session_id):
    """
    Handles the payment for buying all cart products.
    """
    context ={}
    stripe.api_key = settings.STRIPE_SECRET_KEY
    pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()    
    stripe_customer_id = pay["customer"]
    payment_status = pay["payment_status"]
    expires_at = pay["expires_at"]
    amount_total = float(pay["amount_total"]) / 100

    payment_method_types = pay["payment_method_types"]
    
    payment_status = True if payment_status == "paid" else False
    check_customer = User.objects.filter(stripe_customer_id=stripe_customer_id).first()
    check_charge = MerchandiseStoreProductBuy.objects.filter(created_by=check_customer.id, status="CART").values_list("id", flat=True)
    obj = GenerateKey ()
    secret_key = obj.gen_payment_key()
    cart_list = list(check_charge)
    cart_to_add_ = MerchandiseStoreProductBuy.objects.filter(pk__in=cart_list)
    expires_time = None
    save_payment = PaymentTable(
        secret_key=secret_key,
        var_chargeamount=amount_total,              
        payment_for=charge_for,
        payment_for_id=checkout_session_id,
        payment_by=payment_method_types,
        payment_amount=amount_total,
        payment_status=payment_status,
        stripe_response=pay,
        created_by_id=check_customer.id,
        expires_at=expires_time
        )
    save_payment.save()
    save_payment.payment_for_product.add(*cart_to_add_)
    if payment_status is True:
        for kl in cart_list:
            MerchandiseStoreProductBuy.objects.filter(id=kl).update(is_paid=True,status="ORDER PLACED")
        return render(request,"success_payment_for_buy.html",context)
    else:
        for kl in cart_list:
            MerchandiseStoreProductBuy.objects.filter(id=kl).update(is_paid=False,status="CART")
        message = f"error .."
        return render(request,"failed_payment.html")


#################################### payement part end #############################################
  
    
class MerchandiseStoreProductBuySerializer(serializers.ModelSerializer):
    total_price = serializers.IntegerField(source='total_product', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    address = serializers.CharField(source='delivery_address_main.complete_address', read_only=True)
    image = serializers.CharField(source='product.image', read_only=True)
    class Meta:
        model = MerchandiseStoreProductBuy
        exclude = ["id"]
        # fields = ["id", "cart_idd", "product_name", "price_per_product", "quantity", "total_price", "status", "is_paid", "delivery_address", "created_at","address"]


class MyOrder(APIView):
    def get(self, request, *args, **kwargs):
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        status_param = request.GET.get('status')
        if not (user_uuid and user_secret_key):
            return JsonResponse({'error': 'Both user_uuid and user_secret_key are required.'}, status=status.HTTP_400_BAD_REQUEST)
        user = get_object_or_404(User, uuid=user_uuid, secret_key=user_secret_key)
        order_data = MerchandiseStoreProductBuy.objects.filter(created_by_id=user.id, status=status_param)
        serializer = MerchandiseStoreProductBuySerializer(order_data, many=True)
        return JsonResponse({'data': serializer.data})
    

# Not using
@api_view(('GET',))
def show_notifications(request):
    try:
        data = {'status':'','notifications_data':'','user_data':'','message':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            main_role = get_user.get_role()
            user_data = []
            user_data.append("team_manager") if get_user.is_team_manager or get_user.is_coach else None
            user_data.append("player") if get_user.is_player else None

            all_noti = Notifications.objects.filter(user_id = get_user.id,is_read=False).values("id","message","screen","url","timestamp")
            data["status"], data["notifications_data"], data["message"] = status.HTTP_200_OK, all_noti,"Data Found"
            # user check for organizer
            if get_user.is_organizer :
                user_data.append("organizer")
               
            # user check for sponsor
            if get_user.is_sponsor :
                user_data.append("sponsor")
                
            data["user_data"] = {"main_role":main_role,"user_sub_role":user_data}
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# Not using
@api_view(('POST',))
def update_notifications(request):
    try:
        data = {'status':'','data':'','message':''}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        notifications = request.data.get('notifications')
        
        # [{"id":1,"message":"You are Now organizer."},{"id":2,"message":"message"}]
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            notifications_list = json.loads(notifications)
            for i in notifications_list :
                check_noti = Notifications.objects.filter(id=i["id"],message=i["message"],user_id=get_user.id)
                if check_noti.exists():
                    get_noti = check_noti.first()
                    get_noti.is_read = True
                    get_noti.save()
                else:
                    pass
            data["status"], data["data"], data["message"] = status.HTTP_200_OK, "","Data Updated"
        else:
            data["status"], data["data"], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


# @api_view(('POST',))
# def allow_to_make_ambassador(request):
#     try:
#         responsee = {}
#         user_uuid = request.data.get('user_uuid')
#         user_secret_key = request.data.get('user_secret_key')
#         player_uuid = request.data.get('player_uuid')
#         player_secret_key = request.data.get('player_secret_key')
#         check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
#         check_payer = Player.objects.filter(uuid=player_uuid, secret_key=player_secret_key)
#         print(check_payer)
#         if check_user.exists() and check_payer.exists():
#             user_instance = check_user.first()
#             if user_instance.is_admin or user_instance.is_organizer:
#                 payer=check_payer.first().player.id
#                 User.objects.filter(id=int(payer)).update(is_ambassador = True)
#                 player_name= check_payer.first().player.first_name
#                 responsee = {'status': status.HTTP_200_OK, 'message': f'Now {player_name} is Ambassador'}
#             else:
#                 responsee = {'status': status.HTTP_200_OK, 'message': 'User not admin or organiger'}
#         else:
#             responsee = {'status': status.HTTP_400_BAD_REQUEST, 'message': 'Not found user or player'}     
#         return Response(responsee)
#     except Exception as e:
#         responsee = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
#         return Response(responsee, status=responsee['status'])


#change
@api_view(('POST',))
def allow_to_make_ambassador(request):
    """
    Allows a user to become ambassador.
    """
    try:
        responsee = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        player_uuid = request.data.get('player_uuid')
        player_secret_key = request.data.get('player_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        check_payer = Player.objects.filter(uuid=player_uuid, secret_key=player_secret_key)
        
        if check_user.exists() and check_payer.exists():
            user_instance = check_user.first()
            if user_instance.is_admin or user_instance.is_organizer:
                payer=check_payer.first().player.id
                User.objects.filter(id=int(payer)).update(is_ambassador = True)
                check__am = AmbassadorsDetails.objects.filter(ambassador_id=payer)
                
                if len(check__am)==0:
                    AmbassadorsDetails.objects.create(ambassador_id=payer)
                player_name= check_payer.first().player.first_name
                responsee = {'status': status.HTTP_200_OK, 'message': f'Now {player_name} is Ambassador'}
            else:
                responsee = {'status': status.HTTP_200_OK, 'message': 'User not admin or organiger'}
        else:
            responsee = {'status': status.HTTP_400_BAD_REQUEST, 'message': 'Not found user or player'}     
        return Response(responsee)
    except Exception as e:
        responsee = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(responsee, status=responsee['status'])


@api_view(('POST',))
def allow_to_make_ambassador_to_player(request):
    """
    Allows to make an ambassador to player again.
    """
    try:
        responsee = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        player_uuid = request.data.get('player_uuid')
        player_secret_key = request.data.get('player_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        check_payer = Player.objects.filter(uuid=player_uuid, secret_key=player_secret_key)
        if check_user.exists() and check_payer.exists():
            user_instance = check_user.first()
            if user_instance.is_admin or user_instance.is_organizer:
                payer=check_payer.first().player.id
                User.objects.filter(id=int(payer)).update(is_ambassador = False)
                player_name= check_payer.first().player.first_name
                responsee = {'status': status.HTTP_200_OK, 'message': f'Now {player_name} is Removed from Ambassador'}
            else:
                responsee = {'status': status.HTTP_200_OK, 'message': 'User not admin or organiger'}
        else:
            responsee = {'status': status.HTTP_400_BAD_REQUEST, 'message': 'Not found user or player'}     
        return Response(responsee)
    except Exception as e:
        responsee = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(responsee, status=responsee['status'])


@api_view(('GET',))
def ambassador_list(request):
    """
    Displays the list of all ambassadors.
    """
    try:
        data = {'status': '', 'data': [], 'message': ''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        search_text = request.GET.get('search_text')
        
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
                get_user = check_user.first()
                if get_user.is_admin or get_user.is_organizer:
                    if not search_text:
                        all_players = Player.objects.filter(player__is_ambassador=True).values()
                    else:
                        all_players = Player.objects.filter(player__is_ambassador=True).filter(Q(player_first_name__icontains=search_text) | Q(player_last_name__icontains=search_text)).values()
                elif get_user.is_team_manager or get_user.is_coach:
                    if not search_text:
                        all_players = Player.objects.filter(created_by_id=get_user.id,player__is_ambassador=True).values()
                    else:
                        all_players = Player.objects.filter(created_by_id=get_user.id,player__is_ambassador=True).filter(Q(player_first_name__icontains=search_text) | Q(player_last_name__icontains=search_text)).values()
                
                for player_data in all_players:
                    player_id = player_data["id"]
                    user_id = player_data["player_id"]
                    user_image = User.objects.filter(id=user_id).values()
                    
                    ambassador = AmbassadorsDetails.objects.filter(ambassador_id=user_id)
                    if ambassador.exists():
                        get_ambassador = ambassador.first()
                        player_data["follower"] = get_ambassador.follower.count()
                        player_data["following"] = get_ambassador.following.count()
                    else:
                        player_data["follower"] = 0
                        player_data["following"] = 0
                    get_post = list(AmbassadorsPost.objects.filter(created_by_id = user_id))
                    player_data["total_post"] = len(get_post)
                    
                    try:
                        player_data["user_uuid"] = user_image[0]["uuid"]
                        player_data["user_secret_key"] = user_image[0]["secret_key"]
                    except:
                        player_data["user_uuid"] = "error to find"
                        player_data["user_secret_key"] = "error to find"
                    if user_image[0]["image"] is not None or user_image[0]["image"] != "":
                        player_data["player_image"] = user_image[0]["image"]
                    else:
                        player_data["player_image"] = None 
                    player_data["is_edit"] = player_data["created_by_id"] == get_user.id
                    player_instance = Player.objects.get(id=player_id)
                    team_ids = list(player_instance.team.values_list('id', flat=True))
                    player_data["team"] = []
                    for team_id in team_ids:
                        team = Team.objects.filter(id=team_id).values()
                        if team.exists():
                            player_data["team"].append(list(team))

                data["status"] = status.HTTP_200_OK
                data["data"] = list(all_players)
                data["message"] = "Data found"
        else:
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"
        return Response(data, status=data['status'])
    except Exception as e:
        data = {'status': status.HTTP_400_BAD_REQUEST, 'data':[], 'message': str(e)}
        return Response(data, status=data['status'])
    

from django.db.models import CharField, F, Value
from django.db.models.functions import Cast

@api_view(('GET',))
def ambassador_profile_view(request):
    """
    Displays the profile details of an ambassador.
    """
    try:
        data = {'status': '', 'data': [],"ambassador_posts":[], 'message': '', "follower": '', 'following':''}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        ambassador_uuid = request.GET.get('ambassador_uuid')
        ambassador_secret_key = request.GET.get('ambassador_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            player_=Player.objects.filter(uuid=ambassador_uuid, secret_key=ambassador_secret_key)
            player_details = player_.annotate(player_phone_number_str=Cast('player_phone_number', CharField())).values('uuid','secret_key','player_full_name','player_email','player_phone_number_str','player_ranking','created_by__first_name','created_by__first_name')
            created_by = User.objects.filter(id=player_.first().player.id).first()
            all_post = AmbassadorsPost.objects.filter(created_by=created_by).values()
            data["status"] = status.HTTP_200_OK
            data["data"] = player_details
            data["ambassador_posts"] = list(all_post)
            ambassadorsDetails = AmbassadorsDetails.objects.filter(ambassador=created_by)
            if ambassadorsDetails.exists():
                ambassadorsDetails = ambassadorsDetails.first()
                data["follower"] = len(ambassadorsDetails.follower.all())
                data["following"] = len(ambassadorsDetails.following.all())
            else:
                data["follower"] = 0
                data["following"] = 0
            data["message"] = "Data found"
        else:
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"
        return Response(data)
    except Exception as e:
        responsee = {'status': status.HTTP_400_BAD_REQUEST, 'data':[],"ambassador_posts":[], 'message': str(e),  "follower": '', 'following':''}
        return Response(responsee, status=responsee['status'])
    

# Added    
@api_view(('POST',))
def ambassador_follow_or_unfollow(request):
    """
    Is used for a user to follow or unfollow an ambassador.
    """
    try:
        data = {"status":"", "message":""}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        profile_uuid = request.data.get('profile_uuid')
        profile_secret_key = request.data.get('profile_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            check_ambassador = User.objects.filter(uuid=profile_uuid, secret_key=profile_secret_key)
            if check_ambassador.exists():
                get_ambassador=check_ambassador.first()
                check_ambassador_details = AmbassadorsDetails.objects.filter(ambassador=get_ambassador)
                if check_ambassador_details.exists():
                    ambassador = check_ambassador_details.first()
                else:
                    ambassador = AmbassadorsDetails.objects.create(ambassador=get_ambassador)
                if get_user in ambassador.follower.all():
                    ambassador.follower.remove(get_user)
                    
                    check_unfollower_details = AmbassadorsDetails.objects.filter(ambassador=get_user)  
                    if check_unfollower_details.exists():
                        unfollower = check_unfollower_details.first()
                    else:
                        unfollower = AmbassadorsDetails.objects.create(ambassador=get_user)              
                    unfollower.following.remove(get_ambassador)
                    data['status'] = status.HTTP_200_OK
                    data['message'] = "Successfully unfollowed."
                else:
                    ambassador.follower.add(get_user)
                    check_follower_details = AmbassadorsDetails.objects.filter(ambassador=get_user) 
                    if check_follower_details.exists():
                        follower = check_follower_details.first()
                    else:
                        follower = AmbassadorsDetails.objects.create(ambassador=get_user)               
                    follower.following.add(get_ambassador)
                    data['status'] = status.HTTP_200_OK
                    data['message'] = "Successfully followed."
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "Ambassador not found."                
        else:
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"
        return Response(data)            
    except Exception as e:
        data = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(data)
    

@api_view(('GET',))
def check_ambassador_following_or_not(request):
    """
    Fetches the details if a user is following an ambassador or not.
    """
    try:
        data = {"status":"", "message":"", "data":[], "follow": ""}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        ambassador_uuid = request.GET.get('ambassador_uuid')
        ambassador_secret_key = request.GET.get('ambassador_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            check_ambassador = User.objects.filter(uuid=ambassador_uuid, secret_key=ambassador_secret_key)
            if check_ambassador.exists():
                get_ambassador=check_ambassador.first()
                check_ambassador_details = AmbassadorsDetails.objects.filter(ambassador=get_ambassador)
                if check_ambassador_details.exists():
                    get_ambassador_details = check_ambassador_details.first()
                else:
                    get_ambassador_details = AmbassadorsDetails.objects.create(ambassador=get_ambassador)
                if get_user in get_ambassador_details.follower.all():
                    all_followers = get_ambassador_details.follower.all().values("id","uuid","secret_key","username","email","first_name","last_name","phone","user_birthday","image","gender","street","city","state","country","postal_code","is_player","is_organizer","is_sponsor","is_ambassador","is_admin")
                    data["status"] = status.HTTP_200_OK
                    data["data"] ={"ambassador_followers": list(all_followers)}
                    data["follow"] = True
                    data["message"] = "You are following this ambassador."
                else:
                    data["status"] = status.HTTP_200_OK
                    data["follow"] = False
                    data["message"] = "You are not following this ambassador."
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "Ambassador not found."                
        else:
            data['status'] = status.HTTP_401_UNAUTHORIZED
            data['message'] = "Unauthorized access"
        return Response(data)            
    except Exception as e:
        data = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(data)


class AmbassadorsPostSerializer(serializers.ModelSerializer):
    class Meta:
        model = AmbassadorsPost
        fields = '__all__'


# @api_view(['POST'])
# def ambassadors_create_post(request):
#     try:
#         response_data = {}
#         user_uuid = request.data.get('user_uuid')
#         user_secret_key = request.data.get('user_secret_key')
#         post_text = request.data.get('post_text')
        
#         # Access the uploaded file
#         file = request.FILES.get("file")
        
#         if file:  # Check if the file is provided
#             # Get the MIME type from the file itself
#             mime_type = file.content_type
            
#             # if mime_type.startswith('video'):
#             if mime_type == 'video/mp4':
#                 # Check if the user exists
#                 user_instance = get_object_or_404(User, uuid=user_uuid, secret_key=user_secret_key)
#                 player_instance = Player.objects.filter(player=user_instance)
#                 # print(user_instance)
#                 # print(player_instance)
#                 # print(user_instance.is_ambassador)
#                 # Check if the user is an ambassador
#                 if user_instance.is_ambassador and player_instance.exists():
#                     # Create the post
#                     obj = GenerateKey()  # Assuming this is a function you have defined elsewhere
#                     secret_key = obj.gen_ambassadorsPost_key()
#                     post = AmbassadorsPost.objects.create(
#                         secret_key=secret_key,
#                         file=file, 
#                         post_text=post_text, 
#                         created_by=user_instance
#                     )
#                     # Save the file reference in the database
#                     post.save()
#                     serializer = AmbassadorsPostSerializer(post)
#                     response_data["status"] = status.HTTP_200_OK
#                     response_data["message"] = "Post successfully uploaded"
#                     response_data["data"] = serializer.data
#                 else:
#                     response_data["status"] = status.HTTP_400_BAD_REQUEST
#                     response_data["data"] = []
#                     response_data["message"] = "This user is not an ambassador or not in player list"
#             else:
#                 response_data["status"] = status.HTTP_400_BAD_REQUEST
#                 response_data["data"] = []
#                 response_data["message"] = "Uploaded file is not a video"
#         else:
#             response_data["status"] = status.HTTP_400_BAD_REQUEST
#             response_data["data"] = []
#             response_data["message"] = "File not provided"
            
#         return Response(response_data)
#     except Exception as e:
#         response_data = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
#         return Response(response_data, status=response_data['status'])


import mimetypes
@api_view(['POST'])
def ambassadors_create_post(request):
    """
    Is used for an ambassador to add a post.
    """
    try:
        # Get data from request
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        post_text = request.data.get('post_text')
        file = request.FILES.get("file")
        thumbnail = request.FILES.get("thumbnail")

        # Check if file is provided
        if not file and not thumbnail:
            return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': 'File and thumbnail not provided'}, status=status.HTTP_400_BAD_REQUEST)

        # Check the MIME type of the file
        detected_mime_type, _ = mimetypes.guess_type(file.name)
        if not detected_mime_type.startswith('video/'):
            return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': 'Uploaded file is not a video'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if the user exists and is an ambassador
        user_instance = get_object_or_404(User, uuid=user_uuid, secret_key=user_secret_key)
        if not user_instance.is_ambassador:
            return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': 'User is not an ambassador'}, status=status.HTTP_400_BAD_REQUEST)

        # Upload the file to S3 and get the URL
        uploaded_url = upload_file_to_s3(file)        
        thumbnail_url = upload_file_to_s3(thumbnail)
        if not uploaded_url:
            return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': 'Failed to upload file to S3'}, status=status.HTTP_400_BAD_REQUEST)
        if not thumbnail_url:
            return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': 'Failed to upload thumbnail to S3'}, status=status.HTTP_400_BAD_REQUEST)

        # Create the post
        secret_key = GenerateKey().gen_ambassadorsPost_key()
        post = AmbassadorsPost.objects.create(
            secret_key=secret_key,
            file=uploaded_url,
            thumbnail=thumbnail_url,
            post_text=post_text,
            created_by=user_instance
        )
        serializer = AmbassadorsPostSerializer(post)
        return Response({'status': status.HTTP_200_OK, 'message': 'Post successfully uploaded', 'data': serializer.data}, status=status.HTTP_200_OK)
    
    except FileNotFoundError:
        return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': 'File not found'}, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@api_view(('GET',))
def ambassadors_view(request):
    """
    Is used to view the details of a post or the list of posts created by the ambassador.
    """
    try:
        response_data = {}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        post_id = request.GET.get('post_id')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        user_instance = check_user.first()
        #protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        # Construct the complete URL for media files
        media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
        if check_user and user_instance.is_ambassador:
            if post_id is not None:
                data = AmbassadorsPost.objects.filter(id = int(post_id), created_by_id=user_instance.id).values("id", "file", "post_text", "approved_by_admin", "likes")
                data[0]["file"] = media_base_url + data[0]["file"]
                response_data["status"] = status.HTTP_200_OK
                response_data["data"] = list(data)
                response_data["message"] = "View Your Post"
            else:
                data = AmbassadorsPost.objects.filter(created_by_id=user_instance.id).order_by("-id").values("id", "file", "post_text", "approved_by_admin","likes")
                for i in data:
                    i["file"] = media_base_url + i["file"]
                response_data["status"] = status.HTTP_200_OK
                response_data["data"] = list(data)
                response_data["message"] = "View Your Posts"
        else:
            response_data["status"] = status.HTTP_400_BAD_REQUEST
            response_data["data"] = []
            response_data["message"] = "User does not exist or is not an ambassador"

        return Response(response_data)
    except Exception as e:
        response_data = {'status': status.HTTP_400_BAD_REQUEST, 'data': [], 'message': str(e)}
        return Response(response_data)


@api_view(('POST',))
def ambassadors_edit_post(request):
    """
    Is used for an ambassador to edit his post.
    """
    try:
        response_data = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        edit_id = request.data.get('edit_id')
        file = request.FILES.get("file")
        post_text = request.data.get('post_text')
        
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
            
        if check_user.exists():
            user_instance = check_user.first()
            check_user_ambassadors = user_instance.is_ambassador
            
            if check_user_ambassadors:
                # Update only if the file is provided in the request
                if file:
                    update_file = "ambassadors_post/" + file.name
                    AmbassadorsPost.objects.filter(id=edit_id).update(file=update_file)
                
                # Update other fields
                AmbassadorsPost.objects.filter(id=edit_id).update(post_text=post_text)
                
                response_data["status"] = status.HTTP_200_OK
                response_data["message"] = "Post Successfully Edited"
            else:
                response_data["status"] = status.HTTP_400_BAD_REQUEST
                response_data["message"] = "This user is not an ambassador"
        else:
            response_data["status"] = status.HTTP_400_BAD_REQUEST
            response_data["message"] = "User does not exist"
        
        return Response(response_data)
    except Exception as e:
        response_data = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(response_data)


@api_view(('POST',))
def ambassadors_delete_post(request, del_id):
    """
    Is used for an ambassador to delete his post.
    """
    try:
        response_data = {}
        # Check if the post with the given ID exists
        post_to_delete = AmbassadorsPost.objects.filter(id=del_id).first()
        
        if post_to_delete:
            post_to_delete.delete()
            response_data["status"] = status.HTTP_200_OK
            response_data["message"] = f"Post with ID {del_id} deleted successfully."
        else:
            response_data["status"] = status.HTTP_404_NOT_FOUND
            response_data["message"] = f"Post with ID {del_id} does not exist."

        return Response(response_data)
    except Exception as e:
        response_data = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(response_data)


@api_view(('POST',))
def admin_allow_ambassadors_post(request):
    """
    Allows admin to approve or not approve a post.
    """
    try:
        response_data = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        approved_by_admin = request.data.get('approved_by_admin')
        apr_id = request.data.get('apr_id')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        
        if check_user.exists():
            user_instance = check_user.first()
            check_user_admin = user_instance.is_admin
            if check_user_admin:
                if approved_by_admin is not None:
                    AmbassadorsPost.objects.filter(id=int(apr_id)).update(approved_by_admin=approved_by_admin)
                    response_data["status"] = status.HTTP_400_BAD_REQUEST
                    response_data["message"] = "Approved the post"
                else:
                    response_data["status"] = status.HTTP_400_BAD_REQUEST
                    response_data["message"] = "Not approved the post"
            else:
                response_data["status"] = status.HTTP_400_BAD_REQUEST
                response_data["message"] = "User not Admin"
        else:
            response_data["status"] = status.HTTP_400_BAD_REQUEST
            response_data["message"] = "User does not exist"
        return Response(response_data)
    except Exception as e:
        response_data = {'status': status.HTTP_400_BAD_REQUEST, 'message': str(e)}
        return Response(response_data)


@api_view(('GET',))
def ambassadors_view_all_allow_post(request):
    """
    Displays the list of all posts.
    """
    try:
        response_data = {}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        #protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        # Construct the complete URL for media files
        media_base_url = f"{protocol}://{host}"
        if check_user.exists():
            get_user = check_user.first()
            data = list(AmbassadorsPost.objects.all())
            random.shuffle(data)
            paginator = PageNumberPagination()
            paginator.page_size = 10  # Adjust as needed
            result_page = paginator.paginate_queryset(data, request)
            serialized_data = AmbassadorsPostSerializer(result_page, many=True)
            for post in serialized_data.data:
                if post['file']:
                    post['file'] = post['file']
                if post["thumbnail"]:
                    post["thumbnail"] = post["thumbnail"]
                else:
                    post["thumbnail"] = "https://pickleitmedia.s3.amazonaws.com/Reels/PickleIt_logo.png_7908482601214a24bf2f1bbbb3432381.png"
                user_details = User.objects.filter(id=post['created_by']).values("id","uuid", "secret_key", "first_name", "last_name", "image")
                for user in user_details:
                    user['image'] = media_base_url + '/media/' +user['image']
                post['created_by'] = list(user_details)
                post_created_by_id = post["created_by"][0]["id"]
                post['total_likes_count']  = len(post['likes'])
                post_created_by = User.objects.filter(id=post_created_by_id).first()
                if get_user.id in post["likes"]:
                    post["is_liked"] = True
                else:
                    post["is_liked"] = False
                check_ambassador = AmbassadorsDetails.objects.filter(ambassador__id=post_created_by.id)
                if check_ambassador.exists():
                    get_ambassador = check_ambassador.first()
                else:
                    get_ambassador = AmbassadorsDetails.objects.create(ambassador__id=post_created_by.id)
                if get_user in get_ambassador.follower.all():
                    post["is_following"] = True
                else:
                    post["is_following"] = False
            return paginator.get_paginated_response(serialized_data.data)
        else:
            response_data["status"] = status.HTTP_400_BAD_REQUEST
            response_data["result"] = []
            response_data["message"] = "User does not exist"
            return Response(response_data)
    except Exception as e:
        response_data = {'status': status.HTTP_400_BAD_REQUEST, 'result': [], 'message': str(e)}
        return Response(response_data)

# @api_view(('GET',))
# def ambassadors_view_all_allow_post(request):
#     try:
#         response_data = {}
#         user_uuid = request.GET.get('user_uuid')
#         user_secret_key = request.GET.get('user_secret_key')
#         check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        
#         # Get the protocol and host from the request
#         protocol = 'https' if request.is_secure() else 'http'
#         host = request.get_host()
        
#         # Construct the complete URL for media files
#         media_base_url = f"{protocol}://{host}"
        
#         if check_user.exists():
#             data = AmbassadorsPost.objects.all()
#             paginator = PageNumberPagination()
#             paginator.page_size = 2  # Adjust as needed
#             result_page = paginator.paginate_queryset(data, request)
#             serialized_data = AmbassadorsPostSerializer(result_page, many=True)
            
#             for post in serialized_data.data:
#                 if post['file']:
#                     # Prepare file data in the format you specified
#                     filename = post['file'].split("/")[-1]
#                     file_path = post['file'].replace(media_base_url, '')
#                     path = f".{file_path}"
#                     file_data = [(filename, open(path, 'rb'), 'application/octet-stream')]
#                     # print(file_data)
#                     post['file_data_str'] = str(file_data)
                    
#                 # Adjust user image URL
#                 user_details = User.objects.filter(id=post['created_by']).values("uuid", "secret_key", "first_name", "last_name", "image")
#                 for user in user_details:
#                     user['image'] = media_base_url + '/media/' + user['image']
#                 post['created_by'] = list(user_details)
                
#                 # Calculate total likes count
#                 post['total_likes_count'] = len(post['likes'])
            
#             return paginator.get_paginated_response(serialized_data.data)
#         else:
#             response_data["status"] = status.HTTP_400_BAD_REQUEST
#             response_data["result"] = []
#             response_data["message"] = "User does not exist"
#             return Response(response_data)
#     except Exception as e:
#         response_data = {'status': status.HTTP_400_BAD_REQUEST, 'result': [], 'message': str(e)}
#         return Response(response_data)


##piu
@api_view(('POST',))
def add_advertiser_facility(request):
    """
    Is used for a sponsor to add any advertiser facility.
    """
    try:
        data = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        
        facility_name = request.data.get('facility_name')
        facility_type = request.data.get('facility_type')
        court_type = request.data.get('court_type')
        membership_type = request.data.get('membership_type')
        number_of_courts = request.data.get('number_of_courts')
        complete_address = request.data.get('complete_address')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_sponsor == True:
                full_address = complete_address
                state, country, pincode, latitude , longitude = get_address_details(full_address, api_key)

                obj = GenerateKey()
                facility_key = obj.gen_facility_key()
                facility = AdvertiserFacility.objects.create(secret_key=facility_key, facility_name=facility_name, facility_type=facility_type, court_type=court_type, membership_type=membership_type, number_of_courts=number_of_courts, complete_address=complete_address, created_by=get_user)
                facility.latitude = latitude
                facility.longitude = longitude
                facility.save()
                data['status'], data['message'] = status.HTTP_201_CREATED, "Facility created successfully."
            else:
                data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User is not a sponsor, so does not have permission."
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def advertiser_facility_list(request):
    """
    Displays the list of all facilities added by sponsor.
    """
    try:
        data = {}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)        
        if check_user.exists():
            data['data'] = AdvertiserFacility.objects.filter(created_by=check_user.first()).values()
            data['status'] = status.HTTP_200_OK
            data['message'] = "Data found."
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def advertiser_facility_list_for_all(request):
    """
    Displays the list of all advertiser facilities.
    """
    try:
        data = {}
        data['data'] = AdvertiserFacility.objects.all().values()
        data['status'] = status.HTTP_200_OK
        data['message'] = "Data found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)



@api_view(('POST',))
def edit_advertiser_facility(request):
    """
    Is used for sponsor to edit the details of an advertiser facility.
    """
    try:
        data = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        facility_uuid = request.data.get('facility_uuid')
        facility_secret_key = request.data.get('facility_secret_key')        
        facility_name = request.data.get('facility_name')
        facility_type = request.data.get('facility_type')
        court_type = request.data.get('court_type')
        membership_type = request.data.get('membership_type')
        number_of_courts = request.data.get('number_of_courts')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)        
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_sponsor == True:
                check_facility = AdvertiserFacility.objects.filter(uuid=facility_uuid, secret_key=facility_secret_key)
                if check_facility.exists():
                    check_facility.update(facility_name=facility_name, facility_type=facility_type, court_type=court_type, membership_type=membership_type, number_of_courts=number_of_courts)
                    data['status'], data['message'] = status.HTTP_200_OK, "Facility edited successfully."
                else:
                    data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "Facility not found."
            else:
                data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User is not a sponsor, so does not have permission.."
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('POST',))
def delete_advertiser_facility(request):
    """
    Is used for sponsor to delete an advertiser facility.
    """
    try:
        data = {}
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        facility_uuid = request.data.get('facility_uuid')
        facility_secret_key = request.data.get('facility_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)        
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_sponsor == True:
                check_facility = AdvertiserFacility.objects.filter(uuid=facility_uuid, secret_key=facility_secret_key)
                if check_facility.exists():
                    get_facility = check_facility.first()
                    get_facility.delete()
                    data["status"], data["message"] = status.HTTP_204_NO_CONTENT, "Facility deleted successfully."
                else:
                    data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Facility not found."
            else:
                data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User is not a sponsor, so does not have permission."
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)



@api_view(('GET',))
def view_advertiser_facility(request):
    """
    Displays the details of an advertiser facility.
    """
    try:
        data = {}
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        facility_uuid = request.GET.get('facility_uuid')
        facility_secret_key = request.GET.get('facility_secret_key')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key) 
        if check_user.exists():
            check_facility = AdvertiserFacility.objects.filter(uuid=facility_uuid, secret_key=facility_secret_key)
            if check_facility.exists():
                data['status'] = status.HTTP_200_OK
                data['data'] = check_facility.values()                
                data['message'] = "Data found"
            else:
                data['status'] = status.HTTP_404_NOT_FOUND
                data['message'] = "Facility not found"
        else:
            data['status'], data['message'] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)



# def cron_job():
#     # Your code for the periodic task goes here
#     # For example, you might update a database record or send an email
#     check_organizer = User.objects.filter(is_organizer=True)
#     for i in range(len(check_organizer)):
#         get_organizer = check_organizer[i]
#         expires_time = datetime.fromisoformat(str(get_organizer.is_organizer_expires_at))
#         current_time = datetime.fromisoformat(str(datetime.now())+ "+00:00")
#         if expires_time < current_time:
#             get_organizer.is_organizer = False
#             get_organizer.is_organizer_expires_at = None
#             get_organizer.save()
#             print(f"expires_time - {expires_time} is earlier than current_time - {current_time}")
#         else:
#             print(f"{expires_time} is not earlier than {current_time}")
#     print("cron_job..............................cron_job")

# schedule.every(1).seconds.do(cron_job)

# def cron_job_wrapper():
#     while True:
#         schedule.run_pending()
#         time.sleep(55)

# # Run the cron_job_wrapper in a separate thread
# cron_thread = threading.Thread(target=cron_job_wrapper)
# cron_thread.daemon = True
# cron_thread.start()

# # This part will only be executed when using the development server.
# if __name__ == "__main__":
#     # Start the development server
#     from django.core.management import execute_from_command_line
#     execute_from_command_line(["manage.py", "runserver"])

@api_view(('POST',))
def ambassador_post_like_dislike(request):
    """
    Is used for user to like or unlike a post.
    """
    try:
        data = {}
        user_uuid = request.data.get("user_uuid")
        user_secret_key = request.data.get("user_secret_key")
        post_uuid = request.data.get("post_uuid")
        post_secret_key = request.data.get("post_secret_key")
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            check_post = AmbassadorsPost.objects.filter(uuid=post_uuid, secret_key=post_secret_key)
            if check_post.exists():
                get_post = check_post.first()
                if get_user in get_post.likes.all():
                    get_post.likes.remove(get_user)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Successfully disliked the post."
                else:
                    get_post.likes.add(get_user)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Successfully liked the post."
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"Post not found."
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


@api_view(('GET',))
def chech_post_liked_or_not(request):
    """
    Fetches the details if a user has liked a post or not.
    """
    try:
        data = {}
        user_uuid = request.GET.get("user_uuid")
        user_secret_key = request.GET.get("user_secret_key")
        post_id = request.GET.get("post_id")
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            check_post = AmbassadorsPost.objects.filter(id=post_id)
            if check_post.exists():
                get_post = check_post.first()
                total_likes = get_post.likes.all().count()
                liked_status = False
                if get_user in get_post.likes.all():
                    liked_status = True
                    data["status"], data["message"], data["liked_status"], data["total_likes"] = status.HTTP_200_OK, "", liked_status, total_likes
                else:
                    data["status"], data["message"], data["liked_status"], data["total_likes"] = status.HTTP_200_OK, "", liked_status, total_likes
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"Post not found."
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)



@api_view(("GET",))
def filtered_product_list(request):
    try:
        data = {"status":"","message":"", "data":[]}
        user_uuid = request.GET.get("user_uuid")
        user_secret_key = request.GET.get("user_secret_key")
        size = request.GET.get("size")
        min_price = request.GET.get("min_price")
        max_price = request.GET.get("max_price")
        category = request.GET.get("category")
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            all_products = MerchandiseStoreProduct.objects.all()
            if size:
                all_products = all_products.filter(size__contains=[size])
            if min_price and max_price:
                all_products = all_products.filter(Q(price__gte=min_price) & Q(price__lte=max_price))
            if category:
                all_products = all_products.filter(category__name=category)
            products = list(all_products.values())
            paginator = PageNumberPagination()
            paginator.page_size = 10  # Set the page size to 20
            products_data = paginator.paginate_queryset(products, request)
            paginated_response = paginator.get_paginated_response(products_data)
            data["status"] = status.HTTP_200_OK
            data["count"] = paginated_response.data["count"]
            data["previous"] = paginated_response.data["previous"]
            data["next"] = paginated_response.data["next"]
            data["data"] = paginated_response.data["results"]
            data["message"] = "Products are fetched successfully."

        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


from django.db.models import Min, Max
@api_view(['GET'])
def category_details(request):
    data = {"status": "", "message": "", "data": []}
    try:
        all_categories = MerchandiseStoreCategory.objects.all()
        
        categories_list = []
        for category in all_categories:
            category_products = MerchandiseStoreProduct.objects.filter(category=category)
            
            # Get minimum and maximum price
            price_range = category_products.aggregate(
                min_price=Min('price'),
                max_price=Max('price')
            )
            
            details = {
                "id": category.id, 
                "name": category.name, 
                "size": category.size, 
                "min_price": price_range['min_price'],
                "max_price": price_range['max_price']
            }
            categories_list.append(details)
        
        data["status"] = status.HTTP_200_OK
        data["data"] = categories_list
        data["message"] = "Category details fetched successfully."
            
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = str(e)

    return Response(data)
