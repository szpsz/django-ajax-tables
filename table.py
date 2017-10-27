import json
import traceback
from uuid import uuid4
from django.core.exceptions import PermissionDenied, FieldError
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.template import loader, Context, Template
from django.views.decorators.csrf import csrf_protect
from sekizai.context import SekizaiContext


class DjangoAjaxTableAction(object):
    def __init__(self, html, function, security_function=lambda r: None, render_template=False, are_you_sure_question='', show_condition=''):
        self.action_id = str(uuid4())
        if not hasattr(self, 'function'):
            self.function = function
        self.security_function = security_function
        self.are_you_sure_question = are_you_sure_question
        self.show_condition = show_condition
        if not render_template:
            self.template = Template(html)
        else:
            template = loader.get_template(html)
            self.template = template

    def action(self, request):
        self.security_function(request)
        to_return = self.function(request)
        if to_return is None:
            return HttpResponse('', content_type="application/json")
        if isinstance(to_return, basestring):
            return HttpResponse(to_return, content_type="application/javascript")
        else:
            raise TypeError('Action must return a string or None instead of %s' % type(to_return))

    @staticmethod
    def get_content(request):
        return json.loads(request.body.decode('utf-8'))

    @property
    def html(self):
        return self.template.render(Context({}))


class DjangoAjaxTableColumn(object):
    def __init__(self, model_field_name, sortable=False, filterable=False, column_header_name=None, header_classes=''):
        self.model_field_name = model_field_name
        self.column_header_name = column_header_name
        self.sortable = sortable
        self.filterable = filterable
        self.header_classes = header_classes

    def display(self, instance):
        try:
            return getattr(instance, self.model_field_name)
        except:
            print 'tu jest cos nie tak'

    def add_to_table(self, model):
        if self.column_header_name is None:
            self.column_header_name = getattr(getattr(model, self.model_field_name, None), 'verbose_name', self.model_field_name)

    @property
    def title(self):
        return self.column_header_name

    @property
    def sortable_js(self):
        return 'true' if self.sortable else 'false'


class DjangoAjaxTable(object):
    """
    model: django model,
    columns List of columns in table
    """
    tables = {}

    def __init__(self, model, columns, table_actions=None, row_actions=None, excluded=None, **kwargs):
        self.excluded = excluded if excluded else []
        # TODO add check of kwargs for html shit
        self.objects_on_page = kwargs.get('objects_on_page', 20)  # TODO from settings
        self.initial_filter = kwargs.get('initial_filter', {})
        initial_args = {
            "additional_before_table": '<div class="col-md-12"><div class="panel panel-default"><div class="panel-heading">%s</div><div class="panel-body">' % kwargs.get('table_name', ''),
            "additional_after_table": '</div></div>',
            "empty_table": "No records",
            "select_row_checkbox_classes": "big-checkbox",
            "selectable_rows": kwargs.get('selectable_rows', False),
            "action_for_selected": None,  # [{'classes':..., 'function':..., 'description': ..., }, ... ] see table.html
            "rows_ng_classes": kwargs.get('rows_ng_classes', ''),  # {'paid': row.paid && row.type != 'LIST', 'not-paid': !row.paid && row.type != 'LIST'}
        }

        self.model = model
        for c in columns:
            c.add_to_table(model)
        self.columns = columns
        self.table_actions = table_actions if table_actions else []
        initial_args['table_actions'] = self.table_actions
        self.row_actions = row_actions if row_actions else []
        initial_args['row_actions'] = self.row_actions
        initial_args['columns_filters'] = any(True if x.filterable else False for x in columns)
        initial_args['columns'] = columns
        self.ajax_security_function = kwargs.get('ajax_security_function')
        self.table_id = str(uuid4())
        self.tables[self.table_id] = self  # add self to dict of table instance to find it when loading data dynamically
        initial_args['ng_init'] = {'table_id': self.table_id}
        self.template = loader.get_template('django_ajax_tables/table.html')
        self.context = Context(initial_args)
        self.context.update(SekizaiContext())
        self.html = None
        self.sekizai_context = self.context['SEKIZAI_CONTENT_HOLDER']

    def as_html(self):
        if self.html is None:
            self.html = self.template.render(self.context)
        return self.html

    def update_context(self):
        return {'SEKIZAI_CONTENT_HOLDER':  self.sekizai_context}

    def filter_row(self, object, filter):
        for column in self.columns:
            if column.filterable and (column.model_field_name + '_filter' in filter) and not filter[column.model_field_name + '_filter'] in column.display(object):
                return False
        return True

    def skip_not_serializable_keys_or_excluded(self, object):
        object_table_evaluable = {k: getattr(object, k)() for k in dir(object) if 'table_evaluable' in k}
        object_dict = object.__dict__
        object_table_evaluable.update({k: v for k, v in object_dict.iteritems() if k not in self.excluded and str(type(v)).split("'")[1] in ('str', 'unicode', 'int', 'long', 'float', 'bool', 'NoneType')})  # not nice check
        return object_table_evaluable

    def get_ajax_response(self, page, filter, ordered_by):
        objects = self.model.objects.filter(**self.initial_filter)
        # if order by model field use order_by django model function for efficiency, if not load all objects from db and order using sorted :(
        if ordered_by:
            if any(True if f.name == ordered_by or f.name == ordered_by[1:] else False for f in self.model._meta.get_fields()):  # I know what i'am doing...
                objects = objects.order_by(ordered_by)
            else:
                if ordered_by[0] == '-':
                    objects = sorted(objects, key=lambda m: getattr(m, ordered_by[1:]), reverse=True)
                else:
                    objects = sorted(objects, key=lambda m: getattr(m, ordered_by), reverse=False)

        # if filter by model field use filter django model function for efficiency, if not load all objects from db and filter using list comprehension :(
        filter = dict((k, v) for k, v in filter.iteritems() if v)
        if filter:
            if all(any(True if f.name == single_filter.split('_filter')[0] else False for f in self.model._meta.get_fields()) for single_filter in filter.iterkeys()):  # I know what i'am doing...
                filter = dict((k.split('_filter')[0] + '__icontains', v) for k, v in filter.iteritems())
                objects = objects.filter(**filter)
            else:
                objects = [object for object in objects if self.filter_row(object, filter)]

        paginator = Paginator(objects, self.objects_on_page)
        try:
            objects = paginator.page(page)
        except PageNotAnInteger:
            page = 1
            objects = paginator.page(page)
        except EmptyPage:
            page = paginator.num_pages if page != 0 else 1
            objects = paginator.page(page)

        print objects, type(objects)
        rows = [{'checked': False, 'model': self.skip_not_serializable_keys_or_excluded(object), 'content': [column.display(object) for column in self.columns]} for object in objects]
        return rows, page, paginator.num_pages

    @classmethod
    def process_request(cls, request, action=False):
        if request.is_ajax():
            content = json.loads(request.body.decode('utf-8'))
            instance = cls.tables.get(content.get('table_id'))
            if instance is not None:
                if instance.ajax_security_function is not None:
                    instance.ajax_security_function(request)

                if action:
                    action = next(a for a in instance.row_actions + instance.table_actions if a.action_id == content.get('action_id'))
                    return action.action(request)

                page = content.get('page', 1)
                filter = content.get('filter', {})
                ordered_by = content.get('ordered_by')
                rows, page, max_pages = instance.get_ajax_response(page, filter, ordered_by)
                response = {
                    'rows': rows,
                    'page': page,
                    'max_pages': max_pages,
                }
                response = json.dumps(response)
                return HttpResponse(response, content_type="application/json")
        raise PermissionDenied


@csrf_protect
def get_rows(request):
    return DjangoAjaxTable.process_request(request)


@csrf_protect
def action(request):
    return DjangoAjaxTable.process_request(request, action=True)
