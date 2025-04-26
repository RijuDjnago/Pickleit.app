from django.urls import path
from . import views

app_name = "user_side"

urlpatterns = [
    path('', views.user_login, name="user_login"),
    path('logout_view_user', views.logout_view_user, name="logout_view_user"),
    path('signup/', views.user_signup, name="user_signup"),
    path('index/', views.index, name="user_index"),
    path('profile/', views.profile, name="user_profile"),
    path('edit_profile/', views.edit_profile, name="edit_profile"),
    path('find_team_list/', views.find_team_list, name="find_team_list"),
    path('find_my_team_list/', views.find_my_team_list, name="find_my_team_list"),
    path('create_team_user_side/', views.create_team_user_side, name='create_team_user_side'),
    path('search_players_user_side/', views.search_players_user_side, name='search_players_user_side'),
    
    
    path('team_view_user/<int:team_id>/', views.team_view_user, name="team_view_user"),
    path('event/', views.event, name="event_user"),
    path('event_view/<int:event_id>/', views.event_view, name="event_view"),
    path('join_team_event/<int:event_id>/', views.join_team_event, name="join_team_event"),

    path("confirm-payment/", views.confirm_payment, name="confirm_payment"),
    path("initiate-stripe-payment/", views.initiate_stripe_payment, name="initiate_stripe_payment"),
    path('stripe_success/<int:event_id>/<str:team_ids>/<str:checkout_session_id>/', views.stripe_success, name='stripe_success'),

    path('match_history/', views.match_history, name="match_history_user"),
    path('update_match_score/', views.update_match_score, name="update_match_score"),

    path('user_wallet/', views.user_wallet, name="user_wallet"),
    path("add-fund/", views.add_fund, name="add_fund"),
    path("create-checkout-session/", views.create_checkout_session, name="create_checkout_session"),
    path('payment-success/', views.payment_success, name="payment-success"),
    path('payment-failed/', views.payment_failed, name="payment-failed"),
    path("stripe-webhook/", views.stripe_webhook, name="stripe_webhook"),

    path('edit_team/<int:team_id>/', views.edit_team, name="edit_team"),
    path('start_tournament/<int:event_id>/', views.start_tournament, name='start_tournament'),
    path('edit_event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('search_teams/', views.search_teams, name='search_teams'),
    path('search_organizers/', views.search_organizers, name='search_organizers'),
    path('search_players/', views.search_players, name='search_players'),

    path('ad_list/', views.ad_list, name="ad_list"),
    path('my_ad_list/', views.my_ad_list, name="my_ad_list"),
    path('add_advertisement/', views.create_advertisement, name="add_advertisement"),
    path('get_ad_rate/', views.get_ad_rate, name='get_ad_rate'),
    path('confirm_payment_for_advertisement/', views.confirm_payment_for_advertisement, name='confirm_payment_for_advertisement'),
    path('initiate_stripe_payment_for_advertisement/', views.initiate_stripe_payment_for_advertisement, name='initiate_stripe_payment_for_advertisement'),
    path('stripe_success_for_advertisement/<str:my_data>/<str:checkout_session_id>/', views.stripe_success_for_advertisement, name='stripe_success_for_advertisement'),

    path('all_club_list/', views.all_club_list, name='all_club_list'),
    path('fetch_google_clubs/', views.fetch_google_clubs, name='fetch_google_clubs'),
    path('club_view/<int:pk>/', views.club_view, name='club_view'),
    path('my_club_list/', views.my_club_list, name='my_club_list'),
    path('add_my_club', views.add_my_club, name='add_my_club'),
    path('add_my_club_package/', views.add_my_club_package, name="add_my_club_package"),
    path("add-review/", views.add_review, name="add_review"),
    path("load-more-reviews/<int:club_id>/", views.load_more_reviews, name="load_more_reviews"),
    path('get_wallet_balance_and_amount_to_pay/', views.get_wallet_balance_and_amount_to_pay, name='get_wallet_balance_and_amount_to_pay'),
    path('confirm_payment_for_book_club/', views.confirm_payment_for_book_club, name='confirm_payment_for_book_club'),
    path('initiate_stripe_payment_for_booking_club/', views.initiate_stripe_payment_for_booking_club, name='initiate_stripe_payment_for_booking_club'),
    path('stripe_success_for_booking_club/<str:stripe_fees>/<str:my_data>/<str:checkout_session_id>/', views.stripe_success_for_booking_club, name='stripe_success_for_booking_club'),

    path('booking_list/<int:club_id>/', views.booking_list, name='booking_list'),
    path('joined_list/<int:club_id>/', views.joined_list, name='joined_list'),

    path('confirm_payment_for_join_club/', views.confirm_payment_for_join_club, name='confirm_payment_for_join_club'),
    path('initiate_stripe_payment_for_join_club/', views.initiate_stripe_payment_for_join_club, name='initiate_stripe_payment_for_join_club'),
    path('stripe_success_for_join_club/<str:stripe_fees>/<str:my_data>/<str:checkout_session_id>/', views.stripe_success_for_join_club, name='stripe_success_for_join_club'),

    path('all_court_list/', views.all_court_list, name='all_court_list'),
    path('my_court_list/', views.my_court_list, name='my_court_list'),
    path('fetch_pickleball_courts/', views.fetch_pickleball_courts, name='fetch_pickleball_courts'),
    path('court_view/<int:pk>', views.court_view, name='court_view'),
    path('add_my_court/', views.add_my_court, name='add_my_court'),

    path('read_notifications/', views.read_notifications, name='read_notifications'),
]

