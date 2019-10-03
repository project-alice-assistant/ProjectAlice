$(function(){
    $('.widget').draggable({
        containment: '.widgetsPane',
        snap: '.widget',
        grid: [10, 10],
        start: function(event, ui) {
            $(this).parent().append($(this))
        }
    }).css('position', 'absolute');


    $('.widgetsPane').droppable({
        drop: function(event, ui) {
            $.ajax({
                url: '/home/saveWidgetPos',
                data: {
                    id: $(ui.draggable).attr('id'),
                    x: $(ui.draggable).position().left,
                    y: $(ui.draggable).position().top
                },
                type: 'POST'
            })
        }

    });

    $('#addWidgetDialog').dialog({
        autoOpen: false,
        draggable: false,
        width: 600,
        height: 600,
        modal: true,
        resizable: false,
        close: function() {
            location.reload()
        }
    });

    $('#removeWidget').on('click', function() {
        $('.widgetDelete').show();
        $('#widgetCheck').show();
        $('#addWidget').hide();
        $('#removeWidget').hide();
    });

    $('#widgetCheck').on('click', function() {
        $('.widgetDelete').hide();
        $('#widgetCheck').hide();
        $('#addWidget').show();
        $('#removeWidget').show();
        location.reload()
    });

    $('.fa-minus-circle').on('click', function() {
        if ($(this).parents('.widget').length > 0) {
            $.ajax({
                url: '/home/removeWidget',
                data: {
                    id: $(this).parent().parent().attr('id')
                },
                type: 'POST'
            });
            $(this).parent().parent().remove();
        }
    });

    $('.fa-plus-circle').on('click', function() {
        $('#addWidgetDialog').dialog('open');
    });

    $('.addWidgetCheck').on('click', function() {
        if ($(this).parents('.addWidgetLine').length > 0) {
            $.ajax({
                url: '/home/addWidget',
                data: {
                    id: $(this).parent().attr('id')
                },
                type: 'POST'
            });
            $(this).parent().remove();
        }
    });
});