from django.urls import path
from apps.team import views


urlpatterns = [

    #map api
    #old
    path('c9a15248f417c7d4d0b824e22df96120d8c674480928e4024903445df90d30f5/', views.all_map_data, name="all_map_data"),
    
    #map api
    #new
    path('2bdfe77479df1fc79e49e2939ce0a0a8018d4d94f13d7288d4ed79f4b2a96cf8/', views.all_map_data_new, name="all_map_data"),

    # Team Type & Person Type
    path('1963b18359229186f2817624c25bb11c613f9e30b9d2f6f18982064ae2e78d9e/', views.leagues_teamType, name="leagues_teamType"),
    path('8fc896dbad658501526b8f3eca6a4fbba95ea86269d96cd3a71d8d8b9575b1c2/', views.leagues_pesrsonType, name="leagues_pesrsonType"),
    
    # Player
    path('30ddee1c070d318b5054521aaaaf3c9a03d938d90c9bdeacadeecdd76cb99554/', views.create_player, name="create_player"),
    path('6223737bd87561d5efc114403fd56771be64b41af5c5c18dda208fb1ecd851e5/', views.view_player, name="view_player"),
    path('a04269bd4564a6f973d1a959616a037242d4401b31ceafe8236e7fdaf13d2812/', views.list_player, name="list_player"),
    path('6a502a80130911930674f4a9cede39a383f366a684fdf667d26eed49c048e321/', views.email_send_for_create_user, name="email_send_for_create_user"),
    path('08d664c5b48389500adc8c6f8d5f8aa2150ce8eec29fbab7b9630025cdaaa055/', views.edit_player, name="edit_player"), #new add
    path('0951b1ba7bfb43562d3ce1f377ed776bffce89092cc63baa75115723bfde4592/', views.delete_player, name="create_player"), #new add
    path('c6d9792e19b52f2ffb961097f6385e430f668b1dccf46514f900cae955757390/', views.player_list_using_pagination, name="player_list_using_pagination"),
    path('05bb45dd8fd8292f74bdbd04162360d81dfe6a99db3f4dd55c495ac8c474960f/', views.my_player_list, name="my_player_list"),
    path('65070ddb7cef7ff13931e8f3202c93975737469c1e43dc76d6f9ce53bd8d1460/', views.player_profile_details, name="player_profile_details"),
    path('a70163a6be1c608c5975eaf63d680cff6e2dedf945d17871a421500b5cf1f926/', views.player_team_details, name="player_team_details"),
    path('8bfc54fa62aded9ebe0417313eb7e8d3de990e7775ab8de2551ebe8db4f1928f/', views.player_match_statistics, name='player_match_statistics'),
    
    # Team
    path('6b0bfb8e6263728c6b3d3f9224fd5f6f968d7c6d1b02fb4a84503f9c384bbdd8/', views.create_team, name="create_team"),
    path('a055a65f599d3d65289630efd48729d4376b3664b13b5d58ed1d18f664322af2/', views.team_list, name="team_list"),
    path('b7c8cb48779da0733ab972fd456a7bc35999b2732258c671a4c00cc9e5e111ab/', views.edit_team, name="edit_team"),
    path('29479d6589f748706e3fe02759c14de16aba6335ecc51889c4c3ff89d7c35c9d/', views.team_view, name="team_view"),
    path('cf473ee6b572066a6fab74e03ae862a8068649b12524dcef808a647078fbe887/', views.delete_team, name="delete_team"),
    path('3d0c1cc9660d3c13a543d73325f853f764a8b912631928a8f113a1eda6d3b945/', views.team_list_using_pagination, name="team_list_using_pagination"),
    path('8a9ffb9aa08dd06406852b2634f4857058fe5c8f9c30a3b3a3f0926d180d2f17/', views.my_team_list, name="my_team_list"),
    path('c92fef00578afa97b20fd67a590f5a5dde6638f6e1f2f2a29e9177043bcef164/', views.team_match_history, name="team_match_history"),
    path('fe1208e9a81a6a00d0f99158f64f7a840f492193c932ad8f822f5a0b76d5014c/', views.team_profile_details, name="team_profile_details"),
    path('297c74d4476635f3ba48b11cf4343545f56b734b3e04f22430d6d7d418937658/', views.team_statistics, name="team_statistics"),
    path('714c4b4e559a323fe8d2bd968fb5ba0291af816c8291bab2f00341e07eceb849/', views.team_tournament_history, name="team_tournament_history"),

    path('9dce0acaee00068dae47a3fb6e9b6507d9bce69a2832ebbe4bfd14494411e7e9/', views.send_team_member_notification, name="send_team_member_notification"),
    

    path('138687ab4b3ecfd8de04eb7594d103a9f23e47024fab1e6180e9b7b740282e5f/', views.create_leagues, name="create_leagues"),
    path('138687ab4b3ecfd8de04eb7594d103a9f23e47024fab1e6180e9b7b740282e45/', views.create_play_type_details, name="create_play_type_details"),
    
    
    #open play
    path('9da0ecfab64f942376b3a55d75323e7093b3407fddc7debf424964fb3ba2d866/', views.create_open_play_tournament, name="create_open_play_tournament"),


    #new
    path('96240c41e44a0580ccf3acf9446fa1f50608caec4445a0a9e6eba018b06f0022/', views.view_leagues_for_edit, name="view_leagues_for_edit"),
    path('d36377543d4388b68674a16c33686c64cfc14ae07241005e4fca461e970a611d/', views.edit_leagues, name="edit_leagues"),
    path('82577821e2ec5060c52c8e2260ac9b022052fead63ed5838b290fe715ee2fab0/', views.delete_leagues, name="delete_leagues"),
    path('eec3ee15b68b7c7ccda3e5b20c78ddf3b957b81db3905970fc346e777f6a5ed2/', views.save_league, name="save_league"),
    path('2b9e6d28354d75ef21c3ed5d2d39275509317487a6763316c4f2e59446e22c05/', views.check_invited_code, name="check_invited_code"),
    
    path('22fef865dab2109505b61d85df50c5126e24f0c0a10990f2670c179fb841bfd2/', views.assigne_match, name="elimination_round_create_match"),
    path('c383e35ca7159e85cdee6e1cd5d8174bd78c9cdbc5cad74dab1219694693df88/', views.send_notification_organizer_to_player, name="send_notification_organizer_to_player"),

    path('0768e2d54473589c299ce1cc2ca1868b35c3ca755f5a8c3592bb8c7641b5184c/', views.set_tournamens_result, name="set_tournamens_result"),
    path('bbeca046b744bcaad382d4c6faf9475e34cd8d095964fdaf6db7d459812ab7a6/', views.approve_set_tournament_result, name='approve_set_tournament_result'),
    path('5aaf2a913172ab6e5f974cb3d2de516d02aa855fdd0972999cd9d2e635af71db/', views.report_set_tournament_result, name='report_set_tournament_result'),
    
    path('75c06a948ce91223ac237977efcdf4241797c6663fbc911c795bfb047ff9969b/', views.list_leagues_admin, name="list_leagues_admin"),
    path('15b2232182bde38f0e3417c6b76ee8be195650b54a11be799c343007ff1cb16b/', views.list_leagues_user, name="list_leagues_user"),
    path('02b308858b9e0a85a236c47daa5b6cadc3873ef96c439f20e8f8f7085cef7080/', views.my_league, name="my_league"),

    path('1251c996e824040404a9b109661059c5364dd0c7862181ec2debf84bf84b5d6a/', views.add_organizer_league, name="add_organizer_league"),
    path('4fe1a82c9588f5ebdd6f2645a1b623b64e1ef3f30c97222b9cc8daa5cab472c0/', views.search_user_to_add_organizer, name='search_user_to_add_organizer'),

    path('c77f5d64f97d13a18cf68378b1aec5c1cec3bc80155eb97af2bd687cb77722ea/', views.tournament_schedule, name="tournament_schedule"),
    path('77abbea9d67647e3a058cd85a3e40c0b2c8292584673971179d61790e232f5da/', views.edit_leagues_max_team, name="edit_leagues_max_team"),
    
    path('8da2a08a043f05bca31c69c545cb75e82c46b04b80f40895864553bc5857fd70/', views.view_leagues, name="view_leagues"),
    path('0777f38a45a8d18dad6f5a67d26ca711c13f708e9a8af7adba03cf7c4ff532c3/', views.team_register_user, name="team_register_user"),
    path('098aab95e8c33f89813be83b47ee59c8c7d61e1954ec258b49b4cf12f7e61626/', views.add_team_to_leagues, name="add_team_to_leagues"),
    path('c80e2caf03546f11a39db8703fb7f7457afc5cb20db68b5701497fd992a0c29f/<int:charge_for>/<str:my_data>/<str:checkout_session_id>/', views.payment_for_team_registration, name="payment_for_team_registration"),

    #### New updated for wallet implementation
    path('fe8a7fba1488235d4d7fcd16de80104e24910fc0f53d4e5cfed6234ace66ddb2/', views.register_teams_to_league, name='register_teams_to_league'),


    path('a8b080954e46cf104488b5229283a70863b4177524442bb148efbc5f28d0b144/', views.player_or_manager_details, name="player_or_manager_details"),
    path('c43ecd81b003f2be96ea3377de9aaa375f0abb5d370dee415e299d0d108ad855/', views.registered_team_for_leauge_list, name="registered_team_for_leauge_list"),
    path('34e3fb663d4021b5628599d112d0f4773d2fe8f7a99e9bb64dcd5946c408fa44/', views.stats_details, name="stats_details"),
    path('deca7be4ec5148eba16ee9cccc6e1fe5b2fadb25c26f10076855e9bc4bc5b843/', views.tournament_details, name="tournament_details"),

    path('89e6bda1a6a787802c8d249a5a4462d00046edbba6b091847246e9943c6c6d96/', views.add_sponsor, name="add_sponcer"),
    path('d6417dd1eda62fbf7a1b335cbd98fc98f522cefffec1dd0234cac7edb82560b5/', views.view_sponsor_list, name="view_sponsor_list"),
    path('57b8d2d8332ca50830edf80d49b7095564aa2def44d14720153e97d81ea9d4b8/', views.view_sponsor, name="view_sponsor"),
    path('18fce83471a2984e034829201bc2ff6ca6473f183a71afbb7b81f5abf1527f35/', views.resend_email_sponsor, name="resend_email_sponsor"),
    path('56f46054e1a3d341c01181e3a2007b3c659015331d2a18697da573b77ab0e4a1/', views.list_leagues_for_sponsor, name="list_leagues_for_sponsor"),

    path('b1f549d88d5e511e2815684d3dee12e6092c6e43f308038595f543e4b00a75f8/', views.tournament_joined_details, name="tournament_joined_details"),
    path('bd4317606b7517bc4480efb10226f023aee1cdd26632ad3e0ff33dc209f5d411/', views.tournament_saved_details, name="tournament_saved_details"),
    path('ca828a9a696161abaa1dd40af965ffa9399669bc824e735dea156598df09d7ea/', views.open_play_details, name="open_play_details"),
    path('c9241a21e10c70edb0741c62441f57b9b8cd7227187aeb359f996596db49b552/', views.tournament_created_details, name="tournament_created_details"),
    path('0b16a86561028bdb694a46552c6bd26efe088a58c9196ba61a563289a78341a5/', views.tournament_joined_completed_details, name="tournament_joined_completed_details"),
    path('08a05a90319836ae555f5005b6ae36862ef352688a7b8a7988b4657d5b85d0e4/', views.tournament_saved_completed_details, name="tournament_saved_completed_details"),

    # turnament assign#up
    # path('aa7fe9297f4df53eafc5d2837d04b326130278561947c2ad6d393ce49a279aa0/', views.team_assign, name="team_assign"),
    path('7c0d9926c261cb38eb6d6ca1bd367fef79824367bdc21b236542700e04a5ea2e/', views.tournament_edit, name="tournament_edit"),
    #up


    ####for admin
    path('43c1b3de560ac4c3768d5cb397e33e34a2b7601936bd905ac99d63675aebb4da/', views.get_organizer_details, name='get_organizer_details'),
    path('aecedd7701d99e33511be4aca1e89fbfe717f36cea015658bbacc9e7739ddfb9/', views.get_sponsor_details, name='get_sponsor_details'),
    path('8cc7170ae335c23d36e0780766b69b3bee062d4e028cf9cc8ac8ea57d8caba73/', views.get_admin_details, name='get_admin_details'),
    path('2da5e41f58363eaf685a264f5a497c34a8a6ded6f1ce739077eea374ec1e23f6/', views.get_ambassador_details, name='get_ambassador_details'),

    path('aa01d87e3b6fba20549538cf89dfeddc6d86956f2bedff3fe95c479c4f978a97/', views.remove_organizer, name='remove_organizer'),
    path('7e8bd8cc710150f5c39a041325b72cc74bcce5bde17a9c8df82fc5718d5b59e3/', views.remove_sponsor, name='remove_sponsor'),
    path('b0e691c9c95243849ab6cfdcd1d20fe7b5e12075e71437a9efa63b9922881046/', views.remove_admin, name='remove_admin'),
    path('8b892ca78f8d8a5ac2e1cb697a4b0cc179cc825255d53e2840c03fd6497cffab/', views.remove_ambassador, name='remove_ambassador'),
    
    #test
    path('del_code123/', views.del_code, name='del_code'),
    # path('edit_team_test/', views.edit_team_test, name="edit_team_test"),

    # updated view league
    path('4ed35c59e2b4fe9dd55be2f95db4f76ca4737f75bce17c5d22d24080a39602d3/', views.view_playtype_details, name="view_playtype_details"),
    path('93b49e5e88c8eafa6a339a5920f270965db5fbbc2de5d99153a702180d17250d/', views.view_match_details, name="view_match_details"),
    path('221bac590d7d3725e4150a429d364d732f87128b0aebe78e90f9959a9d453b54/', views.view_elimination_details, name="view_knockout_details"),
    path('014891a28506b292f2c9b020834cbbf1f075bf18186042a2dc3deae985a673a9/',views.view_point_table_details, name="view_round_robin_details"),
    path('9edc82d0660cbd0597ab05119784aa8741f9f039a14d0e5fb33fd805db6046bd/', views.get_match_result, name="get_match_result"),
    
    
    path('c1ab03839712158bec69da7c630e9e2563e4391db4b01bf27e34514568cea04e/', views.profile_stats_match_history, name="profile_stats_match_history"),
    path('bb4219c7c842ce05582d6a9a7559e85124ff568beff9921c97ddb4ac87f003a5/', views.get_tournament_count, name="get_tournament_count"),
    path('70a46284ef37448a8d477477c2bdf695245a8a36c4b39ed043409e7bb3bc56bb/', views.get_leagues_list, name="get_leagues_list"),
    path('2d78919ac3a46548aff39f6c752625ef04c5b5c9cd3d96a2c7c6672f6d971b8a/', views.get_final_match_details, name="get_final_match_details"),   

    path('3e5b33694f6e108577e2851e41560cd5c4ce086dd3be909ba25a70cee25e6ba5/', views.home_page_stats_count, name='home_page_stats_count'),
    path('cc9d582d2d1e2dfc03f73e42ea852568fe84be5633a612f26b825f6b766af9cd/', views.search_players_by_location, name='search_players_by_location'),
    path('6a09d24155380583d67da88843a134c836f45e211b15c9c64a0a9c8ff4cedd06/', views.search_tournaments_by_location, name='search_tournaments_by_location'),


    #match score update
    path('event_matches/', views.event_matches, name='event_matches'),
    path('match_view_score/', views.match_view_score, name='match_view_score'),
    # path('2cd8270498d1c7c5e6cef1d06c0b1fb6862d85fedd79afab7bddccfeb3f1713b/', views.filter_player_by_gender_and_rank, name='filter_player_by_gender_and_rank'),
    # path('794db4f35795a58cfbf824d126c56ae1fdae5db680a0f16211be475eb517247b/', views.filter_team, name='filter_team'),
]