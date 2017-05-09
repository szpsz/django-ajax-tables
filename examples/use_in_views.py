# TODO write something...
from django.contrib.auth.models import User
from components.django_ajax_tables.actions import DeleteAction, RedirectToAction, RedirectWithIdAction
from components.django_ajax_tables.table import DjangoAjaxTableAction, DjangoAjaxTableColumn, DjangoAjaxTable


def delete_checked(request):
    '''
    this function is called by action to handle it.
    DjangoAjaxTableAction.get_content(request) returns request body which contains:
    'action_id': field to identify action/not used
    'table_id': field to identify table/not used
    'model_id': if action is model actions this is id of model
    'all_rows': rows to check which are checked (checkbox is checked)
    '''
    rows = DjangoAjaxTableAction.get_content(request)['all_rows']
    count = 0
    for row in rows:
        if row['checked']:
            User.objects.get(id=row['model_id']).delete()
            count += 1
    return u'''alert("%s user deleted");
               $scope.get_page();''' % count  # function should return js code or nothing
                                              # scope.get_page() is reload table function

table_actions = [  # action specific to whole table or all checked rows
    DjangoAjaxTableAction(
        # html code of action will be usually button or something like that
        u'<button class="btn">Delete marked&nbsp <span class="glyphicon glyphicon-trash" aria-hidden="true" title="delete"></span></button>',
        # function is evaluated when action button is pushed
        delete_checked,
        # if you specify are_you_sure_question it will be asked (good while deleting objects)
        are_you_sure_question="Czy na pewno chcesz usunac zaznaczone?"
    ),  # Example action to delete checked users users
    DeleteAction(User, 'Deleted'),  # the same action but using predefined delete action
    RedirectToAction('/'),  # Redirect to url action instead of href
]

row_actions = [  # action specific for single row (model object)
    RedirectWithIdAction('/poll/'),  # redirect action which adds model id to url
]

columns = [  # columns which build table
    DjangoAjaxTableColumn('id', True, False),  # column which represents id field or property is sortable and not filterable
    DjangoAjaxTableColumn('email', True, True),
    DjangoAjaxTableColumn('fullname', True, True, u'Name and surname', ),  # column which represents fullname model property or field is sortable and filterable and have name
    DjangoAjaxTableColumn('address', False, False, u'Adres'),
]

# table itself
dt = DjangoAjaxTable(User, columns, table_actions=table_actions, row_actions=row_actions, selectable_rows=True)


def view(request):  # example basic view
    # tables are created on the first time when the view file is invoke (probably server startup)
    # then tables use ajax for communication
    context = {'django_table': dt.as_html()}

    # context must be updated in this way because table use sekizai tags for its js and css
    context.update(dt.update_context())
    return context
