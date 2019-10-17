$(document).tooltip();

$(function () {

	let storeLoaded = false;

	function checkInstallStatus(module) {
		$.ajax({
			url: '/modules/checkInstallStatus',
			data: {
				'module': module
			},
			type: 'POST'
		}).done(function (status) {
			status = JSON.stringify(status).trim();
			if (status === JSON.stringify('installed')) {
				$('#' + module + 'InstallTile').remove();
			} else if (status === JSON.stringify('failed') || status === JSON.stringify('unknown')) {
				$('#' + module).children('.moduleStoreModuleWaitAnimation').hide();
				$('#' + module).children('.moduleStoreModuleDownloadFail').css('display', 'flex');
			} else {
				setTimeout(function () {
					checkInstallStatus(module);
				}, 5000);
			}
		}).fail(function () {
			setTimeout(function () {
				checkInstallStatus(module);
			}, 1000);
		});
	}

	function addToStore(installer) {
		if ($('#modulesPane').find('#' + installer['name'] + '-' + installer['author']).length === 0) {
			let $tile = $('<div class="moduleStoreModuleTile" id="' + installer['name'] + 'InstallTile">' +
				'<div class="modulesStoreModuleTitle">' + installer['name'] + '</div>' +
				'<div class="modulesStoreModuleAuthor"><i class="fas user-cog"></i> ' + installer['author'] + '</div>' +
				'<div class="modulesStoreModuleVersion"><i class="fas fa-code-branch" style="margin-right: 3px;"></i> ' + installer['version'] + '</div>' +
				'<div class="modulesStoreModuleCategory"><i class="fas fa-bookmark"></i> ' + installer['category'] + '</div>' +
				'<div class="moduleStoreModuleDescription">' + installer['desc'] + '</div>' +
				'<div class="moduleStoreModuleWaitAnimation"><i class="fas fa-spinner fa-spin"></i></div>' +
				'<div class="moduleStoreModuleDownloadFail"><i class="fas fa-exclamation-triangle"></i></div>' +
				'</div>');

			let $button = $('<div class="moduleStoreModuleDownload moduleStoreModuleDownloadButton" data-module="' + installer['name'] + '"><i class="fas fa-download"></i></div>');
			$button.on('click touchstart', function () {
				$button.hide();
				$button.parent().children('.moduleStoreModuleWaitAnimation').css('display', 'flex');
				$.ajax({
					url: '/modules/install',
					data: {
						module: $(this).data('module')
					},
					type: 'POST'
				}).done(function () {
				}).then(function () {
					setTimeout(function () {
						checkInstallStatus(installer['name']);
					}, 10000);
				});
			});

			$tile.append($button);
			$('#modulesStore').append($tile);
		}
	}

	function loadStoreData() {
		$.ajax({
			type: 'GET',
			dataType: 'JSON',
			url: 'https://api.github.com/search/code?q=extension:install+repo:project-alice-powered-by-snips/ProjectAliceModules',
			success: function (data) {
				$.each(data['items'], function (index, searchResult) {
					$.ajax({
						type: 'GET',
						dataType: 'JSON',
						url: searchResult['url'],
						headers: {
							'accept': 'application/vnd.github.VERSION.raw'
						}
					}).done(function (installer) {
						addToStore(installer);
					});
				});
			}
		});
		storeLoaded = true;
	}

	$('[id^=toggle_]').on('click touchstart', function () {
		$.ajax({
			url: '/modules/toggle',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
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

	$('.moduleSettings').on('click touchstart', function () {
		$('#config_for_' + $(this).attr('data-forModule')).dialog('open');
	});

	$('.moduleViewIntents').on('click touchstart', function () {
		$(this).parent('.moduleDefaultView').css('display', 'none');
		$(this).parent().parent().children('.moduleIntentsView').css('display', 'flex');
	});

	$('.moduleIntentsViewCloseButton').on('click touchstart', function () {
		$(this).parent().parent().children('.moduleDefaultView').css('display', 'flex');
		$(this).parent('.moduleIntentsView').css('display', 'none');
	});

	$('.moduleButton').on('click touchstart', function () {
		$.ajax({
			url: '/modules/delete',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
		});
	});

	$('#openModuleStore').on('click touchstart', function () {
		if (!storeLoaded) {
			loadStoreData();
		}

		$('#modulesPane').hide();
		$('#modulesStore').css('display', 'flex');
		$('#openModuleStore').hide();
		$('#closeModuleStore').show();
	});

	$('#closeModuleStore').on('click touchstart', function () {
		location.reload();
	});
});
