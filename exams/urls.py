from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="exam_home"),
    path("api/quick/", views.quick_question, name="exam_quick"),
    path("bank/", views.bank, name="exam_bank"),
    path("practice/", views.practice, name="exam_practice"),
    path("tracks/<slug:slug>/", views.track_detail, name="exam_track"),
    path("subjects/<int:pk>/", views.subject_detail, name="exam_subject"),
    path("test/new/", views.build, name="exam_build"),
    path("test/<int:pk>/", views.take, name="exam_take"),
    path("test/<int:pk>/result/", views.result, name="exam_result"),
    path("lang/<str:code>/", views.set_language, name="exam_lang"),
    path("profile/", views.profile, name="exam_profile"),
    path("me/", views.dashboard, name="exam_dashboard"),
    path("leaderboard/", views.leaderboard, name="exam_leaderboard"),
    path("cq/", views.cq_practice, name="exam_cq"),
]
