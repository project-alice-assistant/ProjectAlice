$( document ).tooltip();

$(function(){
    let module;

	$('[id^=toggle_]').on('click', function () {
		$.ajax({
            url: '/modules/toggle',
            data: {
                id: $(this).attr('id')
            },
            type: 'POST',
            success: function() {
                location.reload();
            }
        });
	});

	$('[id^=config_for_]').dialog({
        autoOpen: false,
        draggable: false,
        width: 600,
        height: 600,
        modal: true,
        resizable: false
    });

	$('.moduleSettings').on('click', function() {
        $('#config_for_' + $(this).attr('data-forModule')).dialog('open');
    });

	$('.moduleViewIntents').on('click', function() {
	    $(this).parent('.moduleDefaultView').css('display', 'none');
        $(this).parent().parent().children('.moduleIntentsView').css('display', 'flex');
    });

    $('.moduleIntentsViewCloseButton').on('click', function() {
        $(this).parent().parent().children('.moduleDefaultView').css('display', 'flex');
	    $(this).parent('.moduleIntentsView').css('display', 'none');
    });

    $('.moduleButton').on('click', function(){
        $.ajax({
            url: '/modules/delete',
            data: {
                id: $(this).attr('id')
            },
            type: 'POST',
            success: function() {
                location.reload();
            }
        });
    });
});