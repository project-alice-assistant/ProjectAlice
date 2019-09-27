$( document ).tooltip();

$(function(){
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

	$('.moduleViewIntents').on('click', function() {
	    $(this).parent('.moduleDefaultView').css('display', 'none');
        $(this).parent().parent().children('.moduleIntentsView').css('display', 'flex');
    });

    $('.moduleIntentsViewCloseButton').on('click', function() {
        $(this).parent().parent().children('.moduleDefaultView').css('display', 'flex');
	    $(this).parent('.moduleIntentsView').css('display', 'none');
    });
});