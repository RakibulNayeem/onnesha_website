from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="pub_home"),
    path("lang/<str:code>/", views.set_language, name="pub_set_language"),
    path("programs/", views.programs, name="pub_programs"),
    path("programs/<int:pk>/", views.program_detail, name="pub_program_detail"),
    path("teachers/", views.teachers, name="pub_teachers"),
    path("notices/", views.notice_list, name="pub_notices"),
    path("notices/<int:pk>/", views.notice_detail, name="pub_notice_detail"),
    path("results/", views.result_index, name="pub_results"),
    path("results/<int:pk>/", views.result_detail, name="pub_result_detail"),
    path("gallery/", views.gallery, name="pub_gallery"),
    path("videos/", views.videos, name="pub_videos"),
    path("downloads/", views.downloads, name="pub_downloads"),
    path("blog/", views.blog_list, name="pub_blog"),
    path("blog/<slug:slug>/", views.blog_detail, name="pub_blog_detail"),
    path("admission/", views.admission, name="pub_admission"),
    path("contact/", views.contact, name="pub_contact"),
    path("about/", views.about, name="pub_about"),
]
