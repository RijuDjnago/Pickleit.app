from django.urls import path
from apps.accessories import views


urlpatterns = [
    # Addvertisment Sponsor
    path('19a18a717c4ee1807e2748cd8a374baeacbc3e4d542a4767c8720e83572e09e5/', views.screen_type_list, name="screen_type_list"),
    path('fcd47604f8505aedf9ea937eb75828995d766a3e27be9a60198585d29e4fcefe/', views.add_advertisement, name="add_advertisement"),

    # Updated for payment gateway
    path('0a17353ad39c003075afffecbfe253e381bc9c331fb1b06a0ac18a7734116f98/', views.create_advertisement, name="craete_advertisement"),
    path('9671103725bb2e332ec083861133f7c0dad8e72b039e76bcdff4a102d453b66a/<str:charge_for>/<str:my_data>/<str:checkout_session_id>/', views.payment_for_advertisement, name="payment_for_advertisement"),

    path('aba97dd0cccde47371ac92197491a84aa60ae487fa3e5bde82e360f8eda27879/', views.list_advertisement, name="list_advertisement"),
    path('ae35895453a924b6d8931bf5c43e1dc0b50da42e10f1875106ea289b73765741/', views.list_advertisement_for_app, name="list_advertisement_for_app"),
    
    path('8a568ce2ff3dcd44588b7a9d7735016863742b231f427b5c3dde9e34565c7ace/', views.view_advertisement, name="view_advertisement"),
    path('ae17d7f687a0e35eab20437fde4e408a26508eef44d14f454b0a597f8e6e654c/', views.advertisement_approved_by_admin, name="advertisement_approved_by_admin"),
    # Payments

    path('9b431a292d0a18597a33e64d24a9dcec284e4cbfd6fae40a5a2410e61f897808/', views.add_charge_amount, name="add_charge_amount"),
    path('1fc6d6c3cb40877310bc9b6f2686ba5bfcfa8e76363a2422161f668b18c7f29a/', views.list_charge_amount, name="list_charge_amount"),
    path('2dad6f72222cefc6737454b3b7e828a24576395bbd2aac30d8f0e059d15b9252/', views.view_charge_amount, name="view_charge_amount"),
    path('434707f123e5ed9dc8974c27fe8e87748a0c7af7cc3f5ed332d88c59188ebba0/', views.edit_charge_amount, name="view_charge_amount"),
    
    #add new for 
    path('1d46a750176f3c2d4a0c31fac7e1579dbd8b102b7aaa2caecdd83bba6a8389e5/', views.allow_to_make_organizer, name="allow_to_make_organizer"),


    path('a5845a43900377965b468e181e6215b911c39d91f547b54215e4e8b3fb0c051a/', views.list_payments, name="list_payments"),
    
    path('c7761e58969f7edd498186641b2021e8477e1bcd230de4cf3435242da4a40d14/', views.checkout, name="checkout"),
    path('040ffd5925d40e11c67b7238a7fc9957850b8b9a46e9729fab88c24d6a98aff2/<str:charge_for>/<str:checkout_session_id>/', views.payment, name="payment"),
    
    # Notifications
    path('576d775a6b0da447c7bf79a1bff13098357dbafc0a2fd82eb3e192225b833ad4/', views.show_notifications, name="show_notifications"),
    path('2b677406c367bf091bd726cdf8a7b0ea1f517fc730c864dc09c8fc1632a387bc/', views.update_notifications, name="update_notifications"),
    # Delivery Address
    path('e29ae6cf70258895fcc0d369c92368be4e65521fbeaf63f129b2cbce8699df66/', views.store_product_love_byUser, name="store_product_love_byUser"),
    path('1b90716282eaebaa0a4244e24c52bc67711de99c32e45001162c6e077a9308e6/', views.user_add_delivery_address, name="user_add_delivery_address"),
    path('d051f9831dd1b28b35a8e14d67b773a683c91e51b7ae193483ab553450d85afa/', views.user_edit_delivery_address, name="user_edit_delivery_address"),
    path('d7887b9d09956be166bd2e8aa1ac41ac2c98eb4e69f91e10170e7be152a1cdf0/', views.user_delivery_address, name="user_delivery_address"),
    path('b1d147cfe77d3d0af1fdefc98037a9070883caf1dd927c71a53e578502dd7fc9/', views.user_delivery_address_change, name="user_delivery_address_change"),
    # Merchandise Store
    path('c3ac6106fdf446f22fb9a7a40ef5f53b2b4ba932fcfa040d44d5e0118a7eb799/', views.store_category_add, name="store_category_add"),
    path('2e7a9372dface2b67fabd1b06ca5ee76abd142ce93497a79023226ce033a8f3d/', views.store_category_edit, name="store_category_edit"),
    path('c32543cf729d1ebcb8b7efe98918cc287b269676db52579abdd7b87aa3820690/', views.store_category_list, name="store_category_list"),
    path('317920220d2d47dfd06a78afef71e5e3b078f0738d8eb531cd37aa3e0b90dce0/', views.store_category_view, name="store_category_view"),
    
    path('ecf5996e26df82090bded2677435fd055b406d213919763606e1e34698f4f74e/', views.store_product_add, name="store_product_add"),
    path('094f7cc88d10be9061913e637d58a6c6cf81d125c101ec88a2646aa03b8017ea/', views.store_product_delete, name="store_product_delete"),
    path('615256f796aa2143421c3764c25acc20d478868e891f64a1af2fa01e8659fb8f/', views.store_product_edit, name="store_product_edit"),
    path('d3c3b488f32fd3c34fee5613c03da4fb5ec02daae27efb478a8f6859649cdad9/', views.store_product_list, name="store_product_list"),
    path('82708a7905621c6069cc592debc1a1eebce89f372d4a73daf79617408870bfe7/', views.my_store_product_list, name="my_store_product_list"),
    path('fbce2ffcbd4f246eb04fc0c9c4f9a6e15e206854cc05bfc6b812c354bf6a0f83/', views.store_product_view, name="store_product_view"),
    path('5457cf58bfb70977bca564f3b9a6fe5efbe71d713d73f57f10594518ff3fbfba/', views.category_wise_product_filter, name="category_wise_product_filter"),
    path('ff4001a548eff92079e17f6a6a1a10daa2f552acb1242eb9f0200313df8cdc3f/', views.search_wise_product_filter, name="search_wise_product_filter"),
    
    # Merchandise Store Payment
    path('a6ec72178c4e6c9fba52aabe8049093276cf37204057624d355afea7772be9bf/', views.buy_now_product, name="buy_now_product"),
    path('694b0ce98afc6fa28631622bc70971b3ca40d25490634a60dcd53a5ff04843f3/<str:charge_for>/<int:cart_id>/<str:checkout_session_id>/', views.buy_now_product_payment, name="buy_now_product_payment"),
    path('9307db8a741165b375126dd0e03710cf8158cfda4d10e2b23c2e17dd903bd278/', views.buy_all_cart_product, name="buy_all_cart_product"),
    path('7417d36367fa2fab97cf476a626b989b2fb842eddc47f55b50e877bd57c97a00/<str:charge_for>/<str:checkout_session_id>/', views.buy_all_cart_product_payment, name="buy_all_cart_product_payment"),
    
    # Cart section
    path('a4609a04ea5881df062f06f0d03d653606b972e9fd94eb8c00dd32641fea511d/', views.product_add_to_cart, name="product_add_to_cart"),
    path('e2134b0a04ee5fb97af0f2bd38c21f42edf027429f1dc8152c43df7c903d69cc/', views.cart_list, name="cart_list"),
    path('399c6d6d6d1a5174fb4fdbb931c06fadb40faa377e0e16f7cb83f492bee755d0/', views.cart_edit, name="cart_edit"),
    path('ad6afd93709535a40ff40f1690c505695085de1b9dbfc153caccddb31eabdb18/', views.cart_delete, name="cart_delete"),
    path('ab2fce6098b4f5e2e1609e50be8d788086de4f31752154595af4921518384cfa/', views.MyOrder.as_view(), name="MyOrder"),
    
    # AmbassadorsPost Store
    path('5900b44497b17085c3877cf81bf6cc1a5def1d234fdaec174e2a8afffdd1fee4/', views.allow_to_make_ambassador, name="allow_to_make_ambassador"),
    path('997a873e4701d0e77a7f5daa83acaecd86f4d6ac5cd6d20c6ddae11d6ae24fdf/', views.ambassador_list, name="ambassador_list"),
    path('7118b97e4abf7ba24f186e726078aebc56c01ebcd229d5f02678aaa1fc09ee4f/', views.ambassador_profile_view, name="ambassador_profile_view"),
    
    path('eb35a300315bbc654886d89bb21464b756e0dffa924aa31f594baf26f1ae3079/', views.ambassadors_create_post, name="ambassadors_create_post"),
    path('b2ef0471e3ec9cac1a9cee8e003016fd2df0b1a03a6fca983c52057bcb2894ae/', views.allow_to_make_ambassador_to_player, name="allow_to_make_ambassador_to_player"),
    path('6122c7562764ec30328dd65c8bc38f13d19f827465c83ae0a8ca096a3a4f6a1e/', views.ambassadors_view, name="ambassadors_view"),
    path('11200503c744f1c654cae555821fcd629753bd1918647145aa9bf740cac01859/', views.ambassadors_edit_post, name="ambassadors_edit_post"),
    path('6aa655d15032b879c635696440ea6be70e266dc286c52b4732017e7551bcc6ca/<del_id>', views.ambassadors_delete_post, name="ambassadors_delete_post"),
    path('349622ad9fe46f5e54ec6cb8f0c2d4d60b199b3d1b20aebba1f461793723506a/', views.admin_allow_ambassadors_post, name="admin_allow_ambassadors_post"),
    path('d787487951b801bf71b50ebb932b8588b762a9baad80c5e7db48fa8736945e6e/', views.ambassadors_view_all_allow_post, name="ambassadors_view_all_allow_post"),
    path('a4ecb8aba7087ba80a6482c6456443f693e57021a02aca9e4bb3e5068e3857c5/', views.ambassador_follow_or_unfollow, name="ambassador_follow_unfollow"),
    path('5100320b960b20b89093b66cc9f75b971916adaaeb02c83e92b030d731c80ccc/', views.check_ambassador_following_or_not, name="check_ambassador_following_or_not"),


    #sponsor facility part
    path('bccd11555e01236e30cd83b102468efb1fac9a94f878ffa415cfde7a513dd269/', views.add_advertiser_facility, name='add_advertiser_facility'),
    path('014de00d30c252365c1cad4bfb9e3a324eb09d991f3dfaa67f7bdef1c1ae3f54/', views.edit_advertiser_facility, name='edit_advertiser_facility'),
    path('e4311d8adde4474b8d2ec95bf65de32147dd9be2d8ba164167b0d8da8c675748/', views.delete_advertiser_facility, name='delete_advertiser_facility'),
    path('a2b51b99225382203c162467b2ad218250e08daf49556189a6901cfd1307f3f8/', views.advertiser_facility_list, name='advertiser_facility_list'),
    path('47934d738322309c5d315ea529f56af1060b130cc30ffda0ea3969a28fe7d9ac/', views.view_advertiser_facility, name="view_advertiser_facility"),
    path('561b99502eed6266370e55a61a644a8a29964713f114f66dedda77857377a6f5/', views.advertiser_facility_list_for_all, name="advertiser_facility_list_for_all"),

    path('c1a8d430388c1f522f509af3d395ecf49070ff79b8fe1bbd78f2faf2114d5fd4/', views.ambassador_post_like_dislike, name="ambassador_post_like_dislike"),
    path('6cdf210339d0397a8fedb681659bf38b7206a863675d1c72ee99ff9d115c06f6/', views.chech_post_liked_or_not, name="chech_post_liked_or_not"),
    path('be80c96ee1ee2b5740b16ab2bd83df9807ba36563996ebaec4f391e291b6beb4/', views.check_store_product_liked_or_not, name="check_store_product_liked_or_not"),
    path('44fa83b26ca103757133c3c51e16837d34a072592ab65ad249b0dfc39ad2ccdb/', views.wishlisted_products, name="wishlisted_products"),
    path('0aa6998dfe603cf9723b393ee94cd2d902b13b5f8f402d0aa655da96fd350b6d/', views.filtered_product_list, name="filtered_product_list"),
    path('12bf1648707891bf113ac4ffd866cc86c451b66b15b45ab6f7ace0918750964f/', views.category_details, name="category_details"),
    path('c894d0e5f50e543aaf26d64eb91ffbccd867a19d29a3b188d14f38ef79e2c1f2/', views.rate_product, name="rate_product"),
]