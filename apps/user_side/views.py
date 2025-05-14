from decimal import Decimal
from pyexpat.errors import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout
from django.urls import reverse
from django.utils.timezone import make_aware
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Exists, OuterRef
from django.views.decorators.http import require_POST
import stripe
from apps.team.models import *
from apps.user.models import AllPaymentsTable, User, Wallet, Transaction, WalletTransaction
from apps.socialfeed.models import *
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import timezone, datetime
from django.views.decorators.csrf import csrf_exempt
from apps.clubs.models import *
from apps.courts.models import *
from django.conf import settings
from geopy.distance import geodesic
from rest_framework import status
from apps.user.helpers import *
from apps.team.views import notify_edited_player, check_add_player
from decimal import Decimal, ROUND_DOWN
import base64
import requests
import json
from apps.chat.models import NotificationBox
from apps.socialfeed.models import *
import uuid
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
   
    #print("Before form submission:", request.user, request.user.is_authenticated)  # Debugging line

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
            #print("After form submission:", request.user, request.user.is_authenticated)  # Debugging line
            return redirect('user_side:user_profile') 
        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")

    context = {"user_details": user, "MAP_API_KEY" : 'AIzaSyAfBo6-cZlOpKGrD1ZYwISIGjYvhH_wPmk'}
    return render(request, 'sides/editprofile.html', context)


@csrf_exempt
def nearby_pickleball(request):
    if request.method == 'POST':
        body = json.loads(request.body)
        lat = float(body.get('lat'))
        lng = float(body.get('lng'))

        # Generate demo data with slight offsets
        player_names = ["John Pickler", "Sarah Smash", "Mike Dinker", "Emma Rally", "Tom Spin"]
        player_descriptions = [
            "Intermediate player, available for casual games",
            "Advanced player, looking for competitive matches",
            "Beginner, loves social play",
            "Enthusiast, plays weekends",
            "Pro player, coaching available"
        ]
        event_names = [
            "City Pickleball Open",
            "Community Meetup",
            "Pro Clinic",
            "Night Tournament",
            "Social Smash"
        ]
        event_descriptions = [
            "Tournament with $500 prize, May 15, 2025",
            "Weekly social play, all levels welcome",
            "Learn from pros, May 20, 2025",
            "Evening matches under lights, May 18, 2025",
            "Fun games with food and music, May 22, 2025"
        ]

        # Generate 3-5 players and events with random offsets
        player_data = []
        event_data = []
        for i in range(3):  # 3 players
            offset_lat = random.uniform(-0.05, 0.05)  # ~5 miles
            offset_lng = random.uniform(-0.05, 0.05)
            player_data.append({
                "name": player_names[i],
                "lat": str(lat + offset_lat),
                "lng": str(lng + offset_lng),
                "description": player_descriptions[i]
            })
        for i in range(3):  # 3 events
            offset_lat = random.uniform(-0.05, 0.05)
            offset_lng = random.uniform(-0.05, 0.05)
            event_data.append({
                "name": event_names[i],
                "lat": str(lat + offset_lat),
                "lng": str(lng + offset_lng),
                "description": event_descriptions[i]
            })

        data = {
            "player_data": player_data,
            "event_data": event_data
        }
        return JsonResponse(data)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required(login_url="/user_side/")
def index(request):
    context = {
        "user_teams_count": 0,
        "balance": 0,
        "join_event_count":0,
        "completed_event_count":0,
        "match_history":[],
        "socail_feed_list":[],
        "API_KEY": settings.MAP_API_KEY
    }
    player = Player.objects.filter(player=request.user).first()
    user_teams = Team.objects.filter(created_by=request.user)
    teams = list(player.team.all()) + list(user_teams)
    join_event = Leagues.objects.filter(registered_team__in = user_teams, is_complete=False).distinct()
    completed_event = Leagues.objects.filter(registered_team__in = user_teams, is_complete=True).distinct()
    user_teams_count = user_teams.count()
    balance = Wallet.objects.filter(user=request.user).first().balance
    join_event_count = join_event.count()
    completed_event_count = completed_event.count()
    
    match_history = Tournament.objects.filter(Q(team1__in=user_teams) | Q(team2__in=user_teams)).distinct()[:5]
    for match_ in match_history:
        if match_.team1 in teams:
            match_.opponent = match_.team2
        else:
            match_.opponent = match_.team1

        match_.scores = TournamentSetsResult.objects.filter(tournament=match_)
    for match_ in match_history:
        match_.score = TournamentSetsResult.objects.filter(tournament=match_)
    
    user_likes = LikeFeed.objects.filter(
        user=request.user, post=OuterRef('pk')
    )
    
    # Annotate posts with is_like
    posts = socialFeed.objects.filter(block=False).annotate(is_like=Exists(user_likes)).order_by('-created_at')[::3]
    context["user_teams_count"] = user_teams_count
    context["balance"] = balance
    context["join_event_count"] = join_event_count
    context["completed_event_count"] = completed_event_count
    context["match_history"] = match_history
    context["socail_feed_list"] = posts
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
def add_event(request):
    YOUR_API_KEY = settings.MAP_API_KEY
    PLAY_TYPE = PLAY_TYPE =(
            ("Group Stage", "Group Stage"),
            ("Round Robin", "Round Robin"),
            ("Single Elimination", "Single Elimination"),
            ("Individual Match Play", "Individual Match Play"),
        )
    LEAGUE_TYPE = LEAGUE_TYPE = (
            ("Invites only", "Invites only"),
            ("Open to all", "Open to all"),
        )
    # Get dynamic choices
    play_type_choices = [choice[0] for choice in PLAY_TYPE]
    team_type_choices = LeaguesTeamType.objects.all()
    person_type_choices = LeaguesPesrsonType.objects.all()
    league_type_choices = [choice[0] for choice in LEAGUE_TYPE]

    
    if request.method == "POST":
        try:
            # Initialize event_data dictionary for processing
            event_data = {
                'event_name': request.POST.get('event_name'),
                'event_description': request.POST.get('event_description'),
                'event_image': request.FILES.get('event_image'),
                'location': request.POST.get('location'),
                'max_team': request.POST.get('max_team'),
                'total_fee': request.POST.get('total_fee'),
                'registration_start': request.POST.get('registration_start'),
                'registration_end': request.POST.get('registration_end'),
                'event_start': request.POST.get('event_start'),
                'event_end': request.POST.get('event_end'),
                'start_rank': request.POST.get('start_rank'),
                'end_rank': request.POST.get('end_rank'),
                'registration_type': request.POST.get('registration_type'),
                'extra_fees': [],
                'cancel_policies': [],
                'play_configs': [],
                'invite_code': None,
                'latitude': request.POST.get('latitude'),
                'longitude': request.POST.get('longitude')
            }

            # Validate required fields
            required_fields = ['event_name', 'event_description', 'location', 'max_team', 
                             'total_fee', 'registration_start', 'registration_end', 
                             'event_start', 'event_end', 'registration_type']
            for field in required_fields:
                if not event_data[field]:
                    raise ValueError(f"{field.replace('_', ' ').title()} is required")

            # Validate league_type
            if event_data['registration_type'] not in league_type_choices:
                raise ValueError("Invalid league type selected")

            # Extra fees
            extra_fee_names = request.POST.getlist('extra_fee_name[]')
            extra_fee_amounts = request.POST.getlist('extra_fee_amount[]')
            for name, amount in zip(extra_fee_names, extra_fee_amounts):
                if name and amount:
                    try:
                        event_data['extra_fees'].append({
                            'name': name.strip(),
                            'amount': float(amount)
                        })
                    except ValueError:
                        raise ValueError("Invalid extra fee amount")

            # Cancellation policy
            cancel_durations = request.POST.getlist('cancel_duration[]')
            cancel_percentages = request.POST.getlist('cancel_percentage[]')
            for duration, percentage in zip(cancel_durations, cancel_percentages):
                if duration and percentage:
                    try:
                        event_data['cancel_policies'].append({
                            'duration': int(duration),
                            'percentage': float(percentage)
                        })
                    except ValueError:
                        raise ValueError("Invalid cancellation policy values")

            # Play configuration
            play_types = request.POST.getlist('play_type[]')
            team_types = request.POST.getlist('team_type[]')
            player_types = request.POST.getlist('player_type[]')
            court_round_robins = request.POST.getlist('court_round_robin[]')
            set_round_robins = request.POST.getlist('set_round_robin[]')
            point_round_robins = request.POST.getlist('point_round_robin[]')
            court_eliminations = request.POST.getlist('court_elimination[]')
            set_eliminations = request.POST.getlist('set_elimination[]')
            point_eliminations = request.POST.getlist('point_elimination[]')
            court_finals = request.POST.getlist('court_final[]')
            set_finals = request.POST.getlist('set_final[]')
            point_finals = request.POST.getlist('point_final[]')

            # Validate play configuration arrays length
            if not (len(play_types) == len(team_types) == len(player_types) ==
                    len(court_round_robins) == len(set_round_robins) == len(point_round_robins) ==
                    len(court_eliminations) == len(set_eliminations) == len(point_eliminations) ==
                    len(court_finals) == len(set_finals) == len(point_finals)):

                raise ValueError("Play configuration arrays have inconsistent lengths")

            for i in range(len(play_types)):
                if (play_types[i] and team_types[i] and player_types[i] and
                    court_round_robins[i] and set_round_robins[i] and point_round_robins[i] and
                    court_eliminations[i] and set_eliminations[i] and point_eliminations[i] and
                    court_finals[i] and set_finals[i] and point_finals[i]):
                    try:
                        # Validate play_type
                        if play_types[i] not in play_type_choices:
                            raise ValueError(f"Invalid play type: {play_types[i]}")
                        # Validate team_type
                        if not LeaguesTeamType.objects.filter(name=team_types[i]).exists():
                            raise ValueError(f"Invalid team type: {team_types[i]}")
                        # Validate person_type
                        if not LeaguesPesrsonType.objects.filter(name=player_types[i]).exists():
                            raise ValueError(f"Invalid person type: {player_types[i]}")
                            
                        event_data['play_configs'].append({
                            'play_type': play_types[i],
                            'team_type': team_types[i],
                            'player_type': player_types[i],
                            'round_robin': {
                                'court': int(court_round_robins[i]),
                                'set': int(set_round_robins[i]),
                                'point': int(point_round_robins[i])
                            },
                            'elimination': {
                                'court': int(court_eliminations[i]),
                                'set': int(set_eliminations[i]),
                                'point': int(point_eliminations[i])
                            },
                            'final': {
                                'court': int(court_finals[i]),
                                'set': int(set_finals[i]),
                                'point': int(point_finals[i])
                            }
                        })
                    except ValueError as e:
                        raise ValueError(f"Invalid play configuration values at index {i}: {str(e)}")

            # Generate invite code if registration_type is 'Invites only'
            if event_data['registration_type'] == 'Invites only':
                event_data['invite_code'] = str(uuid.uuid4())[:6].upper()

            # Create a Leagues instance for each play configuration
            for config in event_data['play_configs']:
                # Retrieve team_type and person_type instances
                team_type = LeaguesTeamType.objects.filter(name=config['team_type']).first()
                if not team_type:
                    raise ValueError(f"Team type {config['team_type']} does not exist")
                
                person_type = LeaguesPesrsonType.objects.filter(name=config['player_type']).first()
                if not person_type:
                    raise ValueError(f"Person type {config['player_type']} does not exist")

                # Create Leagues instance
                league = Leagues.objects.create(
                    secret_key=str(uuid.uuid4()),
                    name=event_data['event_name'],
                    description=event_data['event_description'],
                    image=event_data['event_image'],
                    complete_address=event_data['location'],
                    location=event_data['location'],
                    max_number_team=int(event_data['max_team']) if event_data['max_team'] else 2,
                    registration_fee=float(event_data['total_fee']) if event_data['total_fee'] else 5.0,
                    others_fees=event_data['extra_fees'] if event_data['extra_fees'] else None,
                    registration_start_date=event_data['registration_start'],
                    registration_end_date=event_data['registration_end'],
                    leagues_start_date=event_data['event_start'],
                    leagues_end_date=event_data['event_end'],
                    latitude=float(event_data['latitude']) if event_data['latitude'] else None,
                    longitude=float(event_data['longitude']) if event_data['longitude'] else None,
                    start_rank=float(event_data['start_rank']) if event_data['start_rank'] else None,
                    end_rank=float(event_data['end_rank']) if event_data['end_rank'] else None,
                    league_type=event_data['registration_type'],
                    invited_code=event_data['invite_code'],
                    created_by=request.user,
                    updated_by=request.user,
                    any_rank=False if event_data['start_rank'] or event_data['end_rank'] else True,
                    policy=bool(event_data['cancel_policies']),
                    play_type=config['play_type'],
                    team_type=team_type,
                    team_person=person_type
                )

                # Save cancellation policies
                for policy in event_data['cancel_policies']:
                    LeaguesCancellationPolicy.objects.create(
                        league=league,
                        within_day=policy['duration'],
                        refund_percentage=policy['percentage']
                    )

                
                # Create LeaguesPlayType entry
                play_type_data = [
                    {
                        "name": "Round Robin",
                        "number_of_courts": config['round_robin']['court'],
                        "sets": config['round_robin']['set'],
                        "point": config['round_robin']['point']
                    },
                    {
                        "name": "Elimination",
                        "number_of_courts": config['elimination']['court'],
                        "sets": config['elimination']['set'],
                        "point": config['elimination']['point']
                    },
                    {
                        "name": "Final",
                        "number_of_courts": config['final']['court'],
                        "sets": config['final']['set'],
                        "point": config['final']['point']
                    }
                ]

                LeaguesPlayType.objects.create(
                    type_name=config['play_type'],
                    league_for=league,
                    data=play_type_data
                )

            messages.success(request, f"Successfully created {len(event_data['play_configs'])} events!")
            return redirect('user_side:event_user')

        except ValueError as e:
            messages.error(request, f"Error creating events: {str(e)}")
        except Exception as e:
            messages.error(request, f"Unexpected error: {str(e)}")
            
        return render(request, 'sides/add_event_form.html', {
            'MAP_API_KEY': YOUR_API_KEY,
            'event_data': event_data,
            'play_type_choices': play_type_choices,
            'team_type_choices': team_type_choices,
            'person_type_choices': person_type_choices,
            'league_type_choices': league_type_choices
        })

    return render(request, 'sides/add_event_form.html', {
        'MAP_API_KEY': YOUR_API_KEY,
        'play_type_choices': play_type_choices,
        'team_type_choices': team_type_choices,
        'person_type_choices': person_type_choices,
        'league_type_choices': league_type_choices
    })

@login_required(login_url="/user_side/")
def event(request):
    query = request.GET.get('q', '')
    team_type_filter = request.GET.get('team_type', 'all')
    my_event_type_filter = request.GET.get('my_event_type', 'all')

    # Base queryset: Exclude "Individual Match Play" and order by start date
    leagues = Leagues.objects.exclude(play_type="Individual Match Play")

    # Apply my_event_type_filter
    if my_event_type_filter != 'all':
        if my_event_type_filter == 'org_event':
            leagues = leagues.filter(created_by=request.user) | leagues.filter(add_organizer=request.user)
            leagues = leagues.distinct()
        elif my_event_type_filter == 'join_event':
            player = Player.objects.filter(player=request.user).first()
            if player:
                teams = player.team.all()
                leagues = leagues.filter(registered_team__in=teams, is_complete=False).distinct()
            else:
                leagues = Leagues.objects.none()  # No leagues if user is not a player

    # Apply team_type_filter
    today = datetime.now().date()
    if team_type_filter == 'all':
        pass
    elif team_type_filter == 'Open':
        leagues = leagues.filter(registration_start_date__date__lte=today, registration_end_date__date__gte=today)
    elif team_type_filter == 'Upcoming':
        leagues = leagues.filter(leagues_start_date__date__gte=today, is_complete=False)
    elif team_type_filter == 'Ongoing':
        leagues = leagues.filter(leagues_start_date__date__lte=today, leagues_end_date__date__gte=today, is_complete=False)
    elif team_type_filter == 'Past':
        leagues = leagues.filter(leagues_end_date__date__lte=today, is_complete=True)

    # Apply search query if provided
    if query:
        leagues = leagues.filter(name__icontains=query)

    # Order the final queryset
    leagues = leagues.order_by('-leagues_start_date')

    return render(request, 'sides/event.html', {
        'leagues': leagues,
        'team_type_filter': team_type_filter,
        'my_event_type_filter': my_event_type_filter,
        'text': query
    })

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

    # Calculate total fees
    fees = event.registration_fee
    others_fees = event.others_fees
    if others_fees:
        for val in others_fees:
            if isinstance(val, (int, float)):
                fees += val
            elif isinstance(val, str) and val.isdigit():
                fees += int(val)
    context["total_fees"] = fees

    # Wallet balance
    try:
        wallet = Wallet.objects.filter(user=user).first()
        balance = wallet.balance
    except:
        balance = 0
    context["balance"] = balance

    # My team
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

    # Matches
    matches = Tournament.objects.filter(leagues=event)
    for match in matches:
        match.score = TournamentSetsResult.objects.filter(tournament=match)
    context["matches"] = matches

    # Team stats
    team_stats = {}
    for match in matches:
        if match.team1 and match.team2:
            if match.team1 not in team_stats:
                team_stats[match.team1] = {"played": 0, "wins": 0, "losses": 0, "draws": 0, "points": 0}
            if match.team2 not in team_stats:
                team_stats[match.team2] = {"played": 0, "wins": 0, "losses": 0, "draws": 0, "points": 0}

            team_stats[match.team1]["played"] += 1
            team_stats[match.team2]["played"] += 1

            if match.is_drow:
                team_stats[match.team1]["draws"] += 1
                team_stats[match.team2]["draws"] += 1
                team_stats[match.team1]["points"] += 1
                team_stats[match.team2]["points"] += 1
            elif match.winner_team:
                team_stats[match.winner_team]["wins"] += 1
                team_stats[match.winner_team]["points"] += 3
                loser_team = match.team1 if match.winner_team == match.team2 else match.team2
                team_stats[loser_team]["losses"] += 1
    #round_robin group
    r_group = RoundRobinGroup.objects.filter(league_for=event)
    context["r_group"] = r_group
    # Point table
    point_table = []
    play_type_check_win = event.play_type
    all_group_details = RoundRobinGroup.objects.filter(league_for=event)
    for grp in all_group_details:
        teams = grp.all_teams.all()
        group_score_point_table = []
        for team in teams:
            team_score = {}
            total_match_details = Tournament.objects.filter(leagues=event, match_type="Round Robin").filter(Q(team1=team) | Q(team2=team))
            completed_match_details = total_match_details.filter(is_completed=True)
            win_match_details = completed_match_details.filter(winner_team=team).count()
            loss_match_details = completed_match_details.filter(loser_team=team).count()
            drow_match = len(completed_match_details) - (win_match_details + loss_match_details)
            match_list = list(total_match_details.values_list("id", flat=True))
            for_score = 0
            against_score = 0
            for sc in match_list:
                co_team_position = Tournament.objects.filter(id=sc).first()
                set_score = TournamentSetsResult.objects.filter(tournament_id=sc)
                if co_team_position.team1 == team:
                    for_score += sum(list(set_score.values_list("team1_point", flat=True)))
                    against_score += sum(list(set_score.values_list("team2_point", flat=True)))
                else:
                    for_score += sum(list(set_score.values_list("team2_point", flat=True)))
                    against_score += sum(list(set_score.values_list("team1_point", flat=True)))
                
            point = (win_match_details * 3) + (drow_match * 1)
            team_score["uuid"] = str(team.uuid)
            team_score["secret_key"] = team.secret_key
            team_score["name"] = team.name
            team_score["completed_match"] = len(completed_match_details)
            team_score["win_match"] = win_match_details
            team_score["loss_match"] = loss_match_details
            team_score["drow_match"] = drow_match
            team_score["for_score"] = for_score
            team_score["against_score"] = against_score
            team_score["point"] = point
            group_score_point_table.append(team_score)

        # Sort group score point table
        group_score_point_table = sorted(group_score_point_table, key=lambda x: (x['point'], x['for_score']), reverse=True)

        # Update winner for Round Robin
        if play_type_check_win == "Round Robin":
            total_tournament = Tournament.objects.filter(leagues=event, match_type="Round Robin", leagues__play_type="Round Robin")
            completed_tournament = total_tournament.filter(is_completed=True)
            if total_tournament.count() == completed_tournament.count() and group_score_point_table:
                winner_team = Team.objects.filter(uuid=group_score_point_table[0]["uuid"]).first()
                event.winner_team = winner_team
                event.is_complete = True
                event.save()
                context["winner_team"] = winner_team.name

        grp_data = {
            "id": grp.id,
            "court": grp.court,
            "league_for_id": grp.league_for_id,
            "all_games_status": grp.all_games_status,
            "all_teams": group_score_point_table,
            # "tournament": list(tournament_details_group),
            "seleced_teams_id": grp.seleced_teams_id
        }
        point_table.append(grp_data)

    context["point_table"] = point_table
    
    if event.registered_team.all().count() == 0 and event.created_by == user:
        context["is_del"] = True
    else:
        context["is_del"] = False
    teams = Player.objects.filter(player=user).first().team.all() if Player.objects.filter(player=user).exists() else []
    if event.registered_team.filter(id__in=teams).exists() and not event.is_complete and Tournament.objects.filter(leagues=event).exists():
        context["score_update"] = True
    elif user == event.created_by and Tournament.objects.filter(leagues=event).exists():
        context["score_update"] = True
    else:
        context["score_update"] = False
    if event.registration_end_date:
        context["is_join"] = event.registration_end_date.date() >= today.date()
    else:
        context["is_join"] = False
    sorted_teams = sorted(team_stats.items(), key=lambda x: x[1]["points"], reverse=True)
    context["sorted_teams"] = sorted_teams
    context["groups"] = RoundRobinGroup.objects.filter(league_for=event)

    return render(request, 'sides/event_view.html', context=context)

@login_required(login_url="/user_side/")
def event_delete(request, event_id):
    event = get_object_or_404(Leagues, id=event_id)
    
    if event.registered_team.all().count() == 0 and event.created_by == request.user:
        try:
            # Delete related cancellation policies and play types
            LeaguesCancellationPolicy.objects.filter(league=event).delete()
            LeaguesPlayType.objects.filter(league_for=event).delete()
            # Delete the event
            event.delete()
            # messages.success(request, "Event deleted successfully.")
            return redirect('user_side:event_user')
        except Exception as e:
            # messages.error(request, f"Error deleting event: {str(e)}")
            return redirect('user_side:event_user')
    else:
        # messages.error(
        #     request,
        #     "You cannot delete this event because it has registered teams. Please contact an admin to delete the event."
        # )
        return redirect(reverse('user_side:event_view', kwargs={'event_id': event_id}))


#### assign match 
@login_required(login_url="/user_side/")
def start_tournament(request, event_id):
    """View to start a tournament and assign matches based on play type."""
    event = get_object_or_404(Leagues, id=event_id)
    if request.user != event.created_by:
        messages.error(request, "You are not authorized to start this tournament.")
        return redirect('user_side:event_view', event_id=event_id)

    # Fetch play type details
    playtype_details = get_playtype_details(event)
    registered_teams = event.registered_team.all()
    team_ids = [team.id for team in registered_teams]
    max_teams = event.max_number_team

    # Validate team registration
    if len(team_ids) != max_teams:
        messages.error(request, "All teams are not registered.")
        return redirect('user_side:event_view', event_id=event_id)

    # Send tournament start notifications
    send_tournament_notifications(event, team_ids)

    # Process based on play type
    playtype = event.play_type
    if playtype == "Single Elimination":
        result = handle_single_elimination(event, team_ids, playtype_details)
    elif playtype == "Group Stage":
        result = handle_group_stage(event, team_ids, playtype_details)
    elif playtype == "Round Robin":
        result = handle_round_robin(event, team_ids, playtype_details)
    elif playtype == "Individual Match Play":
        result = handle_individual_match_play(event, team_ids, playtype_details)
    else:
        messages.error(request, "Invalid play type.")
        return redirect('user_side:event_view', event_id=event_id)

    # Display result message
    messages.success(request, result["message"]) if result["status"] == status.HTTP_200_OK else messages.error(request, result["message"])
    return redirect('user_side:event_view', event_id=event_id)

def get_playtype_details(event):
    """Fetch and return play type details for the event."""
    playtype_details = LeaguesPlayType.objects.filter(league_for=event).first()
    if playtype_details:
        return playtype_details.data
    return [
        {"name": "Round Robin", "number_of_courts": 0, "sets": 0, "point": 0},
        {"name": "Elimination", "number_of_courts": 0, "sets": 0, "point": 0},
        {"name": "Final", "number_of_courts": 0, "sets": 0, "point": 0}
    ]

def send_tournament_notifications(event, team_ids):
    """Send notifications to team managers and players when tournament starts."""
    league_name = event.name
    for team_id in team_ids:
        team = Team.objects.get(id=team_id)
        team_manager = team.created_by
        notify_edited_player(
            team_manager.id,
            "Start Tournament",
            f"The tournament {league_name} has started."
        )
        players = Player.objects.filter(team__id=team_id)
        for player in players:
            notify_edited_player(
                player.player.id,
                "Start Tournament",
                f"Player, get ready! The tournament {league_name} has started."
            )

def calculate_team_rank(team):
    """Calculate the average rank of a team based on its players."""
    players = team.player_set.all()
    if not players.exists():
        return 0
    total_rank = sum(float(player.player.rank or '1') for player in players)
    return total_rank / players.count()

def create_group(team_ids, num_parts):
    """Create balanced groups of teams based on their ranks."""
    num_parts = int(num_parts)
    if num_parts <= 0:
        return {"status": status.HTTP_400_BAD_REQUEST, "message": "Number of parts should be greater than zero."}

    teams = Team.objects.filter(id__in=team_ids)
    team_list = [(team.id, calculate_team_rank(team)) for team in teams]
    team_list.sort(key=lambda x: x[1], reverse=True)
    sorted_team_ids = [team[0] for team in team_list]
    total_teams = len(sorted_team_ids)
    teams_per_group = total_teams // num_parts
    remainder = total_teams % num_parts

    group_list = [[] for _ in range(num_parts)]
    for i, team_id in enumerate(sorted_team_ids):
        group_idx = i % num_parts
        group_list[group_idx].append(team_id)

    max_group_size = teams_per_group + (1 if remainder > 0 else 0)
    for i in range(num_parts):
        if len(group_list[i]) > max_group_size:
            group_list[i] = group_list[i][:max_group_size]

    return {"status": status.HTTP_200_OK, "message": "Groups created", "groups": group_list}

def make_shuffle(input_list):
    """Shuffle pairs of teams for elimination rounds."""
    result = []
    try:
        for i in range(0, len(input_list), 2):
            result.extend([
                input_list[i][0],    # A1
                input_list[i+1][1],  # B2
                input_list[i][1],    # A2
                input_list[i+1][0]   # B1
            ])
    except IndexError:
        pass
    return result

def create_tournament_match(event, team1_id, team2_id, match_type, round_number, court_num, sets, points, match_number, group_id=None):
    """Create a tournament match with the given parameters."""
    obj = GenerateKey()
    secret_key = obj.generate_league_unique_id()
    Tournament.objects.create(
        set_number=sets,
        court_num=court_num,
        points=points,
        court_sn=court_num,
        match_number=match_number,
        secret_key=secret_key,
        leagues=event,
        team1_id=team1_id,
        team2_id=team2_id,
        match_type=match_type,
        elimination_round=round_number,
        group_id=group_id
    )

def handle_single_elimination(event, team_ids, playtype_details):
    """Handle Single Elimination tournament logic."""
    court_num_e = int(playtype_details[1]["number_of_courts"])
    set_num_e = int(playtype_details[1]["sets"])
    point_num_e = int(playtype_details[1]["point"])
    court_num_f = int(playtype_details[2]["number_of_courts"])
    set_num_f = int(playtype_details[2]["sets"])
    point_num_f = int(playtype_details[2]["point"])

    if len(team_ids) != event.max_number_team:
        return {"status": status.HTTP_200_OK, "message": "All teams are not joined"}

    check_pre_game = Tournament.objects.filter(leagues=event)
    if check_pre_game.exists():
        check_leagues_com = check_pre_game.filter(is_completed=True)
        if len(check_pre_game) == len(check_leagues_com) and check_leagues_com.exists():
            pre_match_round = check_leagues_com.last().elimination_round
            pre_round_details = Tournament.objects.filter(leagues=event, elimination_round=pre_match_round)
            teams = list(pre_round_details.values_list("winner_team_id", flat=True))
            pre_match_number = check_leagues_com.last().match_number
            court_num = 0

            if len(teams) == 4:
                match_type = "Semi Final"
                sets, courts, points = set_num_e, court_num_e, point_num_e
            elif len(teams) == 2:
                match_type = "Final"
                sets, courts, points = set_num_f, court_num_f, point_num_f
            else:
                match_type = "Elimination Round"
                sets, courts, points = set_num_e, court_num_e, point_num_e
                pre_match_round += 1

            random.shuffle(teams)
            match_number_now = pre_match_number
            for i in range(0, len(teams), 2):
                court_num = (court_num % courts) + 1
                match_number_now += 1
                create_tournament_match(
                    event, teams[i], teams[i+1], match_type, 0 if match_type in ["Semi Final", "Final"] else pre_match_round,
                    court_num, sets, points, match_number_now
                )
            return {"status": status.HTTP_200_OK, "message": f"Matches created for {match_type}"}
        return {"status": status.HTTP_200_OK, "message": "Previous Round is not completed or not updated"}
    else:
        sets, courts, points = set_num_e, court_num_e, point_num_e
        match_number_now = 0
        court_num = 0
        random.shuffle(team_ids)

        if len(team_ids) == 4:
            match_type = "Semi Final"
        elif len(team_ids) == 2:
            match_type = "Final"
            sets, courts, points = set_num_f, court_num_f, point_num_f
        else:
            match_type = "Elimination Round"

        for i in range(0, len(team_ids), 2):
            court_num = (court_num % courts) + 1
            match_number_now += 1
            create_tournament_match(
                event, team_ids[i], team_ids[i+1], match_type, 1 if match_type == "Elimination Round" else 0,
                court_num, sets, points, match_number_now
            )
        return {"status": status.HTTP_200_OK, "message": f"Matches created for {match_type}"}

def handle_group_stage(event, team_ids, playtype_details):
    """Handle Group Stage tournament logic."""
    court_num_r = int(playtype_details[0]["number_of_courts"])
    set_num_r = int(playtype_details[0]["sets"])
    point_num_r = int(playtype_details[0]["point"])
    court_num_e = int(playtype_details[1]["number_of_courts"])
    set_num_e = int(playtype_details[1]["sets"])
    point_num_e = int(playtype_details[1]["point"])
    court_num_f = int(playtype_details[2]["number_of_courts"])
    set_num_f = int(playtype_details[2]["sets"])
    point_num_f = int(playtype_details[2]["point"])

    check_pre_game = Tournament.objects.filter(leagues=event)
    if check_pre_game.exists():
        all_round_robin_match = Tournament.objects.filter(leagues=event)
        all_completed_round_robin_match = Tournament.objects.filter(leagues=event, is_completed=True)
        if all_round_robin_match.count() == all_completed_round_robin_match.count():
            last_match_type = check_pre_game.last().match_type
            last_round = check_pre_game.last().elimination_round
            last_match_number = check_pre_game.last().match_number

            if last_match_type == "Round Robin":
                teams = select_top_teams(event)
                if len(teams) != len(RoundRobinGroup.objects.filter(league_for=event)):
                    return {"status": status.HTTP_200_OK, "message": "Not all groups have winners selected"}

                teams = make_shuffle(teams)
                match_type = "Elimination Round" if len(teams) > 4 else "Semi Final" if len(teams) == 4 else "Final"
                sets = set_num_f if len(teams) == 2 else set_num_e
                courts = court_num_f if len(teams) == 2 else court_num_e
                points = point_num_f if len(teams) == 2 else point_num_e
                round_number = 0 if match_type in ["Semi Final", "Final"] else 1

                court_num = 0
                match_number_now = last_match_number
                for i in range(0, len(teams), 2):
                    court_num = (court_num % courts) + 1
                    match_number_now += 1
                    create_tournament_match(
                        event, teams[i], teams[i+1], match_type, round_number,
                        court_num, sets, points, match_number_now
                    )
                return {"status": status.HTTP_200_OK, "message": f"Matches are created for {match_type}"}
            elif last_match_type in ["Elimination Round", "Semi Final"]:
                teams = list(Tournament.objects.filter(leagues=event, match_type=last_match_type).values_list("winner_team_id", flat=True))
                if len(teams) != len(Tournament.objects.filter(leagues=event, match_type=last_match_type)):
                    return {"status": status.HTTP_200_OK, "message": "Not all groups have winners selected"}

                match_type = "Final" if len(teams) == 2 else "Semi Final" if len(teams) == 4 else "Elimination Round"
                sets = set_num_f if len(teams) == 2 else set_num_e
                courts = court_num_f if len(teams) == 2 else court_num_e
                points = point_num_f if len(teams) == 2 else point_num_e
                round_number = 0 if match_type in ["Semi Final", "Final"] else last_round + 1

                random.shuffle(teams)
                court_num = 0
                match_number_now = last_match_number
                for i in range(0, len(teams), 2):
                    court_num = (court_num % courts) + 1
                    match_number_now += 1
                    create_tournament_match(
                        event, teams[i], teams[i+1], match_type, round_number,
                        court_num, sets, points, match_number_now
                    )
                return {"status": status.HTTP_200_OK, "message": f"Matches are created for {match_type} {round_number}"}
            elif last_match_type == "Final":
                return {"status": status.HTTP_200_OK, "message": "The event results are out! The event is completed successfully."}
        return {"status": status.HTTP_200_OK, "message": "All matches in this round are not completed yet."}
    else:
        group_result = create_group(team_ids, court_num_r)
        if group_result["status"] != status.HTTP_200_OK:
            return group_result

        group_list = group_result["groups"]
        round_robin_group_details = RoundRobinGroup.objects.filter(league_for=event)
        if round_robin_group_details.count() == court_num_r:
            return {"status": status.HTTP_200_OK, "message": f"Round Robin matches already created for {event.name}"}
        round_robin_group_details.delete()

        serial_number = 0
        for index, group_teams in enumerate(group_list, start=1):
            group = RoundRobinGroup.objects.create(court=index, league_for=event, number_sets=set_num_r)
            for team_id in group_teams:
                group.all_teams.add(Team.objects.get(id=team_id))

            match_combinations = [(team1, team2) for i, team1 in enumerate(group_teams) for team2 in group_teams[i+1:]]
            random.shuffle(match_combinations)
            for team1, team2 in match_combinations:
                serial_number += 1
                create_tournament_match(
                    event, team1, team2, "Round Robin", 0,
                    index, set_num_r, point_num_r, serial_number, group.id
                )
        return {"status": status.HTTP_200_OK, "message": "Matches are created successfully"}

def select_top_teams(event):
    """Select top two teams from each group based on points and score."""
    all_group_details = RoundRobinGroup.objects.filter(league_for=event)
    teams = []
    for grp in all_group_details:
        teams_ins = grp.all_teams.all()
        group_score_point_table = []
        for team in teams_ins:
            team_score = {}
            total_match_detals = Tournament.objects.filter(leagues=event).filter(Q(team1=team) | Q(team2=team))
            completed_match_details = total_match_detals.filter(is_completed=True)
            win_match_details = completed_match_details.filter(winner_team=team).count()
            loss_match_details = completed_match_details.filter(loser_team=team).count()
            drow_match = len(completed_match_details) - (win_match_details + loss_match_details)
            point = (win_match_details * 3) + (drow_match * 1)
            match_list = list(total_match_detals.values_list("id", flat=True))
            for_score = aginst_score = 0
            for sc in match_list:
                co_team_position = Tournament.objects.filter(id=sc).first()
                set_score = TournamentSetsResult.objects.filter(tournament_id=sc)
                if co_team_position.team1 == team:
                    for_score += sum(list(set_score.values_list("team1_point", flat=True)))
                    aginst_score += sum(list(set_score.values_list("team2_point", flat=True)))
                else:
                    for_score += sum(list(set_score.values_list("team2_point", flat=True)))
                    aginst_score += sum(list(set_score.values_list("team1_point", flat=True)))
            team_score.update({
                "uuid": team.uuid, "secret_key": team.secret_key,
                "completed_match": len(completed_match_details),
                "win_match": win_match_details, "loss_match": loss_match_details,
                "drow_match": drow_match, "for_score": for_score,
                "aginst_score": aginst_score, "point": point
            })
            group_score_point_table.append(team_score)

        grp_team = sorted(group_score_point_table, key=lambda x: (x['point'], x['for_score']), reverse=True)
        top_two_teams = grp_team[:2]
        teams_ = [Team.objects.get(uuid=top_team["uuid"], secret_key=top_team["secret_key"]).id for top_team in top_two_teams]
        teams.append(teams_)
        RoundRobinGroup.objects.filter(id=grp.id).update(seleced_teams=Team.objects.get(uuid=grp_team[0]["uuid"], secret_key=grp_team[0]["secret_key"]))
    return teams

def handle_round_robin(event, team_ids, playtype_details):
    """Handle Round Robin tournament logic."""
    court_num_r = int(playtype_details[0]["number_of_courts"])
    set_num_r = int(playtype_details[0]["sets"])
    point_num_r = int(playtype_details[0]["point"])

    if len(team_ids) != event.max_number_team:
        return {"status": status.HTTP_200_OK, "message": "All teams are not registered"}

    group_result = create_group(team_ids, 1)
    if group_result["status"] != status.HTTP_200_OK:
        return group_result

    group_list = group_result["groups"]
    round_robin_group_details = RoundRobinGroup.objects.filter(league_for=event)
    if round_robin_group_details.count() == 1:
        return {"status": status.HTTP_200_OK, "message": f"Round Robin group already created for {event.name}"}
    round_robin_group_details.delete()

    serial_number = 0
    for index, group_teams in enumerate(group_list, start=1):
        group = RoundRobinGroup.objects.create(court=index, league_for=event, number_sets=set_num_r)
        for team_id in group_teams:
            group.all_teams.add(Team.objects.get(id=team_id))

        match_combinations = [(team1, team2) for i, team1 in enumerate(group_teams) for team2 in group_teams[i+1:]]
        random.shuffle(match_combinations)
        for team1, team2 in match_combinations:
            serial_number += 1
            create_tournament_match(
                event, team1, team2, "Round Robin", 0,
                index, set_num_r, point_num_r, serial_number, group.id
            )
    return {"status": status.HTTP_200_OK, "message": "Matches created for Round Robin"}

def handle_individual_match_play(event, team_ids, playtype_details):
    """Handle Individual Match Play tournament logic."""
    court_num_f = int(playtype_details[2]["number_of_courts"])
    set_num_f = int(playtype_details[2]["sets"])
    point_num_f = int(playtype_details[2]["point"])

    if Tournament.objects.filter(leagues=event, match_type="Individual Match Play").exists():
        return {"status": status.HTTP_200_OK, "message": "Matches are already created"}
    if len(team_ids) < 2:
        return {"status": status.HTTP_200_OK, "message": "Minimum 2 teams are needed for individual match play"}

    random.shuffle(team_ids)
    match_number_now = 0
    for court_num in range(1, court_num_f + 1):
        match_number_now = court_num
        for i in range(0, len(team_ids), 2):
            create_tournament_match(
                event, team_ids[i], team_ids[i+1], "Individual Match Play", 0,
                court_num, set_num_f, point_num_f, match_number_now
            )
    return {"status": status.HTTP_200_OK, "message": "Matches created for Individual Match Play"}

#### assign match end ###
## update score
@login_required(login_url="/user_side/")
def event_update_score(request, event_id):
    context = {}
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status_filter', '')
    
    event = get_object_or_404(Leagues, id=event_id)
    matches = Tournament.objects.filter(leagues=event).select_related('team1', 'team2', 'leagues')
    
    if query:
        matches = matches.filter(
            Q(match_number__icontains=query) |
            Q(team1__name__icontains=query) |
            Q(team2__name__icontains=query) |
            Q(match_type__icontains=query)
        )
    
    if status_filter:
        if status_filter == "completed":
            matches = matches.filter(is_completed=True)
        elif status_filter == "incompleted":
            matches = matches.filter(is_completed=False)
    
    # Optimize score fetching with prefetch_related
    # matches = matches.prefetch_related('tournamentsetsresult_set')
    
    for match_ in matches:
        match_.score = TournamentSetsResult.objects.filter(tournament=match_)
        match_.set_list = [i+1 for i in range(match_.set_number)]
    context["matches"] = matches
    context["event"] = event
    
    return render(request, 'sides/update_events_score.html', context=context)
### update score end


from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
import json

def update_event_winner(event, match):
    try:
        return True
    except Exception as e:
        return False

   
@login_required(login_url="/user_side/")
@require_POST
def update_match_scores(request, match_id):
    try:
        # Get the match
        match = get_object_or_404(Tournament, id=match_id)
        
        # Parse JSON data from request
        data = json.loads(request.body)
        scores = data.get('scores', [])
        # Update or create scores for each set
        for score in scores:
            set_number = score.get('set_number')
            team1_point = score.get('team1_point')
            team2_point = score.get('team2_point')
            
            # Ensure valid data
            if set_number is None or team1_point is None or team2_point is None:
                return JsonResponse({'success': False, 'error': 'Invalid score data'}, status=400)
            
            # Update or create TournamentSetsResult
            tournament_set, created = TournamentSetsResult.objects.get_or_create(
                tournament=match,
                set_number=set_number,
                defaults={
                    'team1_point': team1_point,
                    'team2_point': team2_point,
                    'is_completed': True,
                    'win_team': match.team1 if team1_point > team2_point else match.team2
                }
            )
            
            if not created:
                tournament_set.team1_point = team1_point
                tournament_set.team2_point = team2_point
                tournament_set.is_completed = True
                tournament_set.win_team = match.team1 if team1_point > team2_point else match.team2
                tournament_set.save()
        
        # Refresh match scores
        match.score = TournamentSetsResult.objects.filter(tournament=match)
        update_event_winner(event, match)
        # Prepare response data
        score_data = [
            {
                'set_number': score.set_number,
                'team1_point': score.team1_point,
                'team2_point': score.team2_point,
                'win_team': score.win_team.name if score.win_team else None
            } for score in match.score
        ]
        
        return JsonResponse({
            'success': True,
            'scores': score_data,
            'is_completed': match.is_completed,
            'team1_name': match.team1.name if match.team1 else '',
            'team2_name': match.team2.name if match.team2 else ''
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required(login_url="/user_side/")
@require_GET
def get_match_scores(request, match_id):
    try:
        match = get_object_or_404(Tournament, id=match_id)
        scores = TournamentSetsResult.objects.filter(tournament=match)
        
        score_data = [
            {
                'set_number': score.set_number,
                'team1_point': score.team1_point,
                'team2_point': score.team2_point
            } for score in scores
        ]
        
        return JsonResponse({
            'success': True,
            'scores': score_data,
            'team1_name': match.team1.name if match.team1 else '',
            'team2_name': match.team2.name if match.team2 else ''
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@login_required(login_url="/user_side/")
@require_POST
def update_tournament_settings(request, match_id):
    try:
        match = get_object_or_404(Tournament, id=match_id)
        
        # Ensure match is not completed
        if match.is_completed:
            return JsonResponse({'success': False, 'error': 'Cannot edit settings for a completed match'}, status=400)
        
        # Parse JSON data
        data = json.loads(request.body)
        set_number = data.get('set_number')
        points = data.get('points')
        
        # Validate data
        if not isinstance(set_number, int) or set_number < 1:
            return JsonResponse({'success': False, 'error': 'Invalid set number'}, status=400)
        if not isinstance(points, int) or points < 1:
            return JsonResponse({'success': False, 'error': 'Invalid points value'}, status=400)
        
        # Update match
        match.set_number = set_number
        match.points = points
        match.save()
        
        return JsonResponse({
            'success': True,
            'set_number': match.set_number,
            'points': match.points,
            'league_name': match.leagues.name if match.leagues else '',
            'court_num': match.court_num,
            'team1_name': match.team1.name if match.team1 else '',
            'team2_name': match.team2.name if match.team2 else '',
            'is_completed': match.is_completed
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


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

    user_teams = Team.objects.filter(created_by=request.user)
    teams = list(player.team.all()) + list(user_teams)
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
def user_wallet_foruser(request):
    start_date = request.GET.get("start_date", None)
    end_date = request.GET.get("end_date", None)
    page = request.GET.get("page", 1)  # Get the current page number from request
    
    wallet = Wallet.objects.filter(user=request.user)
    
    balance = 0.0
    transactions = WalletTransaction.objects.filter(Q(sender=request.user) | Q(reciver=request.user)).order_by("-created_at")
    if start_date and end_date:
        transactions = transactions.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
    #print(transactions)
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
        # #print("stripe.api_key", stripe.api_key)
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
        # #print("hgsdfhgsa")
        # Save to AllPaymentsTable with Pending Status
        AllPaymentsTable.objects.create(
            user=user,
            amount=amount / 100,  # Convert from cents to dollars
            checkout_session_id=session.id,
            payment_for="AddMoney",
            status="Pending",
        )
        # #print("jsgd")
        return JsonResponse({"id": session.id})


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


@csrf_exempt
def confirm_payment(request):
    if request.method == "POST":
        data = json.loads(request.body)
        event_id = data.get("event_id")
        team_ids = data.get("team_id_list", [])
        total_amount = float(data.get("total_amount", 0))
        #print(data)

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
            #print("Received Data:", data)
            event_id = data.get("event_id")
            team_ids = data.get("team_id_list", [])
            total_amount = data.get("total_amount", 0)

            try:
                total_amount = float(total_amount)  # Convert from string to float
            except ValueError:
                #print("Error: Invalid total_amount format:", total_amount)
                return JsonResponse({"success": False, "message": "Invalid total amount format."})

            unit_amount = int(total_amount * 100)  # Convert to cents

            if unit_amount <= 0:
                #print("Error: Amount cannot be zero or negative:", unit_amount)
                return JsonResponse({"success": False, "message": "Amount cannot be zero or negative."})

            #print("Final Amounts:", total_amount, unit_amount)

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

            #print("Session Created:", session)
            return JsonResponse({"success": True, "payment_url": session.url, "session_id": session.id})

        except Exception as e:
            #print("Stripe Error:", str(e))
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Invalid request."})


def stripe_success(request, event_id, team_ids, checkout_session_id):
    
    try:
        # Fetch session details from Stripe
        session = stripe.checkout.Session.retrieve(checkout_session_id)
        
        total_amount = Decimal(session.amount_total) / 100  # Convert cents to dollars
        #print(total_amount)
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
        #print(players)
        if category: 
            if category == "Women":
                players = players.filter(player__gender="Female")
            elif category == "Men":
                players = players.filter(player__gender="Male")
            else:
                players = players
            #print(players)

        player_data = [
            {
                "id": player.id,
                "name": player.player_full_name,
                "image": player.player.image.url if player.player.image else "/static/default-avatar.png"
            }
            for player in players
        ]
        #print(players)
        return JsonResponse({"players": player_data})

    return JsonResponse({"players": []})





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
    #print(event.team_type, event.team_person, event.play_type)   
    if play_type_details:
        play_type_details = play_type_details.first().data

    else:
        play_type_details = [
                    {"name": "Round Robin", "number_of_courts": 0, "sets": 0, "point": 0},
                    {"name": "Elimination", "number_of_courts": 0, "sets": 0, "point": 0},
                    {"name": "Final", "number_of_courts": 0, "sets": 0, "point": 0}
                    ]
    # #print(play_type_details, "play_type_details")    
    for se in play_type_details:
        #print(tournament_play_type, "tournament_play_type")
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
        else:
            # #print("hit")
            se["is_show"] = True 
        # #print(se, "se")
    # #print(play_type_details, "play_type_details")
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
        # #print(data_, "data")
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
        # #print("hit", data_)
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
        #print(form_data)
        
        total_amount = Decimal(session.amount_total) / 100  # Convert cents to dollars
        #print(total_amount)
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
    # #print('this function called')
    if request.method == "POST":
        data = json.loads(request.body)
        #print('Data received:', data)
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
        #print(request_data)
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
        #print('Data received:', data)
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
        #print('Data received:', data)
        club_id = data.get('club_id')
        club = Club.objects.filter(id=club_id).first()
        without_fees = float(data.get('remaining_amount'))
        remaining_amount = float(data.get("total_amount_with_fees"))

        total_charge = round(Decimal(remaining_amount), 2)
        charge_amount = round(float(total_charge * 100))
        stripe_fees = Decimal(remaining_amount - without_fees)

        #print(charge_amount)
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
            #print(type(get_wallet.balance), get_wallet.balance, type(club_amount), club_amount)
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




@login_required(login_url="/user_side/")
def subcription_plan(request):
    plan = [
            {
                "id": 4,
                "name": "Free Version",
                "price": 0.0,
                "description": "",
                "duration_days": 30,
                "product_id": "PICKLEIT",
                "features": [
                    {
                        "name": "Create Account",
                        "is_show": True
                    },
                    {
                        "name": "Create a Player Account",
                        "is_show": True
                    },
                    {
                        "name": "Create Teams",
                        "is_show": True
                    },
                    {
                        "name": "Join Teams",
                        "is_show": True
                    },
                    {
                        "name": "Find Courts",
                        "is_show": True
                    },
                    {
                        "name": "Buy Merchandise",
                        "is_show": True
                    },
                    {
                        "name": "See Advertisements",
                        "is_show": True
                    },
                    {
                        "name": "Live Brackets",
                        "is_show": True
                    },
                    {
                        "name": "Open Play - Schedule and use play",
                        "is_show": True
                    },
                    {
                        "name": "Match Me - Get matched with Other Players for Open Play, Find Other Players through Match Me",
                        "is_show": True
                    },
                    {
                        "name": "Share links from Pickleit on other social media platforms",
                        "is_show": True
                    },
                    {
                        "name": "Pop Up Notifications Opt In",
                        "is_show": True
                    },
                    {
                        "name": "See Social Feeds",
                        "is_show": True
                    },
                    {
                        "name": "Join Digital Club",
                        "is_show": True
                    },
                    {
                        "name": "DUPR Rank Integration",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit VIP Club",
                        "is_show": False
                    },
                    {
                        "name": "Pickleit Wallet & Rewards",
                        "is_show": False
                    },
                    {
                        "name": "Post on Pickleit Social Feeds",
                        "is_show": False
                    },
                    {
                        "name": "Manage Social Content",
                        "is_show": False
                    },
                    {
                        "name": "Create and Manage and Pay for Advertisements",
                        "is_show": False
                    },
                    {
                        "name": "Create and Manage and Send Promotions",
                        "is_show": False
                    },
                    {
                        "name": "Manage Store and Sell Items on Merchandise Store, Receive Payments",
                        "is_show": False
                    },
                    {
                        "name": "Create and Host 'Digital Clubs'",
                        "is_show": False
                    }
                ],
                "is_desable": True,
                "is_active": True,
                "expire_on": None
            },
            {
                "id": 6,
                "name": "Paid Version",
                "price": 2.99,
                "description": "",
                "duration_days": 30,
                "product_id": "pickleit_4",
                "features": [
                    {
                        "name": "Create Account",
                        "is_show": True
                    },
                    {
                        "name": "Create a Player Account",
                        "is_show": True
                    },
                    {
                        "name": "Create Teams",
                        "is_show": True
                    },
                    {
                        "name": "Join Teams",
                        "is_show": True
                    },
                    {
                        "name": "Find Courts",
                        "is_show": True
                    },
                    {
                        "name": "Buy Merchandise",
                        "is_show": True
                    },
                    {
                        "name": "See Advertisements",
                        "is_show": True
                    },
                    {
                        "name": "Live Brackets",
                        "is_show": True
                    },
                    {
                        "name": "Open Play - Schedule and use play",
                        "is_show": True
                    },
                    {
                        "name": "Match Me - Get matched with Other Players for Open Play, Find Other Players through Match Me",
                        "is_show": True
                    },
                    {
                        "name": "Share links from Pickleit on other social media platforms",
                        "is_show": True
                    },
                    {
                        "name": "Pop Up Notifications Opt In",
                        "is_show": True
                    },
                    {
                        "name": "See Social Feeds",
                        "is_show": True
                    },
                    {
                        "name": "Join Digital Club",
                        "is_show": True
                    },
                    {
                        "name": "DUPR Rank Integration",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit VIP Club",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit Wallet & Rewards",
                        "is_show": True
                    },
                    {
                        "name": "Post on Pickleit Social Feeds",
                        "is_show": False
                    },
                    {
                        "name": "Manage Social Content",
                        "is_show": False
                    },
                    {
                        "name": "Create and Manage and Pay for Advertisements",
                        "is_show": False
                    },
                    {
                        "name": "Create and Manage and Send Promotions",
                        "is_show": False
                    },
                    {
                        "name": "Manage Store and Sell Items on Merchandise Store, Receive Payments",
                        "is_show": False
                    },
                    {
                        "name": "Create and Host 'Digital Clubs'",
                        "is_show": False
                    }
                ],
                "is_desable": False,
                "is_active": False,
                "expire_on": None
            },
            {
                "id": 8,
                "name": "Pro Version",
                "price": 12.99,
                "description": "",
                "duration_days": 30,
                "product_id": "pickleit_6",
                "features": [
                    {
                        "name": "Create Account",
                        "is_show": True
                    },
                    {
                        "name": "Create a Player Account",
                        "is_show": True
                    },
                    {
                        "name": "Create Teams",
                        "is_show": True
                    },
                    {
                        "name": "Join Teams",
                        "is_show": True
                    },
                    {
                        "name": "Find Courts",
                        "is_show": True
                    },
                    {
                        "name": "Buy Merchandise",
                        "is_show": True
                    },
                    {
                        "name": "See Advertisements",
                        "is_show": True
                    },
                    {
                        "name": "Live Brackets",
                        "is_show": True
                    },
                    {
                        "name": "Open Play - Schedule and use play",
                        "is_show": True
                    },
                    {
                        "name": "Match Me - Get matched with Other Players for Open Play, Find Other Players through Match Me",
                        "is_show": True
                    },
                    {
                        "name": "Share links from Pickleit on other social media platforms",
                        "is_show": True
                    },
                    {
                        "name": "Pop Up Notifications Opt In",
                        "is_show": True
                    },
                    {
                        "name": "See Social Feeds",
                        "is_show": True
                    },
                    {
                        "name": "Join Digital Club",
                        "is_show": True
                    },
                    {
                        "name": "DUPR Rank Integration",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit VIP Club",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit Wallet & Rewards",
                        "is_show": True
                    },
                    {
                        "name": "Post on Pickleit Social Feeds",
                        "is_show": True
                    },
                    {
                        "name": "Manage Social Content",
                        "is_show": True
                    },
                    {
                        "name": "Create and Manage and Pay for Advertisements",
                        "is_show": False
                    },
                    {
                        "name": "Create and Manage and Send Promotions",
                        "is_show": False
                    },
                    {
                        "name": "Manage Store and Sell Items on Merchandise Store, Receive Payments",
                        "is_show": False
                    },
                    {
                        "name": "Create and Host 'Digital Clubs'",
                        "is_show": False
                    }
                ],
                "is_desable": False,
                "is_active": False,
                "expire_on": None
            },
            {
                "id": 10,
                "name": "Enterprise Version",
                "price": 59.99,
                "description": "",
                "duration_days": 30,
                "product_id": "pickleit_8",
                "features": [
                    {
                        "name": "Create Account",
                        "is_show": True
                    },
                    {
                        "name": "Create a Player Account",
                        "is_show": True
                    },
                    {
                        "name": "Create Teams",
                        "is_show": True
                    },
                    {
                        "name": "Join Teams",
                        "is_show": True
                    },
                    {
                        "name": "Find Courts",
                        "is_show": True
                    },
                    {
                        "name": "Buy Merchandise",
                        "is_show": True
                    },
                    {
                        "name": "See Advertisements",
                        "is_show": True
                    },
                    {
                        "name": "Live Brackets",
                        "is_show": True
                    },
                    {
                        "name": "Open Play - Schedule and use play",
                        "is_show": True
                    },
                    {
                        "name": "Match Me - Get matched with Other Players for Open Play, Find Other Players through Match Me",
                        "is_show": True
                    },
                    {
                        "name": "Share links from Pickleit on other social media platforms",
                        "is_show": True
                    },
                    {
                        "name": "Pop Up Notifications Opt In",
                        "is_show": True
                    },
                    {
                        "name": "See Social Feeds",
                        "is_show": True
                    },
                    {
                        "name": "Join Digital Club",
                        "is_show": True
                    },
                    {
                        "name": "DUPR Rank Integration",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit VIP Club",
                        "is_show": True
                    },
                    {
                        "name": "Pickleit Wallet & Rewards",
                        "is_show": True
                    },
                    {
                        "name": "Post on Pickleit Social Feeds",
                        "is_show": True
                    },
                    {
                        "name": "Manage Social Content",
                        "is_show": True
                    },
                    {
                        "name": "Create and Manage and Pay for Advertisements",
                        "is_show": True
                    },
                    {
                        "name": "Create and Manage and Send Promotions",
                        "is_show": True
                    },
                    {
                        "name": "Manage Store and Sell Items on Merchandise Store, Receive Payments",
                        "is_show": True
                    },
                    {
                        "name": "Create and Host 'Digital Clubs'",
                        "is_show": True
                    }
                ],
                "is_desable": False,
                "is_active": False,
                "expire_on": None
            }
        ]
    STRIPE_PUBLISHABLE_KEY = settings.STRIPE_PUBLIC_KEY
    return render(request, "sides/subcription_plan.html", {"plans": plan, "STRIPE_PUBLISHABLE_KEY": STRIPE_PUBLISHABLE_KEY})

# Set Stripe API key
stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def create_checkout_session_subcription(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    user = request.user

    try:
        # Create or retrieve Stripe customer
        if not hasattr(user, 'stripe_customer_id') or not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
            )
            user.stripe_customer_id = customer.id
            user.save()

        # Create a Stripe Checkout Session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': plan.name,
                    },
                    'unit_amount': int(plan.price * 100),  # Convert to cents
                    'recurring': {
                        'interval': 'month',
                        'interval_count': 1 if plan.duration_days == 30 else int(plan.duration_days / 30),
                    },
                },
                'quantity': 1,
            }],
            mode='subscription',
            customer=user.stripe_customer_id,
            success_url=request.build_absolute_uri(
                reverse('user_side:payment_success') + '?session_id={CHECKOUT_SESSION_ID}'
            ),
            cancel_url=request.build_absolute_uri(
                reverse('user_side:payment_cancel') + '?session_id={CHECKOUT_SESSION_ID}'
            ),
            metadata={
                'plan_id': plan.id,
                'user_id': user.id,
            },
        )

        # Create a pending transaction
        Transaction.objects.create(
            user=user,
            plan=plan,
            transaction_id=session.id,
            platform='stripe',
            status=Transaction.PENDING,
            receipt_data=json.dumps({'checkout_session_id': session.id}),
        )

        return JsonResponse({'sessionId': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def payment_success_membership(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return render(request, 'payments/error.html', {'message': 'Invalid session ID'})

    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        transaction = Transaction.objects.get(transaction_id=session_id)
        user = transaction.user
        plan = transaction.plan

        if session.payment_status == 'paid' and session.status == 'complete':
            # Update transaction to success
            transaction.status = Transaction.SUCCESS
            transaction.receipt_data = json.dumps(session)
            transaction.save()

            # Create or update subscription
            subscription, created = Subscription.objects.get_or_create(
                user=user,
                defaults={
                    'plan': plan,
                    'start_date': make_aware(datetime.now()),
                    'end_date': make_aware(datetime.now()) + timedelta(days=plan.duration_days),
                    'is_active': True,
                }
            )
            if not created:
                subscription.plan = plan
                subscription.end_date = make_aware(datetime.now()) + timedelta(days=plan.duration_days)
                subscription.is_active = True
                subscription.save()

            return render(request, 'payments/sub_success.html', {'plan': plan})
        else:
            # Update transaction to failed
            transaction.status = Transaction.FAILED
            transaction.receipt_data = json.dumps(session)
            transaction.save()
            return render(request, 'payments/error.html', {'message': 'Payment was not completed'})
    except stripe.error.StripeError as e:
        return render(request, 'payments/error.html', {'message': f'Stripe error: {str(e)}'})
    except Transaction.DoesNotExist:
        return render(request, 'payments/error.html', {'message': 'Transaction not found'})

@login_required
def payment_cancel_membership(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return render(request, 'payments/error.html', {'message': 'Invalid session ID'})

    try:
        # Retrieve the session from Stripe
        session = stripe.checkout.Session.retrieve(session_id)
        transaction = Transaction.objects.get(transaction_id=session_id)

        # Update transaction to failed
        transaction.status = Transaction.FAILED
        transaction.receipt_data = json.dumps(session)
        transaction.save()

        return render(request, 'payments/sub_cancel.html', {'message': 'Payment was canceled'})
    except stripe.error.StripeError as e:
        return render(request, 'payments/error.html', {'message': f'Stripe error: {str(e)}'})
    except Transaction.DoesNotExist:
        return render(request, 'payments/error.html', {'message': 'Transaction not found'})


@login_required
def social_feed(request):
    # Subquery to check if the user has liked each post
    user_likes = LikeFeed.objects.filter(
        user=request.user, post=OuterRef('pk')
    )
    
    # Annotate posts with is_like
    posts = socialFeed.objects.filter(block=False).annotate(is_like=Exists(user_likes)).order_by('-created_at')
    print(posts)
    paginator = Paginator(posts, 50)  # Show 50 posts per page
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'sides/social_feed.html', {'page_obj': page_obj})

@login_required
def add_post(request):
    if request.method == 'POST':
        text = request.POST.get('text')
        file = request.FILES.get('file')
        post = socialFeed.objects.create(user=request.user, text=text)
        if file:
            FeedFile.objects.create(post=post, file=file)
        messages.success(request, 'Post created successfully!')
        return redirect('user_side:socail_feed_list')
    return render(request, 'sides/social_feed.html')

@login_required
def like_post(request, post_id):
    post = get_object_or_404(socialFeed, id=post_id)
    like, created = LikeFeed.objects.get_or_create(post=post, user=request.user)
    if not created:
        like.delete()
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('user_side:socail_feed_list')))

@login_required
def like_post_ajax(request, post_id):
    if request.method == 'POST':
        post = get_object_or_404(socialFeed, id=post_id)
        like = LikeFeed.objects.filter(post=post, user=request.user)
        if like:
           like.delete()
           post.number_like = post.number_like - 1
           is_liked = False
        else:
            LikeFeed.objects.create(post=post, user=request.user) 
            is_liked = True
        post.save()
        like_count = post.number_like  # Assuming number_like is a property or method
        return JsonResponse({
            'is_liked': is_liked,
            'like_count': like_count,
        })
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(socialFeed, id=post_id)
    if request.method == 'POST':
        comment_text = request.POST.get('comment_text')
        if comment_text:
            CommentFeed.objects.create(post=post, user=request.user, comment_text=comment_text)
            messages.success(request, 'Comment added successfully!')
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('user_side:socail_feed_list')))

@login_required
def view_post(request, post_id):
    post = get_object_or_404(socialFeed, id=post_id, block=False)
    comments = post.post_comment.all().order_by('-created_at')
    return render(request, 'sides/view_post.html', {'post': post, 'comments': comments})




######open play section
@login_required
def openplay_form(request):
    return render(request, 'sides/open_play_list.html')



