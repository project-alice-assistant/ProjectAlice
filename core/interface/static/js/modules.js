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
	    $(this).parent().css('display', 'none');
        $(this).parent().parent().children('.moduleIntentsView').css('display', 'flex');
    })
});