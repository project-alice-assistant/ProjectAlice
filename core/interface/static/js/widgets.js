$(function(){
    $('.widget').draggable({
        containment: '.widgetsPane',
        snap: '.widget',
        grid: [10, 10]
    });


    $('.widgetsPane').droppable({

        drop: function(event, ui) {
            let posx = $(ui.draggable).position().left;
            let posy = $(ui.draggable).position().top;

            $.ajax({
                url: '/home/saveWidgetPos',
                data: {x: posx, y: posy},
                type: 'POST'
            })
        }

    })

});