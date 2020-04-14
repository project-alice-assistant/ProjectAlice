$(document).tooltip();

$(function () {

	let $floorPlan = $('#floorPlan');
	let editMode = false;

	let moveMode = false;
	let zoneMode = false;
	let buildingMode = false;
	let paintingMode = false;
	let decoratorMode = false;

	let selectedTexture = '';
	let selectedDeco = '';

	function loadHouse() {
		$.ajax({
			url : '/myhome/load/',
			type: 'GET'
		}).done(function(response) {
			let $data = JSON.parse(response);
			$.each($data, function (i, zone) {
				let $zone = newZone(zone);
				$.each(zone['walls'], function(ii, wall) {
					newWall($zone, wall);
				});
				$.each(zone['deco'], function(iii, deco) {
					newDeco($zone, deco);
				});
			})
		});
	}

	function saveHouse() {
		let data = {};
		$floorPlan.children('.floorPlan-Zone').each(function () {
			let zoneName = $(this).data('name');
			data[zoneName] = {
				'name'   : $(this).data('name'),
				'x'      : $(this).position().left,
				'y'      : $(this).position().top,
				'width'  : $(this).width(),
				'height' : $(this).height(),
				'texture': $(this).data('texture')
			};

			data[zoneName]['walls'] = [];
			$(this).children('.floorPlan-Wall').each(function() {
				data[zoneName]['walls'].push({
					'x'      : $(this).position().left,
					'y'      : $(this).position().top,
					'width'  : $(this).width(),
					'height' : $(this).height()
				})
			});

			data[zoneName]['deco'] = [];
			$(this).children('.floorPlan-Deco').each(function() {
				data[zoneName]['deco'].push({
					'x'      : $(this).position().left,
					'y'      : $(this).position().top,
					'width'  : $(this).width(),
					'height' : $(this).height(),
					'texture': $(this).data('texture')
				})
			});
		});

		$.ajax({
			url : '/myhome/',
			type: 'PUT',
			data: {
				'data': JSON.stringify(data)
			}
		});
	}

	function makeResizableAndDraggable($element) {
		$element.resizable({
			containment: 'parent',
			grid: [5, 5]
		}).draggable({
			containment: 'parent',
			cursor: 'move',
			distance: 10,
			grid: [5, 5],
			snap: true,
			snapTolerance: 5,
			zIndex: 9999
		});
	}

	function removeResizableAndDraggable($element) {
		try {
			$element.resizable('destroy').draggable('destroy');
		} catch(err) {}
	}

	function newZone(data) {
		let left = data['x'] - data['x'] % 5;
		let top = data['y'] - data['y'] % 5;
		let $newZone = $('<div class="floorPlan-Zone ' + data["texture"] + '" ' +
			'data-name="' + data["name"] + '" ' +
			'data-texture="' + data["texture"] + '" ' +
			'style="width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; ">' +
			'<div>' + data["name"] + '</div>' +
			'</div>');

		$newZone.offset({left: left, top: top});

		$newZone.on('click touchstart', function () {
			if (buildingMode) {
				let wallData = {
					'x': 50,
					'y': 50,
					'width': 25,
					'height': 75
				}
				let wall = newWall($newZone, wallData);
				makeResizableAndDraggable(wall);
			} else if (paintingMode) {
				$newZone.attr('class', 'floorPlan-Zone');
				$newZone.addClass(selectedTexture);
				$newZone.attr('data-texture', selectedTexture);
			} else if (decoratorMode) {
				if (selectedDeco == null) {
					return;
				}

				let decoData = {
					'x': 25,
					'y': 25,
					'width': 50,
					'height': 50,
					'texture': selectedDeco
				}
				let deco = newDeco($newZone, decoData);
				makeResizableAndDraggable(deco);
			}
		});

		$newZone.on('contextmenu', function () {
			if (moveMode) {
				let result = confirm('Do you really want to delete this zone?');
				if (result == true) {
					$(this).remove();
				}
				return false;
			}
		});

		$floorPlan.append($newZone);
		return $newZone;
	}

	function newWall($element, data) {
		let $newWall = $('<div class="floorPlan-Wall" ' +
			'style="width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; z-index: auto;">' +
			'</div>');

		$newWall.offset({left: data['x'], top: data['y']});

		$newWall.on('click touchstart', function () {
			return false;
		});

		$newWall.on('contextmenu', function () {
			if (buildingMode) {
				$(this).remove();
				return false;
			}
		});

		$element.append($newWall);
		return $newWall;
	}

	function newDeco($element, data) {
		let $newDeco = $('<div class="floorPlan-Deco ' + data["texture"] + '" ' +
			'style="width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; z-index: auto;" ' +
			'data-texture="' + data["texture"] + '">' +
			'</div>');

		$newDeco.offset({left: data['x'], top: data['y']});
		$newDeco.on('click touchstart', function () {
			return false;
		});

		$newDeco.on('contextmenu', function () {
			if (decoratorMode) {
				$(this).remove();
				return false;
			}
		});

		$element.append($newDeco);
		return $newDeco;
	}

	$('#toolbarToggleShow').on('click touchstart', function () {
		$('#toolbar_full').show();
		$('#toolbar_toggle').hide();
		$floorPlan.addClass('floorPlanEditMode');
		editMode = true;
		zoneMode = false;
		buildingMode = false;
		paintingMode = false;
		decoratorMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();
	});

	$('#toolbarToggleHide').on('click touchstart', function () {
		$('#toolbar_full').hide();
		$('#toolbar_toggle').show();
		editMode = false;
		zoneMode = false;
		buildingMode = false;
		paintingMode = false;
		decoratorMode = false;
		$floorPlan.removeClass('floorPlanEditMode');
		$floorPlan.removeClass('floorPlanEditMode-AddingZone');

		removeResizableAndDraggable($('.floorPlan-Zone'));
		removeResizableAndDraggable($('.floorPlan-Wall'));
		removeResizableAndDraggable($('.floorPlan-Deco'));

		$('#painterTiles').hide();
		$('#decoTiles').hide();

		markSelectedTool(null);
		saveHouse();
	});

	$('#addZone').on('click touchstart', function () {
		if (!editMode) {
			return;
		}
		zoneMode = true;
		buildingMode = false;
		moveMode = false;
		paintingMode = false;
		decoratorMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();

		markSelectedTool($(this));
		$('#floorPlan').addClass('floorPlanEditMode-AddingZone');
	});

	$floorPlan.on('click touchstart', function (e) {
		if (!zoneMode) {
			return;
		}

		let zoneName = prompt('Please name this new zone');
		if (zoneName != null && zoneName != '') {
			let data = {
				'name': zoneName,
				'x'    : e.pageX - $(this).offset().left,
				'y'    : e.pageY - $(this).offset().top,
				'width'   : 100,
				'height'  : 100,
				'texture' : ''
			}
			let $zone = newZone(data);
			makeResizableAndDraggable($zone)
		}

		zoneMode = false;
		markSelectedTool(null);
		$(this).removeClass('floorPlanEditMode-AddingZone');
	});

	function markSelectedTool($element) {
		$('.selectedTool').removeClass('selectedTool');

		if ($element != null) {
			$element.addClass('selectedTool');
		}
	}

	$('#builder').on('click touchstart', function () {
		paintingMode = false;
		moveMode = false
		zoneMode = false;
		decoratorMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();

		markSelectedTool($(this));

		if (!buildingMode) {
			buildingMode = true;
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');

			removeResizableAndDraggable($('.floorPlan-Zone'));
			removeResizableAndDraggable($('.floorPlan-Deco'));
			makeResizableAndDraggable($('.floorPlan-Wall'));
		} else {
			buildingMode = false;
			removeResizableAndDraggable($('.floorPlan-Wall'));
		}
	});

	$('#painter').on('click touchstart', function () {
		buildingMode = false;
		moveMode = false;
		zoneMode = false;
		decoratorMode = false;

		$('#decoTiles').hide();

		markSelectedTool($(this));

		if (!paintingMode) {
			paintingMode = true;
			$('#painterTiles').css('display', 'flex');
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');
			removeResizableAndDraggable($('.floorPlan-Zone'));
			removeResizableAndDraggable($('.floorPlan-Wall'));
			removeResizableAndDraggable($('.floorPlan-Deco'));
		} else {
			paintingMode = false;
			$('#painterTiles').hide();
		}
	});

	$('#mover').on('click touchstart', function () {
		buildingMode = false;
		paintingMode = false;
		zoneMode = false;
		decoratorMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();

		markSelectedTool($(this));

		if (!moveMode) {
			moveMode = true;
			makeResizableAndDraggable($('.floorPlan-Zone'));
			removeResizableAndDraggable($('.floorPlan-Wall'));
			removeResizableAndDraggable($('.floorPlan-Deco'));
		} else {
			moveMode = false;
			removeResizableAndDraggable($('.floorPlan-Zone'));
		}
	});

	$('#decorator').on('click touchstart', function () {
		paintingMode = false;
		moveMode = false
		zoneMode = false;
		buildingMode = false;

		$('#painterTiles').hide();

		markSelectedTool($(this));

		if (!decoratorMode) {
			decoratorMode = true;
			$('#decoTiles').css('display', 'flex');
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');
			removeResizableAndDraggable($('.floorPlan-Zone'));
			removeResizableAndDraggable($('.floorPlan-Wall'));
			makeResizableAndDraggable($('.floorPlan-Deco'));
		} else {
			decoratorMode = false;
			removeResizableAndDraggable($('.floorPlan-Deco'));
			$('#decoTiles').hide();
		}
	});

	for (let i = 1; i <= 2; i++) {
		let $tile = $('<div class="floorPlan-tile floor-' + i + '"></div>');

		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedTexture = 'floor-' + i;
			} else {
				$(this).removeClass('selected');
			}
		})

		$('#painterTiles').append($tile);
	}

	for (let i = 1; i <= 1; i++) {
		let $tile = $('<div class="floorPlan-tile-background"><div class="deco-' + i + '"></div></div>');

		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedDeco = 'deco-' + i;
			} else {
				$(this).removeClass('selected');
			}
		})

		$('#decoTiles').append($tile);
	}

	loadHouse();
});
