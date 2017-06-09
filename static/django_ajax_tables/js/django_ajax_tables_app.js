var djangoAjaxTablesApp = angular.module('djangoAjaxTablesApp', []);

djangoAjaxTablesApp.config(function($httpProvider) {
    $httpProvider.defaults.xsrfCookieName = 'csrftoken';
    $httpProvider.defaults.xsrfHeaderName = 'X-CSRFToken';
    $httpProvider.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
});

djangoAjaxTablesApp.config(function($interpolateProvider) {
    $interpolateProvider.startSymbol('{$');
    $interpolateProvider.endSymbol('$}');
});

djangoAjaxTablesApp.factory('djangoAjaxTablesService', function($http){
    return {
        getRows: function(page_data) {
            return $http.post('/pl/django_ajax_tables/get_rows/', page_data);
        },
        action: function(action_data) {
            return $http.post('/pl/django_ajax_tables/action/', action_data);
        },
    }
});

djangoAjaxTablesApp.filter('range', function() {
    return function(output, total, current) {
        var total = parseInt(total) + 1;

        for (var i=1; i<total; i++) {  //probably might be written more pithy...
            if (i < 4){
                output.push(i);
            }
            else if (i > total - 2){
                output.push(i);
            }
            else if ((i > current - 2) && (i < current + 2)){
                output.push(i);
            }
            else if ((i == 4) && (current == 6)){
                output.push(i);
            }
            else if (i == 4){
                output.push('...');
            }
            else if ((i == total - 2) && (current == total - 4)){
                output.push(i);
            }
            else if ((i == total - 2) && (current > 2)){
                output.push('...');
            }
        }

        return output;
    };
});

djangoAjaxTablesApp.controller('djangoAjaxTablesController', function ($scope, djangoAjaxTablesService) {
    $scope.table_id = '';
    $scope.rows = [];
    $scope.page = 1;
    $scope.max_pages = 0;
    $scope.ordered_by = '';
    $scope.filter = {};
    $scope.check_all_value = false;

    $scope.get_page = function(){
        page_data = {
            'table_id': $scope.table_id,
            'page': $scope.page,
            'filter': $scope.filter,
            'ordered_by': $scope.ordered_by,
        }

        djangoAjaxTablesService.getRows(page_data).success(function(new_data) {
            console.log(new_data['rows']);
            $scope.rows = new_data['rows'];
            $scope.page = new_data['page'];
            $scope.max_pages = new_data['max_pages'];
        });
    };

    $scope.init = function(ng_init){
        $scope.table_id = ng_init['table_id'];
        $scope.get_page();
    };

    $scope.next_page = function() {
        $scope.page += 1;
        $scope.get_page();
    };

    $scope.previous_page = function() {
        $scope.page -= 1;
        $scope.get_page();
    };

    $scope.page_number = function(num) {
        $scope.page = num;
        $scope.get_page();
    };

    $scope.order_by_func = function(column) {
        if ($scope.ordered_by == column){
            if ($scope.ordered_by.charAt(0) == '-') $scope.ordered_by = column;
            else $scope.ordered_by = '-' + column;
        }
        else $scope.ordered_by = column;
        $scope.get_page();
    };

    $scope.action = function(action_id, are_you_sure_question, model_id){
        action_data = {
            'action_id': action_id,
            'model_id': model_id,
            'all_rows': $scope.rows,
            'table_id': $scope.table_id
        }

        if (are_you_sure_question){
            if (confirm(are_you_sure_question)){
                djangoAjaxTablesService.action(action_data).success(function(to_evaluate){eval(to_evaluate);});
            }
        }
        else{djangoAjaxTablesService.action(action_data).success(function(to_evaluate){eval(to_evaluate);});}
    };

    $scope.check_all = function(value){
        console.log(value);
        if (value){
            for (var i = 0; i < $scope.rows.length; i++) {
                $scope.rows[i]['checked'] = true;
            }
        }
        else{
            for (var i = 0; i < $scope.rows.length; i++) {
                $scope.rows[i]['checked'] = false;
            }
        }
        console.log($scope.rows);
    };

    $scope.check_single = function(value){
        if (!value){
            $scope.check_all_value = false;
        }
    };
});


