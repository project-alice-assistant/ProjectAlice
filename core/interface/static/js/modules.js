$( document ).tooltip();

$(function(){
    let API_URL = 'https://api.github.com/repositories/193512918/contents/PublishedModules';

    let modules = [];

    function refreshStore() {
        $.ajax({
            dataType: 'json',
            url: API_URL,
            success: function (data) {
                $.each(data, function (author) {
                    author = data[author];
                    if (author['type'] === 'dir') {
                        $.ajax({
                            dataType: 'json',
                            url: author['url'],
                            success: function (subdata) {
                                $.each(subdata, function (module) {
                                    module = subdata[module];
                                    if (module['type'] === 'dir') {
                                        modules.push(module);
                                    }
                                })
                            }
                        })
                    }
                });
            }
        });
    }

    function displayStoreContent() {
        modules.forEach(function(module) {
            let $tile = $('<div class="moduleStoreModuleTile">' + module['name'] + '</div>');
            $('#modulesStore').append($tile)
        });
    }

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

    $('#openModuleStore').on('click', function(){
        $('#modulesPane').hide();
        $('#modulesStore').css('display', 'flex');
        $('#openModuleStore').hide();
        $('#closeModuleStore').show();
        displayStoreContent();
    });

    $('#closeModuleStore').on('click', function(){
        $('#modulesPane').css('display', 'flex');
        $('#modulesStore').hide();
        $('#openModuleStore').show();
        $('#closeModuleStore').hide();
    });

    refreshStore()
});