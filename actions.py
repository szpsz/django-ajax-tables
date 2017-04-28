from components.django_ajax_tables.table import DjangoAjaxTableAction


class DeleteAction(DjangoAjaxTableAction):
    def __init__(self,
                 model,
                 message='',
                 html='<button class="btn">Delete checked&nbsp <span class="glyphicon glyphicon-trash" aria-hidden="true" title="delete"></span></button>',
                 security_function=lambda r: None,
                 render_template=False,
                 are_you_sure_question='Are you sure about deleting this?',
                 show_condition=''
                 ):
        self.model = model
        self.message = message
        super(self.__class__, self).__init__(html, None, security_function, render_template, are_you_sure_question, show_condition)

    def function(self, request):
        rows = DjangoAjaxTableAction.get_content(request)['all_rows']
        count = 0
        for row in rows:
            if row['checked']:
                self.model.objects.get(id=row['model_id']).delete()
                count += 1
        if self.message:
            return u'''alert("%s %s");
                       $scope.get_page();''' % (count, self.message)
        return '$scope.get_page();'


class RedirectToAction(DjangoAjaxTableAction):
    def __init__(self,
                 url,
                 html='<button class="btn">Go to&nbsp <span class="glyphicon glyphicon-share" aria-hidden="true" title="go to"></span></button>',
                 security_function=lambda r: None,
                 render_template=False,
                 show_condition=''
                 ):
        self.url = url
        super(self.__class__, self).__init__(html, lambda r: None, security_function, render_template, '', show_condition)

    def function(self, request):
        return 'window.location.href = "%s";' % self.url


class RedirectWithIdAction(DjangoAjaxTableAction):
    def __init__(self,
                 url,
                 html='<button class="btn btn-default btn-xs"><span class="glyphicon glyphicon-share" aria-hidden="true" title="go to"></span></button>',
                 security_function=lambda r: None,
                 render_template=False,
                 show_condition=''
                 ):
        self.url = url[:-1] if url[-1] == '/' else url
        super(self.__class__, self).__init__(html, lambda r: None, security_function, render_template, '', show_condition)

    def function(self, request):
        return 'window.location.href = "%s/"+model_id;' % self.url