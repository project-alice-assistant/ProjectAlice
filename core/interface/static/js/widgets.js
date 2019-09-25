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

    })

});