$(function () {

/* Edit Position and Size of Widgets */
	$('.widgetsPane').droppable({
		drop: function (event, ui) {
			let arr = [];

			$('.widgetsPane').children().each(function () {
				arr.push($(this).attr('id'));
			});

			$.ajax({
				contentType: 'application/json',
				url: '/home/saveWidgetPosition/',
				data: JSON.stringify({
					id: $(ui.draggable).attr('id'),
					x: $(ui.draggable).position().left,
					y: $(ui.draggable).position().top,
					index: $('.widget').length,
					order: arr
				}),
				type: 'POST'
			});
		}
	});
	let widget = $('.widget');

	widget.draggable({
		containment: '.widgetsPane',
		snap: '.widget',
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
      		$.ajax({
				contentType: 'application/json',
				url: '/home/saveWidgetSize/',
				data: JSON.stringify({
					id: $(this).attr('id'),
					w: $(this).outerWidth(),
					h: $(this).outerHeight()
				}),
				type: 'POST'
			});
		}
    });

/* Toolbar Functions */
	$('#toolbarToggleShow').on('click touchstart', function(){
		$('#toolbar_full').show();
		$('#toolbar_toggle').hide();
		let widget = $('.widget');
		widget.draggable('enable');
		widget.resizable('enable');
	});

	$('#toolbarToggleHide').on('click touchstart', function(){
		$('#toolbar_full').hide();
		$('#toolbar_toggle').show();
		let widget = $('.widget');
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

	/* Functions for the single widgets */
	$('.widgetDelete').on('click touchstart', function () {
		if ($(this).parents('.widget').length > 0) {
			$.ajax({
				url: '/home/removeWidget/',
				data: {
					id: $(this).parent().attr('id')
				},
				type: 'POST'
			});
			$(this).parent().parent().remove();
		}
		return false;
	});

	$('.widgetConfig').on('click touchstart', function () {
		if ($(this).parents('.widget').length > 0) {
			$.ajax({
				url: '/home/readWidgetConfig/',
				data: {
					id: $(this).parent().attr('id')
				},
				type: 'POST',
				success: (data) => {
					console.log(data);
					let newForm = "<form action='/home/saveWidgetConfig/' name='config_for_{{ skillName }}' method='post' autocomplete='off' novalidate>";
					newForm += "<input type='hidden' name='id' value='" + $(this).parent().attr('id') + "'/>";
					jQuery.each(data, function (i, val) {
						newForm += "<div class='configLine'><label class='configLabel'>" + i + "</label><input class='configInput' id='i' value='" + val + "'/></div>";
					});
					newForm += "<div class='buttonLine'><input class='button' type='submit' value='Save'></div>";
					let tab = $('#config_tabs');
					tab.find('#WidgetSettings').html(newForm);
					tab.dialog("open");
				}
			});
		}
		return false;
	});

	$('.addWidgetCheck').on('click touchstart', function () {
		if ($(this).parents('.addWidgetLine').length > 0) {
			$.ajax({
				url: '/home/addWidget/',
				data: {
					id: $(this).parent().parent().attr('id')
				},
				type: 'POST'
			});
			$(this).parent().remove();
		}
		return false;
	});

	function loadConfig(skill) {
		return skill
	}


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
