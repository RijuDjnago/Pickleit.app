from rest_framework import serializers
from .models import *
from apps.user.models import *
from apps.accessories.models import *

class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = '__all__'

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['rank', 'username', 'email', 'first_name', 'last_name', 'uuid', 'secret_key', 'phone', 'image', 'is_ambassador', 'is_sponsor', 'is_organizer', 'is_player', 'gender']

class PlayerSerializer(serializers.ModelSerializer):
    team = TeamSerializer(many=True, read_only=True)
    user = serializers.SerializerMethodField()
    player_ranking = serializers.SerializerMethodField()
    is_follow = serializers.SerializerMethodField()
    gender = serializers.SerializerMethodField()
    is_edit = serializers.SerializerMethodField()
    player_image = serializers.SerializerMethodField()
    user_uuid = serializers.SerializerMethodField()
    user_secret_key = serializers.SerializerMethodField()
    playerCreatedBy = serializers.SerializerMethodField()
    player__is_ambassador = serializers.SerializerMethodField()
    playerCreatedBy = serializers.SerializerMethodField()
    playerUpdatedBy = serializers.SerializerMethodField()
    player__bio = serializers.SerializerMethodField()

    class Meta:
        model = Player
        fields = [
            'id', 'uuid', 'secret_key', 'var_team_name', 'var_team_person',
            'player_id', 'player_image', 'player_first_name', 'player_last_name', 
            'player_full_name', 'player_email', 'player_phone_number', 'player_ranking','player__bio',
            'player_rank_lock', 'identify_player', 'created_at', 'playerCreatedBy',
            'updated_at', 'playerUpdatedBy', 'is_follow', 'user', 'gender', 'user_uuid',
            'player__is_ambassador', 'user_secret_key', 'is_edit', 'team'
        ]

    def get_user(self, obj):
        user = User.objects.filter(id=obj.player_id).first()
        return [UserSerializer(user).data] if user else []

    def get_player_ranking(self, obj):
        user = User.objects.filter(id=obj.player_id).first()
        if user.rank == "null" or user.rank == "" or not user.rank:
            return 1.0
        else:
            return float(user.rank)

    def get_is_follow(self, obj):
        user = self.context.get('request').user
        following = AmbassadorsDetails.objects.filter(ambassador=user.id).first()
        if following and obj.id in following.following.values_list('id', flat=True):
            return True
        return False

    def get_gender(self, obj):
        user = User.objects.filter(id=obj.player_id).first()
        return user.gender if user.gender else "Male"

    def get_is_edit(self, obj):
        user = self.context['request'].user
        return obj.created_by_id == user.id

    def get_player_image(self, obj):
        if obj.player.image:
            return obj.player.image.name  
        return None

    def get_user_uuid(self, obj):
        user = User.objects.filter(id=obj.player_id).first()
        return user.uuid if user else None

    def get_user_secret_key(self, obj):
        user = User.objects.filter(id=obj.player_id).first()
        return user.secret_key if user else None
    
    def get_player__is_ambassador(self, obj):
        user = User.objects.filter(id=obj.player_id).first()
        return user.is_ambassador if user else False
    
    def get_playerCreatedBy(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"
    
    def get_playerUpdatedBy(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}"
    
    def get_player__bio(self, obj):
        return obj.player.bio
    

class TeamListSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    created_by_uuid = serializers.SerializerMethodField()
    created_by_secret_key = serializers.SerializerMethodField()
    player_data = serializers.SerializerMethodField()
    team_rank = serializers.SerializerMethodField()
    team_image = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            'id', 'uuid', 'secret_key', 'name', 'team_image','location',
            'team_type', 'team_person', 'created_by', 'created_by_uuid',
            'created_by_secret_key', 'player_data', 'team_rank'
        ]

    def get_created_by(self, obj):
        first_name = obj.created_by.first_name if obj.created_by is not None else None
        last_name = obj.created_by.last_name if obj.created_by is not None else None
        return f"{first_name} {last_name}"

    def get_created_by_uuid(self, obj):
        uuid = obj.created_by.uuid if obj.created_by is not None else None
        return uuid

    def get_created_by_secret_key(self, obj):
        secret_key = obj.created_by.secret_key if obj.created_by is not None else None
        return secret_key

    def get_player_data(self, obj):
        players = Player.objects.filter(team=obj).values(
            'uuid', 'secret_key', 'player_full_name',
            'player_ranking', 'player__rank', 'player__uuid'
        )
        for player in players:
            player["user_uuid"] = player["player__uuid"]
            player['player_ranking'] = float(player['player__rank']) if player['player__rank'] not in ["", "null", None] else 1
        return list(players)

    def get_team_rank(self, obj):
        players = Player.objects.filter(team=obj)
        if players.exists():
            team_rank = sum(float(player.player.rank) if player.player.rank not in ["", "null", None] else 1 for player in players)
            return team_rank / len(players)
        return 0.0
    
    def get_team_image(self, obj):
        if obj.team_image:
            return obj.team_image.name  
        return None
