$(document).tooltip();

$(function () {

	let $floorPlan = $('#floorPlan');
	let buildingMode = false;
	let paintingMode = false;
	let selectedTexture = '';

	function loadHouse() {
		let $data = JSON.parse($('#houseData').text());
		console.log($data[0]['name']);
	}

	function onClickZone($element) {
		if (buildingMode) {
			let $newWall = $('<div class="floorPlan-Zone-Wall"></div>');
			$newWall.resizable({containment: 'parent'}).draggable({containment: 'parent'});

			$newWall.on('click touchstart', function (e) {
				e.preventDefault();
				$('.floorPlan-Zone-Wall').resizable({containment: 'parent'}).draggable({containment: 'parent'});
			})

			$element.append($newWall);
		} else if (paintingMode) {
			$element.attr('class', 'floorPlan-Zone');
			$element.addClass(selectedTexture);
			$element.attr('data-texture', selectedTexture);
		}
	}

	function saveHouse() {
		let data = {};
		$floorPlan.children('.floorPlan-Zone').each(function(index) {
			data[index] = {
				'name': $(this).data('name'),
				'x': $(this).position().left,
				'y': $(this).position().top,
				'width': $(this).width(),
				'height': $(this).height(),
				'texture': $(this).data('texture')
			};
		});

		$.ajax({
			url: '/myhome/',
			type: 'PUT',
			data: {
				'data': JSON.stringify(data)
			}
		});
	}

	$('#toolbarToggleShow').on('click touchstart', function() {
		$('#toolbar_full').show();
		$('#toolbar_toggle').hide();
		$floorPlan.addClass('floorPlanEditMode');
		$floorPlan.removeClass('floorPlanEditMode-AddingRoom');
		buildingMode = false;
		paintingMode = false;
		$('#painterTiles').hide();

		$('.floorPlan-Zone').resizable().draggable({containment: 'parent'});
	});

	$('#toolbarToggleHide').on('click touchstart', function() {
		$('#toolbar_full').hide();
		$('#toolbar_toggle').show();
		buildingMode = false;
		paintingMode = false;
		$floorPlan.removeClass('floorPlanEditMode');
		$floorPlan.removeClass('floorPlanEditMode-AddingRoom');

		/*$('.floorPlan-Zone').resizable('destroy').draggable('destroy');
		$('.floorPlan-Zone-Wall').resizable('destroy').draggable('destroy');*/

		saveHouse();
	});

	$('#addZone').on('click touchstart', function() {
		$('#floorPlan').addClass('floorPlanEditMode-AddingRoom');
	})

	$floorPlan.on('click touchstart', function(e) {
		if (!$(this).hasClass('floorPlanEditMode-AddingRoom')) {
			return;
		}

		let zoneName = prompt('Please name the new zone');
		if (zoneName != null && zoneName != '') {
			let $newZone = $('<div class="floorPlan-Zone" data-name="' + zoneName + '" data-texture="">' + zoneName + '</div>');
			let posx = $(this).offset().left;
			let posy = $(this).offset().top;
			$newZone.offset({left: e.pageX - posx, top: e.pageY - posy});
			$newZone.resizable().draggable({containment: 'parent'});

			$newZone.on('click touchstart', function() {
				onClickZone($(this));
			})

			$(this).append($newZone);
		}

		$(this).removeClass('floorPlanEditMode-AddingRoom');
	})

	$('#builder').on('click touchstart', function() {
		paintingMode = false;
		$('#painterTiles').hide();
		if (!buildingMode) {
			buildingMode = true;

			$floorPlan.removeClass('floorPlanEditMode');
			$floorPlan.removeClass('floorPlanEditMode-AddingRoom');
			$('.floorPlan-Zone').resizable('destroy').draggable('destroy');
			$('.floorPlan-Zone-Wall').resizable({containment: 'parent'}).draggable({containment: 'parent'});
		} else {
			buildingMode = false;
			$('.floorPlan-Zone-Wall').resizable('destroy').draggable('destroy');
		}
	})

	$('#painter').on('click touchstart', function() {
		buildingMode = false;
		if (!paintingMode) {
			paintingMode = true;
			$('#painterTiles').css('display', 'flex');

			$('.floorPlan-Zone').resizable('destroy').draggable('destroy');
			$('.floorPlan-Zone-Wall').resizable('destroy').draggable('destroy');
		} else {
			paintingMode = false;
			$('#painterTiles').hide();
		}
	})

	$('.floorPlan-Zone').on('click touchstart', function() {
		onClickZone($(this));
	})

	$('.floorPlan-Zone-Wall').on('click touchstart', function(e) {
		e.preventDefault();
		$('.floorPlan-Zone-Wall').resizable({containment: 'parent'}).draggable({containment: 'parent'});
	})

	for (let i = 1; i <= 2; i++) {
		let $tile = $('<div class="floorPlan-Zone-tile floor-' + i + '"></div>')

		$tile.on('click touchstart', function() {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-Zone-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedTexture = 'floor-' + i;
			} else {
				$(this).removeClass('selected');
			}
		})

		$('#painterTiles').append($tile);
	}

	loadHouse();
});
