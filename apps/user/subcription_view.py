APPLE_SANDBOX_URL = "https://sandbox.itunes.apple.com/verifyReceipt"
APPLE_PRODUCTION_URL = "https://buy.itunes.apple.com/verifyReceipt"
from datetime import timedelta
from django.shortcuts import get_object_or_404
import requests
from django.utils.timezone import now
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Transaction, Subscription, SubscriptionPlan, User
from datetime import datetime

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

    if platform == 'apple':
        APPLE_URL = APPLE_SANDBOX_URL  # Change to APPLE_PRODUCTION_URL in live mode
        response = requests.post(APPLE_URL, json={"receipt-data": receipt_data})
        response_data = response.json()

        if response_data.get("status") == 0:  # Valid receipt
            transaction_id = response_data.get("latest_receipt_info", [{}])[0].get("transaction_id")
        else:
            return Response({"error": "Invalid Apple receipt"}, status=400)

    elif platform == 'google':
        # Validate Google receipt (Requires Google Play API)
        transaction_id = request.data.get("transaction_id")
    
    else:
        return Response({"error": "Invalid platform"}, status=400)

    # Create a Transaction
    Transaction.objects.create(
        user=user,
        plan=plan,
        transaction_id=transaction_id,
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
    print("call")
    """
    Returns all subscription plans, marking the free plan as active if the user has no subscription.
    """
    platform = request.GET.get("platform")  # 'google', 'apple'
    user = get_object_or_404(User, uuid=request.GET.get("user_uuid"))

    if not platform or platform not in ['google', 'apple']:
        return Response({"error": "Invalid or missing platform (ios/android)"}, status=400)

    # Fetch all plans (including free) for the requested platform
    plans = SubscriptionPlan.objects.filter(platform=platform).values(
        "id", "name", "price", "description", "duration_days", "product_id", "features"
    )
    print(plans)
    # Check if the user has an active subscription
    active_subscription = Subscription.objects.filter(user=user, end_date__gte=now()).first()

    # Prepare the response data
    plan_list = []
    for plan in plans:
        is_active = active_subscription and active_subscription.plan.id == plan["id"]
        expire_on = active_subscription.end_date if is_active else None
        plan_list.append({
            **plan,
            "is_active": is_active,
            "expire_on": expire_on,
        })

    # If no active subscription, activate the free plan
    if not active_subscription:
        free_plan = SubscriptionPlan.objects.filter(name="Free", platform=platform).first()
        if free_plan:
            plan_list.append({
                "id": free_plan.id,
                "name": free_plan.name,
                "price": free_plan.price,
                "description": free_plan.description,
                "duration_days": free_plan.duration_days,
                "product_id": free_plan.product_id,
                "features": free_plan.features,
                "is_active": True,
                "expire_on": None,
            })

    return Response(plan_list, status=200)