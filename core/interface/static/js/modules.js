$(document).tooltip();

$(function () {
	let selectedModulesToDownload = [];

	function checkInstallStatus(module) {
		$.ajax({
			url: '/modules/checkInstallStatus/',
			data: {
				'module': module
			},
			type: 'POST'
		}).done(function (status) {
			status = JSON.stringify(status).trim();
			if (status === JSON.stringify('installed')) {
				$('#' + module + 'InstallTile').remove();
			} else if (status === JSON.stringify('failed') || status === JSON.stringify('unknown')) {
				$('#' + module + 'InstallTile').children('.moduleStoreModuleWaitAnimation').hide();
				$('#' + module + 'InstallTile').children('.moduleStoreModuleDownloadFail').css('display', 'flex');
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
				'<div class="modulesStoreModuleCategory"><i class="fas fa-tags"></i> ' + installer['category'] + '</div>' +
				'<div class="moduleStoreModuleDescription">' + installer['desc'] + '</div>' +
				'<div class="moduleStoreModuleSelected moduleStoreModuleButtonAnimation"><i class="fas fa-shopping-cart"></i></div>' +
				'<div class="moduleStoreModuleWaitAnimation moduleStoreModuleButtonAnimation"><i class="fas fa-spinner fa-spin"></i></div>' +
				'<div class="moduleStoreModuleDownloadFail moduleStoreModuleButtonAnimation"><i class="fas fa-exclamation-triangle"></i></div>' +
				'</div>');

			let $button = $('<div class="moduleStoreModuleDownload moduleStoreModuleDownloadButton"><i class="fas fa-download"></i></div>');
			$button.on('click touchstart', function () {
				$button.hide();
				$button.parent().children('.moduleStoreModuleSelected').css('display', 'flex');
				selectedModulesToDownload.push({'module': installer['name'], 'author': installer['author']});
				$('#applyModuleStore').show();
				return false;
			});

			$tile.append($button);
			$('#modulesStore').append($tile);
		}
	}

	function loadStoreData() {
		$.ajax({
			url: '/modules/loadStoreData/',
			type: 'POST'
		}).done(function (answer){
			$('#moduleStoreWait').hide();
			$.each(answer, function(moduleName, installer){
				addToStore(installer);
			});
		});
	}

	$('#applyModuleStore').on('click touchstart', function () {
		$('.moduleStoreModuleSelected').hide();
		$(this).hide();
		$.each(selectedModulesToDownload, function (index, module) {
			$('#' + module['module'] + 'InstallTile').children('.moduleStoreModuleWaitAnimation').css('display', 'flex');
		});

		$.ajax({
			url: '/modules/installModules/',
			data: JSON.stringify(selectedModulesToDownload),
			contentType: 'application/json',
			dataType: 'json',
			type: 'POST'
		}).done(function () {
		}).then(function () {
			$.each(selectedModulesToDownload, function (index, module) {
				setTimeout(function () {
					checkInstallStatus(module['module']);
				}, 10000);
			});
		});
		return false;
	});

	$('[id^=toggle_]').on('click touchstart', function () {
		$.ajax({
			url: '/modules/toggleModule/',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
		});
		return false;
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
		return false;
	});

	$('.moduleViewIntents').on('click touchstart', function () {
		$(this).parent('.moduleDefaultView').css('display', 'none');
		$(this).parent().parent().children('.moduleIntentsView').css('display', 'flex');
		return false;
	});

	$('.moduleIntentsViewCloseButton').on('click touchstart', function () {
		$(this).parent().parent().children('.moduleDefaultView').css('display', 'flex');
		$(this).parent('.moduleIntentsView').css('display', 'none');
		return false;
	});

	$('[id^=delete_]').on('click touchstart', function () {
		$.ajax({
			url: '/modules/deleteModule/',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
		});
		return false;
	});

	$('#openModuleStore').on('click touchstart', function () {
		loadStoreData();
		$('#modulesPane').hide();
		$('#modulesStore').css('display', 'flex');
		$('#openModuleStore').hide();
		$('#closeModuleStore').show();
		return false;
	});

	$('#closeModuleStore').on('click touchstart', function () {
		location.reload();
		return false;
	});

	$('#applyModuleStore').hide();
});
