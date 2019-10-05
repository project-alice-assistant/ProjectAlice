$(document).tooltip();

$(function(){
    function loadStoreData() {
        $.ajax({
            type: 'GET',
            dataType: 'JSON',
            url: 'https://api.github.com/search/code?q=extension:install+repo:project-alice-powered-by-snips/ProjectAliceModules',
            success: function(data) {
                $.each(data['items'], function (index, searchResult) {
                    $.ajax({
                        type: 'GET',
                        dataType: 'JSON',
                        url: searchResult['url'],
                        headers: {
                            'accept': 'application/vnd.github.VERSION.raw'
                        },
                        success: function (installer) {
                            addToStore(installer);
                        }
                    })
                });
            }
        });
    }

    function addToStore(installer) {
        if ($('#modulesPane').find('#' + installer['name'] + '-' + installer['author']).length === 0) {
            let $tile = $('<div class="moduleStoreModuleTile">' +
                '<div class="modulesStoreModuleTitle">' + installer['name'] + '</div>' +
                '<div class="modulesStoreModuleAuthor"><i class="fas fa-at"></i> ' + installer['author'] + '</div>' +
                '<div class="modulesStoreModuleVersion"><i class="fas fa-code-branch"></i> ' + installer['version'] + '</div>' +
                '<div class="modulesStoreModuleCategory"><i class="fas fa-bookmark"></i> ' + installer['category'] + '</div>' +
                '<div class="moduleStoreModuleDescription">' + installer['desc'] + '</div>' +
                '<div class="moduleStoreModuleDownload moduleStoreModuleWaitAnimation"><i class="fas fa-spinner fa-spin"></i></div>' +
                '<div class="moduleStoreModuleDownload moduleStoreModuleDownloadButton"><i class="fas fa-download"></i></div>' +
                '</div>');

            $tile.on('click', function(){
                $.ajax({
                    url: '/modules/install',
                    data: {
                        module: installer['name']
                    },
                    type: 'POST',
                    success: function() {
                        $('.moduleStoreModuleWaitAnimation').css('display', 'flex');
                        $('.moduleStoreModuleDownloadButton').css('display', 'none');
                    }
                });
            });

            $('#modulesStore').append($tile);
        }
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
    });

    $('#closeModuleStore').on('click', function(){
        $('#modulesPane').css('display', 'flex');
        $('#modulesStore').hide();
        $('#openModuleStore').show();
        $('#closeModuleStore').hide();
    });

    loadStoreData();
});