APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"
from datetime import timedelta
from django.shortcuts import get_object_or_404
import requests
import json
from decimal import Decimal
import datetime
from django.utils.timezone import now
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Transaction, Subscription, SubscriptionPlan, User


def create_permition_user(data):
    # Sort plans by price (convert to float for correct numerical sorting)
    plans = sorted(data, key=lambda x: float(x['price']))

    # Initialize a dictionary to store feature names and their lowest plan
    feature_plan_map = {}
    current_plan = None
    # Iterate through each plan
    for plan in plans:
        plan_name = plan['product_id']
        if plan["is_active"] == True:
            current_plan = plan
        # Iterate through each feature in the plan
        for feature in plan['features']:
            feature_name = feature['name']
            # Only consider features where is_show is True
            if feature['is_show']:
                # If feature not in map, update it
                if feature_name not in feature_plan_map:
                    feature_plan_map[feature_name] = plan_name

    # Convert to list of objects, including is_access based on plan's is_active
    if current_plan:
        feature_name_list = [fe["name"] for fe in current_plan["features"] if fe["is_show"] in ["True", True, "true"]]
    result = [
        {
            "name": name,
            "lowest_plan": plan,
            "is_access": name in feature_name_list
        }
        for name, plan in sorted(feature_plan_map.items())
    ]
    
    return result

def user_subscription_data(user_uuid, platform):
    try:
        user = get_object_or_404(User, uuid=user_uuid)
        
        if not platform or platform not in ['google', 'apple']:
            return Response({"error": "Invalid or missing platform (ios/android)"}, status=400)
        
        # Fetch all plans for the platform
        plans = SubscriptionPlan.objects.filter(platform=platform).order_by("id").values(
            "id", "name", "price", "description", "duration_days", "product_id", "features"
        )
        
        if not plans.exists():
            return Response({"error": f"No subscription plans found for platform: {platform}"}, status=404)
        
        plan_list = []
        active_subscription = Subscription.objects.filter(user=user, end_date__gte=now()).last()
        
        if active_subscription:
            plan_name = active_subscription.plan.name
            plan_id_list = list(SubscriptionPlan.objects.filter(name=plan_name).values_list("product_id", flat=True))
            current = False
            for plan in plans:
                plan["price"] = str(plan["price"])
                is_active = plan["product_id"] in plan_id_list
                is_desable = not current
                expire_on = active_subscription.end_date if is_active and not current else None
                if is_active and not current:
                    current = True
                if expire_on:
                    expire_on = str(expire_on)
                plan_list.append({
                    **plan,
                    "is_desable": is_desable,
                    "is_active": is_active,
                    "expire_on": expire_on,
                })
        else:
            default_plan_id = "PICKLEIT"
            for plan in plans:
                plan["price"] = str(plan["price"])
                is_active = default_plan_id == plan["product_id"]
                is_desable = default_plan_id == plan["product_id"]
                expire_on = None
                plan_list.append({
                    **plan,
                    "is_desable": is_desable,
                    "is_active": is_active,
                    "expire_on": expire_on,
                })
        
        return plan_list
    except Exception as e:
        print(f"Error in user_subscription_data: {e}")
        return []

@api_view(["GET"])
def get_user_subcription_permition(request):
    # try:
    platform = request.GET.get("platform")
    user_uuid = request.GET.get("user_uuid")
    
    if not user_uuid:
        return Response({"error": "Missing user_uuid"}, status=400)
    
    result = user_subscription_data(user_uuid, platform)
    if isinstance(result, Response):
        return result  # Propagate error responses from user_subscription_data
    
    if not result:
        return Response({"message": "Something is wrong", "data": []}, status=200)
    
    final_result = create_permition_user(result)
    return Response(final_result, status=200)
    # except Exception as e:
    #     print(f"Error in get_user_subcription_permition: {e}")
    #     return Response({"error": str(e)}, status=500)




@api_view(['POST'])
def validate_iap(request):
    """
    Validates an Apple or Google IAP receipt and activates the subscription.
    """
    user = get_object_or_404(User, uuid=request.data.get("user_uuid"))
    receipt_data = request.data.get("receipt_data")
    platform = request.data.get("platform")  # 'apple' or 'google'
    product_id = request.data.get("product_id")
    
    if not receipt_data or not platform:
        return Response({"error": "Missing required fields"}, status=400)

    try:
        plan = SubscriptionPlan.objects.get(product_id=product_id, platform=platform)
    except SubscriptionPlan.DoesNotExist:
        return Response({"error": "Invalid product ID"}, status=400)

    # if platform == 'apple':
    #     APPLE_URL = APPLE_SANDBOX_URL  # Change to APPLE_PRODUCTION_URL in live mode
    #     response = requests.post(APPLE_URL, json={"receipt-data": receipt_data})
    #     response_data = response.json()

    #     if response_data.get("status") == 0:  # Valid receipt
    #         transaction_id = response_data.get("latest_receipt_info", [{}])[0].get("transaction_id")
    #     else:
    #         return Response({"error": "Invalid Apple receipt"}, status=400)

    # elif platform == 'google':
    #     # Validate Google receipt (Requires Google Play API)
    #     transaction_id = request.data.get("transaction_id")
    
    # else:
    #     return Response({"error": "Invalid platform"}, status=400)

    # Create a Transaction
    Transaction.objects.create(
        user=user,
        plan=plan,
        transaction_id=None,
        receipt_data=receipt_data,
        platform=platform,
        status="success",
    )

    # Activate Subscription
    from django.utils import timezone
    from datetime import timedelta
    end_date = timezone.now() + timedelta(days=plan.duration_days)
    check_plan = Subscription.objects.filter(user=user, plan=plan)
    if check_plan:
        get_plan = check_plan.first()
        get_plan.end_date = end_date
        get_plan.save()
    else:
        Subscription.objects.create(user=user, plan=plan, end_date=end_date)

    return Response({"message": "Subscription activated successfully!"}, status=200)

@api_view(['GET'])
def get_subscription_plans(request):
    
    """
    Returns all subscription plans, marking the free plan as active if the user has no subscription.
    """
    platform = request.GET.get("platform")  # 'google', 'apple'
    user_uuid = request.GET.get("user_uuid")

    result = user_subscription_data(user_uuid, platform)
    return Response(result, status=200)

@api_view(['GET'])
def get_next_plans(request):
    """
    Returns the next subscription plan after the current active plan.
    If the user has no active subscription, marks the free plan as current.
    """
    platform = request.GET.get("platform")  # 'google', 'apple'
    user_uuid = request.GET.get("user_uuid")

    if not platform or platform not in ['google', 'apple']:
        return Response({"error": "Invalid or missing platform (google/apple)"}, status=400)
    if not user_uuid:
        return Response({"error": "Missing user_uuid"}, status=400)

    user = get_object_or_404(User, uuid=user_uuid)

    # Fetch all plans for the platform
    plans = list(SubscriptionPlan.objects.filter(platform=platform)
                 .order_by("id")
                 .values("id", "name", "price", "description", "duration_days", "product_id", "features"))

    # Get the user's latest active subscription
    active_subscription = Subscription.objects.filter(user=user, end_date__gte=now()).order_by('-end_date')


    
    if active_subscription:
        current_product_id_list = list(SubscriptionPlan.objects.filter(name=active_subscription.last().plan.name).values_list("product_id", flat=True))
    else:
        current_product_id_list = ["PICKLEIT"]

    result = {
        "name": None,
        "product_id": None,
        "current_plan": None,
        "current_plan_id": None
    }

    found_current = False
    for plan in plans:
        if found_current:
            result["name"] = plan["name"]
            result["product_id"] = plan["product_id"]
            break
        if plan["product_id"] in  current_product_id_list:
            result["current_plan"] = plan["name"]
            result["current_plan_id"] = plan["product_id"]
            found_current = True

    return Response(result, status=200)



