$(function () {

/* Edit Position and Size of Widgets */
	$('.widgetsPane').droppable({
		drop: function (event, ui) {
			let arr = [];

			$('.widgetsPane').children().each(function () {
				arr.push($(this).attr('id'));
			});

			$.post('/home/saveWidgetPosition/',
					{
						id: $(ui.draggable).attr('id'),
						x: $(ui.draggable).position().left,
						y: $(ui.draggable).position().top,
						index: $('.widget').length,
						order: arr
					}
			);
		}
	});

	let widget = $('.widget');

	widget.draggable({
		containment: '.widgetsPane',
		grid: [10, 10],
		disabled: true,
		start: function (event, ui) {
			$(this).parent().append($(this));
			$(this).css('z-index', $('.widgetsPane').children().length);
		}
	}).css('position', 'absolute');

	widget.resizable({
      	grid: 10,
		disabled: true,
		stop : function(event,ui) {
      		$.post('/home/saveWidgetSize/',{
					id: $(this).attr('id'),
					w: $(this).outerWidth(),
					h: $(this).outerHeight()
				});
      		}
    });

/* Toolbar Functions */
	$('#toolbarToggleShow').on('click touchstart', function(){
		$('#toolbar_full').show();
		$('#toolbar_toggle').hide();
		let widget = $('.widget');
		widget.css('outline', "2px var(--accent) dotted");
		widget.draggable('enable');
		widget.resizable('enable');
	});

	$('#toolbarToggleHide').on('click touchstart', function(){
		$('#toolbar_full').hide();
		$('#toolbar_toggle').show();
		let widget = $('.widget');
		widget.css('outline', "none");
		widget.draggable('disable');
		widget.resizable('disable');
	});

	$('.widgetOptions').dialog({
		autoOpen: false,
		draggable: false,
		width: 600,
		height: 600,
		modal: true,
		resizable: false,
		close: function() {
			let tab = $('#config_tabs');
			tab.find('#WidgetSettings').html("");
			tab.find('#GraphicSettings').html("");
    	}
	});

	$('#addWidgetDialog').dialog({
		autoOpen: false,
		draggable: false,
		width: 600,
		height: 600,
		modal: true,
		resizable: false,
		close: function () {
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
			$.post('/home/removeWidget/',{ id: $(this).parent().attr('id')});
			$(this).parent().remove();
		}
		return false;
	});

	function prepareConfigTab(parent, tab){
		$.post('/home/read' + tab + '/',  { id: parent.attr('id') } )
			.done(function(data){
				let dialogContainer = $('#config_tabs');
				// No configuration exists
				if(jQuery.isEmptyObject(data) == true ){
					dialogContainer.find('#'+tab).html("No config for this widget!");
					dialogContainer.dialog("open");
					return;
				}

				// build configuration
				let newForm = "<form action='/home/save"+tab+"/' id='"+tab+"Form' method='post' autocomplete='off' novalidate target=''>";
				newForm += "<input type='hidden' name='id' value='" + parent.attr('id') + "'/>";
				jQuery.each(data, function (i, val) {
					let input = '<input class="configInput widgetConfigInput" type="text" name="' + i + '" value="' + val + '"/></div>';
					if (i === 'background' || i === 'color') {
						input = '<input class="configInput widgetConfigInput" type="color" name="' + i + '" value="' + val + '"/></div>';
					} else if (i === 'background-opacity') {
						input = '<input class="configInput widgetConfigInput" type="number" step="0.1" min="0.0" max="1" name="' + i + '" value="' + val + '"/></div>';
					} else if (i === 'font-size') {
						input = '<input class="configInput widgetConfigInput" type="number" step="0.1" min="0.1" max="5" name="' + i + '" value="' + val + '"/></div>';
					} else if (i === 'titlebar') {
						let checked = ' checked' ? val === 'True' : '';
						input = '<input class="configInput widgetConfigInput" type="checkbox" name="' + i + '" value="True"' + checked + '/></div><span class="slider round"></span>';
						/* Make sure unticked check boxes send off data too */
						input += '<input type="hidden" name="' + i + '" value="False"/></div>';
					}
					newForm += "<div class='configLine'><label class='configLabel'>" + i + "</label>" + input;
				});
				newForm += "<div class='buttonLine'><input id='submitConfig' class='button' type='submit' value='Save'></div>";
				dialogContainer.find('#'+tab).html(newForm);

				$(":checkbox").checkToggler();

				// perform submit/save of the form without switching page
				let form = $('#'+tab+'Form');
				let saveButton = form.find('#submitConfig');
				form.submit(function( event ) {
					saveButton.val("Saveing");
					saveButton.addClass("saveing");
					$.post(form.attr("action"),
							form.serialize()).done(function() {
								saveButton.val("Saved");
								saveButton.addClass("saved");
							  })
							  .fail(function() {
								saveButton.val("Save failed");
								saveButton.addClass("saveFailed");
							  }).always(
								function () {
									saveButton.removeClass("saveing");
								});
					event.preventDefault();
				});

				// change button back to save if something was changed
				$('.widgetConfigInput').change(function() {
					saveButton.val("Save");
					saveButton.removeClass("saved");
					saveButton.removeClass("saveFailed");
				});
			dialogContainer.dialog("open");
		});
	}
	/* Opening of widget specific settings */
	$('.widgetConfig').on('click touchstart', function () {
		if ($(this).parents('.widget').length > 0) {
			let parent = $(this).parent();
			prepareConfigTab(parent,'WidgetConfig');
			prepareConfigTab(parent,'WidgetCustStyle');
		}
		return false;
	});



	$('.addWidgetCheck').on('click touchstart', function () {
		if ($(this).parents('.addWidgetLine').length > 0) {
			$.post('/home/addWidget/', { id: $(this).parent().attr('id')});
			$(this).parent().remove();
		}
		return false;
	});


	/*TODO duplicate from admin.js*/
	let $defaultTab = $('#widgetConfTabContainer ul li:first');
		$('.tabsContent').children().each(function () {
		if ($(this).attr('id') == $defaultTab.data('for')) {
			$(this).show();
		}
		else {
			$(this).hide();
		}
	});

	$('.tab').on('click touchstart', function () {
		let target = $(this).data('for');
		$(this).addClass('activeTab');

		$('#widgetConfTabContainer ul li').each(function () {
			if ($(this).data('for') != target) {
				$(this).removeClass('activeTab');
			}
		});

		$('.tabsContent').children().each(function () {
			if ($(this).attr('id') == target) {
				$(this).show();
			}
			else {
				$(this).hide();
			}
		});
		return false;
	});
});
