from decimal import Decimal
from pyexpat.errors import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout
from django.urls import reverse
import stripe
from apps.team.models import *
from apps.user.models import AllPaymentsTable, User, Wallet, Transaction, WalletTransaction
from apps.socialfeed.models import socialFeed, FeedFile
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timezone, datetime
from django.views.decorators.csrf import csrf_exempt
from apps.clubs.models import *
from apps.courts.models import *
from django.conf import settings
from geopy.distance import geodesic
from apps.user.helpers import *
from apps.team.views import notify_edited_player, check_add_player
from decimal import Decimal, ROUND_DOWN
from django.utils.timezone import make_aware
import base64
import requests
import json
from apps.chat.models import NotificationBox

stripe.api_key = settings.STRIPE_SECRET_KEY
protocol = settings.PROTOCALL

def get_lat_long_google(api_key, location):
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"
    
    # Prepare the request parameters
    params = {
        "address": location,
        "key": api_key
    }

    # Make the request
    response = requests.get(base_url, params=params)
    data = response.json()

    # Extract latitude and longitude
    if data["status"] == "OK":
        lat = data["results"][0]["geometry"]["location"]["lat"]
        lng = data["results"][0]["geometry"]["location"]["lng"]
        return lat, lng
    else:
        return None


### modified
def user_login(request):
    context = {}
    if request.method == "POST":
        username = request.POST.get("email", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            context['message'] = "Email and password are required!"
            return render(request, "auth/login.html", context)

        user = authenticate(request, username=username, password=password)

        if user is None:
            context['message'] = "Invalid credentials!"
        elif user.is_superuser:
            context['message'] = "You are not authorized to log in here!"
        else:
            auth_login(request, user)
            return redirect('user_side:user_index')

    return render(request, "auth/login.html", context)


@login_required(login_url="/user_side/")
def logout_view_user(request):
    logout(request)
    return redirect('user_side:user_login')


def user_signup(request):
    return render(request, 'auth/signup.html')


@login_required(login_url="/user_side/")
def profile(request):  
    player = Player.objects.filter(player=request.user).first()

    if not player:  
        return render(request, 'sides/profile.html', {"user_details": request.user, "player": None})

    teams = player.team.all()
    match_history = Tournament.objects.filter(Q(team1__in=teams) | Q(team2__in=teams)).order_by("-id")

    match_history_cal = match_history.values_list("winner_team", flat=True)

    wins = sum(1 for winner_team in match_history_cal if winner_team in teams)
    losses = match_history.count() - wins

    context = {
        "user_details": request.user,
        "player": player,
        "total_match": match_history.count(),
        "losses": losses,
        "wins": wins,
    }

    return render(request, 'sides/profile.html', context)


### modified
@login_required(login_url="/user_side/")
def edit_profile(request):
   
    print("Before form submission:", request.user, request.user.is_authenticated)  # Debugging line

    user = request.user

    if request.method == "POST":
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.phone = request.POST.get("phone", user.phone)
        user.gender = request.POST.get("gender", user.gender)
        user.rank = request.POST.get("rank", user.rank)
        user.user_birthday = request.POST.get("dob", user.user_birthday)
        user.permanent_location = request.POST.get("location", user.permanent_location)
        
        # Fixing incorrect latitude and longitude field names
        user.latitude = request.POST.get("latitude", user.latitude)
        user.longitude = request.POST.get("longitude", user.longitude)
        
        user.bio = request.POST.get("bio", user.bio)

        if 'profile_picture' in request.FILES:
            user.image = request.FILES['profile_picture']
        
        try:
            user.save()
            auth_login(request, user)  # Keep the user logged in
            print("After form submission:", request.user, request.user.is_authenticated)  # Debugging line
            return redirect('user_side:user_profile') 
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")

    context = {"user_details": user, "MAP_API_KEY" : 'AIzaSyAfBo6-cZlOpKGrD1ZYwISIGjYvhH_wPmk'}
    return render(request, 'sides/editprofile.html', context)


@login_required(login_url="/user_side/")
def index(request):
    context = {
        "user_teams_count": 0,
        "balance": 0,
        "join_event_count":0,
        "completed_event_count":0,
        "match_history":[],
        "socail_feed_list":[]
    }
    user_teams = Team.objects.filter(created_by=request.user)
    join_event = Leagues.objects.filter(registered_team__in = user_teams, is_complete=False).distinct()
    completed_event = Leagues.objects.filter(registered_team__in = user_teams, is_complete=True).distinct()
    user_teams_count = user_teams.count()
    balance = Wallet.objects.filter(user=request.user).first().balance
    join_event_count = join_event.count()
    completed_event_count = completed_event.count()
    match_history = Tournament.objects.filter(Q(team1__in=user_teams) | Q(team2__in=user_teams)).distinct()[:5]
    socail_feed_list = socialFeed.objects.all().order_by("-created_at")[:5]
    for match_ in match_history:
        match_.score = TournamentSetsResult.objects.filter(tournament=match_)
    for feed in socail_feed_list:
        images = FeedFile.objects.filter(post=feed)
        if images:
            feed.image = images.first().file.url
    context["user_teams_count"] = user_teams_count
    context["balance"] = balance
    context["join_event_count"] = join_event_count
    context["completed_event_count"] = completed_event_count
    context["match_history"] = match_history
    context["socail_feed_list"] = socail_feed_list
    return render(request, 'sides/index.html', context=context)


@login_required(login_url="/user_side/")
def find_team_list(request):
    query = request.GET.get('q', '')
    team_type_filter = request.GET.get('team_type', '')
    teams = Team.objects.all()
    
    if query:
        teams = teams.filter(name__icontains=query)
    if team_type_filter:
        teams = teams.filter(team_type=team_type_filter)
    
    for team in teams:
        team.players = Player.objects.filter(team=team).count()
    
    paginator = Paginator(teams, 10)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        teams = paginator.page(page)
    except PageNotAnInteger:
        teams = paginator.page(1)
    except EmptyPage:
        teams = paginator.page(paginator.num_pages)
    
    return render(request, 'sides/teamlist_for_user.html', {
        "teams": teams,
        "query": query,
        "team_type_filter": team_type_filter,
    })

@login_required(login_url="/user_side/")
def find_my_team_list(request):
    query = request.GET.get('q', '')
    team_type_filter = request.GET.get('team_type', '')
    
    teams = Team.objects.filter(created_by = request.user)
    
    if query:
        teams = teams.filter(name__icontains=query)
    if team_type_filter:
        teams = teams.filter(team_type=team_type_filter)
    
    for team in teams:
        team.players = Player.objects.filter(team=team).count()
    
    paginator = Paginator(teams, 10)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        teams = paginator.page(page)
    except PageNotAnInteger:
        teams = paginator.page(1)
    except EmptyPage:
        teams = paginator.page(paginator.num_pages)
    return render(request, 'sides/my_team_list.html', {
        "teams": teams,
        "query": query,
        "team_type_filter": team_type_filter,
    })


@login_required(login_url="/user_side/")
def create_team_user_side(request):
    player_details = list(Player.objects.all().values("id", "player_full_name", "player__rank", "player__image", "player__gender", "player__id"))
    context = {"players":player_details, "team_info":[], "message":"","pre_player_ids":[], "operation":"Create", "button":"Submit"}
    if request.method == "POST":
        name = request.POST.get('team_name')
        location = request.POST.get('location')
        team_person = request.POST.get('team_person')
        team_type = request.POST.get('team_type')
        team_image = request.FILES.get('team_image')
        player_ids = request.POST.get('players', '').split(',')

        if not name and not team_person and not team_type:
            # return HttpResponse("Team name, team person and team type are required.")
            context["message"] = "Team name, team person and team type are required."
            return render(request, "sides/add_team.html", context)
        
        if Team.objects.filter(name = name).exists():
            # return HttpResponse("Team name already exists")
            context["message"] = "Team name already exists."
            return render(request, "sides/add_team.html", context)

        if team_person == "Two Person Team" and len(player_ids) == 2:
            if team_type == "Men":                
                players = Player.objects.filter(id__in=player_ids)
                for player in players:
                    if not player.player.gender == "Male":
                        # return HttpResponse("Select male players only.")  
                        context["message"] = "Select male players only."
                        return render(request, "sides/add_team.html", context)                          
                
                obj = GenerateKey()
                secret_key = obj.gen_team_key()
                team = Team.objects.create(
                    name=name,
                    secret_key=secret_key,
                    team_image=team_image,
                    team_person=team_person,
                    team_type=team_type,
                    created_by_id=request.user.id,
                    location=location
                )                            
                for player in players:                    
                    player.team.add(team)
                    notify_message = f"Hey {player.player_first_name}! You have been added to an awesome team - {team.name}"
                    title = "Team Created."
                    notify_edited_player(user_id=player.player.id, titel=title, message=notify_message)
        
                return redirect(reverse('user_side:find_my_team_list'))            

            elif team_type == "Women":                
                players = Player.objects.filter(id__in=player_ids)
                for player in players:
                    if not player.player.gender == "Female":
                        # return HttpResponse("Select female players only.")  
                        context["message"] = "Select female players only."
                        return render(request, "sides/add_team.html", context)  
                    
                obj = GenerateKey()
                secret_key = obj.gen_team_key()
                team = Team.objects.create(
                    name=name,
                    secret_key=secret_key,
                    team_image=team_image,
                    team_person=team_person,
                    team_type=team_type,
                    created_by_id=request.user.id,
                    location=location
                )                        
                        
                for player in players:
                    player.team.add(team)
                    notify_message = f"Hey {player.player_first_name}! You have been added to an awesome team - {team.name}"
                    title = "Team Created."
                    notify_edited_player(user_id=player.player.id, titel=title, message=notify_message)
        
                return redirect(reverse('user_side:find_my_team_list'))
                    
            elif team_type == "Co-ed":
                players = Player.objects.filter(id__in=player_ids)
                male_player = players.filter(player__gender='Male') 
                female_player = players.filter(player__gender='Female')    
                if len(male_player) == 1 and len(female_player) == 1:                    
                    obj = GenerateKey()
                    secret_key = obj.gen_team_key()
                    team = Team.objects.create(
                        name=name,
                        secret_key=secret_key,
                        team_image=team_image,
                        team_person=team_person,
                        team_type=team_type,
                        created_by_id=request.user.id,
                        location=location
                    )                        
                   
                    players = Player.objects.filter(id__in=player_ids)
                    for player in players:
                        player.team.add(team)
                        notify_message = f"Hey {player.player_first_name}! You have been added to an awesome team - {team.name}"
                        title = "Team Created."
                        notify_edited_player(user_id=player.player.id, titel=title, message=notify_message)
            
                    return redirect(reverse('user_side:find_my_team_list'))
                else:
                    context["message"] = "Select one male player and one female player."
                    return render(request, "sides/add_team.html", context)
                
        elif team_person == "Two Person Team" and len(player_ids) != 2:
            context["message"] = "Need to select two players."
            return render(request, "sides/add_team.html", context) 
          
        elif team_person == "One Person Team" and len(player_ids) == 1:
            if team_type == "Men":                
                players = Player.objects.filter(id__in=player_ids)
                if not players.first().player.gender == "Male": 
                    context["message"] = "Select male player only."
                    return render(request, "sides/add_team.html", context)     
                    
                obj = GenerateKey()
                secret_key = obj.gen_team_key()
                team = Team.objects.create(
                    name=name,
                    secret_key=secret_key,
                    team_image=team_image,
                    team_person=team_person,
                    team_type=team_type,
                    created_by_id=request.user.id,
                    location=location
                )                                  
                for player in players:
                    player.team.add(team)
                    notify_message = f"Hey {player.player_first_name}! You have been added to an awesome team - {team.name}"
                    title = "Team Created."
                    notify_edited_player(user_id=player.player.id, titel=title, message=notify_message)
        
                return redirect(reverse('user_side:find_my_team_list'))                       

            elif team_type == "Women":
                players = Player.objects.filter(id__in=player_ids)
                if not players.first().player.gender == "Female":       
                    context["message"] = "Select female player only."
                    return render(request, "sides/add_team.html", context)
                obj = GenerateKey()
                secret_key = obj.gen_team_key()
                team = Team.objects.create(
                    name=name,
                    secret_key=secret_key,
                    team_image=team_image,
                    team_person=team_person,
                    team_type=team_type,
                    created_by_id=request.user.id,
                    location=location
                )                                    
                for player in players:
                    player.team.add(team)
                    notify_message = f"Hey {player.player_first_name}! You have been added to an awesome team - {team.name}"
                    title = "Team Created."
                    notify_edited_player(user_id=player.player.id, titel=title, message=notify_message)
        
                return redirect(reverse('user_side:find_my_team_list'))
                    
        elif team_person == "One Person Team" and len(player_ids) != 1:
            context["message"] = "Need to select only one person."
            return render(request, "sides/add_team.html.html", context)

        return redirect('user_side:find_my_team_list')  # Redirect to team list

    return render(request, 'sides/add_team.html', context)


@login_required(login_url="/user_side/")
def search_players_user_side(request):
    query = request.GET.get('query', '')
    players = Player.objects.filter(player_full_name__icontains=query)[:10]

    player_data = [{
        'id': p.id, 
        'name': p.player_full_name, 
        'image': p.player.image.url if p.player.image else None  # Get image URL if available
    } for p in players]

    return JsonResponse({'players': player_data})

@login_required(login_url="/user_side/")
def team_view_user(request, team_id):
    context = {}
    team = get_object_or_404(Team, id=team_id)
    query = request.GET.get('q', '').strip()
    
    player = Player.objects.filter(player=request.user).first()
    if not player:
        context["error"] = "Player profile not found."
        return render(request, 'sides/match_history.html', context)

    players = Player.objects.filter(team=team)
    match_history = Tournament.objects.filter(Q(team1=team) | Q(team2=team)).order_by("-id")

    wins = match_history.filter(winner_team=team).count()
    losses = match_history.count() - wins
    total_matches = match_history.count()

    if query:
        match_history = match_history.filter(
            Q(team1__name__icontains=query) |
            Q(team2__name__icontains=query) |
            Q(leagues__name__icontains=query) |
            Q(match_number__icontains=query) |
            Q(leagues__team_type__name__icontains=query)
        ).order_by("-id")

    paginator = Paginator(match_history, 21)
    page_number = request.GET.get('page')
    paginated_matches = paginator.get_page(page_number)

    # Fetch match scores
    for match in paginated_matches:
        match.scores = TournamentSetsResult.objects.filter(tournament=match)

    context.update({
        "team_details": team,
        "players": players,  
        "match_history": paginated_matches if total_matches > 0 else None,  
        "total_matches": total_matches,
        "wins": wins,
        "losses": losses,
        "query": query,  
    })
    return render(request, 'sides/team_view.html', context)

@login_required(login_url="/user_side/")
def event(request):
    query = request.GET.get('q', '')
    team_type_filter = request.GET.get('team_type', '')
    leagues = Leagues.objects.exclude(play_type = "Individual Match Play").order_by('-leagues_start_date')  # Fetch all leagues sorted by start date
    today = datetime.now()
    if team_type_filter == "all":
        pass
    elif team_type_filter == "Open":
        leagues = leagues.filter(registration_start_date__date__lte=today,registration_end_date__date__gte=today)
    elif team_type_filter == "Upcoming":
        leagues = leagues.filter(leagues_start_date__date__gte = today, is_complete=False)
    elif team_type_filter == "Ongoing":
        leagues = leagues.filter(leagues_start_date__date__lte = today, leagues_end_date__date__gte = today, is_complete=False)
    elif team_type_filter == "Past":
        leagues = leagues.filter(leagues_end_date__date__lte = today, is_complete=True)
    return render(request, 'sides/event.html', {'leagues': leagues, "team_type_filter":team_type_filter, "text":query})


@login_required(login_url="/user_side/")
def event_view(request, event_id):
    context = {}
    user = request.user
    today = datetime.now()
    event = get_object_or_404(Leagues, id=event_id)
    context["event"] = event
    context["league_type"] = LeaguesPlayType.objects.filter(league_for=event)
    context["policy"] = LeaguesCancellationPolicy.objects.filter(league=event)
    context["all_join_teams"] = event.registered_team.all()
    context["organizer"] = user == event.created_by
    # calculate total fees
    fees = event.registration_fee
    others_fees = event.others_fees
    if others_fees:
        for val in others_fees.values():
            if isinstance(val, (int, float)):  # Ensure the value is numeric
                fees += val
            elif isinstance(val, str) and val.isdigit():  # Convert string numbers
                fees += int(val)
    context["total_fees"] = fees
    ##wallet balance
    try:
        wallet = Wallet.objects.filter(user=user).first()
        balance = wallet.balance
    except:
        balance = 0
    context["balance"] = balance
    # my team
    my_team = Team.objects.filter(created_by=user)
    team_type = event.team_type
    team_person = event.team_person
    if team_type:
        my_team = my_team.filter(team_type=team_type)
    if team_person:
        my_team = my_team.filter(team_person=team_person)
    for team in my_team:
        team.players = Player.objects.filter(team=team)
    context["my_team"] = my_team
    #matches 
    matches = Tournament.objects.filter(leagues=event)
    for matche in matches:
        matche.score = TournamentSetsResult.objects.filter(tournament=matche)

    context["matches"] = matches
    team_stats = {}
    for match_ in matches:
        if match_.team1 and match_.team2:
            if match_.team1 not in team_stats:
                team_stats[match_.team1] = {"played": 0, "wins": 0, "losses": 0, "draws": 0, "points": 0}
            if match_.team2 not in team_stats:
                team_stats[match_.team2] = {"played": 0, "wins": 0, "losses": 0, "draws": 0, "points": 0}

            team_stats[match_.team1]["played"] += 1
            team_stats[match_.team2]["played"] += 1

            if match_.is_drow:  # If match is a draw
                team_stats[match_.team1]["draws"] += 1
                team_stats[match_.team2]["draws"] += 1
                team_stats[match_.team1]["points"] += 1
                team_stats[match_.team2]["points"] += 1
            elif match_.winner_team:  # If there is a winner
                team_stats[match_.winner_team]["wins"] += 1
                team_stats[match_.winner_team]["points"] += 3  # 3 points for a win
                loser_team = match_.team1 if match_.winner_team == match_.team2 else match_.team2
                team_stats[loser_team]["losses"] += 1

    
    context["is_join"] = event.registration_end_date.date() >= today.date()
    # Sort teams based on points (highest first)
    sorted_teams = sorted(team_stats.items(), key=lambda x: x[1]["points"], reverse=True)
    context["sorted_teams"] = sorted_teams
    context["groups "] = RoundRobinGroup.objects.filter(league_for=event)
    return render(request, 'sides/event_view.html', context=context)


@login_required(login_url="/user_side/")
def join_team_event(request, event_id):
    context = {"STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY}
    user = request.user
    today = datetime.now()
    event = get_object_or_404(Leagues, id=event_id)
    
    # my team
    my_team = Team.objects.filter(created_by=user)
    team_type = event.team_type
    team_person = event.team_person
    if team_type:
        my_team = my_team.filter(team_type=team_type)
    if team_person:
        my_team = my_team.filter(team_person=team_person)
    for team in my_team:
        team.players = Player.objects.filter(team=team)
    context["my_team"] = my_team
    context["event"] = event
    context["balance"] = float(Wallet.objects.filter(user=request.user).first().balance)
    fees = Decimal(float(event.registration_fee))

    others_fees = event.others_fees
    if others_fees:
        for val in others_fees.values():
            try:
                fees += Decimal(float(val))  
            except (ValueError, TypeError):
                continue  
    context["total_fees"] = float(fees)
    return render(request, 'sides/join_event.html', context=context)


@login_required(login_url="/user_side/")
def match_history(request):
    query = request.GET.get('q', '').strip()
    context = {}

    player = Player.objects.filter(player=request.user).first()
    if not player:
        context["error"] = "Player profile not found."
        return render(request, 'sides/match_history.html', context)

    teams = player.team.all()
    match_history = Tournament.objects.filter(Q(team1__in=teams) | Q(team2__in=teams)).order_by("-id")
    match_history_cal = match_history.only("team1", "team2", "winner_team")
    wins = sum(1 for match_ in match_history_cal if match_.winner_team in teams)
    losses = len(match_history_cal) - wins

    if query:
        match_history = match_history.filter(
            Q(team1__name__icontains=query) |
            Q(team2__name__icontains=query) |
            Q(leagues__name__icontains=query) |
            Q(match_number__icontains=query) |
            Q(leagues__team_type__name__icontains=query)
        ).order_by("-id")

    total_matches = match_history.count()
    # print(match_history)
    # Pagination: 21 matches per page
    paginator = Paginator(match_history, 21)
    page_number = request.GET.get('page')
    paginated_matches = paginator.get_page(page_number)

    # Process only paginated matches
    for match_ in paginated_matches:
        if match_.team1 in teams:
            match_.opponent = match_.team2
        else:
            match_.opponent = match_.team1

        match_.scores = TournamentSetsResult.objects.filter(tournament=match_)

    context.update({
        "match_history": paginated_matches,
        "total_matches": total_matches,
        "wins": wins,
        "losses": losses,
        "query": query,  # Pass query for template usage
    })

    return render(request, 'sides/match_history.html', context)


@login_required(login_url="/user_side/")
def update_match_score(request):
    query = request.GET.get('q', '').strip()
    context = {}

    player = Player.objects.filter(player=request.user).first()
    if not player:
        context["error"] = "Player profile not found."
        return render(request, 'sides/update_score.html', context)

    teams = player.team.all()
    current_eventlist = Leagues.objects.filter(registered_team__in = teams, is_complete=False).distinct().only("id", "name", "team_type", "image")
    if query:
        current_eventlist = current_eventlist.filter(Q(name__icontence = query), Q(team_type__name__icontence = query))
    context["events"] = current_eventlist
    return render(request, 'sides/update_score.html', context)


#modified
@login_required(login_url="/user_side/")
def user_wallet(request):
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)
    page = request.GET.get("page", 1)  # Get the current page number from request
    
    wallet = Wallet.objects.filter(user=request.user)
    
    balance = 0.0
    transactions = WalletTransaction.objects.filter(Q(sender=request.user) | Q(reciver=request.user)).order_by("-created_at")
    if start_date and end_date:
        transactions = transactions.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    
    paginator = Paginator(transactions, 10)  
    transactions_page = paginator.get_page(page)  

    if wallet.exists():
        balance = wallet.first().balance

    return render(
        request,
        "sides/wallet.html",
        {
            "wallet_balance": balance,
            "transactions": transactions_page, 
        },
    )


@login_required(login_url="/user_side/")
def add_fund(request):
    return render(request, "sides/add_fund.html", {"STRIPE_PUBLIC_KEY": settings.STRIPE_PUBLIC_KEY})


@csrf_exempt
def create_checkout_session(request):
    """ Creates a Stripe Checkout session """
    if request.method == "POST":
        amount = int(request.POST.get("amount")) * 100  # Convert to cents
        user = request.user
        stripe.api_key = settings.STRIPE_SECRET_KEY 
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Add Funds"},
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=settings.SITE_URL + "/payment-success/?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=settings.SITE_URL + "/payment-failed/",
            )

            # Save to AllPaymentsTable with Pending Status
            AllPaymentsTable.objects.create(
                user=user,
                amount=amount / 100,  # Convert from cents to dollars
                checkout_session_id=session.id,
                payment_for="AddMoney",
                status="Pending",
            )

            return JsonResponse({"id": session.id})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    """ Handles Stripe Webhook for successful payments """
    payload = request.body
    sig_header = request.headers.get("Stripe-Signature")
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user = AllPaymentsTable.objects.filter(checkout_session_id=session["id"]).first().user
        amount = session["amount_total"] / 100  # Convert from cents to dollars

        # Update Payment Status
        payment = AllPaymentsTable.objects.get(checkout_session_id=session["id"])
        payment.status = "Completed"
        payment.payment_mode = "Card"
        payment.json_response = session
        payment.save()

        # Create Wallet Transaction
        WalletTransaction.objects.create(
            sender=user,
            transaction_type="credit",
            transaction_for="AddMoney",
            amount=amount,
            payment_id=session["id"],
            json_response=session
        )

    return HttpResponse(status=200)


@login_required(login_url="/user_side/")
def payment_success(request):
    session_id = request.GET.get("session_id")

    if not session_id:
        return render(request, "payments/payment_failed.html", {"error": "Invalid session ID."})

    stripe.api_key = settings.STRIPE_SECRET_KEY

    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # Ensure payment is completed
        if session.payment_status == "paid":
            user = request.user
            amount = session.amount_total / 100  # Convert cents to dollars
            
            wallet = Wallet.objects.filter(user=user).first()
            wallet.balance += Decimal(str(amount))  # Convert float to Decimal
            wallet.save()
           
            # Store payment record
            payment = AllPaymentsTable.objects.create(
                user=user,
                amount=amount,
                checkout_session_id=session.id,
                payment_for="Wallet Recharge",
                payment_mode="Stripe",
                json_response=session,
                status="Completed"
            )

            # Add to Wallet Transaction
            WalletTransaction.objects.create(
                sender=user,
                transaction_type="credit",
                transaction_for="AddMoney",
                amount=amount,
                payment_id=session.id,
                json_response=session,
                description=f"${amount} is added to your PickleIt wallet."
            )

            return render(request, "payments/payment_success.html", {"amount": amount})
        else:
            return render(request, "payments/payment_failed.html", {"error": "Payment not completed."})

    except stripe.error.StripeError as e:
        return render(request, "payments/payment_failed.html", {"error": str(e)})

def payment_failed(request):
    return render(request, "payments/payment_failed.html", {"error": "Your payment was unsuccessful."})


############piu

###payment for team join
@csrf_exempt
def confirm_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        event_id = data.get("event_id")
        team_ids = data.get("team_id_list", [])
        total_amount = float(data.get("total_amount", 0))
        print(data)

        user = request.user
        event = Leagues.objects.get(id=event_id)
        wallet = Wallet.objects.get(user=user)

        if float(wallet.balance) >= total_amount:
            organizer_amount = (Decimal(total_amount) * Decimal(settings.ORGANIZER_PERCENTAGE)) / Decimal(100)
            admin_amount = (Decimal(total_amount) * Decimal(settings.ADMIN_PERCENTAGE)) / Decimal(100)

            WalletTransaction.objects.create(
                sender=request.user,
                reciver=event.created_by,                        
                admin_cost=admin_amount.quantize(Decimal('0.001'), rounding=ROUND_DOWN),
                reciver_cost=organizer_amount.quantize(Decimal('0.001'), rounding=ROUND_DOWN),
                getway_charge=Decimal(0),                        
                transaction_for="TeamRegistration",                                   
                transaction_type="debit",
                amount=Decimal(total_amount).quantize(Decimal('0.001'), rounding=ROUND_DOWN),
                payment_id=None, 
                description=f"${total_amount} is debited from your PickleIt wallet for registering teams to league {event.name}."
            )

            # ✅ Update admin wallet
            admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
            if admin_wallet:
                admin_wallet.balance = Decimal(admin_wallet.balance + admin_amount)
                admin_wallet.save()

            # ✅ Deduct from user wallet
            wallet.balance = Decimal(float(wallet.balance) - total_amount)
            wallet.save()
            
            # ✅ Update organizer wallet
            organizer_wallet = Wallet.objects.filter(user=event.created_by).first()
            if organizer_wallet:
                organizer_wallet.balance = Decimal(str(organizer_wallet.balance)) + organizer_amount
                organizer_wallet.save()

            for team_id in team_ids:
                team = Team.objects.get(id=team_id)
                event.registered_team.add(team)

            return JsonResponse({"success": True, "message": "Teams joined successfully!"})
        else:
            return JsonResponse({"success": False, "message": "Insufficient balance."})

    return JsonResponse({"success": False, "message": "Invalid request."})


@csrf_exempt
def initiate_stripe_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            print("Received Data:", data)
            event_id = data.get("event_id")
            team_ids = data.get("team_id_list", [])
            total_amount = data.get("total_amount", 0)

            try:
                total_amount = float(total_amount)  # Convert from string to float
            except ValueError:
                print("Error: Invalid total_amount format:", total_amount)
                return JsonResponse({"success": False, "message": "Invalid total amount format."})

            unit_amount = int(total_amount * 100)  # Convert to cents

            if unit_amount <= 0:
                print("Error: Amount cannot be zero or negative:", unit_amount)
                return JsonResponse({"success": False, "message": "Amount cannot be zero or negative."})

            print("Final Amounts:", total_amount, unit_amount)

            # Create Stripe session
            host = request.get_host()
            current_site = f"{protocol}://{host}"
            main_url = f"{current_site}/user_side/stripe_success/{event_id}/{'-'.join(team_ids)}/"
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Event Registration"},
                        "unit_amount": unit_amount,  # Must be an integer
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{main_url}{{CHECKOUT_SESSION_ID}}/",
                cancel_url=request.build_absolute_uri(reverse("user_side:event_view", args=[event_id])),
            )

            print("Session Created:", session)
            return JsonResponse({"success": True, "payment_url": session.url, "session_id": session.id})

        except Exception as e:
            print("Stripe Error:", str(e))
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request."})


def stripe_success(request, event_id, team_ids, checkout_session_id):
    
    try:
        # Fetch session details from Stripe
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        
        total_amount = Decimal(session.amount_total) / 100  # Convert cents to dollars
        print(total_amount)
        payment_status = session.get("payment_status") == "paid"
        payment_method_types = session.get("payment_method_types", [])

        if not payment_status:
            return JsonResponse({"success": False, "message": "Payment not completed."})

        user = request.user
        wallet = Wallet.objects.get(user=user)
        event = Leagues.objects.get(id=event_id)
        team_ids = team_ids.split('-')

        
        wallet.balance = Decimal(wallet.balance) + total_amount  
        wallet.balance -= total_amount  
        wallet.save()

        AllPaymentsTable.objects.create(
            user=user,
            amount=total_amount,
            checkout_session_id=checkout_session_id,
            payment_mode=", ".join(payment_method_types),
            payment_for=f"Registering {len(team_ids)} Team(s) in {event.name}",
            status="Completed"
        )
        fees = float(event.registration_fee)

        others_fees = event.others_fees
        if others_fees:
            for val in others_fees.values():
                try:
                    fees += float(val) 
                except (ValueError, TypeError):
                    continue  
        total_amount = fees * len(team_ids)
        organizer_amount = round((Decimal(total_amount) * Decimal(settings.ORGANIZER_PERCENTAGE)) / 100, 2)
        admin_amount = round((Decimal(total_amount) * Decimal(settings.ADMIN_PERCENTAGE)) / 100, 2)

        WalletTransaction.objects.create(
            sender=user,
            reciver=event.created_by,
            admin_cost=admin_amount,
            reciver_cost=organizer_amount,
            getway_charge=Decimal(0),
            transaction_for="TeamRegistration",
            transaction_type="debit",
            amount=Decimal(total_amount),
            payment_id=checkout_session_id,
            description=f"${total_amount} is debited from your PickleIt wallet for registering teams in event {event.name}."
        )
        for team_id in team_ids:
            team = Team.objects.get(id=team_id)
            event.registered_team.add(team)

        return redirect("user_side:event_view", event_id=event_id)

    except stripe.error.StripeError as e:
        return JsonResponse({"success": False, "message": f"Stripe error: {str(e)}"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


def edit_team(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    players = list(Player.objects.filter(team=team).values("id", "player_full_name", "player__rank", "player__image", "player__gender", "player__id"))
    pre_player_ids = list(Player.objects.filter(team__id=team_id).values_list("id", flat=True))
    context = {"players":players, "team":team, "message":"","pre_player_ids":pre_player_ids, "oppration":"Edit", "button":"Submit"}
    
    if request.method == "POST":
        team_name = request.POST.get('team_name')
        team_image = request.FILES.get('team_image')
        team_person = request.POST.get('team_person')
        team_type = request.POST.get('team_type')
        player_ids = request.POST.getlist('selected_players')  
        if not team_name and not team_person and not team_type:
            # return HttpResponse("Team name, team person and team type are required.")
            context["message"] = "Team name, team person and team type are required."
            return render(request, "sides/edit_team.html", context)
        
        # Update team information
        team.name = team_name
        if team_image:
            team.team_image = team_image
        team.team_person = team_person
        team.team_type = team_type
        team.save()
        
        # Update players associated with the team
        if team_person == "Two Person Team":
            if len(player_ids) != 2:
                context["message"] = "Need to select two players."
                return render(request, "sides/edit_team.html", context)
        elif team_person == "One Person Team":
            if len(player_ids) != 1:
                context["message"] = "Need to select only one player."
                return render(request, "sides/edit_team.html", context)
        
        removed_players = []
        new_players = []
        if team_type == "Men" or team_type == "Women":
            players = Player.objects.filter(id__in=player_ids)
            
            for player_id in pre_player_ids:
                pre_player = Player.objects.get(id=player_id)
                removed_players.append(player_id) 
                pre_player.team.remove(team)
            for player in players:
                new_players.append(player.id)
                player.team.add(team)
            team.save()
            add, rem = check_add_player(new_players, removed_players)
                
            titel = "Team Membership Modification"
            for r in rem:
                message = f"You have been removed from team {team.name}"
                user_id = Player.objects.filter(id=r).first().player.id
                notify_edited_player(user_id, titel, message)

            titel = "Team Membership Modification"
            for r in add:
                message = f"You have been added to team {team.name}"
                user_id = Player.objects.filter(id=r).first().player.id
                notify_edited_player(user_id, titel, message)

            return redirect(reverse('user_side:find_my_team_list'))
                              
        elif team_type == "Co-ed":
            players = Player.objects.filter(id__in=player_ids)
            male_player = players.filter(player__gender='Male') 
            female_player = players.filter(player__gender='Female')    
            if len(male_player) == 1 and len(female_player) == 1:
                for player_id in pre_player_ids:
                    pre_player = Player.objects.get(id=player_id)
                    removed_players.append(player_id) 
                    pre_player.team.remove(team)
                for player in players:                            
                    new_players.append(player.id)
                    player.team.add(team)
                team.save()
                add, rem = check_add_player(new_players, removed_players)
                
                titel = "Team Membership Modification"
                for r in rem:
                    message = f"You have been removed from team {team.name}"
                    user_id = Player.objects.filter(id=r).first().player.id
                    notify_edited_player(user_id, titel, message)

                titel = "Team Membership Modification"
                for r in add:
                    message = f"You have been added to team {team.name}"
                    user_id = Player.objects.filter(id=r).first().player.id
                    notify_edited_player(user_id, titel, message)
                return redirect(reverse('user_side:find_my_team_list'))
            else:
                context["message"] = "Select one male player and one female player."
                return render(request, "sides/edit_team.html", context)    
                         
        else:
            context["message"] = "Something is Wrong"
    return render(request, "sides/edit_team.html", context)


def search_players(request):
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()  # Get category from request

    if query:
        players = Player.objects.filter(Q(player__first_name__icontains=query) | Q(player__last_name__icontains=query) | Q(player__username__icontains=query))
        print(players)
        if category: 
            if category == "Women":
                players = players.filter(player__gender="Female")
            elif category == "Men":
                players = players.filter(player__gender="Male")
            else:
                players = players
            print(players)

        player_data = [
            {
                "id": player.id,
                "name": player.player_full_name,
                "image": player.player.image.url if player.player.image else "/static/default-avatar.png"
            }
            for player in players
        ]
        print(players)
        return JsonResponse({"players": player_data})

    return JsonResponse({"players": []})


@login_required(login_url="/user_side/")
def start_tournament(request, event_id):
    check_tour = Leagues.objects.filter(id=event_id).first()
    tour_create_by = check_tour.created_by
    max_no_teams = check_tour.max_number_team
    registered_teams = check_tour.registered_team.count()
    if registered_teams != max_no_teams:
        check_tour.max_number_team = registered_teams
        check_tour.save()

    host = request.get_host()
    current_site = f"{protocol}://{host}"
    url = f"{current_site}/team/22fef865dab2109505b61d85df50c5126e24f0c0a10990f2670c179fb841bfd2/"
    # print(url)
    payload = {
        'user_uuid': str(tour_create_by.uuid),
        'user_secret_key': str(tour_create_by.secret_key),
        'league_uuid': str(check_tour.uuid),
        'league_secret_key': str(check_tour.secret_key)
    }
    response = requests.post(url, json=payload)
    # print(response)
    return redirect('user_side:event_view', event_id=event_id)


def check_data_structure(data_structure):
    for item in data_structure:
        if item["number_of_courts"] != 0 or item["sets"] != 0 or item["point"] != 0:
            return False
    return True


def edit_event(request, event_id):
    context = {}
    event = get_object_or_404(Leagues, id=event_id)  
    context["event"] = event
    users = User.objects.all()  # Fetch all users
    context["users"] = users
    play_type_details = LeaguesPlayType.objects.filter(league_for=event)
    cancelation_policy = LeaguesCancellationPolicy.objects.filter(league=event)

    tournament_play_type = event.play_type
        
    if play_type_details:
        play_type_details = play_type_details.first().data
        
    else:
        play_type_details = [
                    {"name": "Round Robin", "number_of_courts": 0, "sets": 0, "point": 0},
                    {"name": "Elimination", "number_of_courts": 0, "sets": 0, "point": 0},
                    {"name": "Final", "number_of_courts": 0, "sets": 0, "point": 0}
                    ]
        
    for se in play_type_details:
        if tournament_play_type == "Group Stage":
            se["is_show"] = True

        elif tournament_play_type == "Round Robin": 
            if se["name"] == "Round Robin":
                se["is_show"] = True
            else:
                se["is_show"] = False
        elif tournament_play_type == "Single Elimination":
            if se["name"] != "Round Robin":
                se["is_show"] = True
            else:
                se["is_show"] = False
        elif tournament_play_type == "Individual Match Play":
            if se["name"] == "Final":
                se["is_show"] = True
            else:
                se["is_show"] = False 

    context["teams"] = Team.objects.all()
    context["play_type_details"] = play_type_details
    context["policies"] = cancelation_policy
        
    check_data = check_data_structure(play_type_details)
    context["play_details_update"] = check_data


    if request.method == "POST": 
        event.name = request.POST.get("tournament_name", event.name)
        event.leagues_start_date = request.POST.get("league_start_date", event.leagues_start_date)
        event.leagues_end_date = request.POST.get("league_end_date", event.leagues_end_date)
        event.registration_start_date = request.POST.get("registration_start_date", event.registration_start_date)
        event.registration_end_date = request.POST.get("registration_end_date", event.registration_end_date)
        event.max_number_team = request.POST.get("max_join_team", event.max_number_team)
        event.registration_fee = request.POST.get("registration_fee", event.registration_fee)
        event.description = request.POST.get("description", event.description)
        event.location = request.POST.get("location", event.location)
        
        # Handle many-to-many relationship with teams (Join Team)
        selected_teams = request.POST.getlist("join_team")
        event.registered_team.set(selected_teams)

        # Handle other fees, if any
        other_fees_topic = request.POST.getlist("other_fees_topic[]")
        other_fees = request.POST.getlist("other_fees[]")
        other_fees_dict = dict(zip(other_fees_topic, other_fees))
        event.others_fees = other_fees_dict
        if "image" in request.FILES:
            event.image = request.FILES["image"]

        # Handle Organizer Selection
        organizer_ids = request.POST.getlist("organizer")  # Get multiple selected users
        if organizer_ids:
            event.add_organizer.set(organizer_ids)  # Directly set the ManyToMany field
        else:
            event.add_organizer.clear()

        cancellation_days = request.POST.getlist("cancellation_days[]")
        refund_percentages = request.POST.getlist("refund_percentage[]")

        # Clear existing policies
        LeaguesCancellationPolicy.objects.filter(league=event).delete()

        # Save new policies
        for day, refund in zip(cancellation_days, refund_percentages):
            if day and refund:
                LeaguesCancellationPolicy.objects.create(
                    league=event,
                    within_day=int(day),
                    refund_percentage=(float(refund))
                )

        event.save()


        courts_1 = request.POST.get("courts_1", 0)
        sets_1 = request.POST.get("sets_1", 0)
        points_1 = request.POST.get("points_1", 0)

        courts_2 = request.POST.get("courts_2", 0)
        sets_2 = request.POST.get("sets_2", 0)
        points_2 = request.POST.get("points_2", 0)

        courts_3 = request.POST.get("courts_3", 0)
        sets_3 = request.POST.get("sets_3", 0)
        points_3 = request.POST.get("points_3", 0)

        play_details = LeaguesPlayType.objects.filter(league_for=event).first()
        tournament_play_type = event.play_type
        data_ = [{"name": "Round Robin", "number_of_courts": courts_1, "sets": sets_1, "point": points_1},
                {"name": "Elimination", "number_of_courts": courts_2, "sets": sets_2, "point": points_2},
                {"name": "Final", "number_of_courts": courts_3, "sets": sets_3, "point": points_3}]
        # print(data_, "data")
        for se in data_:
            if tournament_play_type == "Group Stage":
                se["is_show"] = True
            elif tournament_play_type == "Round Robin": 
                if se["name"] == "Round Robin":
                    se["is_show"] = True
                else:
                    se["is_show"] = False
            elif tournament_play_type == "Single Elimination":
                if se["name"] != "Round Robin":
                    se["is_show"] = True
                else:
                    se["is_show"] = False
            elif tournament_play_type == "Individual Match Play":
                if se["name"] == "Final":
                    se["is_show"] = True
                else:
                    se["is_show"] = False 
        # print("hit", data_)
        play_details.data = data_
        play_details.save()


        return redirect(reverse("user_side:event_view", kwargs={"event_id":event_id}))
    else:
        return render(request, "sides/edit_event.html", context)


def search_teams(request):
    query = request.GET.get("q", "").strip()
    if query:
        teams = Team.objects.filter(name__icontains=query).values("id", "name", "team_image")
        return JsonResponse({"teams": list(teams)})
    return JsonResponse({"teams": []})


def search_organizers(request):
    query = request.GET.get("q", "").strip()
    if query:
        organizers = User.objects.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(username__icontains=query)).values("id", "first_name", "last_name", "image", "email")
        return JsonResponse({"organizers": list(organizers)})
    return JsonResponse({"organizers": []})


@login_required(login_url="/user_side/")
def ad_list(request):
    context = {}
    query = request.GET.get('q', '')
    ads = Advertisement.objects.filter(approved_by_admin=True)
    if query:
        ads = ads.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(script_text__icontains=query))
    paginator = Paginator(ads, 9)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        ads = paginator.page(page)
    except PageNotAnInteger:
        ads = paginator.page(1)
    except EmptyPage:
        ads = paginator.page(paginator.num_pages)

    context["advertisements"] = ads
    context['query'] = query
    return render(request, 'sides/ad_list.html', context)

@login_required(login_url="/user_side/")
def my_ad_list(request):
    context = {}
    query = request.GET.get('q', '')
    ads = Advertisement.objects.filter(approved_by_admin=True, created_by=request.user)

    if query:
        ads = ads.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(script_text__icontains=query))

    # Calculate status (days until expiry)
    for ad in ads:
        days_left = (ad.end_date - now()).days
        if days_left < 0:
            ad.status = "Expired"
        else:
            ad.status = f"Expires in {days_left} days"

    # Pagination
    paginator = Paginator(ads, 9)  # Show 9 ads per page
    page = request.GET.get('page')
    
    try:
        ads = paginator.page(page)
    except PageNotAnInteger:
        ads = paginator.page(1)
    except EmptyPage:
        ads = paginator.page(paginator.num_pages)

    context["advertisements"] = ads
    context['query'] = query
    return render(request, 'sides/my_ad_list.html', context)


@login_required(login_url="/user_side/")
def create_advertisement(request):
    durations = AdvertisementDurationRate.objects.all()
    wallet_balance = Wallet.objects.get(user=request.user).balance

    return render(request, 'sides/advertisement_form.html', {
        'durations': durations, 
        'wallet_balance': wallet_balance
    })


def get_ad_rate(request):
    duration_id = request.GET.get("duration_id")
    try:
        duration = AdvertisementDurationRate.objects.get(id=duration_id)
        return JsonResponse({"rate": duration.rate})
    except AdvertisementDurationRate.DoesNotExist:
        return JsonResponse({"error": "Invalid duration ID"}, status=400)


@login_required(login_url="/user_side/")
def confirm_payment_for_advertisement(request):
    """Handles the payment confirmation after checking wallet balance."""
    if request.method == "POST":
        duration_id = request.POST.get('duration_id')
        name = request.POST.get('name')
        url = request.POST.get('url')
        company_name = request.POST.get('company_name')
        company_website = request.POST.get('company_website')
        start_date = request.POST.get('start_date')

        image = request.FILES.get('image') 
        script_text = request.POST.get('script_text') 
        description = request.POST.get('description')

        wallet = get_object_or_404(Wallet, user=request.user)

        duration_instance = AdvertisementDurationRate.objects.filter(id=int(duration_id)).first()
        rate = duration_instance.rate
        if float(balance) >= float(rate):
            obj = GenerateKey()
            advertisement_key = obj.gen_advertisement_key()
            ad = Advertisement.objects.create(
                    secret_key=advertisement_key,
                    name=name,
                    image=image,
                    url=url,
                    created_by_id=request.user.id,
                    description=description,
                    script_text=script_text,
                    start_date=start_date,
                    company_name=company_name,
                    company_website=company_website,
                    duration=duration_instance)
            
            WalletTransaction.objects.create(
                sender = request.user,
                reciver = None,                        
                admin_cost=Decimal(rate),
                getway_charge = 0,                        
                transaction_for="Advertisement",                                   
                transaction_type="debit",
                amount=Decimal(rate),
                payment_id=None, 
                description=f"${rate} is debited from your PickleIt wallet for creating advertisement."
                )
            balance = float(balance) - float(rate)
            wallet.balance = Decimal(balance)
            wallet.save()

            admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
            admin_balance = float(admin_wallet.balance) + float(rate)
            admin_wallet.balance = Decimal(admin_balance)
            admin_wallet.save()
            
            # send notification to admin
            admin_users = User.objects.filter(is_admin=True).values_list('id', flat=True)
            title = "New Advertisement created."
            message = f"{request.user.first_name} {request.user.last_name} has created an advertisement named {ad.name}. Please review this."
            for user_id in admin_users:
                notify_edited_player(user_id, title, message)
            
            return JsonResponse({'success': 'Advertisement created successfully'}, status=201)   
        else:
            return JsonResponse({'error': 'Insufficient balance'}, status=400)         
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

import urllib.parse

@csrf_exempt
def initiate_stripe_payment_for_advertisement(request):
    if request.method == "POST":
        duration_id = request.POST.get("duration_id")
        remaining_amount = float(request.POST.get("total_amount_with_fees"))

        # Save form data in session
        form_data = request.POST.dict()
        request.session["ad_form_data"] = form_data

        # Convert form data to JSON and encode it for URL
        json_data = json.dumps({"duration_id": duration_id, "form_data": form_data})
        my_data = urllib.parse.quote(json_data)
        stripe.api_key = settings.STRIPE_SECRET_KEY
        host = request.get_host()
        current_site = f"{protocol}://{host}"
        main_url = f"{current_site}/user_side/stripe_success_for_advertisement/{my_data}/"

        try:
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Ad Payment"},
                        "unit_amount": int(remaining_amount * 100),  # Convert to cents
                    },
                    "quantity": 1,
                }],
                mode="payment",
                success_url=f"{main_url}{{CHECKOUT_SESSION_ID}}/",
                cancel_url=request.build_absolute_uri(reverse("user_side:my_ad_list")),
            )

            return JsonResponse({"success": True, "stripe_url": session.url})
        
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


def stripe_success_for_advertisement(request, my_data, checkout_session_id):
    # Retrieve saved form data from session
    try:
        # Fetch session details from Stripe
        session = stripe.checkout.Session.retrieve(checkout_session_id)

        json_data = json.loads(urllib.parse.unquote(my_data))
        duration_id = json_data.get("duration_id")
        form_data = json_data.get("form_data")
        print(form_data)
        
        total_amount = Decimal(session.amount_total) / 100  # Convert cents to dollars
        print(total_amount)
        payment_status = session.get("payment_status") == "paid"
        payment_method_types = session.get("payment_method_types", [])

        if not payment_status:
            return JsonResponse({"success": False, "message": "Payment not completed."})

        user = request.user
        wallet = Wallet.objects.get(user=user)
        wallet.balance = Decimal(wallet.balance) + total_amount  
        wallet.balance -= total_amount  
        wallet.save()

        AllPaymentsTable.objects.create(
            user=user,
            amount=total_amount,
            checkout_session_id=checkout_session_id,
            payment_mode=", ".join(payment_method_types),
            payment_for=f"Creating Advertisement.",
            status="Completed"
        )
        rate = AdvertisementDurationRate.objects.get(id=duration_id).rate
        WalletTransaction.objects.create(
                sender = request.user,
                reciver = None,                        
                admin_cost=Decimal(rate),
                getway_charge = 0,                        
                transaction_for="Advertisement",                                   
                transaction_type="debit",
                amount=Decimal(rate),
                payment_id=None, 
                description=f"${rate} is debited from your PickleIt wallet for creating advertisement."
                )

        obj = GenerateKey()
        advertisement_key = obj.gen_advertisement_key()
        duration_instance = AdvertisementDurationRate.objects.filter(id=int(duration_id)).first()
        ad = Advertisement.objects.create(
                secret_key=advertisement_key,
                name=form_data.get('name'),
                image=form_data.get('image'),
                url=form_data.get('url'),
                created_by_id=request.user.id,
                description=form_data.get('description'),
                script_text=form_data.get('script_text'),
                start_date=form_data.get('start_date'),
                company_name=form_data.get('company_name'),
                company_website=form_data.get('company_website'),
                duration=duration_instance)

        return redirect("user_side:my_ad_list")

    except stripe.error.StripeError as e:
        return JsonResponse({"success": False, "message": f"Stripe error: {str(e)}"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


def fetch_google_clubs(request):
    """
    Fetch nearby clubs using Google Places API
    """
    google_api_key = settings.MAP_API_KEY
    lat = request.GET.get("lat")  # Get latitude from request
    lng = request.GET.get("lng")  # Get longitude from request
    radius = 5000  # 5km radius

    google_places_url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
        f"location={lat},{lng}&radius={radius}&type=club&key={google_api_key}"
    )

    response = requests.get(google_places_url)
    data = response.json()

    if "results" in data:
        google_clubs = [
            {"name": place["name"], "latitude": place["geometry"]["location"]["lat"],
             "longitude": place["geometry"]["location"]["lng"]}
            for place in data["results"]
        ]
        return JsonResponse({"google_clubs": google_clubs})
    return JsonResponse({"google_clubs": []})


def fetch_pickleball_courts(request):
    """
    Fetch nearby pickleball courts using Google Places API
    """
    google_api_key = settings.MAP_API_KEY
    lat = request.GET.get("lat")  # Get latitude from request
    lng = request.GET.get("lng")  # Get longitude from request
    radius = 5000  # 5km radius

    google_places_url = (
        f"https://maps.googleapis.com/maps/api/place/nearbysearch/json?"
        f"location={lat},{lng}&radius={radius}&keyword=pickleball+court&key={google_api_key}"
    )

    response = requests.get(google_places_url)
    data = response.json()

    if "results" in data:
        pickleball_courts = [
            {
                "name": place["name"],
                "latitude": place["geometry"]["location"]["lat"],
                "longitude": place["geometry"]["location"]["lng"],
                "address": place.get("vicinity", "No address available")
            }
            for place in data["results"]
        ]
        return JsonResponse({"pickleball_courts": pickleball_courts})
    
    return JsonResponse({"pickleball_courts": []})


@login_required(login_url="/user_side/")
def all_club_list(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    clubs = Club.objects.filter(diactivate=False)

    if query:
        clubs = clubs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if location:
        latitude, longitude = get_lat_long_google(settings.MAP_API_KEY, location)
        user_location = (float(latitude), float(longitude))
        max_distance_km = 100  # Search radius in km

        # Filter clubs by distance using geopy
        clubs = [club for club in clubs if geodesic(user_location, (float(club.latitude), float(club.longitude))).km <= max_distance_km]

    clubs_json = json.dumps(list(clubs.values('id', 'name', 'location', 'latitude', 'longitude')))
    paginator = Paginator(clubs, 9)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        clubs = paginator.page(page)
    except PageNotAnInteger:
        clubs = paginator.page(1)
    except EmptyPage:
        clubs = paginator.page(paginator.num_pages)

    
    return render(request, 'sides/club_list.html', {'clubs':clubs, 'query':query, 'location_query':location, "google_api_key": settings.MAP_API_KEY, "clubs_json": clubs_json})


def club_view(request, pk):
    club = get_object_or_404(Club, id=int(pk))
    club_paackages = ClubPackage.objects.filter(club=club)
    check_join = JoinClub.objects.filter(user=request.user, club=club)

    # Check if the user has joined the club
    is_joined = check_join.exists()  # Returns True if any record exists, otherwise False
    wallet_balance = Wallet.objects.filter(user=request.user).first().balance
    return render(request, 'sides/club_view.html', {
        'club': club, 
        'packages': club_paackages, 
        'is_joined': is_joined,
        'wallet_balance':wallet_balance
    })

def get_wallet_balance_and_amount_to_pay(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        package_id = data.get('package_id')
        booking_date = data.get('booking_date')

        # Get the package and calculate the amount to pay
        package = ClubPackage.objects.get(id=package_id)
        if JoinClub.objects.filter(user=request.user, club=package.club).exists():
            discount = package.member_ship_discount
            if not discount:
                discount = 0
            pay_amount = package.price - (package.price*discount)/100
        else:
            pay_amount = package.price  # Assuming the price of the package is the amount to pay

        # Get the user's wallet balance
        wallet = Wallet.objects.get(user=request.user)
        wallet_balance = wallet.balance

        return JsonResponse({
            'wallet_balance': wallet_balance,
            'amount_to_pay': pay_amount,
        })
    
    
def confirm_payment_for_book_club(request):
    if request.method == "POST":
        data = json.loads(request.body)
        package_id = data.get('package_id')
        booking_date = data.get('booking_date')
        if not booking_date:
            return JsonResponse({"error": "not proper date"}, status=400)
        date = datetime.strptime(booking_date, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed
        date = make_aware(date)
        date_today = timezone.now()
        if date_today >= date:
            return JsonResponse({"error": "please select proper date"}, status=400)
        
        club_package = get_object_or_404(ClubPackage, id=int(package_id))

        if JoinClub.objects.filter(user=request.user, club=club_package.club).exists():
            discount = club_package.member_ship_discount
            if not discount:
                discount = 0
            pay_amount = club_package.price - (club_package.price*discount)/100
        else:
            pay_amount = club_package.price
        
        wallet = get_object_or_404(Wallet, user=request.user)
        balance = wallet.balance if wallet else 0
        
        if pay_amount in [0, 0.00, None, "0.0"]:
            join = BookClub(user=request.user, package=club_package, price=pay_amount, date=date)
            join.status = True
            join.save()
            return JsonResponse({"message": "Club Booked successfully!"}, status=201)

        club_wallet = Wallet.objects.filter(user=club_package.club.user).first()
        admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
        
        if balance >= pay_amount:
            club_amount = (pay_amount * Decimal(settings.CLUB_PERCENTAGE)) / 100
            admin_amount = (pay_amount * Decimal(settings.ADMIN_PERCENTAGE_CLUB)) / 100
            if admin_amount is not None:
                admin_amount = admin_amount.quantize(Decimal("0.01"))  # Keeps 2 decimal places
            if club_amount is not None:
                club_amount = club_amount.quantize(Decimal("0.01"))

            WalletTransaction.objects.create(
                sender = request.user,
                reciver = club_package.club.user, 
                reciver_cost =  str(club_amount),                      
                admin_cost= str(admin_amount),
                getway_charge = 0,                        
                transaction_for="BookClub",                                   
                transaction_type="debit",
                amount=pay_amount,
                payment_id=None, 
                description=f"${pay_amount} is debited from your PickleIt wallet for Booking {club_package.name} package from {club_package.club.name} club."
                )
            wallet.balance -= pay_amount
            wallet.save()
            club_wallet.balance += club_amount
            club_wallet.save()
            admin_wallet.balance += admin_amount
            admin_wallet.save()
            # ✅ Create JoinClub Entry
            join = BookClub(user=request.user, package=club_package, price=pay_amount, date=date)
            join.status = True
            join.save()
            # ✅ Send Notification
            user_id = club_package.club.user.id
            message = f"{request.user.first_name} booked your club: {club_package.club.name} at {date}"
            title = "User Booked Club"
            notify_edited_player(user_id, title, message)
            
            return JsonResponse({'success': 'Booking club is successfull'}, status=201)   
        else:
            return JsonResponse({'error': 'Insufficient balance'}, status=400)         
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

protocol = settings.PROTOCALL
def initiate_stripe_payment_for_booking_club(request):
    print('this function called')
    if request.method == "POST":
        data = json.loads(request.body)
        print('Data received:', data)
        package_id = data.get('package_id')
        booking_date = data.get('booking_date')
        without_fees = float(data.get('remaining_amount'))
        remaining_amount = float(data.get("total_amount_with_fees"))

        if not booking_date:
            return JsonResponse({"error": "not proper date"}, status=400)
        try:
            if " " in booking_date:  # Check if time is included
                date = datetime.strptime(booking_date, "%Y-%m-%d %H:%M:%S")
            else:
                date = datetime.strptime(booking_date, "%Y-%m-%d")
        except ValueError:
            return JsonResponse({"error": "Invalid date format"}, status=400)

        date = make_aware(date)
        date_today = timezone.now()
        if date_today >= date:
            return JsonResponse({"error": "please select proper date"}, status=400)
             
        package = ClubPackage.objects.filter(id=package_id).first()
        json_data = json.dumps({"booking_date": date.strftime("%Y-%m-%d %H:%M:%S"), "package_id": package_id})
        my_data = base64.b64encode(json_data.encode("utf-8")).decode("utf-8")
        stripe.api_key = settings.STRIPE_SECRET_KEY

        host = request.get_host()
        current_site = f"{settings.PROTOCALL}://{host}"
       
        product_name = f"Book {package.name} package in {package.club.name} Club"
        product_description = "Payment received by Pickleit"
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if request.user.stripe_customer_id :
            stripe_customer_id = request.user.stripe_customer_id
        else:
            customer = stripe.Customer.create(email=request.user.email).to_dict()
            stripe_customer_id = customer["id"]
            request.user.stripe_customer_id = stripe_customer_id
            request.user.save()
        
        protocol = settings.PROTOCALL
        host = request.get_host()
        current_site = f"{protocol}://{host}"
        total_charge = round(Decimal(remaining_amount), 2)
        charge_amount = round(float(total_charge * 100))
        stripe_fees = Decimal(remaining_amount - without_fees)

        main_url = f"{current_site}/user_side/stripe_success_for_booking_club/{stripe_fees}/{my_data}/"
        product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
        price = stripe.Price.create(unit_amount=charge_amount,currency='usd',product=product["id"],).to_dict()

        try:
            # Create Stripe Checkout Session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[
                    {
                        # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                        'price': price["id"],
                        'quantity': 1,
                    },
                ],
                mode="payment",
                success_url=f"{main_url}{{CHECKOUT_SESSION_ID}}/",
                cancel_url=request.build_absolute_uri(reverse("user_side:club_view", args=[package.club.id])),
            )

            return JsonResponse({"success": True, "stripe_url": session.url})
        
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


def stripe_success_for_booking_club(request, stripe_fees, my_data, checkout_session_id):
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()
        
        payment_status = pay.get("payment_status") == "paid"
        amount_total = Decimal(pay.get("amount_total", 0)) / 100  # Convert to Decimal
        payment_method_types = pay.get("payment_method_types", [])

        # Decode and parse JSON data
        json_bytes = base64.b64decode(my_data)
        request_data = json.loads(json_bytes.decode('utf-8'))
        print(request_data)
        booking_date = request_data.get("booking_date")
        date = datetime.strptime(booking_date, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed      
       
        package_id = request_data.get("package_id")
        package = get_object_or_404(ClubPackage, id=package_id)
        club = get_object_or_404(Club, id=package.club.id)

        payment_for = f"join {club.name} club"
        user_wallet = Wallet.objects.filter(user=request.user).first()
        get_wallet = Wallet.objects.filter(user=club.user).first()
        admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
        existing_payment = AllPaymentsTable.objects.filter(user=request.user, checkout_session_id=checkout_session_id).exists()

        if not existing_payment and payment_status:
            AllPaymentsTable.objects.create(
                user=request.user,
                amount=amount_total,
                checkout_session_id=checkout_session_id,
                payment_mode=", ".join(payment_method_types),
                payment_for=payment_for,
                status="Completed" if payment_status else "Failed"
            )
            join = BookClub(user=request.user, package=package, price=package.price, date=date)
            join.status = True
            join.save()
            ###
            # try:
            club_amount = (package.price * settings.CLUB_PERCENTAGE) / 100
            admin_amount = (package.price * settings.ADMIN_PERCENTAGE_CLUB) / 100
            
            if admin_amount is not None:
                admin_amount = admin_amount.quantize(Decimal("0.01"))  # Keeps 2 decimal places
            if club_amount is not None:
                club_amount = club_amount.quantize(Decimal("0.01"))
            
            WalletTransaction.objects.create(
                sender=request.user,
                reciver=club.user,
                admin_cost=admin_amount,
                reciver_cost=club_amount,
                getway_charge=stripe_fees,
                transaction_for="BookClub",
                transaction_type="debit",
                amount=package.price,
                payment_id=checkout_session_id,
                description=f"${package.price} is debited from your PickleIt wallet for join club to {club.name}."
            )
            get_wallet.balance += club_amount
            admin_wallet.balance += admin_amount
            get_wallet.save()
            admin_wallet.save()
            user_wallet.balance = 0.0
            user_wallet.save()

            # messages.success(request, f"You have successfully joined {club.name}!")

                # ✅ Redirect to club view
            return redirect("user_side:club_view", pk=club.id)
        else:
            return JsonResponse({"success": True, "message": f"You have already booked the club."})

    except stripe.error.StripeError as e:
        return JsonResponse({"success": False, "message": f"Stripe error: {str(e)}"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


def booking_list(request, club_id):
    date = request.GET.get("date")
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")
    search_query = request.GET.get("search", "")
    
    club = Club.objects.get(id=int(club_id))
    packages = ClubPackage.objects.filter(club=club)
    bookings = BookClub.objects.filter(package__in=packages)

    # Filter by single date or date range
    if date:
        bookings = bookings.filter(date__date=date)
    elif start_date and end_date:
        bookings = bookings.filter(date__date__range=[start_date, end_date])

    # Search filter
    if search_query:
        bookings = bookings.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )


    paginator = Paginator(bookings, 10)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        bookings = paginator.page(page)
    except PageNotAnInteger:
        bookings = paginator.page(1)
    except EmptyPage:
        bookings = paginator.page(paginator.num_pages)

    results = [
        {
            "name": booking.user.username,
            "email": booking.user.email,
            "booking_date": booking.date.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for booking in bookings
    ]

    return render(request, 'sides/booking_list.html', {
        "results": results,
        
        "total_bookings": len(bookings),  # Total booking count
        "search_query": search_query,
        "selected_date": date,
        "start_date": start_date,
        "end_date": end_date,
        'club_id':club.id
        
    })


def joined_list(request, club_id):
    search_query = request.GET.get("search", "")
    club = get_object_or_404(Club, id=club_id)
    
    joined_users = JoinClub.objects.filter(club=club, status=True, block=False)
    if search_query:
        joined_users = joined_users.filter(
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(user__username__icontains=search_query)
        )
    paginator = Paginator(joined_users, 10)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        joined_users = paginator.page(page)
    except PageNotAnInteger:
        joined_users = paginator.page(1)
    except EmptyPage:
        joined_users = paginator.page(paginator.num_pages)

    results = [
        {
            "name": join.user.username,
            "email": join.user.email,
        }
        for join in joined_users
    ]

    return render(request, 'sides/joined_list.html', {
        "results": results,
        
        "total_joined": len(joined_users),  # Total booking count
        "search_query": search_query,
        'club_id':club.id
        
    })

def confirm_payment_for_join_club(request):
    if request.method == "POST":
        data = json.loads(request.body)
        print('Data received:', data)
        club_id = data.get('club_id')
        club = Club.objects.filter(id=club_id).first()
        if JoinClub.objects.filter(user=request.user, club=club).exists():
            return JsonResponse({"error": "Already joined in club"}, status=400)

        # ✅ Get User Wallet & Balance
        wallet = Wallet.objects.filter(user=request.user).first()
        club_wallet = Wallet.objects.filter(user=club.user).first()
        admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
        balance = wallet.balance if wallet else 0

        if club.join_amount in [0, 0.0, None, "0"]:
            # ✅ Create JoinClub Entry
            join = JoinClub(user=request.user, club=club)
            join.status = True
            join.save()
            return JsonResponse({"success": "Club joined successfully!"}, status=201)

        # ✅ Validate Join Price
        join_price = club.join_amount if club.join_amount not in [None, "null", "None"] else 0
        club_wonner_wallet = Wallet.objects.filter(user=club.user).first()
        if balance >= join_price:
            club_amount = (club.join_amount * Decimal(settings.CLUB_PERCENTAGE)) / 100
            admin_amount = (club.join_amount * Decimal(settings.ADMIN_PERCENTAGE_CLUB)) / 100
            
            WalletTransaction.objects.create(
                sender = request.user,
                reciver = club.user,   
                reciver_cost = round(club_amount, 2),                  
                admin_cost= round(admin_amount, 2),
                getway_charge = 0,                        
                transaction_for="JoinClub",                                   
                transaction_type="debit",
                amount= club.join_amount,
                payment_id=None, 
                description=f"${club.join_amount} is debited from your PickleIt wallet for join {club.name} club."
                )
            wallet.balance -= join_price
            club_wallet.balance += club_amount
            admin_wallet.balance += admin_amount
            admin_wallet.save()
            club_wallet.save()
            wallet.save()
            club_wonner_wallet.balance = club_wonner_wallet.balance + join_price
            club_wonner_wallet.save()
            
            # ✅ Create JoinClub Entry
            join = JoinClub(user=request.user, club=club)
            join.status = True
            join.save()
            #update admin wallet balance
            admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
            if admin_wallet:
                admin_wallet.balance = Decimal(str(admin_wallet.balance)) + join_price
                admin_wallet.save()
            
            # ✅ Send Notification
            user_id = club.user.id
            message = f"{request.user.first_name} join your club: {club.name}"
            title = "User Join Club"
            notify_edited_player(user_id, title, message)
            return JsonResponse({'success': 'Booking club is successfull'}, status=201)   
        else:
            return JsonResponse({'error': 'Insufficient balance'}, status=400)         
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


def initiate_stripe_payment_for_join_club(request):
    if request.method == "POST":
        data = json.loads(request.body)
        print('Data received:', data)
        club_id = data.get('club_id')
        club = Club.objects.filter(id=club_id).first()
        without_fees = float(data.get('remaining_amount'))
        remaining_amount = float(data.get("total_amount_with_fees"))

        total_charge = round(Decimal(remaining_amount), 2)
        charge_amount = round(float(total_charge * 100))
        stripe_fees = Decimal(remaining_amount - without_fees)

        print(charge_amount)
        make_request_data = {"club_id":club.id}
        json_bytes = json.dumps(make_request_data).encode('utf-8')
        my_data = base64.b64encode(json_bytes).decode('utf-8')
        product_name = f"Join {club.name} Club"
        product_description = "Payment received by Pickleit"
        stripe.api_key = settings.STRIPE_SECRET_KEY
        if request.user.stripe_customer_id :
            stripe_customer_id = request.user.stripe_customer_id
        else:
            customer = stripe.Customer.create(email=request.user.email).to_dict()
            stripe_customer_id = customer["id"]
            request.user.stripe_customer_id = stripe_customer_id
            request.user.save()        

        protocol = settings.PROTOCALL
        host = request.get_host()
        current_site = f"{protocol}://{host}"
        main_url = f"{current_site}/user_side'stripe_success_for_join_club/{stripe_fees}/{my_data}/"
        product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
        price = stripe.Price.create(unit_amount=charge_amount,currency='usd',product=product["id"],).to_dict()
        try:
            session = stripe.checkout.Session.create(
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
            return JsonResponse({"success": True, "stripe_url": session.url})
        
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})

    return JsonResponse({"success": False, "error": "Invalid request"})


def stripe_success_for_join_club(request, stripe_fees, my_data, checkout_session_id):
    try:
        
        pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()
        payment_status = pay.get("payment_status") == "paid"
        amount_total = Decimal(pay.get("amount_total", 0)) / 100  # Convert to Decimal
        payment_method_types = pay.get("payment_method_types", [])

        # Decode and parse JSON data
        json_bytes = base64.b64decode(my_data)
        request_data = json.loads(json_bytes.decode('utf-8'))
        club_id = request_data.get("club_id")
        club = get_object_or_404(Club, id=club_id)
        get_user = get_object_or_404(User, id=request_data.get("user_id"))
        payment_for = f"join {club.name} club"
        wallet = Wallet.objects.filter(user_id=request.user.id).first()
        get_wallet = Wallet.objects.filter(user=club.user).first()
        admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
            
        existing_payment = AllPaymentsTable.objects.filter(user=get_user, checkout_session_id=checkout_session_id).exists()

        if not existing_payment and payment_status:
            AllPaymentsTable.objects.create(
                user=get_user,
                amount=club.join_amount,
                checkout_session_id=checkout_session_id,
                payment_mode=", ".join(payment_method_types),
                payment_for=payment_for,
                status="Completed" if payment_status else "Failed"
            )
            wallet.balance=0
            wallet.save()
            join = JoinClub(user=get_user, club=club)
            join.status = True
            join.save()
            
            club_amount = (club.join_amount * Decimal(settings.CLUB_PERCENTAGE)) / 100
            admin_amount = (club.join_amount * Decimal(settings.ADMIN_PERCENTAGE_CLUB)) / 100

            # Ensure rounding is done while keeping values as Decimal
            if admin_amount is not None:
                admin_amount = admin_amount.quantize(Decimal("0.01"))  # Keeps 2 decimal places
            if club_amount is not None:
                club_amount = club_amount.quantize(Decimal("0.01"))
            WalletTransaction.objects.create(
                sender=get_user,
                reciver=club.user,
                admin_cost=str(admin_amount),
                reciver_cost=str(club_amount),
                getway_charge=str(stripe_fees),
                transaction_for="JoinClub",
                transaction_type="debit",
                amount=Decimal(round(float(club.join_amount), 2)),
                payment_id=checkout_session_id,
                description=f"${amount_total} is debited from your PickleIt wallet for join club to {club.name}."
            )
            print(type(get_wallet.balance), get_wallet.balance, type(club_amount), club_amount)
            get_wallet.balance += club_amount
            admin_wallet.balance += admin_amount
            get_wallet.save()
            admin_wallet.save()
            return redirect("user_side:club_view", pk=club.id)
        else:
            return JsonResponse({"success": True, "message": f"You have already booked the club."})

    except stripe.error.StripeError as e:
        return JsonResponse({"success": False, "message": f"Stripe error: {str(e)}"})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})


@login_required(login_url="/user_side/")
def add_my_club(request):
    if request.method == "POST":
        name = request.POST.get("name")
        location = request.POST.get("location")        
        open_time = request.POST.get("open_time")
        close_time = request.POST.get("close_time")
        contact = request.POST.get("contact")
        email = request.POST.get("email")
        is_vip = request.POST.get("is_vip") == "on"
        description = request.POST.get("description")
        join_amount = request.POST.get("join_amount")
        unit = request.POST.get("unit")
        latitude, longitude = get_lat_long_google(settings.MAP_API_KEY, location)

        club = Club.objects.create(
            user=request.user,
            name=name,
            location=location,
            latitude=latitude,
            longitude=longitude,
            open_time=open_time,
            close_time=close_time,
            contact=contact,
            email=email,
            is_vip=is_vip,
            description=description,
            join_amount=join_amount,
            unit=unit           
        )

        # Handling Image Uploads
        images = request.FILES.getlist("images")
        for image in images:
            ClubImage.objects.create(club=club, image=image)

        return redirect("user_side:my_club_list")  # Redirect to a club list or another page

    return render(request, "sides/add_my_club.html")

def my_club_list(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    clubs = Club.objects.filter(diactivate=False, user=request.user)

    if query:
        clubs = clubs.filter(Q(name__icontains=query) | Q(description__icontains=query))
    if location:
        latitude, longitude = get_lat_long_google(settings.MAP_API_KEY, location)
        user_location = (float(latitude), float(longitude))
        max_distance_km = 100  # Search radius in km

        # Filter clubs by distance using geopy
        clubs = [club for club in clubs if geodesic(user_location, (float(club.latitude), float(club.longitude))).km <= max_distance_km]

    clubs_json = json.dumps(list(clubs.values('id', 'name', 'location', 'latitude', 'longitude')))
    paginator = Paginator(clubs, 9)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        clubs = paginator.page(page)
    except PageNotAnInteger:
        clubs = paginator.page(1)
    except EmptyPage:
        clubs = paginator.page(paginator.num_pages)

    return render(request, 'sides/my_club_list.html', {'clubs':clubs, 'query':query, 'location_query':location, "google_api_key": settings.MAP_API_KEY, 'clubs_json':clubs_json})

@csrf_exempt
def add_my_club_package(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            club = Club.objects.get(id=data["club_id"])
            
            # Ensure only the club creator can add packages
            if request.user != club.user:
                return JsonResponse({"success": False, "error": "Permission denied!"}, status=403)

            ClubPackage.objects.create(
                club=club,
                name=data["name"],
                price=data["price"],
                unit=data["unit"],
                valid_start_date=data.get("valid_start_date"),
                valid_end_date=data.get("valid_end_date"),
                member=data.get("member", 1),
                member_ship_discount=data.get("member_ship_discount", 0),
                description=data["description"]
            )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method!"}, status=405)


def load_more_reviews(request, club_id):
    reviews = ClubRating.objects.filter(club_id=club_id).order_by("id")
    paginator = Paginator(reviews, 2)  # Load 2 reviews per request
    page = request.GET.get("page", 1)

    try:
        reviews_page = paginator.page(page)  # Correct way to get a specific page
    except:
        return JsonResponse({"reviews": [], "has_more": False})

    reviews_data = [
        {"username": r.name, "rating": r.rating, "comment": r.comment} for r in reviews_page
    ]

    return JsonResponse({"reviews": reviews_data, "has_more": reviews_page.has_next()})


@csrf_exempt
def add_review(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            club = Club.objects.get(id=data["club_id"])

            if request.user == club.user:
                return JsonResponse({"success": False, "error": "You cannot review your own club!"}, status=403)

            ClubRating.objects.create(
                club=club,
                name=f"{request.user.first_name}",
                rating=int(data["rating"]),
                comment=data.get("comment", "")
            )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method!"}, status=405)


def all_court_list(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    courts = Courts.objects.all()

    if query:
        courts = courts.filter(Q(name__icontains=query) | Q(about__icontains=query))
    if location:
        latitude, longitude = get_lat_long_google(settings.MAP_API_KEY, location)
        user_location = (float(latitude), float(longitude))
        max_distance_km = 100  # Search radius in km

        # Filter clubs by distance using geopy
        courts = [court for court in courts if geodesic(user_location, (float(court.latitude), float(court.longitude))).km <= max_distance_km]

    courts_json = json.dumps([
        {
            "id": court.id,
            "name": court.name,
            "location": court.location,
            "latitude": float(court.latitude) if isinstance(court.latitude, Decimal) else court.latitude,
            "longitude": float(court.longitude) if isinstance(court.longitude, Decimal) else court.longitude,
        }
        for court in courts
    ])
    paginator = Paginator(courts, 9)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        courts = paginator.page(page)
    except PageNotAnInteger:
        courts = paginator.page(1)
    except EmptyPage:
        courts = paginator.page(paginator.num_pages)

    
    return render(request, 'sides/court_list.html', {'courts':courts, 'query':query, 'location_query':location, "google_api_key": settings.MAP_API_KEY, "courts_json": courts_json})


def my_court_list(request):
    query = request.GET.get('q', '')
    location = request.GET.get('location', '')
    
    courts = Courts.objects.filter(created_by=request.user)

    if query:
        courts = courts.filter(Q(name__icontains=query) | Q(about__icontains=query))
    if location:
        latitude, longitude = get_lat_long_google(settings.MAP_API_KEY, location)
        user_location = (float(latitude), float(longitude))
        max_distance_km = 100  # Search radius in km

        # Filter clubs by distance using geopy
        courts = [court for court in courts if geodesic(user_location, (float(court.latitude), float(court.longitude))).km <= max_distance_km]

    courts_json = json.dumps([
        {
            "id": court.id,
            "name": court.name,
            "location": court.location,
            "latitude": float(court.latitude) if isinstance(court.latitude, Decimal) else court.latitude,
            "longitude": float(court.longitude) if isinstance(court.longitude, Decimal) else court.longitude,
        }
        for court in courts
    ])
    paginator = Paginator(courts, 9)  # Show 10 teams per page
    page = request.GET.get('page')
    
    try:
        courts = paginator.page(page)
    except PageNotAnInteger:
        courts = paginator.page(1)
    except EmptyPage:
        courts = paginator.page(paginator.num_pages)

    
    return render(request, 'sides/my_court_list.html', {'courts':courts, 'query':query, 'location_query':location, "google_api_key": settings.MAP_API_KEY, "courts_json": courts_json})

def court_view(request, pk):
    court = get_object_or_404(Courts, id=int(pk))
    return render(request, 'sides/court_view.html', {'court':court})

def add_my_court(request):
    if request.method == "POST":
        name = request.POST.get('name')
        location = request.POST.get('location')
        open_time = request.POST.get('open_time')
        close_time = request.POST.get('close_time')
        price = request.POST.get('price')
        price_unit = request.POST.get('price_unit')
        offer_price = request.POST.get('offer_price') if request.POST.get('offer_price') else None
        about = request.POST.get('about')
        owner_name = request.POST.get('owner_name')
        latitude, longitude = get_lat_long_google(settings.MAP_API_KEY, location)

        court = Courts(
            name=name,
            location=location,
            open_time=open_time,
            close_time=close_time,
            price=price,
            price_unit=price_unit,
            offer_price=offer_price,
            about=about,
            owner_name=owner_name,
            created_by=request.user  # Set the user who created the court
        )


        # Handling Image Uploads
        images = request.FILES.getlist("images")
        for image in images:
            CourtImage.objects.create(court=court, image=image)

        return redirect("user_side:my_court_list")  # Redirect to a club list or another page

    return render(request, "sides/add_my_court.html")



def read_notifications(request):
    """
    Marks notifications as read based on provided IDs.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)  
            notification_ids = data.get("unread_notification_ids", [])

            if not notification_ids:
                return JsonResponse({"error": "No notification IDs provided"}, status=400)
            
            updated_count = NotificationBox.objects.filter(
                id__in=notification_ids, notify_for=request.user, is_read=False
            ).update(is_read=True)

            return JsonResponse({"success": True, "updated_count": updated_count}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
    
    return JsonResponse({"error": "Invalid request method"}, status=405)