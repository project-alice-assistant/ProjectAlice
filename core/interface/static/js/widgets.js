$(function(){
    $('.widget').draggable({
        containment: '.widgetsPane',
        snap: '.widget',
        grid: [10, 10]
    });

    $('.widget').position().css(function() {
        return {top: $(this).attr('data-posy'), left: $(this).attr('data-posx')}
    });

    console.log($('.widget').attr('data-posx'));

    $('.widgetsPane').droppable({

        drop: function(event, ui) {
            let posx = $(ui.draggable).position().left;
            let posy = $(ui.draggable).position().top;
        }

    })

});