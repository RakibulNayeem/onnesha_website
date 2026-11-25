from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="panel_home"),
    path("questions/", views.questions, name="panel_questions"),
    path("questions/new/", views.question_edit, name="panel_question_new"),
    path("questions/<int:pk>/", views.question_edit, name="panel_question_edit"),
    path("questions/<int:pk>/delete/", views.question_delete, name="panel_question_delete"),
    path("content/<str:kind>/", views.content_list, name="panel_content"),
    path("content/<str:kind>/new/", views.content_edit, name="panel_content_new"),
    path("content/<str:kind>/<int:pk>/", views.content_edit, name="panel_content_edit"),
    path("content/<str:kind>/<int:pk>/delete/", views.content_delete, name="panel_content_delete"),
    path("users/", views.users, name="panel_users"),
    path("payments/", views.payments, name="panel_payments"),
    path("payments/<int:pk>/receipt/", views.payment_proof, name="panel_payment_proof"),
    path("users/new/", views.user_edit, name="panel_user_new"),
    path("users/<int:pk>/", views.user_edit, name="panel_user_edit"),
]
