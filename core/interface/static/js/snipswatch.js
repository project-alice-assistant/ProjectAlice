$(function() {
    function refreshData(type) {
        let container = $('#console');
        $.get('/snipswatch/' + type, function(data) {
            for (let i = 0; i < data.data.length; i++) {
                container.append(
                    '<span class="logLine">' + data.data[i] + '</span>'
                );
            }
        }).always(function(data) {
            if ($('#checkedCheckbox').is(':visible')) {
                container.scrollTop(container.prop('scrollHeight'))
            }
        });
    }

        $('#checkedCheckbox').on('click', function() {
        $(this).hide();
        $('#emptyCheckbox').show();
    });

    $('#emptyCheckbox').on('click', function() {
        $(this).hide();
        $('#checkedCheckbox').show();
    });


    refreshData('refresh');

    setInterval(function() {
        refreshData('update')
    }, 500)
});