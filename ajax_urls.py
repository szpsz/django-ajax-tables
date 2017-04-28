from django.conf.urls import patterns, url
from table import get_rows, action

urlpatterns = patterns(
    'django_ajax_tables',
    url(r'^action/$', action, name="django_ajax_table_other_action"),
    url(r'^get_rows/$', get_rows, name="django_ajax_table_page"),
    )
