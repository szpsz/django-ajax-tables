django-ajax-tables
==================

Tables which are dynamic, easy to use, efficient and not ugly.

Installation
------------

+ To install it using pip just type in `sudo pip install django-ajax-tables`, add it to your settings: INSTALLED_APPS and add `url(r'^django_ajax_tables/', include('components.django_ajax_tables.ajax_urls'))`, to your base urls.
+ If you want install it in another way you probably know what you are doing

Usage
-----

+ Usage examples can be found in examples folder, it should be easy enough to learn from it.

Efficiency
----------

+ Table will be much more efficient if you allow to filter and order only by model fields (not by property). See code exaples and source code.