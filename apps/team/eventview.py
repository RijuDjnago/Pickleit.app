import os
import json
import email
from datetime import timedelta
from itertools import combinations
from apps.team.views import notify_edited_player
import random, json, base64, stripe # type: ignore
from math import radians, cos, sin, asin, sqrt
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_DOWN
from apps.user.models import *
from apps.chat.models import *
from apps.team.models import *
from apps.user.helpers import *
from django.db.models import Q
from apps.team.serializers import *
from apps.pickleitcollection.models import *
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from django.core.cache.backends.base import DEFAULT_TIMEOUT
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.pagination import PageNumberPagination

protocol = settings.PROTOCALL
stripe.api_key = settings.STRIPE_PUBLIC_KEY
CACHE_TTL = getattr(settings, 'CACHE_TTL', DEFAULT_TIMEOUT)

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, '%Y-%m-%d')  # Change format if needed
    except ValueError:
        raise ValueError(f"Invalid date format: '{date_str}'. Expected format: YYYY-MM-DD")

#create event api
@api_view(('POST',))
def create_leagues(request):
    data = {'status':'','data':[],'message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        name = request.data.get('name')
        leagues_start_date = request.data.get('leagues_start_date')
        leagues_end_date = request.data.get('leagues_end_date')
        registration_start_date = request.data.get('registration_start_date')
        registration_end_date = request.data.get('registration_end_date')
        team_type = request.data.get('team_type')
        play_type = request.data.get('play_type')
        team_person = request.data.get('team_person')
        location = request.data.get('location')
        city = request.data.get('city')
        others_fees = request.data.get('others_fees')
        max_number_team = request.data.get('max_number_team')
        registration_fee = request.data.get('registration_fee')
        description = request.data.get('description')
        image = request.FILES.get('image')
        team_type = json.loads(team_type)
        team_person = json.loads(team_person)
        others_fees = json.loads(others_fees)
        league_type = request.data.get('league_type')
        invited_code = request.data.get('invited_code', None)
        latitude = request.data.get('latitude', None)
        longitude = request.data.get('longitude', None)
        start_rank = request.data.get('start_rank') 
        end_rank = request.data.get('end_rank')       
        
        if int(max_number_team) % 2 != 0 or int(max_number_team) == 0 or int(max_number_team) == 1:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Max number of team must be even"
            return Response(data)
        leagues_start_date = datetime.strptime(leagues_start_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        leagues_end_date = datetime.strptime(leagues_end_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        registration_start_date = datetime.strptime(registration_start_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        registration_end_date = datetime.strptime(registration_end_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        leagues_id = []
        if check_user.exists():
            mesage_box = []
            counter = 0
            for kk in team_type:
                check_leagues = LeaguesTeamType.objects.filter(name=str(kk))
                check_person = LeaguesPesrsonType.objects.filter(name=str(team_person[counter]))
                
                if check_leagues.exists() and check_person.exists():
                    check_leagues_id = check_leagues.first().id
                    check_person_id = check_person.first().id
                    check_unq = Leagues.objects.filter(team_person_id=check_person_id,team_type_id=check_leagues_id,name=name,created_by=check_user.first())
                    if check_unq.exists():
                        message = f"{name}-{kk}"
                        mesage_box.append(message)
                        continue
                    else:
                        pass
                obj = GenerateKey()
                secret_key = obj.gen_leagues_key()
                save_leagues = Leagues(secret_key=secret_key,name=name,leagues_start_date=leagues_start_date,leagues_end_date=leagues_end_date,location=location,
                                    registration_start_date=registration_start_date,registration_end_date=registration_end_date,created_by_id=check_user.first().id,
                                    city=city,max_number_team=max_number_team, play_type=play_type,
                                    registration_fee=registration_fee,description=description,image=image,league_type=league_type)
                if league_type == "Invites only":
                    save_leagues.invited_code = invited_code 
                cleaned_others_fees = {k: v for k, v in others_fees.items() if k and v is not None}
                save_leagues.others_fees = cleaned_others_fees
                # save_leagues.others_fees = others_fees
                save_leagues.save() 
                
                # if lat is not None and long is not None:
                save_leagues.latitude=latitude
                save_leagues.longitude=longitude
                save_leagues.save()
                if start_rank and end_rank:
                    save_leagues.any_rank = False
                    save_leagues.start_rank = start_rank
                    save_leagues.end_rank = end_rank
                    save_leagues.save()
                counter = counter+1
                if check_leagues.exists() and check_person.exists():
                    check_leagues_id = check_leagues.first().id
                    check_person_id = check_person.first().id
                    save_leagues.team_type_id = check_leagues_id
                    save_leagues.team_person_id = check_person_id
                    save_leagues.save()
                leagues_id.append(save_leagues.id)
                
            result = []
            for dat in leagues_id:
                main_data = Leagues.objects.filter(id=dat)
                tournament_play_type = play_type
                data_structure = [{"name": "Round Robin", "number_of_courts": 0, "sets": 0, "point": 0},
                          {"name": "Elimination", "number_of_courts": 0, "sets": 0, "point": 0},
                          {"name": "Final", "number_of_courts": 0, "sets": 0, "point": 0}]
                for se in data_structure:
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
                pt = LeaguesPlayType.objects.create(type_name=save_leagues.play_type,league_for=main_data.first(),data=data_structure)
                main_data = main_data.values()
                for i in main_data:
                    i["team_type"] = LeaguesTeamType.objects.filter(id = i["team_type_id"]).first().name
                    i["team_person"] = LeaguesPesrsonType.objects.filter(id = i["team_person_id"]).first().name
                    user_first_name = check_user.first().first_name
                    user_last_name = check_user.first().last_name
                    i["created_by"] = f"{user_first_name} {user_last_name}"
                    i["play_type_data"] = list(LeaguesPlayType.objects.filter(id=pt.id).values())
                    del i ["team_person_id"]
                    del i ["team_type_id"]
                    del i ["created_by_id"]
                result.append(main_data[0])
            message = ""
            if len(mesage_box) != 0:
                for ij in mesage_box:
                    if message == "":
                        message = message+ij
                    else:
                        message = message + "," +ij
                if len(mesage_box) == 1:
                    set_msg = f"{message} tournament already exists"
                elif len(mesage_box) > 1:
                    set_msg = f"{message} tournaments already exist"
            else:
                set_msg = "Tournament created successfully"
            data["status"], data["data"],data["message"] = status.HTTP_200_OK, result, set_msg
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

@api_view(('POST',))
def create_play_type_details(request):
    data = {'status':'','data':[],'message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        total_data = request.data.get('data')
        is_policy = request.data.get('is_policy', False)
        l_uuids = request.data.get('l_uuids', [])
        policy_data = request.data.get('policy_data', [])
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() and check_user.first().is_admin or check_user.first().is_organizer:
            my_result = []
            # print(len(total_data))
            for fo in total_data:
                l_uuid = fo["l_uuid"]
                l_secret_key = fo["l_secret_key"]
                get_data = fo["data"]
                Leagues_check = Leagues.objects.filter(uuid=l_uuid, secret_key=l_secret_key)
                if Leagues_check.exists:
                    get_league = Leagues_check.first()
                    pt = LeaguesPlayType.objects.filter(league_for=get_league)
                    pt.update(data=get_data)
                    #league_data
                    league_data = Leagues_check.values()
                    # print(league_data)
                    for i in league_data:
                        i["team_type"] = LeaguesTeamType.objects.filter(id = i["team_type_id"]).first().name
                        i["team_person"] = LeaguesPesrsonType.objects.filter(id = i["team_person_id"]).first().name
                        user_first_name = check_user.first().first_name
                        user_last_name = check_user.first().last_name
                        i["created_by"] = f"{user_first_name} {user_last_name}"
                        i["play_type_data"] = list(LeaguesPlayType.objects.filter(id=pt.first().id).values())
                        del i ["team_person_id"]
                        del i ["team_type_id"]
                        del i ["created_by_id"]
                    # print(league_data[0])
                    my_result.append(league_data[0])
                else:
                    my_result.append({"error":"League not found"})
            
            if is_policy is True:
                for i_uuid in l_uuids:
                    # try:
                    get_league = Leagues.objects.filter(uuid=i_uuid).first()
                    get_league.policy = is_policy
                    get_league.save()
                    for p_data in policy_data:
                        add_league_policy = LeaguesCancellationPolicy(league=get_league, within_day=p_data["within_day"], refund_percentage=p_data["percentage"])
                        add_league_policy.save()
                    # except:
                    #     pass



            data["status"],data["data"], data["message"] = status.HTTP_200_OK,my_result,"Created playtype successfully"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

#event list api(keyword and location based search)
@api_view(('GET',))
def list_leagues_admin(request):
    data = {'status':'','data':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        filter_by = request.GET.get('filter_by', None)
        search_text = request.GET.get('search_text')
        '''
        registration_open, future, past
        '''
        user = get_object_or_404(User, uuid=user_uuid)
        today_date = datetime.now()
        
        events = Leagues.objects.exclude(team_type__name ='Open-team')
        if filter_by == "future" :
            events = events.filter(Q(registration_start_date__date__lte=today_date, registration_end_date__date__gte=today_date) | Q(registration_start_date__date__gte=today_date))
        elif filter_by == "past" :
            events = events.filter(leagues_end_date__date__lte=today_date, is_complete=True)
        elif filter_by == "registration_open" :
            events = events.filter(leagues_start_date__date__lte=today_date, leagues_end_date__date__gte=today_date, is_complete=False)
        if search_text:
            events = events.filter(Q(name__icontains=search_text) & Q(is_created=True)).order_by('-id')

        events_list = events.values('id','uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name','any_rank','start_rank','end_rank',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude","image", "others_fees", "league_type","registration_fee")

        output = []
        grouped_data = {}
        for item in list(events_list):
            item["is_reg_diable"] = True
            match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
            if match_.exists():
                item["is_reg_diable"] = False
            le = Leagues.objects.filter(id=item["id"]).first()
            reg_team =le.registered_team.all().count()
            max_team = le.max_number_team
            if max_team <= reg_team:
                item["is_reg_diable"] = False
            key = item['name']
            if key not in grouped_data:
                grouped_data[key] = {
                                    'name': item['name'], 
                                    'lat':item['latitude'], 
                                    'long':item["longitude"],
                                    'registration_start_date':item["registration_start_date"],
                                    'registration_end_date':item["registration_end_date"],
                                    'leagues_start_date':item["leagues_start_date"],
                                    'leagues_end_date':item["leagues_end_date"],
                                    'location':item["location"],
                                    'image':item["image"],
                                    'type': [item['team_type__name']], 
                                    'data': [item]
                                    }
            else:
                grouped_data[key]['type'].append(item['team_type__name'])
                grouped_data[key]['data'].append(item)

        # Building the final output
        for key, value in grouped_data.items():
            output.append(value)

        # print(output)
        events_list = output

        for item in events_list:
            item["data"] = sorted(item["data"], key=lambda x: x["id"], reverse=True)

        # Sort the main list based on the 'id' of the first item in the 'data' list
        leagues_sorted = sorted(events_list, key=lambda x: x["data"][0]["id"], reverse=True)     
        paginator = PageNumberPagination()
        paginator.page_size = 5 
        result_page = paginator.paginate_queryset(leagues_sorted, request)    
        paginated_response = paginator.get_paginated_response(result_page)    
        data["status"] = status.HTTP_200_OK
        data["count"] = paginated_response.data["count"]
        data["previous"] = paginated_response.data["previous"]
        data["next"] = paginated_response.data["next"]
        data["data"] = paginated_response.data["results"]
        data["message"] = "Data found" 
        return Response(data)
    except Exception as e:
        data["status"] = status.HTTP_200_OK
        data["count"] = None
        data["previous"] = None
        data["next"] = None
        data["data"] = []
        data["message"] = str(e) 
        return Response(data)
            

@api_view(('GET',))
def my_league(request):
    data = {'status':'','data':[], 'message':''}
    try:
        user_uuid = request.GET.get('user_uuid')
        filter_by = request.GET.get('filter_by', None)
        search_text = request.GET.get('search_text')
        '''
        registration_open, future, past
        '''
        user = get_object_or_404(User, uuid=user_uuid)
        today_date = datetime.now()
        
        events = Leagues.objects.filter(created_by=user)
        if filter_by == "future" :
            events = events.filter(Q(registration_start_date__date__lte=today_date, registration_end_date__date__gte=today_date) | Q(registration_start_date__date__gte=today_date))
        elif filter_by == "past" :
            events = events.filter(leagues_end_date__date__lte=today_date, is_complete=True)
        elif filter_by == "registration_open" :
            events = events.filter(leagues_start_date__date__lte=today_date, leagues_end_date__date__gte=today_date, is_complete=False)
        if search_text:
            events = events.filter(Q(name__icontains=search_text) & Q(is_created=True)).order_by('-id')

        events_list = events.values('id','uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name','any_rank','start_rank','end_rank',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude","image", "others_fees", "league_type","registration_fee")

        output = []
        grouped_data = {}
        for item in list(events_list):
            item["is_reg_diable"] = True
            match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
            if match_.exists():
                item["is_reg_diable"] = False
            le = Leagues.objects.filter(id=item["id"]).first()
            reg_team =le.registered_team.all().count()
            max_team = le.max_number_team
            if max_team <= reg_team:
                item["is_reg_diable"] = False
            key = item['name']
            if key not in grouped_data:
                grouped_data[key] = {
                                    'name': item['name'], 
                                    'lat':item['latitude'], 
                                    'long':item["longitude"],
                                    'registration_start_date':item["registration_start_date"],
                                    'registration_end_date':item["registration_end_date"],
                                    'leagues_start_date':item["leagues_start_date"],
                                    'leagues_end_date':item["leagues_end_date"],
                                    'location':item["location"],
                                    'image':item["image"],
                                    'type': [item['team_type__name']], 
                                    'data': [item]
                                    }
            else:
                grouped_data[key]['type'].append(item['team_type__name'])
                grouped_data[key]['data'].append(item)

        # Building the final output
        for key, value in grouped_data.items():
            output.append(value)

        # print(output)
        events_list = output

        for item in events_list:
            item["data"] = sorted(item["data"], key=lambda x: x["id"], reverse=True)

        # Sort the main list based on the 'id' of the first item in the 'data' list
        leagues_sorted = sorted(events_list, key=lambda x: x["data"][0]["id"], reverse=True)     
        paginator = PageNumberPagination()
        paginator.page_size = 5 
        result_page = paginator.paginate_queryset(leagues_sorted, request)    
        paginated_response = paginator.get_paginated_response(result_page)    
        data["status"] = status.HTTP_200_OK
        data["count"] = paginated_response.data["count"]
        data["previous"] = paginated_response.data["previous"]
        data["next"] = paginated_response.data["next"]
        data["data"] = paginated_response.data["results"]
        data["message"] = "Data found" 
        return Response(data)
    except Exception as e:
        data["status"] = status.HTTP_200_OK
        data["count"] = None
        data["previous"] = None
        data["next"] = None
        data["data"] = []
        data["message"] = str(e) 
        return Response(data)


#view event apies
#view event for edit
@api_view(['GET'])
def view_leagues_for_edit(request):
    response = {
        'data': [],
        'name': None,
        'person_type': None,
        'play_type':None,
        'team_type': None,
        'max_number_team': None,
        'location': None,
        'latitude': None,
        'longitude': None,
        'leagues_start_date': None,
        'leagues_end_date': None,
        'registration_start_date': None,
        'registration_end_date': None,
        'tournament_details': [],
        'status': '',
        'message': '',
    }

    try:
        user_uuid = request.GET.get('user_uuid')
        league_uuid = request.GET.get('league_uuid')

        if not user_uuid or not league_uuid:
            raise ValueError("Both 'user_uuid' and 'league_uuid' are required.")

        user = get_object_or_404(User, uuid=user_uuid)
        league = get_object_or_404(Leagues, uuid=league_uuid)

        t_details = LeaguesPlayType.objects.filter(league_for=league)
        if t_details.exists():
            playtype = t_details.first()
            data_structure = playtype.data
        else:
            data_structure = [
                {"name": "Round Robin", "number_of_courts": 0, "sets": 0, "point": 0, "is_show": True},
                {"name": "Elimination", "number_of_courts": 0, "sets": 0, "point": 0, "is_show": True},
                {"name": "Final", "number_of_courts": 0, "sets": 0, "point": 0, "is_show": True}
            ]

        response.update({
            'name': league.name,
            'person_type': league.team_person.name,
            'team_type': league.team_type.name,
            'play_type':league.play_type,
            'max_number_team': league.max_number_team,
            'location': league.location,
            'latitude': league.latitude,
            'longitude': league.longitude,
            'leagues_start_date': league.leagues_start_date,
            'leagues_end_date': league.leagues_end_date,
            'registration_start_date': league.registration_start_date,
            'registration_end_date': league.registration_end_date,
            'tournament_details': data_structure,
            'status': status.HTTP_200_OK,
            'message': "Data Found"
        })

    except Exception as e:
        response['status'] = status.HTTP_400_BAD_REQUEST
        response['message'] = str(e)

    return Response(response)

@api_view(('GET',))
def view_playtype_details(request):    
    data = {
            'status':'',
            'create_group_status':False,
            'max_team': None,
            'total_register_team':None,
            'is_organizer': False,
            'is_register':False,
            'sub_organizer_data':[],
            'organizer_name_data':[],
            'invited_code':None,
            'winner_team': 'Not Declared',
            'data':[],
            'tournament_detais':[],
            'message':''            
            }
    user_uuid = request.GET.get('user_uuid')
    user_secret_key = request.GET.get('user_secret_key')
    league_uuid = request.GET.get('league_uuid')
    league_secret_key = request.GET.get('league_secret_key')
    protocol = 'https'
    host = request.get_host()
    media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
    '''
    registration_open, future, past
    '''
    check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
    check_leagues = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
    if check_user.exists() and check_leagues.exists():
        leagues = check_leagues.values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                            'registration_start_date','registration_end_date','team_type__name','team_person__name',
                            "street","city","state","postal_code","country","complete_address","latitude","longitude","play_type","registration_fee","description","image","others_fees", "league_type")
        league = check_leagues.first()
        get_user = check_user.first()
        today_date = datetime.today().date()
        if league.registration_end_date not in [None, "null", "", "None"]:
            if league.registration_end_date.date() >= today_date and league.league_type != "Invites only" and league.max_number_team > league.registered_team.count() and not league.is_complete:
                data["is_register"] = True
        
        organizers = list(User.objects.filter(id=league.created_by.id).values('id','uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code'))
        sub_organizer_data = list(league.add_organizer.all().values('id','uuid','secret_key','username','first_name','last_name','email','phone','gender','user_birthday','role','rank','image','street','city','state','country','postal_code'))
        
        organizer_list = organizers + sub_organizer_data
        for nu in organizer_list:
            nu["phone"] = str(nu["phone"])
        data['sub_organizer_data'] = organizer_list
        
        organizer_list = []
        for org in data['sub_organizer_data']:
            first_name = org["first_name"]
            last_name = org["last_name"]
            if not first_name:
                first_name = " "
            if not last_name:
                last_name = " "
            name = f"{first_name} {last_name}"
            organizer_list.append(name)
        data['organizer_name_data'] = organizer_list

        sub_org_list = list(league.add_organizer.all().values_list("id", flat=True))  
        if get_user == league.created_by or get_user.id in sub_org_list:
            data['is_organizer'] =  True
            data['invited_code'] =  league.invited_code
        all_team = check_leagues.first().registered_team.all()
        
        teams = []
        for t in all_team:
            img_str = str(t.team_image) if t.team_image not in ["null", None, "", " "] else None
            if img_str:
                team_image = f"{media_base_url}{img_str}"
            else:
                team_image = "https://pickleit.app/static/images/pickleit_newlogo.jpg"
            player = list(Player.objects.filter(team=t).values_list("player_full_name", flat=True))
            teams.append({"team_uuid":t.uuid, "team_secret_key":t.secret_key, "name":t.name, "team_image": team_image, "person":t.team_person, "team_type":t.team_type, "player":player})
        
        today_date = date.today()
        try:
            check_days_for_cencel_registration = league.leagues_start_date.date() - today_date
        except:
            check_days_for_cencel_registration = 0 
        if isinstance(check_days_for_cencel_registration, int):
            day_left = check_days_for_cencel_registration
        else:
            day_left = check_days_for_cencel_registration.days
        if check_leagues.first().policy is True:
            cancilation_policy = list(LeaguesCancellationPolicy.objects.filter(league = check_leagues.first()).order_by('within_day').values("within_day","refund_percentage"))
            if not cancilation_policy:
                charge_refund_percentage_per_team = 100.0
            else:
                charge_refund_percentage_per_team = 0.0
            for roul in cancilation_policy:
                if int(day_left) >= int(roul["within_day"]):
                    charge_refund_percentage_per_team = roul["refund_percentage"]
        else:
            cancilation_policy = []
            charge_refund_percentage_per_team = 0.0
        #calculate fees
        fees = league.registration_fee
        others_fees = league.others_fees
        if others_fees:
            for val in others_fees.values():
                if isinstance(val, (int, float)):  # Ensure the value is numeric
                    fees += val
                elif isinstance(val, str) and val.isdigit():  # Convert string numbers
                    fees += int(val) 
        
        refund_amount = fees * (charge_refund_percentage_per_team/100)
        if league.leagues_start_date:
            data['is_cancel_button'] = league.leagues_start_date.date() > today_date
        else:
            data['is_cancel_button'] = False
        data['day_left'] = day_left
        data['refund_amount'] = refund_amount 
        data['fees'] = fees
        data['refund_parcentage'] = charge_refund_percentage_per_team
        data['teams'] = teams        
        data['max_team'] =  league.max_number_team
        data['total_register_team'] =  league.registered_team.all().count()
        data['tournament_detais'] = LeaguesPlayType.objects.filter(league_for = check_leagues.first()).values()
        data['cancellation_policy'] = cancilation_policy
        data["create_group_status"] = get_user.is_organizer and check_leagues.first().created_by == get_user
        data['data'] = leagues
        if league.winner_team:
            data['winner_team'] = league.winner_team.name
        data['message'] = "Play type details fetched successfully."
        data['status'] = status.HTTP_200_OK
    else:
        data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User or league not found."
    return Response(data)



@api_view(("GET",))
def view_match_details(request):
    data = {
             'status':'',             
             'message':'',
             'match':[]
             }
    user_uuid = request.GET.get('user_uuid')
    user_secret_key = request.GET.get('user_secret_key')
    league_uuid = request.GET.get('league_uuid')
    league_secret_key = request.GET.get('league_secret_key')
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
    '''
    registration_open, future, past
    '''
    check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
    check_leagues = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
    if check_user.exists() and check_leagues.exists():
        league = check_leagues.first()
        get_user = check_user.first()
        tournament_details = Tournament.objects.filter(leagues=check_leagues.first()).order_by("match_number").values("id","match_number","uuid","secret_key","leagues__name"
                                                                                                                        ,"team1_id", "team2_id", "team1__team_image", "team2__team_image", 
                                                                                                                        "team1__name", "team2__name", "winner_team_id", "winner_team__name", 
                                                                                                                        "playing_date_time","match_type","group__court","is_completed"
                                                                                                                        ,"elimination_round","court_sn","set_number","court_num","points","is_drow")
        
        sub_org_list = list(league.add_organizer.all().values_list("id", flat=True))
        organizers = list(User.objects.filter(id=league.created_by.id).values_list('id', flat=True))
        
        
        organizer_list = organizers + sub_org_list
        for sc in tournament_details:
            if sc["group__court"] is None:
                sc["group__court"] = sc["court_sn"]

            team_1_player = list(Player.objects.filter(team__id=sc["team1_id"]).values_list("player_id", flat=True))
            team_2_player = list(Player.objects.filter(team__id=sc["team2_id"]).values_list("player_id", flat=True))
            team_1_created_by = Team.objects.filter(id=sc["team1_id"]).first().created_by
            team_2_created_by = Team.objects.filter(id=sc["team2_id"]).first().created_by            
            team_1_created_by_id = team_1_created_by.id if team_1_created_by else None
            team_2_created_by_id = team_2_created_by.id if team_2_created_by else None
            check_score_set = TournamentSetsResult.objects.filter(tournament__id=sc["id"])
            if sc["is_completed"] == True:
                sc["is_save"] = False

            if (get_user.id in organizer_list) or (get_user.id in team_1_player) or (get_user.id == team_1_created_by_id) or (get_user.id in team_2_player) or (get_user.id == team_2_created_by_id):
                
                sc["is_save"] = True
                sc["is_edit"] = True
                
            else:
                sc["is_save"] = False
                sc["is_edit"] = False

            check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=sc["id"],  organizer_approval=True)

            if check_score_approved.exists():                
                sc["is_save"] = False     
                sc["is_score_approved"] = True
                sc["is_edit"] = False   
            else:
                sc["is_score_approved"] = False                  
            
            check_score_reported = TournamentScoreReport.objects.filter(tournament__id=sc["id"], status="Pending")
            if check_score_reported.exists():
                sc["is_score_reported"] = True   
                         
                if get_user.id in organizer_list:
                    sc["is_save"] = True
                    sc["is_edit"] = True
                else:
                    sc["is_save"] = False 
                    sc["is_edit"] = True 
            else:
                sc["is_score_reported"] = False 

            team1_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True).exists()
            team2_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team2_approval=True).exists()           

            if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                sc['is_organizer'] = False
                sc["is_button_show"] = True
                sc['is_approve'] = True
                sc["is_report"] = True
                sc["is_save"] = False

            elif check_score_set.exists() and team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                sc['is_organizer'] = False
                sc["is_button_show"] = False
                sc['is_approve'] = False
                sc["is_report"] = False
                sc["is_save"] = False
            
            elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                sc['is_organizer'] = False
                sc["is_button_show"] = True
                sc['is_approve'] = True
                sc["is_report"] = True
                sc["is_save"] = False
            
            elif check_score_set.exists() and  team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                sc['is_organizer'] = False
                sc["is_button_show"] = False
                sc['is_approve'] = False
                sc["is_report"] = False
                sc["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and team1_approval and team2_approval and not check_score_approved.exists() and not check_score_reported.exists():
                sc['is_organizer'] = True
                sc["is_button_show"] = True
                sc['is_approve'] = True
                sc["is_report"] = False
                sc["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                sc['is_organizer'] = True
                sc["is_button_show"] = True        
                sc['is_approve'] = True
                sc["is_report"] = False
                sc["is_save"] = False

            elif check_score_set.exists() and (get_user.id in organizer_list) and not (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                sc['is_organizer'] = True
                sc["is_button_show"] = True            
                sc['is_approve'] = True
                sc["is_report"] = False
                sc["is_save"] = False
            else:
                sc['is_organizer'] = False
                sc["is_button_show"] = False
                sc['is_approve'] = False
                sc["is_report"] = False
                # sc["is_save"] = False

            if sc["team1__team_image"] != "":
                img_str = sc["team1__team_image"]
                sc["team1__team_image"] = f"{media_base_url}{img_str}"
            if sc["team2__team_image"] != "":
                img_str = sc["team2__team_image"]
                sc["team2__team_image"] = f"{media_base_url}{img_str}"
            #"set_number","court_num","points"
            set_list_team1 = []
            set_list_team2 = []
            score_list_team1 = []
            score_list_team2 = []
            win_status_team1 = []
            win_status_team2 = []
            is_completed_match = sc["is_completed"]
            is_win_match_team1 = False
            is_win_match_team2 = False
            team1_name = sc["team1__name"]
            team2_name = sc["team2__name"]
            if sc["team1_id"] == sc["winner_team_id"] and sc["winner_team_id"] is not None:
                is_win_match_team1 = True
                is_win_match_team2 = False
            elif sc["team2_id"] == sc["winner_team_id"] and sc["winner_team_id"] is not None:
                is_win_match_team2 = True
                is_win_match_team1 = False
            for s in range(sc["set_number"]):
                index = s+1
                set_str = f"s{index}"
                set_list_team1.append(set_str)
                set_list_team2.append(set_str)
                score_details_for_set = TournamentSetsResult.objects.filter(tournament_id=sc["id"],set_number=index).values()
                if len(score_details_for_set)!=0:
                    team_1_score = score_details_for_set[0]["team1_point"]
                    team_2_score = score_details_for_set[0]["team2_point"]
                else:
                    team_1_score = None
                    team_2_score = None
                score_list_team1.append(team_1_score)
                score_list_team2.append(team_2_score)
                if team_1_score is not None and team_2_score is not None:
                    if team_1_score >= team_2_score:
                        win_status_team1.append(True)
                        win_status_team2.append(False)
                    else:
                        win_status_team1.append(False)
                        win_status_team2.append(True)
                else:
                    win_status_team1.append(False)
                    win_status_team2.append(False)
            score = [
                {
                    "name": team1_name,"set": set_list_team2,
                    "score": score_list_team1,"win_status": win_status_team1,
                    "is_win": is_win_match_team1,"is_completed": is_completed_match,
                    "is_drow":sc["is_drow"]
                    },
                {
                "name": team2_name,"set": set_list_team2,
                "score": score_list_team2,"win_status": win_status_team1,
                "is_win": is_win_match_team2,"is_completed": is_completed_match,
                "is_drow":sc["is_drow"]
                }
                ]
            sc["score"] = score
            # print(score)
        
            # List to store data for the point table
        tournament_details = sorted(tournament_details, key=lambda x: x['is_completed'])
        data['match'] = tournament_details
        data['message'] = "Match details fetched successfully."
        data['status'] = status.HTTP_200_OK
    else:
        data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User or league not found."
    return Response(data)


@api_view(("GET",))
def view_elimination_details(request):
    data = {
             'status':'',             
             'elemination':[], 
             'semi_final':[],
             'final':[], 
             'message':''
             }
    user_uuid = request.GET.get('user_uuid')
    user_secret_key = request.GET.get('user_secret_key')
    league_uuid = request.GET.get('league_uuid')
    league_secret_key = request.GET.get('league_secret_key')
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
    '''
    registration_open, future, past
    '''
    check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
    check_leagues = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
    if check_user.exists() and check_leagues.exists():
        league = check_leagues.first()
        get_user = check_user.first()
        sub_org_list = list(league.add_organizer.all().values_list("id", flat=True))        
        organizers = list(User.objects.filter(id=league.created_by.id).values_list('id', flat=True))
        
        
        organizer_list = organizers + sub_org_list
        knock_out_tournament_elimination_data = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Elimination Round").values("id","uuid","secret_key","match_number","match_type","elimination_round","team1__name", "team1_id", "team2_id"
                                                                                                            ,"team1__team_image","team2__name","team2__team_image","winner_team__name", "winner_team_id", "loser_team_id", "winner_team__team_image","loser_team__name","loser_team__team_image","is_completed","play_ground_name")
        for ele_tour in knock_out_tournament_elimination_data:

            team_1_player = list(Player.objects.filter(team__id=ele_tour["team1_id"]).values_list("player_id", flat=True))
            team_2_player = list(Player.objects.filter(team__id=ele_tour["team2_id"]).values_list("player_id", flat=True))
            team_1_created_by = Team.objects.filter(id=ele_tour["team1_id"]).first().created_by
            team_2_created_by = Team.objects.filter(id=ele_tour["team2_id"]).first().created_by

            # ele_tour["is_edit"] = get_user.is_organizer and check_leagues.first().created_by == get_user or ele_tour["team1_id"] == get_user.id or ele_tour["team2_id"] == get_user.id
            if (get_user.id in organizer_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                ele_tour["is_save"] = True
                ele_tour["is_edit"] = True
            else:
                ele_tour["is_save"] = False
                ele_tour["is_edit"] = False

            check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=ele_tour["id"], organizer_approval=True)

            if check_score_approved.exists():                
                ele_tour["is_save"] = False     
                ele_tour["is_score_approved"] = True
                ele_tour["is_edit"] = False   
            else:
                ele_tour["is_score_approved"] = False                  
            
            check_score_reported = TournamentScoreReport.objects.filter(tournament__id=ele_tour["id"], status="Pending")
            if check_score_reported.exists():
                ele_tour["is_score_reported"] = True   
                         
                if get_user.id in organizer_list:
                    ele_tour["is_save"] = True
                    ele_tour["is_edit"] = True
                else:
                    ele_tour["is_save"] = False 
                    ele_tour["is_edit"] = False 
            else:
                ele_tour["is_score_reported"] = False 

            team1_approval = TournamentScoreApproval.objects.filter(tournament__id=ele_tour["id"], team1_approval=True).exists()
            team2_approval = TournamentScoreApproval.objects.filter(tournament__id=ele_tour["id"], team2_approval=True).exists()
            check_score_set = TournamentSetsResult.objects.filter(tournament__id=ele_tour["id"])

            if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                ele_tour['is_organizer'] = False
                ele_tour["is_button_show"] = True
                ele_tour['is_approve'] = True
                ele_tour["is_report"] = True
                ele_tour["is_save"] = False

            elif check_score_set.exists() and team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                ele_tour['is_organizer'] = False
                ele_tour["is_button_show"] = False
                ele_tour['is_approve'] = False
                ele_tour["is_report"] = False
                ele_tour["is_save"] = False
            
            elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                ele_tour['is_organizer'] = False
                ele_tour["is_button_show"] = True
                ele_tour['is_approve'] = True
                ele_tour["is_report"] = True
                ele_tour["is_save"] = False
            
            elif check_score_set.exists() and  team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                ele_tour['is_organizer'] = False
                ele_tour["is_button_show"] = False
                ele_tour['is_approve'] = False
                ele_tour["is_report"] = False
                ele_tour["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and team1_approval and team2_approval and not check_score_approved.exists() and not check_score_reported.exists():
                ele_tour['is_organizer'] = True
                ele_tour["is_button_show"] = True
                ele_tour['is_approve'] = True
                ele_tour["is_report"] = False
                ele_tour["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                ele_tour['is_organizer'] = True
                ele_tour["is_button_show"] = True        
                ele_tour['is_approve'] = True
                ele_tour["is_report"] = False
                ele_tour["is_save"] = False

            elif check_score_set.exists() and (get_user.id in organizer_list) and not (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                ele_tour['is_organizer'] = True
                ele_tour["is_button_show"] = True            
                ele_tour['is_approve'] = True
                ele_tour["is_report"] = False
                ele_tour["is_save"] = False
            else:
                ele_tour['is_organizer'] = False
                ele_tour["is_button_show"] = False
                ele_tour['is_approve'] = False
                ele_tour["is_report"] = False
                # ele_tour["is_save"] = False

            score = [{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True},{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True}]
            
            if ele_tour["team1_id"] == ele_tour["winner_team_id"] and ele_tour["winner_team_id"] is not None:
                score[0]["is_win"] = True
                score[1]["is_win"] = False
            elif ele_tour["team2_id"] == ele_tour["winner_team_id"] and ele_tour["winner_team_id"] is not None:
                score[1]["is_win"] = True
                score[0]["is_win"] = False
            else:
                score[1]["is_win"] = None
                score[0]["is_win"] = None
            score_details = TournamentSetsResult.objects.filter(tournament_id=ele_tour["id"]).values()
            score[0]["name"] = ele_tour["team1__name"]
            score[1]["name"] = ele_tour["team2__name"]
            score[0]["set"] = ["s1","s2","s3"]
            score[1]["set"] = ["s1","s2","s3"]
            for l__ in range(3):
                
                if l__ < len(score_details):
                    l = {"team1_point":score_details[l__]["team1_point"],"team2_point":score_details[l__]["team2_point"]}
                else:
                    l = {"team1_point":None,"team2_point":None}
                
                score[0]["score"].append(l["team1_point"])
                score[1]["score"].append(l["team2_point"])
                
                if l["team1_point"] == None or l["team1_point"] == None:
                    score[0]["win_status"].append(None)
                    score[1]["win_status"].append(None)
                elif l["team1_point"] > l["team2_point"]:
                    score[0]["win_status"].append(True)
                    score[1]["win_status"].append(False)
                else:
                    score[0]["win_status"].append(False)
                    score[1]["win_status"].append(True)
            ele_tour["score"] = score
        data['elemination'] = list(knock_out_tournament_elimination_data)

        #this data for Semi Final   
        knock_out_semifinal_tournament_data = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Semi Final").values("id","uuid","secret_key","match_number","match_type","elimination_round","team1__name", "team1_id", "team2_id"
                                                                                                        ,"team1__team_image","team2__name","team2__team_image","winner_team__name", "winner_team_id", "loser_team_id", "winner_team__team_image","loser_team__name","loser_team__team_image","is_completed","play_ground_name")
        for semi_tour in knock_out_semifinal_tournament_data:
            team_1_player = list(Player.objects.filter(team__id=semi_tour["team1_id"]).values_list("player_id", flat=True))
            team_2_player = list(Player.objects.filter(team__id=semi_tour["team2_id"]).values_list("player_id", flat=True))
            team_1_created_by = Team.objects.filter(id=semi_tour["team1_id"]).first().created_by
            team_2_created_by = Team.objects.filter(id=semi_tour["team2_id"]).first().created_by

            if (get_user.id in organizer_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                semi_tour["is_save"] = True
                semi_tour["is_edit"] = True
            else:
                semi_tour["is_save"] = False
                semi_tour["is_edit"] = False

            check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=semi_tour["id"], organizer_approval=True)

            if check_score_approved.exists():                
                semi_tour["is_save"] = False     
                semi_tour["is_score_approved"] = True
                semi_tour["is_edit"] = False   
            else:
                semi_tour["is_score_approved"] = False                  
            
            check_score_reported = TournamentScoreReport.objects.filter(tournament__id=semi_tour["id"], status="Pending")
            if check_score_reported.exists():
                semi_tour["is_score_reported"] = True   
                         
                if get_user.id in organizer_list:
                    semi_tour["is_save"] = True
                    semi_tour["is_edit"] = True
                else:
                    semi_tour["is_save"] = False 
                    semi_tour["is_edit"] = False 
            else:
                semi_tour["is_score_reported"] = False 

            team1_approval = TournamentScoreApproval.objects.filter(tournament__id=semi_tour["id"], team1_approval=True).exists()
            team2_approval = TournamentScoreApproval.objects.filter(tournament__id=semi_tour["id"], team2_approval=True).exists()
            check_score_set = TournamentSetsResult.objects.filter(tournament__id=semi_tour["id"])

            if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                semi_tour['is_organizer'] = False
                semi_tour["is_button_show"] = True
                semi_tour['is_approve'] = True
                semi_tour["is_report"] = True
                semi_tour["is_save"] = False

            elif check_score_set.exists() and team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                semi_tour['is_organizer'] = False
                semi_tour["is_button_show"] = False
                semi_tour['is_approve'] = False
                semi_tour["is_report"] = False
                semi_tour["is_save"] = False
            
            elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                semi_tour['is_organizer'] = False
                semi_tour["is_button_show"] = True
                semi_tour['is_approve'] = True
                semi_tour["is_report"] = True
                semi_tour["is_save"] = False
            
            elif check_score_set.exists() and  team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                semi_tour['is_organizer'] = False
                semi_tour["is_button_show"] = False
                semi_tour['is_approve'] = False
                semi_tour["is_report"] = False
                semi_tour["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and team1_approval and team2_approval and not check_score_approved.exists() and not check_score_reported.exists():
                semi_tour['is_organizer'] = True
                semi_tour["is_button_show"] = True
                semi_tour['is_approve'] = True
                semi_tour["is_report"] = False
                semi_tour["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                semi_tour['is_organizer'] = True
                semi_tour["is_button_show"] = True        
                semi_tour['is_approve'] = True
                semi_tour["is_report"] = False
                semi_tour["is_save"] = False

            elif check_score_set.exists() and (get_user.id in organizer_list) and not (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                semi_tour['is_organizer'] = True
                semi_tour["is_button_show"] = True            
                semi_tour['is_approve'] = True
                semi_tour["is_report"] = False
                semi_tour["is_save"] = False
            else:
                semi_tour['is_organizer'] = False
                semi_tour["is_button_show"] = False
                semi_tour['is_approve'] = False
                semi_tour["is_report"] = False
                # semi_tour["is_save"] = False

            score = [{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True},{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True}]
            
            if semi_tour["team1_id"] == semi_tour["winner_team_id"] and semi_tour["winner_team_id"] is not None:
                score[0]["is_win"] = True
                score[1]["is_win"] = False
            elif semi_tour["team2_id"] == semi_tour["winner_team_id"] and semi_tour["winner_team_id"] is not None:
                score[1]["is_win"] = True
                score[0]["is_win"] = False
            else:
                score[1]["is_win"] = None
                score[0]["is_win"] = None
            score_details = TournamentSetsResult.objects.filter(tournament_id=semi_tour["id"]).values()
            score[0]["name"] = semi_tour["team1__name"]
            score[1]["name"] = semi_tour["team2__name"]
            score[0]["set"] = ["s1","s2","s3"]
            score[1]["set"] = ["s1","s2","s3"]
            for l__ in range(3):
                
                if l__ < len(score_details):
                    l = {"team1_point":score_details[l__]["team1_point"],"team2_point":score_details[l__]["team2_point"]}
                else:
                    l = {"team1_point":None,"team2_point":None}
                
                score[0]["score"].append(l["team1_point"])
                score[1]["score"].append(l["team2_point"])
                
                if l["team1_point"] == None or l["team1_point"] == None:
                    score[0]["win_status"].append(None)
                    score[1]["win_status"].append(None)
                elif l["team1_point"] > l["team2_point"]:
                    score[0]["win_status"].append(True)
                    score[1]["win_status"].append(False)
                else:
                    score[0]["win_status"].append(False)
                    score[1]["win_status"].append(True)
            semi_tour["score"] = score
        data['semi_final'] = list(knock_out_semifinal_tournament_data)

        #this data for Final 
        knock_out_final_tournament_data = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Final").values("id","uuid","secret_key","match_number","match_type","elimination_round","team1__name", "team1_id", "team2_id"
                                                                                                        ,"team1__team_image","team2__name","team2__team_image","winner_team__name", "winner_team_id", "loser_team_id", "winner_team__team_image","loser_team__name","loser_team__team_image","is_completed","play_ground_name")
        for final_tour in knock_out_final_tournament_data:
            team_1_player = list(Player.objects.filter(team__id=final_tour["team1_id"]).values_list("player_id", flat=True))
            team_2_player = list(Player.objects.filter(team__id=final_tour["team2_id"]).values_list("player_id", flat=True))
            team_1_created_by = Team.objects.filter(id=final_tour["team1_id"]).first().created_by
            team_2_created_by = Team.objects.filter(id=final_tour["team2_id"]).first().created_by

            if (get_user.id in organizer_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                final_tour["is_save"] = True
                final_tour["is_edit"] = True
            else:
                final_tour["is_save"] = False
                final_tour["is_edit"] = False

            check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=final_tour["id"], organizer_approval=True)

            if check_score_approved.exists():                
                final_tour["is_save"] = False     
                final_tour["is_score_approved"] = True
                final_tour["is_edit"] = False   
            else:
                final_tour["is_score_approved"] = False                  
            
            check_score_reported = TournamentScoreReport.objects.filter(tournament__id=final_tour["id"], status="Pending")
            if check_score_reported.exists():
                final_tour["is_score_reported"] = True   
                         
                if get_user.id in organizer_list:
                    final_tour["is_save"] = True
                    final_tour["is_edit"] = True
                else:
                    final_tour["is_save"] = False 
                    final_tour["is_edit"] = False 
            else:
                final_tour["is_score_reported"] = False 

            team1_approval = TournamentScoreApproval.objects.filter(tournament__id=final_tour["id"], team1_approval=True).exists()
            team2_approval = TournamentScoreApproval.objects.filter(tournament__id=final_tour["id"], team2_approval=True).exists()
            check_score_set = TournamentSetsResult.objects.filter(tournament__id=final_tour["id"])

            if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                final_tour['is_organizer'] = False
                final_tour["is_button_show"] = True
                final_tour['is_approve'] = True
                final_tour["is_report"] = True
                final_tour["is_save"] = False

            elif check_score_set.exists() and team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                final_tour['is_organizer'] = False
                final_tour["is_button_show"] = False
                final_tour['is_approve'] = False
                final_tour["is_report"] = False
                final_tour["is_save"] = False
            
            elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                final_tour['is_organizer'] = False
                final_tour["is_button_show"] = True
                final_tour['is_approve'] = True
                final_tour["is_report"] = True
                final_tour["is_save"] = False
            
            elif check_score_set.exists() and  team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                final_tour['is_organizer'] = False
                final_tour["is_button_show"] = False
                final_tour['is_approve'] = False
                final_tour["is_report"] = False
                final_tour["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and team1_approval and team2_approval and not check_score_approved.exists() and not check_score_reported.exists():
                final_tour['is_organizer'] = True
                final_tour["is_button_show"] = True
                final_tour['is_approve'] = True
                final_tour["is_report"] = False
                final_tour["is_save"] = False
                
            elif check_score_set.exists() and (get_user.id in organizer_list) and (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                final_tour['is_organizer'] = True
                final_tour["is_button_show"] = True        
                final_tour['is_approve'] = True
                final_tour["is_report"] = False
                final_tour["is_save"] = False

            elif check_score_set.exists() and (get_user.id in organizer_list) and not (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                final_tour['is_organizer'] = True
                final_tour["is_button_show"] = True            
                final_tour['is_approve'] = True
                final_tour["is_report"] = False
                final_tour["is_save"] = False
            else:
                final_tour['is_organizer'] = False
                final_tour["is_button_show"] = False
                final_tour['is_approve'] = False
                final_tour["is_report"] = False
                # final_tour["is_save"] = False

            score = [{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True},{"name": "","set": [],"score": [],"win_status": [],"is_win": True,"is_completed": True}]
            
            if final_tour["team1_id"] == final_tour["winner_team_id"] and final_tour["winner_team_id"] is not None:
                score[0]["is_win"] = True
                score[1]["is_win"] = False
            elif final_tour["team2_id"] == final_tour["winner_team_id"] and final_tour["winner_team_id"] is not None:
                score[1]["is_win"] = True
                score[0]["is_win"] = False
            else:
                score[1]["is_win"] = None
                score[0]["is_win"] = None
            score_details = TournamentSetsResult.objects.filter(tournament_id=final_tour["id"]).values()
            score[0]["name"] = final_tour["team1__name"]
            score[1]["name"] = final_tour["team2__name"]
            score[0]["set"] = ["s1","s2","s3"]
            score[1]["set"] = ["s1","s2","s3"]
            for l__ in range(3):
                
                if l__ < len(score_details):
                    l = {"team1_point":score_details[l__]["team1_point"],"team2_point":score_details[l__]["team2_point"]}
                else:
                    l = {"team1_point":None,"team2_point":None}
                
                score[0]["score"].append(l["team1_point"])
                score[1]["score"].append(l["team2_point"])
                
                if l["team1_point"] == None or l["team1_point"] == None:
                    score[0]["win_status"].append(None)
                    score[1]["win_status"].append(None)
                elif l["team1_point"] > l["team2_point"]:
                    score[0]["win_status"].append(True)
                    score[1]["win_status"].append(False)
                else:
                    score[0]["win_status"].append(False)
                    score[1]["win_status"].append(True)
            final_tour["score"] = score
        data['final'] = list(knock_out_final_tournament_data)
        data['message'] = "Elimination details fetched successfully."
        data['status'] = status.HTTP_200_OK
        
    else:
        data["status"], data["message"] = status.HTTP_404_NOT_FOUND, f"User or league not found."
    return Response(data)


@api_view(("GET",))
def view_point_table_details(request):
    data = {
             'status':'',             
             'point_table':[],              
             'message':''             
             }
    user_uuid = request.GET.get('user_uuid')
    user_secret_key = request.GET.get('user_secret_key')
    league_uuid = request.GET.get('league_uuid')
    league_secret_key = request.GET.get('league_secret_key')
    protocol = 'https' if request.is_secure() else 'http'
    host = request.get_host()
    media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
    '''
    registration_open, future, past
    '''
    check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
    check_leagues = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
    if check_user.exists() and check_leagues.exists():
        league = check_leagues.first()
        get_user = check_user.first()
        play_type_check_win = league.play_type        
        all_group_details = RoundRobinGroup.objects.filter(league_for=league)
        for grp in all_group_details:
            teams = grp.all_teams.all()
            group_score_point_table = []
            # print(teams)
            for team in teams:
                team_score = {}
                total_match_detals = Tournament.objects.filter(leagues=league, match_type="Round Robin").filter(Q(team1=team) | Q(team2=team))
                completed_match_details = total_match_detals.filter(is_completed=True)
                win_match_details = completed_match_details.filter(winner_team=team).count()
                loss_match_details = completed_match_details.filter(loser_team=team).count()
                drow_match = len(completed_match_details) - (win_match_details + loss_match_details)
                match_list = list(total_match_detals.values_list("id", flat=True))
                for_score = 0
                aginst_score = 0
                for sc in match_list:
                    co_team_position = Tournament.objects.filter(id=sc).first()
                    set_score = TournamentSetsResult.objects.filter(tournament_id=sc)
                    if co_team_position.team1 == team:
                        for_score = for_score + sum(list(set_score.values_list("team1_point", flat=True)))
                        aginst_score = aginst_score + sum(list(set_score.values_list("team2_point", flat=True)))
                    else:
                        for_score = for_score + sum(list(set_score.values_list("team2_point", flat=True)))
                        aginst_score = aginst_score + sum(list(set_score.values_list("team1_point", flat=True)))
                
                point = (win_match_details * 3) + (drow_match * 1)
                team_score["uuid"], team_score["secret_key"] = team.uuid, team.secret_key
                team_score["name"], team_score["completed_match"] = team.name, len(completed_match_details)
                team_score["win_match"], team_score["loss_match"] = win_match_details, loss_match_details
                team_score["drow_match"], team_score["for_score"] = drow_match, for_score
                team_score["aginst_score"], team_score["point"] = aginst_score, point
                group_score_point_table.append(team_score)
            # Append team details to group data
            tournament_details_group = Tournament.objects.filter(leagues=league,group=grp).values("id","uuid","secret_key","team1__name","team2__name","leagues__name","match_type","is_completed","group__court","play_ground_name","playing_date_time","group_id")
            for k_ in tournament_details_group:
                round_robin_group_detals = RoundRobinGroup.objects.filter(league_for=league, id=k_["group_id"]).first()
                k_["sets"] = round_robin_group_detals.number_sets
                k_["court"] = round_robin_group_detals.court
                k_["score"] = list(TournamentSetsResult.objects.filter(tournament_id=k_["id"]).values())
            
            group_score_point_table = sorted(group_score_point_table, key=lambda x: (x['point'], x['for_score']), reverse=True)
            # print(group_score_point_table)

            ###### tournament winning team update and declare
            if play_type_check_win == "Round Robin":
                total_tournament = Tournament.objects.filter(leagues=check_leagues.first(),match_type="Round Robin",leagues__play_type="Round Robin")
                completed_tournament = total_tournament.filter(is_completed=True)
                if total_tournament.count() == completed_tournament.count():
                    winner_team = Team.objects.filter(uuid=group_score_point_table[0]["uuid"]).first()
                    winner_team_name = winner_team.name
                    league.winner_team = winner_team
                    league.is_complete = True
                    league.save()
                    data["winner_team"] = winner_team_name
            grp_data = {
                "id": grp.id,
                "court": grp.court,
                "league_for_id": grp.league_for_id,
                "all_games_status": grp.all_games_status,
                "all_tems": group_score_point_table,
                "tournament": tournament_details_group,
                "seleced_teams_id": grp.seleced_teams_id
            }
            data['point_table'].append(grp_data)
        
        data["status"], data["message"] = status.HTTP_200_OK, "Point table data fetched successfully."
    else:
        data["status"], data['data'], data["message"] = status.HTTP_404_NOT_FOUND, [],  "User or League not found."
    return Response(data)


@api_view(("GET",))
def get_match_result(request):
    data = {'status': '', 'match_details':[], 'message': ''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        match_id = request.GET.get('match_id')
        # tournament_secret_key = request.data.get('tournament_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_match = Tournament.objects.filter(id=match_id)
        print(check_user,check_match)
        protocol = 'https' if request.is_secure() else 'http'
        host = request.get_host()
        media_base_url = f"{protocol}://{host}{settings.MEDIA_URL}"
        if check_user.exists() and check_match.exists():
            get_match = check_match.first()
            get_user= check_user.first()
            league = get_match.leagues

            tournament_details = Tournament.objects.filter(id=match_id).order_by("match_number").values("id","match_number","uuid","secret_key","leagues__name"
                                                                                                                        ,"team1_id", "team2_id", "team1__team_image", "team2__team_image", 
                                                                                                                        "team1__name", "team2__name", "winner_team_id", "winner_team__name", 
                                                                                                                        "playing_date_time","match_type","group__court","is_completed"
                                                                                                                        ,"elimination_round","court_sn","set_number","court_num","points","is_drow")
            
            sub_org_list = list(league.add_organizer.all().values_list("id", flat=True))
            organizers = list(User.objects.filter(id=league.created_by.id).values_list('id', flat=True))
            
            
            organizer_list = organizers + sub_org_list
            for sc in tournament_details:
                if sc["group__court"] is None:
                    sc["group__court"] = sc["court_sn"]

                team_1_player = list(Player.objects.filter(team__id=sc["team1_id"]).values_list("player_id", flat=True))
                team_2_player = list(Player.objects.filter(team__id=sc["team2_id"]).values_list("player_id", flat=True))
                team_1_created_by = Team.objects.filter(id=sc["team1_id"]).first().created_by
                team_2_created_by = Team.objects.filter(id=sc["team2_id"]).first().created_by

                if (get_user.id in organizer_list) or (get_user.id in team_1_player) or (get_user == team_1_created_by) or (get_user.id in team_2_player) or ((get_user == team_2_created_by)):
                    sc["is_save"] = True
                    sc["is_edit"] = True
                else:
                    sc["is_save"] = False
                    sc["is_edit"] = False

                check_score_approved = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], organizer_approval=True)

                if check_score_approved.exists():                
                    sc["is_save"] = False     
                    sc["is_score_approved"] = True
                    sc["is_edit"] = False   
                else:
                    sc["is_score_approved"] = False                  
                
                check_score_reported = TournamentScoreReport.objects.filter(tournament__id=sc["id"], status="Pending")
                if check_score_reported.exists():
                    sc["is_score_reported"] = True   
                            
                    if get_user.id in organizer_list:
                        sc["is_save"] = True
                        sc["is_edit"] = True
                    else:
                        sc["is_save"] = False 
                        sc["is_edit"] = False 
                else:
                    sc["is_score_reported"] = False 

                team1_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team1_approval=True).exists()
                team2_approval = TournamentScoreApproval.objects.filter(tournament__id=sc["id"], team2_approval=True).exists()
                check_score_set = TournamentSetsResult.objects.filter(tournament__id=sc["id"])

                if check_score_set.exists() and not team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                    sc['is_approve'] = True
                    sc["is_report"] = True
                    sc["is_save"] = False

                elif check_score_set.exists() and team1_approval and ((get_user.id in team_1_player) or (get_user == team_1_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = False
                    sc['is_approve'] = False
                    sc["is_report"] = False
                    sc["is_save"] = False
                
                elif check_score_set.exists() and not team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = True
                    sc['is_approve'] = True
                    sc["is_report"] = True
                    sc["is_save"] = False
                
                elif check_score_set.exists() and  team2_approval and ((get_user.id in team_2_player) or (get_user == team_2_created_by)) and not check_score_approved.exists() and not check_score_reported.exists():
                    sc['is_organizer'] = False
                    sc["is_button_show"] = False
                    sc['is_approve'] = False
                    sc["is_report"] = False
                    sc["is_save"] = False
                    
                elif check_score_set.exists() and (get_user.id in organizer_list) and team1_approval and team2_approval and not check_score_approved.exists() and not check_score_reported.exists():
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True
                    sc['is_approve'] = True
                    sc["is_report"] = False
                    sc["is_save"] = False
                    
                elif check_score_set.exists() and (get_user.id in organizer_list) and (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True        
                    sc['is_approve'] = True
                    sc["is_report"] = False
                    sc["is_save"] = False

                elif check_score_set.exists() and (get_user.id in organizer_list) and not (team1_approval or team2_approval) and not check_score_approved.exists() and not check_score_reported.exists():   
                    sc['is_organizer'] = True
                    sc["is_button_show"] = True            
                    sc['is_approve'] = True
                    sc["is_report"] = False
                    sc["is_save"] = False
                else:
                    sc['is_organizer'] = False
                    sc["is_button_show"] = False
                    sc['is_approve'] = False
                    sc["is_report"] = False
                    # sc["is_save"] = False

                if sc["team1__team_image"] != "":
                    img_str = sc["team1__team_image"]
                    sc["team1__team_image"] = f"{media_base_url}{img_str}"
                if sc["team2__team_image"] != "":
                    img_str = sc["team2__team_image"]
                    sc["team2__team_image"] = f"{media_base_url}{img_str}"
                #"set_number","court_num","points"
                set_list_team1 = []
                set_list_team2 = []
                score_list_team1 = []
                score_list_team2 = []
                win_status_team1 = []
                win_status_team2 = []
                is_completed_match = sc["is_completed"]
                is_win_match_team1 = False
                is_win_match_team2 = False
                team1_name = sc["team1__name"]
                team2_name = sc["team2__name"]
                if sc["team1_id"] == sc["winner_team_id"] and sc["winner_team_id"] is not None:
                    is_win_match_team1 = True
                    is_win_match_team2 = False
                elif sc["team2_id"] == sc["winner_team_id"] and sc["winner_team_id"] is not None:
                    is_win_match_team2 = True
                    is_win_match_team1 = False
                for s in range(sc["set_number"]):
                    index = s+1
                    set_str = f"s{index}"
                    set_list_team1.append(set_str)
                    set_list_team2.append(set_str)
                    score_details_for_set = TournamentSetsResult.objects.filter(tournament_id=sc["id"],set_number=index).values()
                    if len(score_details_for_set)!=0:
                        team_1_score = score_details_for_set[0]["team1_point"]
                        team_2_score = score_details_for_set[0]["team2_point"]
                    else:
                        team_1_score = None
                        team_2_score = None
                    score_list_team1.append(team_1_score)
                    score_list_team2.append(team_2_score)
                    if team_1_score is not None and team_2_score is not None:
                        if team_1_score >= team_2_score:
                            win_status_team1.append(True)
                            win_status_team2.append(False)
                        else:
                            win_status_team1.append(False)
                            win_status_team2.append(True)
                    else:
                        win_status_team1.append(False)
                        win_status_team2.append(False)
                score = [
                    {
                        "name": team1_name,"set": set_list_team2,
                        "score": score_list_team1,"win_status": win_status_team1,
                        "is_win": is_win_match_team1,"is_completed": is_completed_match,
                        "is_drow":sc["is_drow"]
                        },
                    {
                    "name": team2_name,"set": set_list_team2,
                    "score": score_list_team2,"win_status": win_status_team1,
                    "is_win": is_win_match_team2,"is_completed": is_completed_match,
                    "is_drow":sc["is_drow"]
                    }
                    ]
                sc["score"] = score
                # print(score)
            
                # List to store data for the point table
            
            data['match_details'] = tournament_details
            data['message'] = "Match result fetched successfully."
            data['status'] = status.HTTP_200_OK

        else:
            data["status"], data["message"], data["match_details"] = status.HTTP_404_NOT_FOUND, "User or Match not found.",[]
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    return Response(data)

#edit event api
@api_view(['POST'])
def edit_leagues(request):
    response = {'status': '', 'message': ''}

    try:
        user_uuid = request.data.get('user_uuid')
        league_uuid = request.data.get('league_uuid')

        if not user_uuid or not league_uuid:
            raise ValueError("Both 'user_uuid' and 'league_uuid' are required.")

        user = get_object_or_404(User, uuid=user_uuid)
        league = get_object_or_404(Leagues, uuid=league_uuid)

        # Parse JSON data list
        total_data = request.data.get('data')
        if isinstance(total_data, str):
            data_list = json.loads(total_data) if total_data else []
        elif isinstance(total_data, list):
            data_list = total_data
        else:
            data_list = []

        # Update PlayType data
        LeaguesPlayType.objects.update_or_create(
            league_for=league,
            defaults={'data': data_list}
        )

        # Optional fields
        max_number_team = request.data.get('max_number_team')
        league.leagues_start_date = parse_date(request.data.get('leagues_start_date')) or league.leagues_start_date
        league.leagues_end_date = parse_date(request.data.get('leagues_end_date')) or league.leagues_end_date
        league.registration_start_date = parse_date(request.data.get('registration_start_date')) or league.registration_start_date
        league.registration_end_date = parse_date(request.data.get('registration_end_date')) or league.registration_end_date

        if max_number_team:
            league.max_number_team = int(max_number_team)

        league.save()

        response['status'] = status.HTTP_200_OK
        response['message'] = "Your Event updated successfully"

    except Exception as e:
        response['status'] = status.HTTP_400_BAD_REQUEST
        response['message'] = str(e)

    return Response(response)

@api_view(('POST',))
def edit_leagues_max_team(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        league_uuid = request.data.get('league_uuid')
        league_secret_key = request.data.get('league_secret_key')
        max_team = request.data.get('max_team')
        
        if int(max_team) < 2:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "Minimun need two teams for assigning match"
            return Response(data)
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_league  = Leagues.objects.filter(uuid=league_uuid,secret_key=league_secret_key)
        if check_user.exists() and check_league.exists():
            get_tornament = check_league.first()
            get_user = check_user.first()
            all_org_list = list(get_tornament.add_organizer.all().values_list("id", flat=True))
            if get_tornament.created_by==get_user or get_user.id in all_org_list:
                check_have_match = Tournament.objects.filter(leagues=get_tornament)
                if not check_have_match.exists():
                    check_league.update(max_number_team=int(max_team))
                    data["status"], data["message"] = status.HTTP_200_OK, "League updated successfully"
                else:
                    data["status"], data["message"] = status.HTTP_200_OK, "This Tournament already start"
            else:
                data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "This is not your tournamnet"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User or League not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


#delete event api
@api_view(('POST',))
def delete_leagues(request):
    data = {'status':'','message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        leagues_id = request.data.get('leagues_id')
        
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        check_league  = Leagues.objects.filter(id=leagues_id)
        if check_user.exists() and check_league.exists():
            get_tornament = check_league.first()
            get_user = check_user.first()
            join_team = get_tornament.registered_team.all().count()
            if join_team != 0:
                data["status"], data["message"] = status.HTTP_200_OK, "You cann't  delete this tournament"
            else:
                check_league.delete()
                data["status"], data["message"] = status.HTTP_200_OK, "League deleted successfully"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User or League not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)


#event log api
#pending

#get registarable teams for event api
@api_view(('GET',))
def team_register_user(request):
    data = {'status': '', 'data': '', 'message': ''}
    try:
        # Extract parameters from the request
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        league_uuid = request.GET.get('league_uuid')
        league_secret_key = request.GET.get('league_secret_key')

        # Check if the user exists and is a team manager
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        if check_user.exists():
            get_user = check_user.first()
            # Retrieve teams created by the user
            get_teams = Team.objects.filter(created_by=get_user)
            # Check if league exists
            check_league = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)
            if check_league.exists():
                league = check_league.first()
                if league.team_type.name == "Open-team":
                    team_type = None
                else:
                    team_type = league.team_type.name
                team_person = league.team_person.name
                team_data = []
                
                team_id_list = list(league.registered_team.all().values_list("id", flat=True))
                # print(team_id_list)
                # Iterate through user's teams
                for team in get_teams:
                    flg = True
                    flg_text = ""
                    register_team_id_list = list(league.registered_team.all().values_list("id", flat=True))
                    is_view = False
                    if team.id not in register_team_id_list:
                       is_view = True 
                    # Check if team's type and person type match the league's requirements
                    if team_person and team.team_person:
                        if team_person.strip() != team.team_person.strip():
                            flg = False
                    if team_type and team.team_type:
                        if team_type.strip() != team.team_type.strip():
                            flg = False

                        
                    # Retrieve players in the team
                    player_data = Player.objects.filter(team=team).values("player_full_name", "player_ranking", "player__rank")
                    team_rank = 0
                    for pla in player_data:
                        pla["player_ranking"] = pla["player__rank"]                  
                        if pla["player__rank"] == "0" or pla["player__rank"] in [0,"", "null", None]:
                            team_rank += 1
                        else:
                            team_rank += float(pla["player__rank"])
                    try:
                        team_rank = team_rank / len(player_data)
                    except:
                        team_rank = 1.0

                    # Append team details to the response
                    team_info = {
                        "uuid": team.uuid,
                        "secret_key": team.secret_key,
                        "team_name": team.name,
                        "team_rank":team_rank,
                        "team_image": str(team.team_image),
                        "location": team.location,
                        "created_by_name": f"{team.created_by.first_name} {team.created_by.last_name}",
                        "flg": flg,
                        "is_view":is_view,
                        "flg_text": flg_text,
                        "team_person": team.team_person,
                        "team_type": team.team_type,
                        "player_data": player_data,
                    }
                    if team_info["flg"] == True and team.id not in team_id_list:
                        team_data.append(team_info)
                    else:
                        pass
                fees = league.registration_fee
                others_fees = league.others_fees
                if others_fees:
                    for val in others_fees.values():
                        if isinstance(val, (int, float)):  # Ensure the value is numeric
                            fees += val
                        elif isinstance(val, str) and val.isdigit():  # Convert string numbers
                            fees += int(val)
                if league.policy is True:
                    cancel_policy = list(LeaguesCancellationPolicy.objects.filter(league=league).values())
                else:
                    cancel_policy = []
                # Prepare league data
                league_data = {
                    "uuid": league.uuid,
                    "secret_key": league.secret_key,
                    "name": league.name,
                    "leagues_start_date": league.leagues_start_date,
                    "leagues_end_date": league.leagues_end_date,
                    "registration_start_date": league.registration_start_date,
                    "registration_end_date": league.registration_end_date,
                    "team_type__name": league.team_type.name,
                    "team_person__name": league.team_person.name,
                    "max_join_team":league.max_number_team,
                    "total_join_team":len(team_id_list),
                    "any_rank_status":league.any_rank,
                    "league_start_rank":league.start_rank,
                    "league_end_rank":league.end_rank,
                    "fees": fees,
                    "cancelation_policy": cancel_policy
                }
                # Prepare response data
                main_data = {"league_data": [league_data], "team_data": team_data}
                data["status"], data['data'], data["message"] = status.HTTP_200_OK, main_data, "Data found."
            else:
                data["status"], data['data'], data["message"] = status.HTTP_404_NOT_FOUND, "", "Tournament  not found"
        else:
            data["status"], data['data'], data["message"] = status.HTTP_404_NOT_FOUND, "", "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    return Response(data)



@api_view(('GET',))
def registered_team_for_leauge_list(request):
    data = {'status':'','data':'','message':''}
    try:        
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        leauge_uuid = request.GET.get('leauge_uuid')
        leauge_secret_key = request.GET.get('leauge_secret_key')
        check_user = User.objects.filter(uuid=user_uuid,secret_key=user_secret_key)
        if check_user.exists() :
            get_user = check_user.first()
            main_data = []
            if get_user.is_admin :
                check_leauge = Leagues.objects.filter(uuid=leauge_uuid,secret_key=leauge_secret_key)
                get_leauge = check_leauge.first()
                team_data = []
                leauge_data = {"uuid":get_leauge.uuid,"secret_key":get_leauge.secret_key,"name":get_leauge.name,
                               "location":get_leauge.location,"leagues_start_date":get_leauge.leagues_start_date,"leagues_end_date":get_leauge.leagues_end_date,
                               "registration_start_date":get_leauge.registration_start_date,"registration_end_date":get_leauge.registration_end_date,
                               "team_type__name":get_leauge.team_type.name,"team_person__name":get_leauge.team_person.name}
                get_team = Team.objects.filter(leagues__id = get_leauge.id).order_by("name")
                for i in get_team :
                    team = [{"uuid":i.uuid,"secret_key":i.secret_key,"name":i.name,"location":i.location,"team_image": str(i.team_image) ,"created_by":f"{i.created_by.first_name} {i.created_by.last_name}"}]
                    player_data = []
                    get_player = Player.objects.filter(team__in=[i.id])
                    for i in get_player :
                        player_data.append({"uuid":i.uuid,"secret_key":i.secret_key,"player_full_name":i.player_full_name,"player_ranking":i.player.rank})
                    team_data.append({"team":team,"player_data":player_data})
                main_data = {"leauge_data":leauge_data,"team_data":team_data}
            else:
                check_leauge = Leagues.objects.filter(uuid=leauge_uuid,secret_key=leauge_secret_key)
                get_leauge = check_leauge.first()
                team_data = []
                leauge_data = {"uuid":get_leauge.uuid,"secret_key":get_leauge.secret_key,"name":get_leauge.name,
                               "location":get_leauge.location,"leagues_start_date":get_leauge.leagues_start_date,"leagues_end_date":get_leauge.leagues_end_date,
                               "registration_start_date":get_leauge.registration_start_date,"registration_end_date":get_leauge.registration_end_date,
                               "team_type__name":get_leauge.team_type.name,"team_person__name":get_leauge.team_person.name}
                get_team = Team.objects.filter(leagues__id = get_leauge.id,created_by_id=get_user.id).order_by("name")
                for i in get_team :
                    team = [{"uuid":i.uuid,"secret_key":i.secret_key,"name":i.name,"location":i.location,"team_image": str(i.team_image) ,"created_by":f"{i.created_by.first_name} {i.created_by.last_name}"}]
                    player_data = []
                    get_player = Player.objects.filter(team__in=[i.id])
                    for i in get_player :
                        player_data.append({"uuid":i.uuid,"secret_key":i.secret_key,"player_full_name":i.player_full_name,"player_ranking":i.player.rank})
                    team_data.append({"team":team,"player_data":player_data})
                main_data = {"leauge_data":leauge_data,"team_data":team_data}
            data["status"], data['data'], data["message"] = status.HTTP_200_OK, main_data,"Data found."
        else:
            data["status"], data['data'], data["message"] = status.HTTP_404_NOT_FOUND, "","User not found."
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

#join/register event api
@api_view(('POST',))
def check_invited_code(request):
    data = {'status':'', 'message':''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        league_uuid = request.data.get('league_uuid')
        league_secret_key = request.data.get('league_secret_key')
        invited_code = request.data.get('invited_code')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        check_league = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)
        if check_user.exists() and check_league.exists():
            get_league = check_league.first()
            if get_league.invited_code == invited_code:
                data['status'], data['message'] = status.HTTP_200_OK, "Successfully matched."
            else:
                data['status'], data['message'] = status.HTTP_403_FORBIDDEN, "Didn't match."
        else:
            data['status'] = status.HTTP_404_NOT_FOUND
            data['message'] = "User or league not found"
        return Response(data)
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"{e}"
    return Response(data)

@api_view(('POST',))
def register_teams_to_league(request):
    try:     
        chage_amount = None   
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        league_uuid = request.data.get('league_uuid')
        league_secret_key = request.data.get('league_secret_key')
        team_uuid_all = request.data.get('team_uuid')
        team_secret_key_all = request.data.get('team_secret_key') 
        discount = request.data.get('discount', 0) 

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        check_league = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)

        if not check_user.exists() or not check_league.exists():
            return Response({"status": status.HTTP_400_BAD_REQUEST,"payement": None, "url":None, "add_amount":None, "message": "User or Tournament not found"})

        get_league = check_league.first() 
        get_user = check_user.first()

        check_wallet = Wallet.objects.filter(user=get_user)
        if not check_wallet.exists():
            return Response({"status": status.HTTP_404_NOT_FOUND, "message": "No wallet found."})

        get_wallet = check_wallet.first()
        balance = Decimal(str(get_wallet.balance))  # ✅ Ensure balance is Decimal

        total_registered_teams = get_league.registered_team.count()
        today_date = timezone.now()
        if get_league.team_type.name != 'Open-team':
            if get_league.registration_end_date < today_date or get_league.max_number_team == total_registered_teams or get_league.is_complete:
                return Response({"status": status.HTTP_400_BAD_REQUEST,"payement": None, "url":None, "add_amount":None, "message": "Registration is over."})
        else:
            if get_league.leagues_start_date < today_date :
                return Response({"status": status.HTTP_400_BAD_REQUEST,"payement": None, "url":None, "add_amount":None, "message": "Registration is over."})
        team_uuid_all = str(team_uuid_all).split(",")
        team_secret_key_all = str(team_secret_key_all).split(",")
        all_team_id = []
        team_details_list = []

        for t in range(len(team_uuid_all)):
            team = Team.objects.filter(uuid=team_uuid_all[t], secret_key=team_secret_key_all[t])
            if team.exists():
                get_team = team.first()
                all_team_id.append(get_team.id)
                team_details_list.append((get_team.id, get_team.name))

        if not all_team_id:
            return Response({"status": status.HTTP_400_BAD_REQUEST, "payement": None, "url":None,"add_amount":None,"message": "No valid teams found."})

        if get_league.start_rank and get_league.end_rank:
            for team_id in all_team_id:
                team = Team.objects.get(id=team_id)
                players = Player.objects.filter(team=team).select_related('player')

                if not players.exists():
                    return Response({"status": status.HTTP_400_BAD_REQUEST, "message": f"Team {team['name']} has no players."})

                team_rank = sum(float(p.player.rank or 0) for p in players) / max(len(players), 1)
                
                if not (get_league.start_rank <= team_rank <= get_league.end_rank):
                    return Response({"status": status.HTTP_400_BAD_REQUEST,"payement": None, "url":None, "add_amount":None, "message": f"{team['name']} does not have the required rank."})

        # ✅ Calculate fees with Decimal
        number_of_team_join = len(all_team_id)
        fees = Decimal(str(get_league.registration_fee))

        others_fees = get_league.others_fees
        if others_fees:
            for val in others_fees.values():
                try:
                    fees += Decimal(str(val))  # Convert everything to Decimal safely
                except (ValueError, TypeError):
                    continue  # Skip non-numeric values safely
        total_amount = fees * Decimal(number_of_team_join)
        #add discount
        if discount != 0:
            discount = Decimal(str(discount))  # Ensure discount is a Decimal
            total_amount = Decimal(str(total_amount))  # Ensure total_amount is a Decimal
            total_amount -= (total_amount * discount) / Decimal("100")
        organizer_amount = (total_amount * Decimal(settings.ORGANIZER_PERCENTAGE)) / Decimal(100)
        admin_amount = (total_amount * Decimal(settings.ADMIN_PERCENTAGE)) / Decimal(100)



        #redy the user register data
        transactiondetails = {}
        transactiondetails["event_id"] = get_league.id
        transactiondetails["event_name"] = get_league.name
        transactiondetails["event_person_type"] = get_league.team_person.name
        transactiondetails["register_user"] = get_user.id
        transactiondetails["team_details_list"] = team_details_list
        if total_amount == 0:
           get_league.registered_team.add(*all_team_id) 
           return Response({"status": status.HTTP_200_OK,"payement": None, "url":None, "add_amount":None, "message": f"You have successfully registered the teams to event {get_league.name}"})
        if balance >= total_amount:
            get_league.registered_team.add(*all_team_id)

            wallet_transaction = WalletTransaction.objects.create(
                sender=get_user,
                reciver=get_league.created_by,                        
                admin_cost=admin_amount.quantize(Decimal('0.001'), rounding=ROUND_DOWN),
                reciver_cost=organizer_amount.quantize(Decimal('0.001'), rounding=ROUND_DOWN),
                getway_charge=Decimal(0),                        
                transaction_for="TeamRegistration",                                   
                transaction_type="debit",
                amount=total_amount.quantize(Decimal('0.001'), rounding=ROUND_DOWN),
                payment_id=None, 
                description=f"${total_amount} is debited from your PickleIt wallet for registering teams to league {get_league.name}."
            )
            # ✅ store team register details
            transaction_for = TransactionFor(transaction=wallet_transaction, details=transactiondetails)
            transaction_for.save()

            # ✅ Update admin wallet
            admin_wallet = Wallet.objects.filter(user__is_superuser=True).first()
            if admin_wallet:
                admin_wallet.balance = Decimal(str(admin_wallet.balance)) + admin_amount
                admin_wallet.save()

            # ✅ Deduct from user wallet
            get_wallet.balance = balance - total_amount
            get_wallet.save()
            
            # ✅ Update organizer wallet
            organizer_wallet = Wallet.objects.filter(user=get_league.created_by).first()
            if organizer_wallet:
                organizer_wallet.balance = Decimal(str(organizer_wallet.balance)) + organizer_amount
                organizer_wallet.save()

            return Response({"status": status.HTTP_200_OK,"payement": "wallet", "url":None, "add_amount":None, "message": f"You have successfully registered the teams to event {get_league.name}"})

        else:
            
            pay_balance = float(total_amount - balance)
            
            stripe_fee = Decimal(pay_balance * 0.029) + Decimal(0.30)
            total_charge = Decimal(pay_balance) + stripe_fee  # Add Stripe fee to total amount
            total_charge = round(total_charge, 2)
            stripe_send_amount = int(round(float(total_charge * 100)))
            # Convert to cents (Stripe works with smallest currency unit)
            chage_amount = int(round(float(pay_balance * 100)))
            # print("chage_amount", chage_amount)
            make_request_data = {"tournament_id":get_league.id,"user_id":get_user.id,"team_id_list":all_team_id, "debited_wallet_balance":str(balance), "details":transactiondetails}
            json_bytes = json.dumps(make_request_data).encode('utf-8')
            my_data = base64.b64encode(json_bytes).decode('utf-8')
            product_name = "Payment For Register Team"
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
            main_url = f"{current_site}/team/c80e2caf03546f11a39db8703fb7f7457afc5cb20db68b5701497fd992a0c29f/{chage_amount}/{my_data}/"
            product = stripe.Product.create(name=product_name,description=product_description,).to_dict()
            price = stripe.Price.create(unit_amount=stripe_send_amount,currency='usd',product=product["id"],).to_dict()
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
            return Response({"status": status.HTTP_200_OK,"payement": "stripe", "url": checkout_session.url,"add_amount":total_charge, "message": f"Please add ${total_charge} to your wallet to register the teams."}) 
    except Exception as e:
        return Response({"status": status.HTTP_400_BAD_REQUEST,"payement": None, "url": None,"add_amount":None, "message": str(e)}) 

def payment_for_team_registration(request, charge_for, my_data, checkout_session_id):
    try:
        stripe.api_key = settings.STRIPE_SECRET_KEY
        pay = stripe.checkout.Session.retrieve(checkout_session_id).to_dict()

        stripe_customer_id = pay.get("customer")
        payment_status = pay.get("payment_status") == "paid"
        expires_at = pay.get("expires_at")
        amount_total = Decimal(pay.get("amount_total", 0)) / 100  # Convert to Decimal
        payment_method_types = pay.get("payment_method_types", [])

        # Decode and parse JSON data
        json_bytes = base64.b64decode(my_data)
        request_data = json.loads(json_bytes.decode('utf-8'))
        debited_wallet_balance = request_data.get("balance")
        transactiondetails = request_data.get("details")
        teams_list = list(request_data.get("team_id_list", []))
        get_user = get_object_or_404(User, id=request_data.get("user_id"))
        teams_count = len(teams_list)
        payment_for = f"Register {teams_count} Team"

        check_tournament = Leagues.objects.filter(id=request_data.get("tournament_id")).first()
        existing_payment = AllPaymentsTable.objects.filter(user=get_user, checkout_session_id=checkout_session_id).exists()

        if not existing_payment and payment_status:
            AllPaymentsTable.objects.create(
                user=get_user,
                amount=amount_total,
                checkout_session_id=checkout_session_id,
                payment_mode=", ".join(payment_method_types),
                payment_for=payment_for,
                status="Completed" if payment_status else "Failed"
            )
            check_tournament.registered_team.add(*teams_list)
            try:
                organizer_amount = (amount_total * Decimal(settings.ORGANIZER_PERCENTAGE)) / 100
                admin_amount = (amount_total * Decimal(settings.ADMIN_PERCENTAGE)) / 100
                if debited_wallet_balance not in ["", 0.00, "None", None, "null", "0.00", 0, "0"]: 
                    total_debit = float(debited_wallet_balance) + float(amount_total)
                else:
                    total_debit = float(amount_total)
                if admin_amount is not None:
                    admin_amount = round(float(admin_amount), 2)
                if organizer_amount is not None:
                    organizer_amount = round(float(organizer_amount), 2)
                if total_debit is not None:
                    total_debit = round(float(total_debit), 2)
                wallet_transaction = WalletTransaction.objects.create(
                    sender=get_user,
                    reciver=check_tournament.created_by,
                    admin_cost=admin_amount,
                    reciver_cost=organizer_amount,
                    getway_charge=Decimal(0),
                    transaction_for="TeamRegistration",
                    transaction_type="debit",
                    amount=total_debit,
                    payment_id=checkout_session_id,
                    description=f"${amount_total} is debited from your PickleIt wallet for registering teams to event {check_tournament.name}."
                )
                # ✅ store team register details
                transaction_for = TransactionFor(transaction=wallet_transaction, details=transactiondetails)
                transaction_for.save()
            except:
                pass

        if payment_status:
            return render(request, "success_payment_for_register_team.html")
        else:
            return render(request, "failed_paymentregister_team.html")

    except Exception as e:
        print(f"Error in payment_for_team_registration: {str(e)}")
        return render(request, "failed_paymentregister_team.html")


#get organizer event api
@api_view(('GET',))
def search_user_to_add_organizer(request):
    data = {'status': '', 'message': ''}
    try:
        user_uuid = request.GET.get('user_uuid') 
        search_name = request.GET.get('search_name')
        check_user = User.objects.filter(uuid=user_uuid)

        if not check_user.exists():
            return Response({
                "data": [],
                "status": status.HTTP_401_UNAUTHORIZED, 
                "message": "Unauthorized access"
            })
        matching_users = User.objects.filter(Q(first_name__icontains=search_name) | Q(last_name__icontains=search_name)).exclude(uuid=user_uuid)

        if not matching_users.exists():
            return Response({
                "data": [],
                "status": status.HTTP_404_NOT_FOUND,
                "message": "No users found with the given name."
            }, status=status.HTTP_404_NOT_FOUND)

        # Prepare response data
        data['data'] = [{"id": user.id, "first_name": user.first_name, "last_name": user.last_name} for user in matching_users]
        data['status'], data['message'] = status.HTTP_200_OK, "Users retrieved successfully."  

    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)

    return Response(data)


#add organizer api
@api_view(('POST',))
def add_organizer_league(request):
    data = {'status': '', 'message': ''}
    try:
        user_uuid = request.data.get('user_uuid')       
        league_uuid = request.data.get('league_uuid')       
        organizer_id_list = request.data.get('organizer_id_list')      
        if isinstance(organizer_id_list, str):
            try:
                organizer_id_list = json.loads(organizer_id_list)  # Convert JSON string to list
            except json.JSONDecodeError:
                return Response({
                    "status": status.HTTP_400_BAD_REQUEST,
                    "message": "Invalid JSON format for organizer_id_list."
                }, status=status.HTTP_400_BAD_REQUEST)

        # If it's a single integer, convert it to a list
        if isinstance(organizer_id_list, int):
            organizer_id_list = [organizer_id_list]  # Wrap in a list

        # Ensure it's a list of integers
        if not isinstance(organizer_id_list, list) or not all(isinstance(i, int) for i in organizer_id_list):
            return Response({
                "status": status.HTTP_400_BAD_REQUEST,
                "message": "organizer_id_list must be a list of integers."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        check_user = User.objects.filter(uuid=user_uuid)
        check_league = Leagues.objects.filter(uuid=league_uuid)

        if not check_user.exists():
            return Response({
                "data": [],
                "status": status.HTTP_401_UNAUTHORIZED, 
                "message": "Unauthorized access"
            })
        
        if not check_league.exists():
            return Response({
                "data": [],
                "status": status.HTTP_401_UNAUTHORIZED, 
                "message": "League not found"
            })
         
        get_user = check_user.first()
        get_league = check_league.first()

        if get_league.created_by == get_user or get_user in get_league.add_organizer.all():            
            get_league.add_organizer.clear()
            for org_id in organizer_id_list:
                organizer_instance = User.objects.filter(id=int(org_id)).first()
                if organizer_instance:
                    get_league.add_organizer.add(organizer_instance)
            get_league.save()

            data["status"], data["message"] = status.HTTP_200_OK, "Tournament organizers updated successfully."
        else:
            data["status"], data["message"] = status.HTTP_403_FORBIDDEN, "User does not have permission to add organizers for this tournament."
        
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)

    return Response(data)


#removed organizer api

#start event api
def calculate_team_rank(team):
    """Calculate the average rank of a team based on its players."""
    players = team.player_set.all()  # Assuming 'playerTeam' is the related_name for Player.team
    if not players.exists():
        return 0  # Default rank if no players
    total_rank = sum(float(player.player.rank or '1') for player in players)
    return total_rank / players.count()

def create_group(team_ids, num_parts):
    num_parts = int(num_parts)
    if num_parts <= 0:
        return "Number of parts should be greater than zero."
    
    # Fetch teams corresponding to the team_ids (using id instead of uuid)
    teams = Team.objects.filter(id__in=team_ids)
    
    # Calculate rank for each team and sort by rank (highest first)
    team_list = [(team.id, calculate_team_rank(team)) for team in teams]
    team_list.sort(key=lambda x: x[1], reverse=True)  # Sort by rank, descending
    # Extract sorted team IDs
    sorted_team_ids = [team[0] for team in team_list]
    total_teams = len(sorted_team_ids)
    
    # Calculate how many teams per group
    teams_per_group = total_teams // num_parts
    remainder = total_teams % num_parts  # Extra teams to distribute
    
    # Initialize groups
    group_list = [[] for _ in range(num_parts)]
    
    # Distribute teams using the pattern: R1, R1+num_parts, R1+2*num_parts, etc.
    for i, team_id in enumerate(sorted_team_ids):
        # Determine which group this team goes into
        group_idx = i % num_parts
        group_list[group_idx].append(team_id)
    
    # Ensure groups are balanced (trim if uneven due to remainder)
    max_group_size = teams_per_group + (1 if remainder > 0 else 0)
    for i in range(num_parts):
        if len(group_list[i]) > max_group_size:
            group_list[i] = group_list[i][:max_group_size]
    print(group_list)
    return group_list

def make_shuffale(input_list):
    result = []
    try:
        for i in range(0, len(input_list), 2):  # Step by 2 to process pairs
            # First pair of the set
            result.append(input_list[i][0])    # A1
            result.append(input_list[i+1][1])  # B2
            result.append(input_list[i][1])    # A2
            result.append(input_list[i+1][0])  # B1
    except:
        pass
    return result


@api_view(('POST',))
def assigne_match(request):
    data = {'status': '', 'message': ''}
    user_uuid = request.data.get('user_uuid')
    user_secret_key = request.data.get('user_secret_key')
    league_uuid = request.data.get('league_uuid')
    league_secret_key = request.data.get('league_secret_key')
    check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
    check_leagues = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)
    
    if check_user.exists() and check_leagues.exists():
        league = check_leagues.first()
        playtype = league.play_type
        get_details = LeaguesPlayType.objects.filter(league_for=league).values("data")
        
        registered_teams = league.registered_team.all() if league else None
        team_details_list = [team.id for team in registered_teams] if registered_teams else []
        max_team = league.max_number_team
        if int(max_team) != len(team_details_list):
            data["status"],  data["message"] = status.HTTP_200_OK, f"All teams are not registered"
            return Response(data)
        
        #round rabin
        court_num_r = int(get_details[0]["data"][0]["number_of_courts"])
        set_num_r = int(get_details[0]["data"][0]["sets"])
        point_num_r = int(get_details[0]["data"][0]["point"])

        #elemination
        # if get_details[0]["data"][1]["number_of_courts"] == 0 or not get_details[0]["data"][1]["number_of_courts"]:
        court_num_e = int(get_details[0]["data"][1]["number_of_courts"])
        set_num_e = int(get_details[0]["data"][1]["sets"])
        point_num_e = int(get_details[0]["data"][1]["point"])


        #final
        court_num_f = int(get_details[0]["data"][2]["number_of_courts"])
        set_num_f = int(get_details[0]["data"][2]["sets"])
        point_num_f = int(get_details[0]["data"][2]["point"])

        # tournamnet start notification all team
        try:
            # If start the tournament
            #backup 
            if not Tournament.objects.filter(leagues = league).exists():
                league_name = league.name
                # send the notification
                all_team = league.registered_team.all().values_list("id", flat=True)
                for s_team in list(all_team):
                    team_manager_message = f"The tournament {league_name}, has started."
                    team_manager = Team.objects.filter(id=s_team).first().created_by
                    print(team_manager)
                    titel=f"Start Tournament"
                    notify_edited_player(team_manager.id, titel, team_manager_message)

                    # how many player in team and player details
                    player_in_team = Player.objects.filter(team__id = s_team)
                    for p in player_in_team:
                        message_s = f"Player, get ready! The tournament {league_name}, has started."
                        user = p.player
                        titel=f"Start Tournament"
                        notify_edited_player(user.id, titel, message_s)
        except:
            pass
        #done
        if playtype == "Single Elimination":
            register_team = league.registered_team.all().count()
            if league.max_number_team != register_team:
                data["status"], data["message"] = status.HTTP_200_OK, "All teams are not joined"
                return Response(data)
            
            check_pre_game =  Tournament.objects.filter(leagues=league)
            if check_pre_game.exists():
                check_leagues_com = check_pre_game.filter(is_completed=True)
                if len(check_pre_game) == len(check_leagues_com) and len(check_leagues_com) != 0:
                    pre_match_round = check_leagues_com.last().elimination_round
                    pre_round_details =  Tournament.objects.filter(leagues=league,elimination_round=pre_match_round)
                    teams = list(pre_round_details.values_list("winner_team_id", flat=True))
                    pre_match_number = check_leagues_com.last().match_number
                    court_num = 0
                    if len(teams) == 4:
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        match_type = "Semi Final"
                        round_number = 0
                        random.shuffle(teams)
                        match_number_now = pre_match_number
                        
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num = court_num + 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                        return Response(data)   
                    elif len(teams) == 2:
                        sets__ = set_num_f
                        courts__ = court_num_f
                        points__ = point_num_f
                        match_type = "Final"
                        round_number = 0
                        random.shuffle(teams)
                        match_number_now = pre_match_number
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num = court_num + 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                        return Response(data)
                    else:
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        match_type = "Elimination Round"
                        round_number = pre_match_round + 1
                        random.shuffle(teams)
                        match_number_now = pre_match_number
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num = court_num + 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}-{round_number}"
                        return Response(data)
                else:
                    data["status"], data["message"] = status.HTTP_200_OK, "Previous Round is not completed or not updated"
                    return Response(data)
            else:
                teams = []
                court_num = 0
                sets__ = set_num_e
                courts__ = court_num_e
                points__ = point_num_e
                for grp in check_leagues:
                    teams__ = grp.registered_team.all()
                    for te in teams__:
                        teams.append(te.id)
                if len(teams) == 4:
                    match_type = "Semi Final"
                    random.shuffle(teams)
                    match_number_now = 0
                    for i in range(0, len(teams), 2):
                        team1 = teams[i]
                        team2 = teams[i + 1]
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        match_number_now = match_number_now + 1
                        court_num = court_num + 1
                        if courts__ <= court_num:
                            court_num = 1
                        Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=0)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                    return Response(data)
                if len(teams) == 2:
                    sets__ = set_num_f
                    courts__ = court_num_f
                    points__ = point_num_f
                    match_type = "Final"
                    random.shuffle(teams)
                    match_number_now = 0
                    for i in range(0, len(teams), 2):
                        team1 = teams[i]
                        team2 = teams[i + 1]
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        match_number_now = match_number_now + 1
                        court_num = court_num + 1
                        if courts__ <= court_num:
                            court_num = 1
                        Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=0)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                    return Response(data)
                else:
                    print("hit")
                    match_type = "Elimination Round"
                    random.shuffle(teams)
                    match_number_now = 0
                    for i in range(0, len(teams), 2):
                        team1 = teams[i]
                        team2 = teams[i + 1]
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        match_number_now = match_number_now + 1
                        court_num = court_num + 1
                        if courts__ <= court_num:
                            court_num = 1
                        Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=1)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                    return Response(data)
        
        #done
        elif playtype == "Group Stage":
            check_pre_game =  Tournament.objects.filter(leagues=league)
            if check_pre_game.exists():
                all_round_robin_match = Tournament.objects.filter(leagues=league)
                all_completed_round_robin_match = Tournament.objects.filter(leagues=league, is_completed=True)
                if all_round_robin_match.exists() and all_completed_round_robin_match.exists() and all_round_robin_match.count() == all_completed_round_robin_match.count():
                    check_pre_game =  Tournament.objects.filter(leagues=league)
                    last_match_type = check_pre_game.last().match_type
                    last_round = check_pre_game.last().elimination_round
                    last_match_number = check_pre_game.last().match_number
                    if last_match_type == "Round Robin":
                        all_group_details = RoundRobinGroup.objects.filter(league_for=league)
                        teams = []
                        # ch = []
                        for grp in all_group_details:
                            teams_ins = grp.all_teams.all()
                            group_score_point_table = []
                            for team in teams_ins:
                                team_score = {}
                                total_match_detals = Tournament.objects.filter(leagues=league).filter(Q(team1=team) | Q(team2=team))
                                completed_match_details = total_match_detals.filter(is_completed=True)
                                win_match_details = completed_match_details.filter(winner_team=team).count()
                                loss_match_details = completed_match_details.filter(loser_team=team).count()
                                drow_match = len(completed_match_details) - (win_match_details + loss_match_details)
                                point = (win_match_details * 3) + (drow_match * 1)
                                match_list = list(total_match_detals.values_list("id", flat=True))
                                for_score = 0
                                aginst_score = 0
                                for sc in match_list:
                                    co_team_position = Tournament.objects.filter(id=sc).first()
                                    set_score = TournamentSetsResult.objects.filter(tournament_id=sc)
                                    if co_team_position.team1 == team:
                                        for_score = for_score + sum(list(set_score.values_list("team1_point", flat=True)))
                                        aginst_score = aginst_score + sum(list(set_score.values_list("team2_point", flat=True)))
                                    else:
                                        for_score = for_score + sum(list(set_score.values_list("team2_point", flat=True)))
                                        aginst_score = aginst_score + sum(list(set_score.values_list("team1_point", flat=True)))
                                team_score["uuid"], team_score["secret_key"] = team.uuid, team.secret_key
                                team_score["completed_match"] = len(completed_match_details)
                                team_score["win_match"], team_score["loss_match"] = win_match_details, loss_match_details
                                team_score["drow_match"], team_score["for_score"] = drow_match, drow_match
                                team_score["aginst_score"], team_score["point"] = drow_match, for_score
                                group_score_point_table.append(team_score)
                            #need to check
                            grp_team = sorted(group_score_point_table, key=lambda x: (x['point'], x['for_score']), reverse=True)
                            # print(grp_team)
                            top_two_teams = grp_team[:2]
                            # print(top_two_teams)
                            teams_ = []
                            for top_team in top_two_teams:
                                team_instance = Team.objects.get(uuid=top_team["uuid"], secret_key=top_team["secret_key"])
                                # teams.append(team_instance.id)
                                teams_.append(team_instance.id)
                            teams.append(teams_)
                            select_team_instance = Team.objects.filter(uuid=grp_team[0]["uuid"],secret_key=grp_team[0]["secret_key"])
                            RoundRobinGroup.objects.filter(id=grp.id).update(seleced_teams=select_team_instance.first())
                        
                        
                        match_type = "Elimination Round"
                        round_number = 1
                        
                        if len(teams) != len(RoundRobinGroup.objects.filter(league_for=league)):
                            data["status"],  data["message"] = status.HTTP_200_OK, f"Not all groups have winners selected"
                            return Response(data)
                        teams = make_shuffale(teams)
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        if len(teams) == 2:
                            match_type = "Final"
                            round_number = 0
                            sets__ = set_num_f
                            courts__ = court_num_f
                            points__ = point_num_f
                        elif len(teams) == 4:
                            match_type = "Semi Final"
                            round_number = 0
                            sets__ = set_num_e
                            courts__ = court_num_e
                            points__ = point_num_e
                        elif len(teams) > 4:
                            match_type = "Elimination Round"
                        # random.shuffle(teams)
                        # print(teams)
                        match_number_now = last_match_number
                        court_num = 0
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num += 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created for {match_type}"
                        return Response(data)
                    
                    elif last_match_type == "Elimination Round":
                        match_type = "Elimination Round"
                        round_number = last_round + 1
                        # win_teams
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        teams = list(Tournament.objects.filter(leagues=league, elimination_round=last_round).values_list("winner_team_id", flat=True))
                        if len(teams) != len(Tournament.objects.filter(leagues=league, elimination_round=last_round)):
                            data["status"],  data["message"] = status.HTTP_200_OK, f"Not all groups have winners selected"
                            return Response(data)
                        
                        elif len(teams) == 2:
                            match_type = "Final"
                            round_number = 0
                            sets__ = set_num_f
                            courts__ = court_num_f
                            points__ = point_num_f
                        elif len(teams) == 4:
                            match_type = "Semi Final"
                            round_number = 0
                        random.shuffle(teams)
                        match_number_now = last_match_number
                        court_num = 0
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num += 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created for {match_type} {round_number}"
                        return Response(data)
                    elif last_match_type == "Semi Final":
                        match_type = "Final"
                        round_number = 0
                        sets__ = set_num_f
                        courts__ = court_num_f
                        points__ = point_num_f
                        winning_teams = list(Tournament.objects.filter(leagues=league, match_type="Semi Final").values_list('winner_team_id', flat=True))
                        
                        #Tournament.objects.filter(leagues=league, match_type="Semi Final") #backup
                        if len(winning_teams) != 2:
                            data["status"],  data["message"] = status.HTTP_200_OK, f"Not all groups have winners selected"
                            return Response(data)
                        random.shuffle(winning_teams)
                        match_number_now = last_match_number
                        court_num = 0
                        for i in range(0, len(winning_teams), 2):
                            team1 = winning_teams[i]
                            team2 = winning_teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num += 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created for {match_type} ."
                        return Response(data)
                    elif last_match_type == "Final":
                        data["status"],  data["message"] = status.HTTP_200_OK, f"The event results are out! The event is completed successfully."
                        return Response(data)
                else:
                    data["status"],  data["message"] = status.HTTP_200_OK, f"All matches in this round are not completed yet."
                    return Response(data)
            else:
                #create Robin Round
                registered_teams = league.registered_team.all() if league else None
                team_details_list = [team.id for team in registered_teams] if registered_teams else []
                
                play_details = LeaguesPlayType.objects.filter(league_for=league).first()
                number_of_group = court_num_r
                
                group_list = create_group(team_details_list, number_of_group)
                
                round_robin_group_details = RoundRobinGroup.objects.filter(league_for=league)
                if round_robin_group_details.exists():
                    if len(round_robin_group_details) == number_of_group:
                        
                        data["status"],  data["message"] = status.HTTP_200_OK, f"Round Robin matches already created for {league.name}"
                        return Response(data)
                    else:
                        for gr in round_robin_group_details:
                            Tournament.objects.filter(group_id=gr.id).delete
                            gr.delete()
                serial_number = 0
                
                for index, group_teams in enumerate(group_list, start=1):
                    group = RoundRobinGroup.objects.create(court=index, league_for=league, number_sets=set_num_r)
                    for team_id in group_teams:
                        team = Team.objects.get(id=team_id)
                        group.all_teams.add(team)
                    
                    # match_combinations = list(combinations(group_teams, 2))
                    match_combinations = [(team1, team2) for i, team1 in enumerate(group_teams) for team2 in group_teams[i+1:]]

                    # Shuffle the matches to randomize
                    random.shuffle(match_combinations)
                    for teams in match_combinations:
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        team1, team2 = teams
                        serial_number = serial_number+1
                        Tournament.objects.create(set_number=set_num_r,court_num=index,points=point_num_r,match_number=serial_number,secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, group_id=group.id,match_type="Round Robin")
                data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created successfully"
                return Response(data)
        
        #done
        elif playtype in ["Round Robin", "Round Robbin Compete to Final" , "Robbin Randomizer"]:
            match_type = playtype
            registered_teams = league.registered_team.all() if league else None
            team_details_list = [team.id for team in registered_teams] if registered_teams else []
            max_team = league.max_number_team
            play_details = LeaguesPlayType.objects.filter(league_for=league).first()
            number_of_group = 1
            if int(max_team) != len(team_details_list):
                data["status"],  data["message"] = status.HTTP_200_OK, f"All teams are not registered"
                return Response(data)
            group_list = create_group(team_details_list, number_of_group)
            round_robin_group_details = RoundRobinGroup.objects.filter(league_for=league)
            if round_robin_group_details.exists():
                if len(round_robin_group_details) == number_of_group:
                    data["status"],  data["message"] = status.HTTP_200_OK, f"Round Robin group already created for {league.name}"
                    return Response(data)
                else:
                    for gr in round_robin_group_details:
                        Tournament.objects.filter(group_id=gr.id).delete
                        gr.delete()
            serial_number = 0
            
            for index, group_teams in enumerate(group_list, start=1):
                group = RoundRobinGroup.objects.create(court=index, league_for=league, number_sets=set_num_r)
                for team_id in group_teams:
                    team = Team.objects.get(id=team_id)
                    group.all_teams.add(team)
                
                # match_combinations = list(combinations(group_teams, 2))
                match_combinations = [(team1, team2) for i, team1 in enumerate(group_teams) for team2 in group_teams[i+1:]]

                # Shuffle the matches to randomize
                random.shuffle(match_combinations)
                for teams in match_combinations:
                    obj = GenerateKey()
                    secret_key = obj.generate_league_unique_id()
                    team1, team2 = teams
                    serial_number = serial_number+1
                    Tournament.objects.create(set_number=set_num_r,court_num=index,points=point_num_r,match_number=serial_number,secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, group_id=group.id,match_type="Round Robin")
            data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
            return Response(data)
        
       
        elif playtype == "Individual Match Play":
            print("enter")
            match_type = playtype
            team____ = league.registered_team.all()
            teams = []
            for te in team____:
                teams.append(te.id)
            check_tournament = Tournament.objects.filter(leagues=league,match_type=match_type)
            if check_tournament.exists():
                data["status"], data["message"] = status.HTTP_200_OK, "Matches are already created"
                return Response(data) 
            if len(teams) != 2:
                data["status"], data["message"] = status.HTTP_200_OK, "Mininum 2 teams are needed for individual match play"
                return Response(data) 
            sets__ = set_num_f
            courts__ = court_num_f
            points__ = point_num_f
            round_number = 0
            random.shuffle(teams)
            match_number_now = 0
            # court_num = 0

            set_court = 8
            court_num = 0
            for count in range(courts__):
                court_num = court_num + 1
                match_number_now = court_num
                for i in range(0, len(teams), 2):
                    team1 = teams[i]
                    team2 = teams[i + 1]
                    obj = GenerateKey()
                    secret_key = obj.generate_league_unique_id()
                    Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number) 
            
            data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
            return Response(data)
    # if tournamnet not found
    else:
        data["status"], data["data"],data["ttt"],data["uuu"], data["message"] = status.HTTP_404_NOT_FOUND, [user_uuid,user_secret_key,league_uuid,league_secret_key],list(check_leagues),list(check_user), "User or Tournament not found."
    return Response(data)





"""
[
{"name": "Round Robin", "sets": "1", "point": "15", "is_show": true, "number_of_courts": "4"}, 
{"name": "Elimination", "sets": "1", "point": "15", "is_show": true, "number_of_courts": "4"}, 
{"name": "Final", "sets": "3", "point": "11", "is_show": true, "number_of_courts": "1"}
]
"""

def get_play_type_details(event_id):
    responce = {"status": False, "message": "", "data": []}
    play_type = LeaguesPlayType.objects.filter(league_for_id=event_id)
    if not play_type.exists():
        responce["status"] = False
        responce["message"] = "Play type not found"
        return responce

    play_type = play_type.first()
    data = play_type.data
    #get number of courts list
    number_of_courts = [typ["number_of_courts"] for typ in data if typ["is_show"] in [True, "true"]]
    if 0 in number_of_courts:
        responce["status"] = False
        responce["message"] = "Number of courts should be greater than 0, please set playtype details again"
        return responce
    responce["status"] = True
    responce["message"] = "Play type details found"
    responce["data"] = data
    return responce

def event_point_table(event_id):
    ponit_table = []
    event = Leagues.objects.filter(id=event_id)
    group = RoundRobinGroup.objects.filter(league_for=event)
    Tournament.objects.filter(leagues=event)
    return ponit_table


@api_view(('POST',))
def assigne_match(request):
    data = {'status': '', 'message': ''}
    user_uuid = request.data.get('user_uuid')
    league_uuid = request.data.get('league_uuid')
    user = get_object_or_404(User, uuid=user_uuid)
    event = get_object_or_404(Leagues, uuid=league_uuid)
    organizer_list = event.organizer.all()
    join_team_count = event.registered_team.all().count()
    max_team = event.max_number_team

    if user not in organizer_list:
        data["status"], data["message"] = status.HTTP_403_FORBIDDEN, "You are not authorized to access this event."
        return Response(data)
    if join_team_count != max_team:
        data["status"], data["message"] = status.HTTP_200_OK, "All teams are not registered yet."
        return Response(data)


    #ready the play type details
    play_details = get_play_type_details(event.id)
    if play_details["status"] == False:
        data["status"], data["message"] = status.HTTP_200_OK, play_details["message"]
        return Response(data)
    
    play_type_details = play_details["data"]
    #round robin play details
    R_court_num = int(play_type_details[0]["number_of_courts"])
    R_set = int(play_type_details[0]["sets"])
    R_point = int(play_type_details[0]["point"])
    #elemination play details
    E_court_num = int(play_type_details[1]["number_of_courts"])
    E_set = int(play_type_details[1]["sets"])
    E_point = int(play_type_details[1]["point"])
    #final play details
    F_court_num = int(play_type_details[2]["number_of_courts"])
    F_set = int(play_type_details[2]["sets"])
    F_point = int(play_type_details[2]["point"])


    
    if event.play_type == "Individual Match Play":
        pass
    if event.play_type == "Single Elimination":
        pass
    if event.play_type == "Group Stage":
        #check the game is strated or not
        check_group = RoundRobinGroup.objects.filter(league_for=event)
        tournament_complete_status = Tournament.objects.filter(leagues=event, is_completed=False)
        # if match started but not completed all matches
        if check_group.exists() and tournament_complete_status.exists():
            data["status"], data["message"] = status.HTTP_200_OK, "Tournament already started, After Complete the All matches, you can assign Next."
            return Response(data)
        # if complete all matches
        elif check_group.exists() and not tournament_complete_status.exists():
            #need to calculate the point table and need a output to organizer how many teams are selected
            point_table = event_point_table(event.id)
    
    if event.play_type == "Round Robin":
        pass


    if check_user.exists() and check_leagues.exists():
        league = check_leagues.first()
        playtype = league.play_type
        get_details = LeaguesPlayType.objects.filter(league_for=league).values("data")
        
        registered_teams = league.registered_team.all() if league else None
        team_details_list = [team.id for team in registered_teams] if registered_teams else []
        max_team = league.max_number_team
        if int(max_team) != len(team_details_list):
            data["status"],  data["message"] = status.HTTP_200_OK, f"All teams are not registered"
            return Response(data)
        
        #round rabin
        court_num_r = int(get_details[0]["data"][0]["number_of_courts"])
        set_num_r = int(get_details[0]["data"][0]["sets"])
        point_num_r = int(get_details[0]["data"][0]["point"])

        #elemination
        # if get_details[0]["data"][1]["number_of_courts"] == 0 or not get_details[0]["data"][1]["number_of_courts"]:
        court_num_e = int(get_details[0]["data"][1]["number_of_courts"])
        set_num_e = int(get_details[0]["data"][1]["sets"])
        point_num_e = int(get_details[0]["data"][1]["point"])


        #final
        court_num_f = int(get_details[0]["data"][2]["number_of_courts"])
        set_num_f = int(get_details[0]["data"][2]["sets"])
        point_num_f = int(get_details[0]["data"][2]["point"])

        # tournamnet start notification all team
        try:
            # If start the tournament
            #backup 
            if not Tournament.objects.filter(leagues = league).exists():
                league_name = league.name
                # send the notification
                all_team = league.registered_team.all().values_list("id", flat=True)
                for s_team in list(all_team):
                    team_manager_message = f"The tournament {league_name}, has started."
                    team_manager = Team.objects.filter(id=s_team).first().created_by
                    print(team_manager)
                    titel=f"Start Tournament"
                    notify_edited_player(team_manager.id, titel, team_manager_message)

                    # how many player in team and player details
                    player_in_team = Player.objects.filter(team__id = s_team)
                    for p in player_in_team:
                        message_s = f"Player, get ready! The tournament {league_name}, has started."
                        user = p.player
                        titel=f"Start Tournament"
                        notify_edited_player(user.id, titel, message_s)
        except:
            pass
        #done
        if playtype == "Single Elimination":
            register_team = league.registered_team.all().count()
            if league.max_number_team != register_team:
                data["status"], data["message"] = status.HTTP_200_OK, "All teams are not joined"
                return Response(data)
            
            check_pre_game =  Tournament.objects.filter(leagues=league)
            if check_pre_game.exists():
                check_leagues_com = check_pre_game.filter(is_completed=True)
                if len(check_pre_game) == len(check_leagues_com) and len(check_leagues_com) != 0:
                    pre_match_round = check_leagues_com.last().elimination_round
                    pre_round_details =  Tournament.objects.filter(leagues=league,elimination_round=pre_match_round)
                    teams = list(pre_round_details.values_list("winner_team_id", flat=True))
                    pre_match_number = check_leagues_com.last().match_number
                    court_num = 0
                    if len(teams) == 4:
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        match_type = "Semi Final"
                        round_number = 0
                        random.shuffle(teams)
                        match_number_now = pre_match_number
                        
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num = court_num + 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                        return Response(data)   
                    elif len(teams) == 2:
                        sets__ = set_num_f
                        courts__ = court_num_f
                        points__ = point_num_f
                        match_type = "Final"
                        round_number = 0
                        random.shuffle(teams)
                        match_number_now = pre_match_number
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num = court_num + 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                        return Response(data)
                    else:
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        match_type = "Elimination Round"
                        round_number = pre_match_round + 1
                        random.shuffle(teams)
                        match_number_now = pre_match_number
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num = court_num + 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}-{round_number}"
                        return Response(data)
                else:
                    data["status"], data["message"] = status.HTTP_200_OK, "Previous Round is not completed or not updated"
                    return Response(data)
            else:
                teams = []
                court_num = 0
                sets__ = set_num_e
                courts__ = court_num_e
                points__ = point_num_e
                for grp in check_leagues:
                    teams__ = grp.registered_team.all()
                    for te in teams__:
                        teams.append(te.id)
                if len(teams) == 4:
                    match_type = "Semi Final"
                    random.shuffle(teams)
                    match_number_now = 0
                    for i in range(0, len(teams), 2):
                        team1 = teams[i]
                        team2 = teams[i + 1]
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        match_number_now = match_number_now + 1
                        court_num = court_num + 1
                        if courts__ <= court_num:
                            court_num = 1
                        Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=0)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                    return Response(data)
                if len(teams) == 2:
                    sets__ = set_num_f
                    courts__ = court_num_f
                    points__ = point_num_f
                    match_type = "Final"
                    random.shuffle(teams)
                    match_number_now = 0
                    for i in range(0, len(teams), 2):
                        team1 = teams[i]
                        team2 = teams[i + 1]
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        match_number_now = match_number_now + 1
                        court_num = court_num + 1
                        if courts__ <= court_num:
                            court_num = 1
                        Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=0)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                    return Response(data)
                else:
                    print("hit")
                    match_type = "Elimination Round"
                    random.shuffle(teams)
                    match_number_now = 0
                    for i in range(0, len(teams), 2):
                        team1 = teams[i]
                        team2 = teams[i + 1]
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        match_number_now = match_number_now + 1
                        court_num = court_num + 1
                        if courts__ <= court_num:
                            court_num = 1
                        Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now, secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, match_type=match_type, elimination_round=1)
                    data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
                    return Response(data)
        
        #done
        elif playtype == "Group Stage":
            check_pre_game =  Tournament.objects.filter(leagues=league)
            if check_pre_game.exists():
                all_round_robin_match = Tournament.objects.filter(leagues=league)
                all_completed_round_robin_match = Tournament.objects.filter(leagues=league, is_completed=True)
                if all_round_robin_match.exists() and all_completed_round_robin_match.exists() and all_round_robin_match.count() == all_completed_round_robin_match.count():
                    check_pre_game =  Tournament.objects.filter(leagues=league)
                    last_match_type = check_pre_game.last().match_type
                    last_round = check_pre_game.last().elimination_round
                    last_match_number = check_pre_game.last().match_number
                    if last_match_type == "Round Robin":
                        all_group_details = RoundRobinGroup.objects.filter(league_for=league)
                        teams = []
                        # ch = []
                        for grp in all_group_details:
                            teams_ins = grp.all_teams.all()
                            group_score_point_table = []
                            for team in teams_ins:
                                team_score = {}
                                total_match_detals = Tournament.objects.filter(leagues=league).filter(Q(team1=team) | Q(team2=team))
                                completed_match_details = total_match_detals.filter(is_completed=True)
                                win_match_details = completed_match_details.filter(winner_team=team).count()
                                loss_match_details = completed_match_details.filter(loser_team=team).count()
                                drow_match = len(completed_match_details) - (win_match_details + loss_match_details)
                                point = (win_match_details * 3) + (drow_match * 1)
                                match_list = list(total_match_detals.values_list("id", flat=True))
                                for_score = 0
                                aginst_score = 0
                                for sc in match_list:
                                    co_team_position = Tournament.objects.filter(id=sc).first()
                                    set_score = TournamentSetsResult.objects.filter(tournament_id=sc)
                                    if co_team_position.team1 == team:
                                        for_score = for_score + sum(list(set_score.values_list("team1_point", flat=True)))
                                        aginst_score = aginst_score + sum(list(set_score.values_list("team2_point", flat=True)))
                                    else:
                                        for_score = for_score + sum(list(set_score.values_list("team2_point", flat=True)))
                                        aginst_score = aginst_score + sum(list(set_score.values_list("team1_point", flat=True)))
                                team_score["uuid"], team_score["secret_key"] = team.uuid, team.secret_key
                                team_score["completed_match"] = len(completed_match_details)
                                team_score["win_match"], team_score["loss_match"] = win_match_details, loss_match_details
                                team_score["drow_match"], team_score["for_score"] = drow_match, drow_match
                                team_score["aginst_score"], team_score["point"] = drow_match, for_score
                                group_score_point_table.append(team_score)
                            #need to check
                            grp_team = sorted(group_score_point_table, key=lambda x: (x['point'], x['for_score']), reverse=True)
                            # print(grp_team)
                            top_two_teams = grp_team[:2]
                            # print(top_two_teams)
                            teams_ = []
                            for top_team in top_two_teams:
                                team_instance = Team.objects.get(uuid=top_team["uuid"], secret_key=top_team["secret_key"])
                                # teams.append(team_instance.id)
                                teams_.append(team_instance.id)
                            teams.append(teams_)
                            select_team_instance = Team.objects.filter(uuid=grp_team[0]["uuid"],secret_key=grp_team[0]["secret_key"])
                            RoundRobinGroup.objects.filter(id=grp.id).update(seleced_teams=select_team_instance.first())
                        
                        
                        match_type = "Elimination Round"
                        round_number = 1
                        
                        if len(teams) != len(RoundRobinGroup.objects.filter(league_for=league)):
                            data["status"],  data["message"] = status.HTTP_200_OK, f"Not all groups have winners selected"
                            return Response(data)
                        teams = make_shuffale(teams)
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        if len(teams) == 2:
                            match_type = "Final"
                            round_number = 0
                            sets__ = set_num_f
                            courts__ = court_num_f
                            points__ = point_num_f
                        elif len(teams) == 4:
                            match_type = "Semi Final"
                            round_number = 0
                            sets__ = set_num_e
                            courts__ = court_num_e
                            points__ = point_num_e
                        elif len(teams) > 4:
                            match_type = "Elimination Round"
                        # random.shuffle(teams)
                        # print(teams)
                        match_number_now = last_match_number
                        court_num = 0
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num += 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created for {match_type}"
                        return Response(data)
                    elif last_match_type == "Elimination Round":
                        match_type = "Elimination Round"
                        round_number = last_round + 1
                        # win_teams
                        sets__ = set_num_e
                        courts__ = court_num_e
                        points__ = point_num_e
                        teams = list(Tournament.objects.filter(leagues=league, elimination_round=last_round).values_list("winner_team_id", flat=True))
                        if len(teams) != len(Tournament.objects.filter(leagues=league, elimination_round=last_round)):
                            data["status"],  data["message"] = status.HTTP_200_OK, f"Not all groups have winners selected"
                            return Response(data)
                        
                        elif len(teams) == 2:
                            match_type = "Final"
                            round_number = 0
                            sets__ = set_num_f
                            courts__ = court_num_f
                            points__ = point_num_f
                        elif len(teams) == 4:
                            match_type = "Semi Final"
                            round_number = 0
                        random.shuffle(teams)
                        match_number_now = last_match_number
                        court_num = 0
                        for i in range(0, len(teams), 2):
                            team1 = teams[i]
                            team2 = teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num += 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created for {match_type} {round_number}"
                        return Response(data)
                    elif last_match_type == "Semi Final":
                        match_type = "Final"
                        round_number = 0
                        sets__ = set_num_f
                        courts__ = court_num_f
                        points__ = point_num_f
                        winning_teams = list(Tournament.objects.filter(leagues=league, match_type="Semi Final").values_list('winner_team_id', flat=True))
                        
                        #Tournament.objects.filter(leagues=league, match_type="Semi Final") #backup
                        if len(winning_teams) != 2:
                            data["status"],  data["message"] = status.HTTP_200_OK, f"Not all groups have winners selected"
                            return Response(data)
                        random.shuffle(winning_teams)
                        match_number_now = last_match_number
                        court_num = 0
                        for i in range(0, len(winning_teams), 2):
                            team1 = winning_teams[i]
                            team2 = winning_teams[i + 1]
                            obj = GenerateKey()
                            secret_key = obj.generate_league_unique_id()
                            match_number_now = match_number_now + 1
                            court_num += 1
                            if courts__ <= court_num:
                                court_num = 1
                            Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number)
                        data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created for {match_type} ."
                        return Response(data)
                    elif last_match_type == "Final":
                        data["status"],  data["message"] = status.HTTP_200_OK, f"The event results are out! The event is completed successfully."
                        return Response(data)
                else:
                    data["status"],  data["message"] = status.HTTP_200_OK, f"All matches in this round are not completed yet."
                    return Response(data)
            else:
                #create Robin Round
                registered_teams = league.registered_team.all() if league else None
                team_details_list = [team.id for team in registered_teams] if registered_teams else []
                
                play_details = LeaguesPlayType.objects.filter(league_for=league).first()
                number_of_group = court_num_r
                
                group_list = create_group(team_details_list, number_of_group)
                
                round_robin_group_details = RoundRobinGroup.objects.filter(league_for=league)
                if round_robin_group_details.exists():
                    if len(round_robin_group_details) == number_of_group:
                        
                        data["status"],  data["message"] = status.HTTP_200_OK, f"Round Robin matches already created for {league.name}"
                        return Response(data)
                    else:
                        for gr in round_robin_group_details:
                            Tournament.objects.filter(group_id=gr.id).delete
                            gr.delete()
                serial_number = 0
                
                for index, group_teams in enumerate(group_list, start=1):
                    group = RoundRobinGroup.objects.create(court=index, league_for=league, number_sets=set_num_r)
                    for team_id in group_teams:
                        team = Team.objects.get(id=team_id)
                        group.all_teams.add(team)
                    
                    # match_combinations = list(combinations(group_teams, 2))
                    match_combinations = [(team1, team2) for i, team1 in enumerate(group_teams) for team2 in group_teams[i+1:]]

                    # Shuffle the matches to randomize
                    random.shuffle(match_combinations)
                    for teams in match_combinations:
                        obj = GenerateKey()
                        secret_key = obj.generate_league_unique_id()
                        team1, team2 = teams
                        serial_number = serial_number+1
                        Tournament.objects.create(set_number=set_num_r,court_num=index,points=point_num_r,match_number=serial_number,secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, group_id=group.id,match_type="Round Robin")
                data["status"], data["message"] = status.HTTP_200_OK, f"Matches are created successfully"
                return Response(data)
        
        #done
        elif playtype == "Round Robin":
            match_type = playtype
            registered_teams = league.registered_team.all() if league else None
            team_details_list = [team.id for team in registered_teams] if registered_teams else []
            max_team = league.max_number_team
            play_details = LeaguesPlayType.objects.filter(league_for=league).first()
            number_of_group = 1
            if int(max_team) != len(team_details_list):
                data["status"],  data["message"] = status.HTTP_200_OK, f"All teams are not registered"
                return Response(data)
            group_list = create_group(team_details_list, number_of_group)
            round_robin_group_details = RoundRobinGroup.objects.filter(league_for=league)
            if round_robin_group_details.exists():
                if len(round_robin_group_details) == number_of_group:
                    data["status"],  data["message"] = status.HTTP_200_OK, f"Round Robin group already created for {league.name}"
                    return Response(data)
                else:
                    for gr in round_robin_group_details:
                        Tournament.objects.filter(group_id=gr.id).delete
                        gr.delete()
            serial_number = 0
            
            for index, group_teams in enumerate(group_list, start=1):
                group = RoundRobinGroup.objects.create(court=index, league_for=league, number_sets=set_num_r)
                for team_id in group_teams:
                    team = Team.objects.get(id=team_id)
                    group.all_teams.add(team)
                
                # match_combinations = list(combinations(group_teams, 2))
                match_combinations = [(team1, team2) for i, team1 in enumerate(group_teams) for team2 in group_teams[i+1:]]

                # Shuffle the matches to randomize
                random.shuffle(match_combinations)
                for teams in match_combinations:
                    obj = GenerateKey()
                    secret_key = obj.generate_league_unique_id()
                    team1, team2 = teams
                    serial_number = serial_number+1
                    Tournament.objects.create(set_number=set_num_r,court_num=index,points=point_num_r,match_number=serial_number,secret_key=secret_key, leagues=league, team1_id=team1, team2_id=team2, group_id=group.id,match_type="Round Robin")
            data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
            return Response(data)
        
       
        elif playtype == "Individual Match Play":
            print("enter")
            match_type = playtype
            team____ = league.registered_team.all()
            teams = []
            for te in team____:
                teams.append(te.id)
            check_tournament = Tournament.objects.filter(leagues=league,match_type=match_type)
            if check_tournament.exists():
                data["status"], data["message"] = status.HTTP_200_OK, "Matches are already created"
                return Response(data) 
            if len(teams) != 2:
                data["status"], data["message"] = status.HTTP_200_OK, "Mininum 2 teams are needed for individual match play"
                return Response(data) 
            sets__ = set_num_f
            courts__ = court_num_f
            points__ = point_num_f
            round_number = 0
            random.shuffle(teams)
            match_number_now = 0
            # court_num = 0

            set_court = 8
            court_num = 0
            for count in range(courts__):
                court_num = court_num + 1
                match_number_now = court_num
                for i in range(0, len(teams), 2):
                    team1 = teams[i]
                    team2 = teams[i + 1]
                    obj = GenerateKey()
                    secret_key = obj.generate_league_unique_id()
                    Tournament.objects.create(set_number=sets__,court_num=court_num,points=points__,court_sn=court_num,match_number=match_number_now,secret_key=secret_key, leagues=league,team1_id=team1, team2_id=team2,match_type=match_type,elimination_round=round_number) 
            
            data["status"], data["message"] = status.HTTP_200_OK, f"Matches created for {match_type}"
            return Response(data)
    # if tournamnet not found
    else:
        data["status"], data["data"],data["ttt"],data["uuu"], data["message"] = status.HTTP_404_NOT_FOUND, [user_uuid,user_secret_key,league_uuid,league_secret_key],list(check_leagues),list(check_user), "User or Tournament not found."
    return Response(data)




#set score api
#approved score api
#report score api

def determine_match_winner(team1_points, team2_points, total_sets):
    """
    Determine set winners and overall match winner based on points per set.
    
    Args:
        team1_points (list): List of points scored by team1 in each set.
        team2_points (list): List of points scored by team2 in each set.
        total_sets (int): Total number of sets in the match (e.g., 3 for best of 3).
    
    Returns:
        tuple: ([list of set winners], overall winner), e.g., (['t2', 'not define', 'not define'], 'not define').
    """
    # Ensure points lists are of the same length
    if len(team1_points) != len(team2_points):
        raise ValueError("Both teams must have the same number of set points.")
    
    # Initialize set winners list and set win counters
    set_winners = []
    team1_sets_won = 0
    team2_sets_won = 0
    
    # Calculate sets needed to win (majority)
    sets_needed = (total_sets // 2) + 1  # e.g., 2 sets for a 3-set match
    
    # Compare points for each set
    for set_idx in range(len(team1_points)):
        if team1_points[set_idx] > team2_points[set_idx]:
            set_winners.append('t1')
            team1_sets_won += 1
        elif team2_points[set_idx] > team1_points[set_idx]:
            set_winners.append('t2')
            team2_sets_won += 1
        else:
            raise ValueError(f"Set {set_idx + 1} has equal points, which is invalid.")
        
        # Check if a team has won enough sets
        if team1_sets_won >= sets_needed:
            # Fill remaining sets with 'not define'
            set_winners.extend(['not define'] * (total_sets - len(set_winners)))
            return set_winners, 't1'
        if team2_sets_won >= sets_needed:
            # Fill remaining sets with 'not define'
            set_winners.extend(['not define'] * (total_sets - len(set_winners)))
            return set_winners, 't2'
    
    # Fill remaining sets with 'not define'
    set_winners.extend(['not define'] * (total_sets - len(set_winners)))
    
    # If neither team has won enough sets, overall winner is 'not define'
    if team1_sets_won < sets_needed and team2_sets_won < sets_needed:
        return set_winners, 'not define'
    
    # If all sets processed, determine winner
    if team1_sets_won > team2_sets_won:
        return set_winners, 't1'
    return set_winners, 't2'

@api_view(['POST'])
def set_tournamens_result(request):
    data = {'status': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.data.get('user_uuid')
        league_uuid = request.data.get('league_uuid')
        tournament_uuid = request.data.get('tournament_uuid')
        team1_point = request.data.get('team1_point')
        team2_point = request.data.get('team2_point')
        set_number = request.data.get('set_number')

        user = get_object_or_404(User, uuid=user_uuid)
        event = get_object_or_404(Leagues, uuid=league_uuid)
        tournament = get_object_or_404(Tournament, uuid=tournament_uuid)

        team1_point_list = team1_point.split(",")
        team2_point_list = team2_point.split(",")
        set_number_list = set_number.split(",")

        organizer_list = [event.created_by.id] + list(event.add_organizer.all().values_list("id", flat=True))
        team1_p_list = []
        team2_p_list = []

        if tournament.team1:
            team1_p_list = list(
                set(Player.objects.filter(team=tournament.team1).values_list("player_id", flat=True))
            ) + [tournament.team1.created_by.id]

        if tournament.team2:
            team2_p_list = list(
                set(Player.objects.filter(team=tournament.team2).values_list("player_id", flat=True))
            ) + [tournament.team2.created_by.id]

        user_type = None
        if user.id in organizer_list:
            user_type = "Organizer"
        elif user.id in team1_p_list:
            user_type = "Team1"
        elif user.id in team2_p_list:
            user_type = "Team2"

        if not user_type:
            data["status"] = status.HTTP_403_FORBIDDEN
            data["message"] = "You are not authorized to update the score"
            return Response(data)

        set_winner_list, final_winner = determine_match_winner(team1_point_list, team2_point_list, len(set_number_list))

        for set_index in range(1, len(set_number_list) + 1):
            t1_score = int(team1_point_list[set_index - 1])
            t2_score = int(team2_point_list[set_index - 1])
            winner_flag = set_winner_list[set_index - 1]

            score_obj, created = TournamentSetsResult.objects.get_or_create(
                tournament=tournament, set_number=set_index,
                defaults={"team1_point": t1_score, "team2_point": t2_score}
            )
            if not created:
                score_obj.team1_point = t1_score
                score_obj.team2_point = t2_score

            if winner_flag == "t1":
                score_obj.win_team = tournament.team1
            elif winner_flag == "t2":
                score_obj.win_team = tournament.team2
            else:
                score_obj.win_team = None

            score_obj.is_completed = True
            score_obj.save()

        if final_winner == 't1':
            winner = tournament.team1
            looser = tournament.team2
        elif final_winner == 't2':
            winner = tournament.team2
            looser = tournament.team1
        else:
            winner = None
            looser = None
            data["status"] = status.HTTP_400_BAD_REQUEST
            data["message"] = "Match result could not be determined"
            return Response(data)

        # Update tournament record
        tournament.winner_team = winner
        tournament.loser_team = looser
        title = "Match score update"
        if user_type == "Organizer":
            tournament.is_completed = True
            message = f"Wow, you have won the match {tournament.match_number}."
            message2 = f"Sorry, you have lost the match {tournament.match_number}."
            org_message = f"{tournament.winner_team.name} has won the match {tournament.match_number} of league {tournament.leagues.name}"
            if final_winner == "t1":
                for user_id in team1_p_list:                            
                    notify_edited_player(user_id, title, message) 
                for user_id in team2_p_list:                            
                    notify_edited_player(user_id, title, message2)
                for user_id in organizer_list:
                    notify_edited_player(user_id, title, org_message)
            else:
                for user_id in team2_p_list:                            
                    notify_edited_player(user_id, title, message) 
                for user_id in team1_p_list:                            
                    notify_edited_player(user_id, title, message2)
                for user_id in organizer_list:
                    notify_edited_player(user_id, title, org_message)
        elif user_type == "Team1":
            message = f"Wow, you have won the match {tournament.match_number}, {tournament.team1.name} updated the score"
            message2 = f"Sorry, you have lost the match {tournament.match_number}, Your teammate updated the score"
            org_message = f"{tournament.winner_team.name} has won the match {tournament.match_number} of league {tournament.leagues.name}, Players updated the score. Please check and approve"
            if final_winner == "t1":
                for user_id in team1_p_list:                            
                    notify_edited_player(user_id, title, message) 
                for user_id in team2_p_list:                            
                    notify_edited_player(user_id, title, message2)
                for user_id in organizer_list:
                    notify_edited_player(user_id, title, org_message)
            else:
                for user_id in team2_p_list:                            
                    notify_edited_player(user_id, title, message) 
                for user_id in team1_p_list:                            
                    notify_edited_player(user_id, title, message2)
                for user_id in organizer_list:
                    notify_edited_player(user_id, title, org_message)
        elif user_type == "Team2":
            message = f"Wow, you have won the match {tournament.match_number}, {tournament.team2.name} updated the score"
            message2 = f"Sorry, you have lost the match {tournament.match_number}, Your teammate updated the score"
            org_message = f"{tournament.winner_team.name} has won the match {tournament.match_number} of league {tournament.leagues.name}, Players updated the score. Please check and approve"
            if final_winner == "t1":
                for user_id in team1_p_list:                            
                    notify_edited_player(user_id, title, message) 
                for user_id in team2_p_list:                            
                    notify_edited_player(user_id, title, message2)
                for user_id in organizer_list:
                    notify_edited_player(user_id, title, org_message)
            else:
                for user_id in team2_p_list:                            
                    notify_edited_player(user_id, title, message) 
                for user_id in team1_p_list:                            
                    notify_edited_player(user_id, title, message2)
                for user_id in organizer_list:
                    notify_edited_player(user_id, title, org_message)
        tournament.save()

        # Update event if it's a final or individual match play
        if tournament.match_type in ["final", "Individual Match Play"] and user.id in organizer_list:
            event.winner_team = winner
            event.save()

        data["status"] = status.HTTP_200_OK
        data["message"] = "Successfully updated the score"
    except Exception as e:
        data['status'] = status.HTTP_400_BAD_REQUEST
        data['message'] = f"Error occurred: {str(e)}"
    return Response(data)


@api_view(('POST',))
def approve_set_tournament_result(request):
    data = {'status': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.data.get('user_uuid')
        league_uuid = request.data.get('league_uuid')
        tournament_uuid = request.data.get('tournament_uuid')
       
        user = get_object_or_404(User, uuid=user_uuid)
        event = get_object_or_404(Leagues, uuid=league_uuid)
        tournament = get_object_or_404(Tournament, uuid=tournament_uuid)
        
        team1_p_list = []
        team2_p_list = []

        if tournament.team1:
            team1_p_list = list(
                set(Player.objects.filter(team=tournament.team1).values_list("player_id", flat=True))
            ) + [tournament.team1.created_by.id]

        if tournament.team2:
            team2_p_list = list(
                set(Player.objects.filter(team=tournament.team2).values_list("player_id", flat=True))
            ) + [tournament.team2.created_by.id]
        check_approve = TournamentScoreApproval.objects.filter(tournament=tournament)
        if check_approve.exists():
            get_approve = check_approve.first()
        else:
            get_approve = TournamentScoreApproval.objects.create(tournament=tournament)
            
        if user.id in team1_p_list:
            get_approve.team1_approval = True
            #send notification
        elif user.id in team2_p_list:
            get_approve.team2_approval = True
            #send notification
        get_approve.save()
        team1_approval = get_approve.team1_approval
        team2_approval = get_approve.team2_approval
        if team1_approval and team2_approval:
            #game over
            tournament.is_completed = True
            get_approve.organizer_approval = True
            get_approve.save()
            tournament.save()
            #send notification to all players and organizer
            title = "Match score update"
            message = f"Match score has been approved for match {tournament.match_number} of league {tournament.leagues.name}."
            for user_id in team1_p_list + team2_p_list:
                notify_edited_player(user_id, title, message)
        elif not team1_approval or not team2_approval:
            #game not over
            pass

    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    return Response(data)

@api_view(('POST',))
def report_set_tournament_result(request):
    data = {'status': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        league_uuid = request.data.get('league_uuid')
        league_secret_key = request.data.get('league_secret_key')
        tournament_uuid = request.data.get('tournament_uuid')
        tournament_secret_key = request.data.get('tournament_secret_key')  

        report_text = request.data.get('report_text') 

        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        check_leagues = Leagues.objects.filter(uuid=league_uuid, secret_key=league_secret_key)
        tournament = Tournament.objects.filter(uuid=tournament_uuid, secret_key=tournament_secret_key, leagues=check_leagues.first())
        
        if check_user.exists() and check_leagues.exists() and tournament.exists():
            league = check_leagues.first()
            tournament_obj = tournament.first()
            get_user = check_user.first()
            team1_p_list = list(Player.objects.filter(team__id = tournament_obj.team1.id).values_list("player_id", flat=True))
            team2_p_list = list(Player.objects.filter(team__id = tournament_obj.team2.id).values_list("player_id", flat=True))

            if (tournament_obj.team1.created_by == get_user) or (tournament_obj.team2.created_by == get_user) or (get_user.id in team1_p_list) or (get_user.id in team2_p_list):
                TournamentScoreReport.objects.create(tournament=tournament_obj, text=report_text, created_by=get_user,status="Pending")

                #Notification for organizer
                main_org = list(User.objects.filter(id=league.created_by.id).values_list('id', flat=True))
                sub_org_list = list(league.add_organizer.all().values_list("id", flat=True))
                org_list = main_org +  sub_org_list

                title = "Match score report"
                message = f'{get_user.first_name} {get_user.last_name} has reported the scores of match {tournament_obj.match_number} of league {tournament_obj.leagues.name}. Please resolve this and update the score.'
                for user_id in org_list:
                    notify_edited_player(user_id, title, message)

                player_list = team1_p_list + team2_p_list
                if tournament_obj.team2.created_by.id not in player_list:
                    player_list.append(tournament_obj.team2.created_by.id)
                
                if tournament_obj.team1.created_by.id not in player_list:
                    player_list.append(tournament_obj.team1.created_by.id)

                title = "Match score report"
                message = f'{get_user.first_name} {get_user.last_name} has reported the scores of match {tournament_obj.match_number} of league {tournament_obj.leagues.name}.'
                for user_id in player_list:
                    notify_edited_player(user_id, title, message)

                data["status"], data["message"] = status.HTTP_200_OK, f"You have successfully reported the scores of match {tournament_obj.match_number}"
            else:
                data["status"], data["message"] = status.HTTP_200_OK, "You can't report the score"
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User or Tournament not found."

    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, str(e)
    return Response(data)

#match score update
@api_view(["GET"])
def event_matches(request):
    data = {'status':'', 'message':'', 'match':[]}
    try:
        # user_uuid = request.GET.get('user_uuid')
        league_uuid = request.GET.get('league_uuid')
        # user = get_object_or_404(User, uuid=user_uuid)
        event = get_object_or_404(Leagues, uuid=league_uuid)
        tournamnets = Tournament.objects.filter(leagues=event).order_by("match_number")
        serializer = MatchListSerializer(tournamnets, many=True)
        data["status"] = status.HTTP_200_OK
        data["match"] = serializer.data
        return Response(data, status=status.HTTP_200_OK)
    except Exception as e:
        data["status"] = status.HTTP_200_OK
        data["message"] = str(e)
        return Response(data, status=status.HTTP_200_OK)

@api_view(["GET"])
def match_view_score(request):
    data = {
        "status": None,
        "score": [],
        "is_edit": False,
        "is_save": False,
        "is_approve": False,
        "is_reject": False,
        "message": None
    }

    try:
        user_uuid = request.GET.get('user_uuid')
        tournament_uuid = request.GET.get('tournament_uuid')

        user = get_object_or_404(User, uuid=user_uuid)
        tournament = get_object_or_404(Tournament, uuid=tournament_uuid)
        set_results = TournamentSetsResult.objects.filter(tournament=tournament).order_by("set_number")

        # These lists should be filled based on logic
        organizer_user_list = []
        team1_player_user_list = []
        team2_player_user_list = []  # Note: This was declared but not used later; keeping it as is for consistency

        # Get team 1 and team 2 player IDs, handling cases where team might be None
        team_1_player = list(Player.objects.filter(team=tournament.team1).values_list("player_id", flat=True)) if tournament.team1 else []
        team_2_player = list(Player.objects.filter(team=tournament.team2).values_list("player_id", flat=True)) if tournament.team2 else []  # Fixed: using team2 instead of team1

        # Get created_by IDs for team1 and team2, with None checks
        team_1_created_by = [tournament.team1.created_by.id] if tournament.team1 and tournament.team1.created_by else []
        team_2_created_by = [tournament.team2.created_by.id] if tournament.team2 and tournament.team2.created_by else []

        # Update player user lists by combining player IDs and created_by IDs
        team1_player_user_list = list(set(team_1_player + team_1_created_by))
        team2_player_user_list = list(set(team_2_player + team_2_created_by))

        # Organizer list, with None checks
        organizers_id_list = [tournament.leagues.created_by.id] if tournament.leagues and tournament.leagues.created_by else []
        sub_organizer_data = list(tournament.leagues.add_organizer.values_list("id", flat=True)) if tournament.leagues else []
        organizer_user_list = list(set(organizers_id_list + sub_organizer_data))
        
        score_approved = TournamentScoreApproval.objects.filter(tournament=tournament).first()
        score_report = TournamentScoreReport.objects.filter(tournament=tournament).first()
        if not tournament.is_completed:
            report_form_team1 = report_form_team2 = False
            if score_report:
                report_user = score_report.created_by
                report_form_team1 = user.id in team1_player_user_list
                report_form_team2 = user.id in team2_player_user_list

            team1_approval = team2_approval = organizer_approval = False
            if score_approved:
                team1_approval = score_approved.team1_approval
                team2_approval = score_approved.team2_approval
                organizer_approval = score_approved.organizer_approval

            if user.id in organizer_user_list:
                if set_results:
                    if score_report:
                        data["message"] = "Opponent team has reported the score"
                        data["is_edit"] = True
                        data["is_save"] = True
                    else:
                        data["is_edit"] = True

                    if not organizer_approval:
                        data["is_edit"] =True
                        data["is_approve"] = True
                    else:
                        data["is_edit"] = True
                        
                else:
                    data["is_edit"] = True
                    data["is_save"] = True
           
            # Check permissions and statuses
            elif user.id in team1_player_user_list:
                if set_results:                    

                    if report_form_team2:
                        data["message"] = "Opponent team has reported your score"
                        data["is_edit"] = True

                    elif report_form_team1:
                        data["message"] = "You reported this score, wait for the organizer's action"
                        data["is_edit"] = True

                    if not report_form_team1 and not report_form_team2:
                        if not team1_approval and not organizer_approval:
                            data["is_edit"] = True
                            data["is_approve"] = True
                            data["is_reject"] = True

                        elif not team1_approval and organizer_approval:
                            data["is_edit"] = True
                            data["is_approve"] = False
                            data["is_reject"] = False

                        elif team1_approval:
                            data["is_edit"] = True
                            data["is_approve"] = False
                            data["is_reject"] = False  

                        elif not organizer_approval or not team1_approval or not team2_approval:
                            data["is_edit"] = True
                            data["message"] = "Waiting for all tournament players' approval"
                        
                else:
                    data["is_edit"] = True
                    data["is_save"] = True

            elif user.id in team2_player_user_list:
                if set_results:                   

                    if report_form_team1:
                        data["message"] = "Opponent team has reported your score"
                        data["is_edit"] = True 

                    elif report_form_team2:
                        data["message"] = "You reported this score, wait for the organizer's action"
                        data["is_edit"] = True

                    if not report_form_team1 and not report_form_team2:
                        if not team2_approval and not organizer_approval:
                            data["is_edit"] = True
                            data["is_approve"] = True
                            data["is_reject"] = True

                        elif not team2_approval and organizer_approval:
                            data["is_edit"] = True
                            data["is_approve"] = False
                            data["is_reject"] = False

                        elif team2_approval:
                            data["is_edit"] = True
                            data["is_approve"] = False
                            data["is_reject"] = False 

                        elif not organizer_approval or not team1_approval or not team2_approval:
                            data["is_edit"] = True
                            data["message"] = "Waiting for all tournament players' approval"
                else:
                    data["is_edit"] = True
                    data["is_save"] = True

            

        # Processing match scores
        team_scores = {}
        for set_result in set_results:
            for team in [tournament.team1, tournament.team2]:
                if not team:
                    continue

                team_name = team.name
                is_winner = set_result.win_team == team
                if team_name not in team_scores:
                    team_scores[team_name] = {
                        "name": team_name,
                        "set": [],
                        "score": [],
                        "win_status": [],
                        "is_win": False,
                        "is_completed": tournament.is_completed,
                        "is_drow": tournament.is_drow
                    }

                team_scores[team_name]["set"].append(f"s{set_result.set_number}")
                team_scores[team_name]["score"].append(
                    set_result.team1_point if team == tournament.team1 else set_result.team2_point
                )
                team_scores[team_name]["win_status"].append(is_winner)

        if tournament.winner_team and tournament.winner_team.name in team_scores:
            team_scores[tournament.winner_team.name]["is_win"] = True

        data["score"] = list(team_scores.values())
        data["status"] = status.HTTP_200_OK

    except Exception as e:
        data["status"] = "error"
        data["message"] = str(e)

    return Response(data)



#save event view 
@api_view(('POST',))
def save_league(request):
    data = {'status':'','message':''}
    try:
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        # team_uuid = request.data.get('team_uuid')
        league_uuid = request.data.get('league_uuid')
        check_user = User.objects.filter(secret_key=user_secret_key,uuid=user_uuid)
        obj = GenerateKey()
        _key = obj.gen_advertisement_key()
        # if user_uuid is None or user_secret_key is None:
        #         data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"Both 'user_uuid' and 'user_secret_key' are required parameters."
        if league_uuid is None:
                data['status'], data['message'] = status.HTTP_200_OK, f"League_uuid is required parameter."
        if check_user.exists():
            get_user = check_user.first()
            try:
                league_name = Leagues.objects.filter(uuid=league_uuid).first().name
                league_id = Leagues.objects.filter(uuid=league_uuid).first().id
                # team_id = Team.objects.filter(uuid=team_uuid).first().id
                ch_leaugh = SaveLeagues.objects.filter(ch_league_id=int(league_id),created_by=get_user)
                if ch_leaugh.exists():
                    pass
                else:
                    SaveLeagues.objects.create(secret_key=_key, ch_league_id=int(league_id),created_by=get_user)
                data['status'], data['message'] = status.HTTP_200_OK, f"You saved the {league_name} in your account"
            except Exception as e :
                data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
        else:
            data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"user not found"
    except Exception as e :
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

## create open play
@api_view(('POST',))
def create_open_play_tournament(request):
    data = {'status': '', 'message': ''}
    try:        
        user_uuid = request.data.get('user_uuid')
        user_secret_key = request.data.get('user_secret_key')
        leagues_start_date = request.data.get('leagues_start_date')
        location = request.data.get('location')
        play_type = request.data.get('play_type')
        team_type = "Open-team"
        team_person = request.data.get('team_person')
        team_id_list = request.data.get('team_id_list')
        team_id_list = json.loads(team_id_list)
        
        court = request.data.get('court')
        sets = request.data.get('sets')
        points = request.data.get('points')
        
        max_number_team = 2
        registration_fee = 0
        description = "None"
        league_type = "Open to all"

        if len(team_id_list) != 2:
            data["status"], data["message"] = status.HTTP_400_BAD_REQUEST, "Max number of team is Two"
            return Response(data)
        
        team_1_id = team_id_list[0]
        team_2_id = team_id_list[1]
        team1_players = list(Player.objects.filter(team__id=team_1_id).values_list("id", flat=True))
        team2_players = list(Player.objects.filter(team__id=team_2_id).values_list("id", flat=True))
        for player_id in team1_players:
            if player_id in team2_players:
                data["status"], data["message"] = status.HTTP_400_BAD_REQUEST, "Same player cannot be in both teams."
                return Response(data)

        leagues_start_date = datetime.strptime(leagues_start_date, '%m/%d/%Y').strftime('%Y-%m-%d')
        check_user = User.objects.filter(uuid=user_uuid, secret_key=user_secret_key)
        counter = 0
        team_names = {}
        for team in team_id_list:
            counter += 1
            team_instance = Team.objects.filter(id=team).first()
            team_names[f'team{counter}_name'] = team_instance.name
        tournament_name = f"{team_names['team1_name']} VS {team_names['team2_name']}"
        if check_user.exists():
            check_leagues = LeaguesTeamType.objects.filter(name=team_type)
            check_person = LeaguesPesrsonType.objects.filter(name=team_person)
            full_address = location
            api_key = settings.MAP_API_KEY
            state, country, pincode, latitude, longitude = get_address_details(full_address, api_key)
            if latitude is None:
                latitude = 38.908683
            if longitude is None:
                longitude = -76.937352
            obj = GenerateKey()
            secret_key = obj.gen_leagues_key()

            save_leagues = Leagues(
                secret_key=secret_key,
                name=tournament_name,
                leagues_start_date=leagues_start_date,
                location=location,
                created_by_id=check_user.first().id,
                street=state,
                city="Extract city from full_address",
                state=state,
                postal_code=pincode,
                country=country,
                max_number_team=max_number_team,
                play_type=play_type,
                registration_fee=registration_fee,
                description=description,
                league_type=league_type
            )

            save_leagues.save()

            save_leagues.latitude = latitude
            save_leagues.longitude = longitude
            save_leagues.save()
            if check_leagues.exists() and check_person.exists():
                check_leagues_id = check_leagues.first().id
                check_person_id = check_person.first().id
                save_leagues.team_type_id = check_leagues_id
                save_leagues.team_person_id = check_person_id
                save_leagues.save()

            for team in team_id_list:
                team_instance = Team.objects.filter(id=team).first()
                save_leagues.registered_team.add(team_instance)

            if not court:
                court = 0
            else:
                court = int(court)

            if not sets:
                sets = 0
            else:
                sets = int(sets)

            if not points:
                points = 0
            else:
                points = int(points)

            play_type_data = [{"name": "Round Robin", "number_of_courts": 0, "sets": 0, "point": 0},
                              {"name": "Elimination", "number_of_courts": 0, "sets": 0, "point": 0},
                              {"name": "Final", "number_of_courts": court, "sets": sets, "point": points}]
            for j in play_type_data:
                if play_type == "Individual Match Play":
                    j["is_show"] = True
                else:
                    j["is_show"] = False
            LeaguesPlayType.objects.create(type_name=save_leagues.play_type, league_for=save_leagues,
                                           data=play_type_data)
            #notification           
            for team_id in team_id_list:
                team_instance = Team.objects.filter(id=team_id).first()
                titel = "Open play created."
                notify_message = f"Hey player! Your team {team_instance.name} has been added for an open play - {tournament_name}"
                players = Player.objects.filter(team=team_instance)
                for player in players:
                    notify_edited_player(player.player.id, titel, notify_message)

            set_msg = "Tournament created successfully"
            data["status"], data["message"] = status.HTTP_200_OK, set_msg
        else:
            data["status"], data["message"] = status.HTTP_404_NOT_FOUND, "User not found."
    except Exception as e:
        data['status'], data['message'] = status.HTTP_400_BAD_REQUEST, f"{e}"
    return Response(data)

"""
Dashboard API for Event View
"""


@api_view(('GET',))
def tournament_joined_details(request):
    data = {'status':'','data':[], 'message':''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        order_by = request.GET.get('order_by')
        check_user = User.objects.filter(secret_key=user_secret_key,uuid=user_uuid)
        today_date = timezone.now()
        if check_user.exists():
            get_user = check_user.first()
            all_leagues = Leagues.objects.exclude(Q(registration_end_date__date__lte=today_date)|Q(is_complete=True)|Q(leagues_start_date__date__lte=today_date))
            check_player = Player.objects.filter(player_email=get_user.email)
            if check_player.exists():
                print(check_player)
                get_player = check_player.first()
                player_teams = get_player.team.values_list("id", flat=True) if get_player else []
                all_leagues = all_leagues.filter(registered_team__in=player_teams, is_complete=False).distinct()
                print("bgfdhgfgf",all_leagues)
            else:
                data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"data not found"
                return Response(data)
        else:
            data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
            return Response(data)
        if order_by == "registration_open_date" :
            all_leagues = all_leagues.order_by("leagues_start_date")
        elif order_by == "registration_open_name" :
            all_leagues = all_leagues.order_by("name")
        elif order_by == "registration_open_city" :
            all_leagues = all_leagues.order_by("city")
        elif order_by == "registration_open_state" :
            all_leagues = all_leagues.order_by("state")
        elif order_by == "registration_open_country" :
            all_leagues = all_leagues.order_by("country")
        else:
            all_leagues = all_leagues
        print(all_leagues)
        leagues = all_leagues.values(
            "id", "uuid", "secret_key", "name", "location", "leagues_start_date", "leagues_end_date",
            "registration_start_date", "registration_end_date", "team_type__name", "team_person__name",
            "any_rank", "start_rank", "end_rank", "street", "city", "state", "postal_code", "country","is_complete",
            "complete_address", "latitude", "longitude", "image", "others_fees", "league_type", "registration_fee"
        )

        # Initialize output and grouping
        output = []
        grouped_data = {}

        # Group and process data
        for item in list(leagues):
            # Registration control
            item["is_reg_diable"] = True
            match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
            if match_.exists():
                item["is_reg_diable"] = False

            le = Leagues.objects.filter(id=item["id"]).first()
            sub_organizer_list = list(le.add_organizer.all().values_list("id", flat=True))
            reg_team = le.registered_team.all().count()
            max_team = le.max_number_team
            if max_team <= reg_team:
                item["is_reg_diable"] = False

            # Organizer roles
            if get_user == le.created_by:
                item["main_organizer"] = True
                item["sub_organizer"] = False
            elif get_user.id in sub_organizer_list:
                item["main_organizer"] = False
                item["sub_organizer"] = True
            else:
                item["main_organizer"] = False
                item["sub_organizer"] = False

            # Grouping by 'name'
            key = item['name']
            if key not in grouped_data:
                grouped_data[key] = {
                    'name': item['name'],
                    'lat': item['latitude'],
                    'long': item["longitude"],
                    'registration_start_date': item["registration_start_date"],
                    'registration_end_date': item["registration_end_date"],
                    'leagues_start_date': item["leagues_start_date"],
                    'leagues_end_date': item["leagues_end_date"],
                    'location': item["location"],
                    'image': item["image"],
                    'type': [item['team_type__name']],
                    'data': [item]
                }
            else:
                grouped_data[key]['type'].append(item['team_type__name'])
                grouped_data[key]['data'].append(item)

        # Build the final output
        for key, value in grouped_data.items():
            value["is_edit"] = True
            value["is_delete"] = True
            output.append(value)

        # Serialization for JSON compatibility
        from decimal import Decimal
        from uuid import UUID
        def serialize_field(value):
            if isinstance(value, Decimal):
                return float(value)
            elif isinstance(value, datetime):
                return value.isoformat()
            elif isinstance(value, UUID):
                return str(value)
            elif isinstance(value, dict):
                return {k: serialize_field(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [serialize_field(v) for v in value]
            else:
                return value

        serialized_output = [serialize_field(item) for item in output]         

        data['status'], data['data'], data['message'] = status.HTTP_200_OK, serialized_output, f"Data Found"
    except Exception as e :
        data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"{e}"
    return Response(data)



@api_view(('GET',))
def tournament_saved_details(request):
    data = {'status': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        order_by = request.GET.get('order_by')
        check_user = User.objects.filter(secret_key=user_secret_key, uuid=user_uuid)
        today_date = timezone.now()
        
        if check_user.exists():
            get_user = check_user.first()
            all_leagues = Leagues.objects.all()
            save_leagues = SaveLeagues.objects.filter(created_by=get_user).values("ch_league_id")
            leagues_ids = [i["ch_league_id"] for i in save_leagues]
            print(leagues_ids)
            all_leagues = all_leagues.filter(id__in=leagues_ids)
            if order_by == "registration_open_date":
                all_leagues = all_leagues.order_by("leagues_start_date")
            elif order_by == "registration_open_name":
                all_leagues = all_leagues.order_by("name")
            elif order_by == "registration_open_city":
                all_leagues = all_leagues.order_by("city")
            elif order_by == "registration_open_state":
                all_leagues = all_leagues.order_by("state")
            elif order_by == "registration_open_country":
                all_leagues = all_leagues.order_by("country")

            leagues = all_leagues.values(
                "id", "uuid", "secret_key", "name", "location", "leagues_start_date", "leagues_end_date",
                "registration_start_date", "registration_end_date", "team_type__name", "team_person__name",
                "any_rank", "start_rank", "end_rank", "street", "city", "state", "postal_code", "country",
                "complete_address", "latitude", "longitude", "image", "others_fees", "league_type", "registration_fee"
            )

            # Initialize output and grouping
            output = []
            grouped_data = {}

            # Group and process data
            for item in list(leagues):
                # Registration control
                item["is_reg_diable"] = True
                match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
                if match_.exists():
                    item["is_reg_diable"] = False

                le = Leagues.objects.filter(id=item["id"]).first()
                sub_organizer_list = list(le.add_organizer.all().values_list("id", flat=True))
                reg_team = le.registered_team.all().count()
                max_team = le.max_number_team
                if max_team <= reg_team:
                    item["is_reg_diable"] = False

                # Organizer roles
                if get_user == le.created_by:
                    item["main_organizer"] = True
                    item["sub_organizer"] = False
                elif get_user.id in sub_organizer_list:
                    item["main_organizer"] = False
                    item["sub_organizer"] = True
                else:
                    item["main_organizer"] = False
                    item["sub_organizer"] = False

                # Grouping by 'name'
                key = item['name']
                if key not in grouped_data:
                    grouped_data[key] = {
                        'name': item['name'],
                        'lat': item['latitude'],
                        'long': item["longitude"],
                        'registration_start_date': item["registration_start_date"],
                        'registration_end_date': item["registration_end_date"],
                        'leagues_start_date': item["leagues_start_date"],
                        'leagues_end_date': item["leagues_end_date"],
                        'location': item["location"],
                        'image': item["image"],
                        'type': [item['team_type__name']],
                        'data': [item]
                    }
                else:
                    grouped_data[key]['type'].append(item['team_type__name'])
                    grouped_data[key]['data'].append(item)

            # Build the final output
            for key, value in grouped_data.items():
                value["is_edit"] = True
                value["is_delete"] = True
                output.append(value)

            # Serialization for JSON compatibility
            from decimal import Decimal
            from uuid import UUID
            def serialize_field(value):
                if isinstance(value, Decimal):
                    return float(value)
                elif isinstance(value, datetime):
                    return value.isoformat()
                elif isinstance(value, UUID):
                    return str(value)
                elif isinstance(value, dict):
                    return {k: serialize_field(v) for k, v in value.items()}
                elif isinstance(value, list):
                    return [serialize_field(v) for v in value]
                else:
                    return value

            serialized_output = [serialize_field(item) for item in output]

            data['status'], data['data'], data['message'] = status.HTTP_200_OK, serialized_output, "Data Found"
        else:
            data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], "User not found"
    except Exception as e:
        data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], str(e)
    return Response(data)


@api_view(('GET',))
def open_play_details(request):
    data = {'status': '', 'data': [], 'message': ''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user = get_object_or_404(User, uuid=user_uuid)

        
        all_leagues = []
        invited_leages = OpenPlayInvitation.objects.filter(user=user).exclude(status='Declined')
        check_player = Player.objects.filter(player=user).first()
        if check_player:
            team_ids = check_player.team.values_list('id', flat=True)
            all_leagues = Leagues.objects.filter(
                Q(is_complete=False) & 
                (Q(registered_team__id__in=team_ids) | Q(created_by=user)),
                team_type__name="Open-team"
            ).distinct()
        leagues = all_leagues + invited_leages
        leagues = leagues.values(
            "id", "uuid", "secret_key", "name", "location", "leagues_start_date", "leagues_end_date",
            "registration_start_date", "registration_end_date", "team_type__name", "team_person__name",
            "any_rank", "start_rank", "end_rank", "street", "city", "state", "postal_code", "country",
            "complete_address", "latitude", "longitude", "image", "others_fees", "league_type", "registration_fee"
        )

        # Initialize output and grouping
        output = []
        grouped_data = {}

        # Group and process data
        for item in list(leagues):
            # Registration control
            item["is_reg_diable"] = True
            match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
            if match_.exists():
                item["is_reg_diable"] = False

            le = Leagues.objects.filter(id=item["id"]).first()
            sub_organizer_list = list(le.add_organizer.all().values_list("id", flat=True))
            reg_team = le.registered_team.all().count()
            max_team = le.max_number_team
            if max_team <= reg_team:
                item["is_reg_diable"] = False

            # Organizer roles
            if user == le.created_by:
                item["main_organizer"] = True
                item["sub_organizer"] = False
            elif user.id in sub_organizer_list:
                item["main_organizer"] = False
                item["sub_organizer"] = True
            else:
                item["main_organizer"] = False
                item["sub_organizer"] = False

            # Grouping by 'name'
            key = item['name']
            if key not in grouped_data:
                grouped_data[key] = {
                    'name': item['name'],
                    'lat': item['latitude'],
                    'long': item["longitude"],
                    'registration_start_date': item["registration_start_date"],
                    'registration_end_date': item["registration_end_date"],
                    'leagues_start_date': item["leagues_start_date"],
                    'leagues_end_date': item["leagues_end_date"],
                    'location': item["location"],
                    'image': item["image"],
                    'type': [item['team_type__name']],
                    'data': [item]
                }
            else:
                grouped_data[key]['type'].append(item['team_type__name'])
                grouped_data[key]['data'].append(item)

        # Build the final output
        for key, value in grouped_data.items():
            value["is_edit"] = True
            value["is_delete"] = True
            output.append(value)

        # Final leagues data
        leagues = output

        data['status'], data['data'], data['message'] = status.HTTP_200_OK, leagues, "Data found"
       
    except Exception as e:
        data['status'], data['message'] = status.HTTP_500_INTERNAL_SERVER_ERROR, f"Error: {str(e)}"

    return Response(data)


@api_view(('GET',))
def tournament_created_details(request):
    data = {'status':'','data':[], 'message':''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        order_by = request.GET.get('order_by')
        check_user = User.objects.filter(secret_key=user_secret_key,uuid=user_uuid)
        today_date = timezone.now()
        if check_user.exists():
            get_user = check_user.first()
            all_leagues = Leagues.objects.exclude(registration_end_date__date__lte=today_date).filter(created_by=get_user)
            if order_by == "registration_open_date" :
                all_leagues = all_leagues.order_by("leagues_start_date")
            elif order_by == "registration_open_name" :
                order_by = all_leagues.order_by("name")
            elif order_by == "registration_open_city" :
                all_leagues = all_leagues.order_by("city")
            elif order_by == "registration_open_state" :
                all_leagues = all_leagues.order_by("state")
            elif order_by == "registration_open_country" :
                all_leagues = all_leagues.order_by("country")

            all_leagues = all_leagues.values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                               'registration_start_date','registration_end_date','team_type__name','team_person__name',
                               "street","city","state","postal_code","country","complete_address","latitude","longitude")
            data['status'], data['data'], data['message'] = status.HTTP_200_OK, all_leagues, f"Data found"
        else:
            data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
    except Exception as e :
        data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"{e}"
    return Response(data)



@api_view(('GET',))
def tournament_joined_completed_details(request):
    data = {'status':'','data':[], 'message':''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        order_by = request.GET.get('order_by')
        check_user = User.objects.filter(secret_key=user_secret_key,uuid=user_uuid)
        if check_user.exists():
            get_user = check_user.first()
            if get_user.is_coach or get_user.is_team_manager or get_user.is_organizer:
                check_player = Player.objects.filter(player_email=get_user.email)
                if not check_player.exists():
                    data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
                    return Response(data)
                get_player = check_player.first()
                get_player_team = get_player.team.all()
                team_id = [i.id for i in get_player_team]
                all_leagues = Leagues.objects.filter(
                                Q(registered_team__in=team_id, is_complete=True) |
                                Q(add_organizer__in=[get_user.id], is_complete=True) |
                                Q(created_by=get_user, is_complete=True)
                            ).distinct()

                if order_by == "registration_open_date" :
                    all_leagues = all_leagues.order_by("leagues_start_date")
                elif order_by == "registration_open_name" :
                    order_by = all_leagues.order_by("name")
                elif order_by == "registration_open_city" :
                    all_leagues = all_leagues.order_by("city")
                elif order_by == "registration_open_state" :
                    all_leagues = all_leagues.order_by("state")
                elif order_by == "registration_open_country" :
                    all_leagues = all_leagues.order_by("country")
                else:
                    all_leagues = all_leagues

                leagues = all_leagues.values(
                    "id", "uuid", "secret_key", "name", "location", "leagues_start_date", "leagues_end_date",
                    "registration_start_date", "registration_end_date", "team_type__name", "team_person__name",
                    "any_rank", "start_rank", "end_rank", "street", "city", "state", "postal_code", "country",
                    "complete_address", "latitude", "longitude", "image", "others_fees", "league_type", "registration_fee"
                )

                # Initialize output and grouping
                output = []
                grouped_data = {}

                # Group and process data
                for item in list(leagues):
                    # Registration control
                    item["is_reg_diable"] = True
                    match_ = Tournament.objects.filter(leagues_id=item["id"]).values()
                    if match_.exists():
                        item["is_reg_diable"] = False

                    le = Leagues.objects.filter(id=item["id"]).first()
                    sub_organizer_list = list(le.add_organizer.all().values_list("id", flat=True))
                    reg_team = le.registered_team.all().count()
                    max_team = le.max_number_team
                    if max_team <= reg_team:
                        item["is_reg_diable"] = False

                    # Organizer roles
                    if get_user == le.created_by:
                        item["main_organizer"] = True
                        item["sub_organizer"] = False
                    elif get_user.id in sub_organizer_list:
                        item["main_organizer"] = False
                        item["sub_organizer"] = True
                    else:
                        item["main_organizer"] = False
                        item["sub_organizer"] = False

                    # Grouping by 'name'
                    key = item['name']
                    if key not in grouped_data:
                        grouped_data[key] = {
                            'name': item['name'],
                            'lat': item['latitude'],
                            'long': item["longitude"],
                            'registration_start_date': item["registration_start_date"],
                            'registration_end_date': item["registration_end_date"],
                            'leagues_start_date': item["leagues_start_date"],
                            'leagues_end_date': item["leagues_end_date"],
                            'location': item["location"],
                            'image': item["image"],
                            'type': [item['team_type__name']],
                            'data': [item]
                        }
                    else:
                        grouped_data[key]['type'].append(item['team_type__name'])
                        grouped_data[key]['data'].append(item)

                # Build the final output
                for key, value in grouped_data.items():
                    value["is_edit"] = True
                    value["is_delete"] = True
                    output.append(value)

                # Serialization for JSON compatibility
                from decimal import Decimal
                from uuid import UUID
                def serialize_field(value):
                    if isinstance(value, Decimal):
                        return float(value)
                    elif isinstance(value, datetime):
                        return value.isoformat()
                    elif isinstance(value, UUID):
                        return str(value)
                    elif isinstance(value, dict):
                        return {k: serialize_field(v) for k, v in value.items()}
                    elif isinstance(value, list):
                        return [serialize_field(v) for v in value]
                    else:
                        return value

                serialized_output = [serialize_field(item) for item in output]
            
                data['status'], data['data'], data['message'] = status.HTTP_200_OK, serialized_output, f"Data found"
        else:
            data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
    except Exception as e :
        data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"{e}"
    return Response(data)


@api_view(('GET',))
def tournament_saved_completed_details(request):
    data = {'status':'','data':[], 'message':''}
    try:
        user_uuid = request.GET.get('user_uuid')
        user_secret_key = request.GET.get('user_secret_key')
        order_by = request.GET.get('order_by')
        check_user = User.objects.filter(secret_key=user_secret_key,uuid=user_uuid)
        today_date = timezone.now()
        if check_user.exists():
            get_user = check_user.first()
            all_leagues1 = []
            all_leagues2 = []
            sv = SaveLeagues.objects.filter(ch_league__registration_end_date__date__lte=today_date).values("ch_league_id")
            sv_id = [i["ch_league_id"] for i in sv]
            all_leagues_main = Leagues.objects.filter(id__in=sv_id,is_complete=True)
            if get_user.is_coach is True or get_user.is_team_manager is True:
                all_leagues1 = list(all_leagues_main.filter(registered_team__created_by=get_user))
            if get_user.is_player :
                check_player = Player.objects.filter(player_email=get_user.email)
                if check_player.exists():
                    get_player = check_player.first()
                    get_player_team = get_player.team.all()
                    team_id = [i.id for i in get_player_team]
                    all_leagues2 = list(all_leagues_main.filter(registered_team__id__in=team_id))
                else:
                    data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
                    return Response(data)
            
            all_leagues = all_leagues1 + all_leagues2
            if len(all_leagues) > 0 :
                all_leagues_id = [i.id for i in all_leagues]
                all_leagues = all_leagues_main.filter(id__in=all_leagues_id)

                if order_by == "registration_open_date" :
                    all_leagues = all_leagues.order_by("leagues_start_date")
                elif order_by == "registration_open_name" :
                    order_by = all_leagues.order_by("name")
                elif order_by == "registration_open_city" :
                    all_leagues = all_leagues.order_by("city")
                elif order_by == "registration_open_state" :
                    all_leagues = all_leagues.order_by("state")
                elif order_by == "registration_open_country" :
                    all_leagues = all_leagues.order_by("country")
                else:
                    all_leagues = all_leagues

                all_leagues = all_leagues.values('uuid','secret_key','name','location','leagues_start_date','leagues_end_date',
                                'registration_start_date','registration_end_date','team_type__name','team_person__name',
                                "street","city","state","postal_code","country","complete_address","latitude","longitude")
                
                data['status'], data['data'], data['message'] = status.HTTP_200_OK, all_leagues, f"Data found"
        else:
            data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"user not found"
    except Exception as e :
        data['status'], data['data'], data['message'] = status.HTTP_400_BAD_REQUEST, [], f"{e}"
    return Response(data)




