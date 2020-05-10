$(function () {

	let $widgets = $('.widget');
	/* Edit Position and Size of Widgets */
	$widgets.draggable({
		containment: '.widgetsPane',
		grid       : [10, 10],
		disabled   : true
	}).css('position', 'absolute');

	$widgets.resizable({
		grid    : 10,
		disabled: true
	});

	$widgets.each(function () {
		initIndexers($(this));
	});

	/* Toolbar Functions */
	$('#toolbarToggleShow').on('click touchstart', function () {
		$('#toolbar_full').show();
		$('#toolbar_toggle').hide();
		let widget = $('.widget');
		widget.css('outline', "2px var(--accent) dotted");
		widget.draggable('enable');
		widget.resizable('enable');
		$('.zindexer').show();
	});

	$('#toolbarToggleHide').on('click touchstart', function () {
		$('#toolbar_full').hide();
		$('#toolbar_toggle').show();
		let widget = $('.widget');
		widget.css('outline', 'none');
		widget.draggable('disable');
		widget.resizable('disable');
		$('.zindexer').hide();

		let data = {};
		widget.each(function () {
			data[$(this).attr('id')] = {
				id    : $(this).attr('id'),
				x     : $(this).position().left,
				y     : $(this).position().top,
				w     : $(this).outerWidth(),
				h     : $(this).outerHeight(),
				zindex: $(this).css('z-index')
			}
		});

		$.ajax({
			url        : '/home/saveWidgets/',
			data       : JSON.stringify(data),
			contentType: 'application/json',
			dataType   : 'json',
			type       : 'POST'
		});
	});

	$('.widgetOptions').dialog({
		autoOpen : false,
		draggable: false,
		width    : '60%',
		height   : 600,
		modal    : true,
		resizable: false,
		close    : function () {
			let tab = $('#config_tabs');
			tab.find('#WidgetSettings').html("");
			tab.find('#GraphicSettings').html("");
		}
	});

	$('#addWidgetDialog').dialog({
		autoOpen : false,
		draggable: false,
		width    : 600,
		height   : 600,
		modal    : true,
		resizable: false,
		close    : function () {
			location.reload();
		}
	});


	$('#removeWidget').on('click touchstart', function () {
		$('.widgetDelete').show();
		$('#toolbar_checkmark').show();
		$('#toolbar_full').hide();
		return false;
	});

	$('#addWidget').on('click touchstart', function () {
		$('#addWidgetDialog').dialog('open');
		return false;
	});

	$('#configToggle').on('click touchstart', function () {
		$('.widgetConfig').show();
		$('#toolbar_checkmark').show();
		$('#toolbar_full').hide();
		return false;
	});

	$('#cinemaToggle').on('click touchstart', function () {
		$('nav').toggle();
		$('#toolbar_full').hide();
		$('header').toggle();
		let widget = $('.widget');
		widget.css('outline', 'none');
		widget.draggable('disable');
		widget.resizable('disable');
		$('.zindexer').hide();
	});

	$('#widgetCheck').on('click touchstart', function () {
		$('#toolbar_checkmark').hide();
		$('.widgetDelete').hide();
		$('.widgetConfig').hide();
		location.reload();
		return false;
	});

	/*=================== Functions for the single widgets ======================*/
	/* Remove the selected widget */
	$('.widgetDelete').on('click touchstart', function () {
		if ($(this).parents('.widget').length > 0) {
			$.post('/home/removeWidget/', {id: $(this).parent().attr('id')});
			$(this).parent().remove();
		}
		return false;
	});

	function prepareConfigTab(parent, tab) {
		$.post('/home/read' + tab + '/', {id: parent.attr('id')})
			.done(function (data) {
				let dialogContainer = $('#config_tabs');
				// No configuration exists
				if (jQuery.isEmptyObject(data) == true) {
					dialogContainer.find('#' + tab).html($('#langNoConf').text());
					dialogContainer.dialog('open');
					return;
				}

				// build configuration
				let newForm = "<form action='/home/save" + tab + "/' id='" + tab + "Form' method='post' autocomplete='off' novalidate target=''>";
				newForm += "<input type='hidden' name='id' value='" + parent.attr('id') + "'/>";
				jQuery.each(data, function (i, val) {
					let input = '<input class="configInput widgetConfigInput" type="text" name="' + i + '" value="' + val + '"/></div>';
					if (i == 'background') {
						if (!val) {
							val = getComputedStyle(document.documentElement).getPropertyValue('--windowBG').trim();
						}
						input = '<input class="configInput widgetConfigInput" type="color" name="' + i + '" value="' + val + '"/></div>';
					} else if (i == 'color') {
						if (!val) {
							val = getComputedStyle(document.documentElement).getPropertyValue('--text').trim();
						}
						input = '<input class="configInput widgetConfigInput" type="color" name="' + i + '" value="' + val + '"/></div>';
					} else if (i == 'background-opacity') {
						input = '<input class="configInput widgetConfigInput" type="number" step="0.1" min="0.0" max="1" name="' + i + '" value="' + val + '"/></div>';
					} else if (i == 'font-size') {
						input = '<input class="configInput widgetConfigInput" type="number" step="0.1" min="0.1" max="5" name="' + i + '" value="' + val + '"/></div>';
					} else if (i == 'titlebar') {
						let checked = val === 'True' ? ' checked' : '';
						input = '<input class="configInput widgetConfigInput" type="checkbox" name="' + i + '" value="True"' + checked + '/></div><span class="slider round"></span>';
						/* Make sure unticked check boxes send off data too */
						input += '<input type="hidden" name="' + i + '" value="False"/></div>';
					}

					newForm += "<div class='configLine'><label class='configLabel'>" + i + "</label>" + input;
				});
				newForm += "<div class='buttonLine'><input id='submitConfig' class='button' type='submit' value='" + $('#langConfSave').text() + "'></div>";
				dialogContainer.find('#' + tab).html(newForm);

				$(":checkbox").checkToggler();

				// perform submit/save of the form without switching page
				let form = $('#' + tab + 'Form');
				let saveButton = form.find('#submitConfig');
				// noinspection JSDeprecatedSymbols
				form.submit(function (event) {
					saveButton.val($('#langConfSaving').text());
					saveButton.addClass('saving');
					$.post(form.attr('action'),
						form.serialize()).done(function () {
						saveButton.val($('#langConfSaved').text());
						saveButton.addClass('saved');
					})
						.fail(function () {
							saveButton.val($('#langConfSaveFailed').text());
							saveButton.addClass('saveFailed');
						}).always(
						function () {
							saveButton.removeClass('saving');
						});
					event.preventDefault();
				});

				// change button back to save if something was changed
				$('.widgetConfigInput').on('change', function () {
					saveButton.val($('#langConfSave').text());
					saveButton.removeClass('saved');
					saveButton.removeClass('saveFailed');
				});
				dialogContainer.dialog('open');
			});
	}

	/* Opening of widget specific settings */
	$('.widgetConfig').on('click touchstart', function () {
		if ($(this).parents('.widget').length > 0) {
			let parent = $(this).parent();
			prepareConfigTab(parent, 'WidgetConfig');
			prepareConfigTab(parent, 'WidgetCustStyle');
		}
		return false;
	});

	$('.addWidgetCheck').on('click touchstart', function () {
		if ($(this).parents('.addWidgetLine').length > 0) {
			$.post('/home/addWidget/', {id: $(this).parent().attr('id')});
			$(this).parent().remove();
		}
		return false;
	});

});
