$(function(){
    $('.widget').draggable({
        containment: '.widgetsPane',
        snap: '.widget',
        grid: [10, 10]
    });


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
    })
});