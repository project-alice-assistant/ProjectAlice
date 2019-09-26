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
	})
});