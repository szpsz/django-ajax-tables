import json
from uuid import uuid4
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.http import HttpResponse
from django.template import loader, Context
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
            self.html = html
        else:
            template = loader.get_template(html)
            self.html = template.render({})

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


class DjangoAjaxTableColumn(object):
    def __init__(self, model_field_name, sortable=False, filterable=False, column_header_name=None, header_classes=''):
        self.model_field_name = model_field_name
        self.column_header_name = column_header_name
        self.sortable = sortable
        self.filterable = filterable
        self.header_classes = header_classes

    def display(self, instance):
        return getattr(instance, self.model_field_name)

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

    def __init__(self, model, columns, table_actions=None, row_actions=None, **kwargs):
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
            "row_ng_classes": '',  # {'paid': row.paid && row.type != 'LIST', 'not-paid': !row.paid && row.type != 'LIST'}
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
        self.tables[self.table_id] = self
        initial_args['ng_init'] = {'table_id': self.table_id}
        template = loader.get_template('django_ajax_tables/table.html')
        context = Context(initial_args)
        context.update(SekizaiContext())
        self.html = template.render(context)
        self.sekizai_context = context['SEKIZAI_CONTENT_HOLDER']

    def as_html(self):
        return self.html

    def update_context(self):
        return {'SEKIZAI_CONTENT_HOLDER':  self.sekizai_context}

    def filter_row(self, object, filter):
        for column in self.columns:
            if column.filterable and (column.model_field_name + '_filter' in filter) and not filter[column.model_field_name + '_filter'] in column.display(object):
                return False
        return True

    def get_ajax_response(self, page, filter, ordered_by):
        objects = self.model.objects.filter(**self.initial_filter)

        if ordered_by:
            if any(True if f.name in ordered_by else False for f in self.model._meta.get_fields()):  # I know what i'am doing...
                objects = objects.order_by(ordered_by)
            else:
                if ordered_by[0] == '-':
                    objects = sorted(objects, key=lambda m: getattr(m, ordered_by[1:]), reverse=True)
                else:
                    objects = sorted(objects, key=lambda m: getattr(m, ordered_by), reverse=False)

        filter = dict((k, v) for k, v in filter.iteritems() if v)
        if filter:
            if all(any(True if f.name in single_filter else False for f in self.model._meta.get_fields()) for single_filter in filter.iterkeys()):  # I know what i'am doing...
                filter = dict((k.split('_filter')[0]+'__icontains', v) for k, v in filter.iteritems())
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

        rows = [{'checked': False, 'model_id': object.id, 'content': [column.display(object) for column in self.columns]} for object in objects]
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
                response = {'rows': rows,
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
