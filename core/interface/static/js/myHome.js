$(function () {

	let $floorPlan = $('#floorPlan');
	let editMode = false;

	let moveMode = false;
	let zoneMode = false;
	let buildingMode = false;
	let paintingMode = false;
	let decoratorMode = false;

	let selectedFloor = '';
	let selectedDeco = '';
	let selectedConstruction = '';

	function loadHouse() {
		$.ajax({
			url : '/myhome/load/',
			type: 'GET'
		}).done(function (response) {
			let $data = JSON.parse(response);
			$.each($data, function (i, zone) {
				let $zone = newZone(zone);
				$.each(zone['walls'], function (ii, wall) {
					newWall($zone, wall);
				});
				$.each(zone['construction'], function (iii, construction) {
					newConstruction($zone, construction);
				});
				$.each(zone['deco'], function (iiii, deco) {
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
				'name'    : $(this).data('name'),
				'x'       : $(this).css('left').replace('px', ''),
				'y'       : $(this).css('top').replace('px', ''),
				'z-index' : $(this).css('z-index'),
				'rotation': matrixToAngle($(this).css('transform')),
				'width'   : $(this).width(),
				'height'  : $(this).height(),
				'texture' : $(this).data('texture')
			};

			data[zoneName]['walls'] = [];
			$(this).children('.floorPlan-Wall').each(function () {
				data[zoneName]['walls'].push({
					'x'       : $(this).css('left').replace('px', ''),
					'y'       : $(this).css('top').replace('px', ''),
					'rotation': matrixToAngle($(this).css('transform')),
					'width'   : $(this).width(),
					'height'  : $(this).height()
				})
			});

			data[zoneName]['construction'] = [];
			$(this).children('.floorPlan-Construction').each(function () {
				data[zoneName]['construction'].push({
					'x'       : $(this).css('left').replace('px', ''),
					'y'       : $(this).css('top').replace('px', ''),
					'rotation': matrixToAngle($(this).css('transform')),
					'width'   : $(this).width(),
					'height'  : $(this).height(),
					'texture' : $(this).data('texture')
				})
			});

			data[zoneName]['deco'] = [];
			$(this).children('.floorPlan-Deco').each(function () {
				data[zoneName]['deco'].push({
					'x'       : $(this).css('left').replace('px', ''),
					'y'       : $(this).css('top').replace('px', ''),
					'rotation': matrixToAngle($(this).css('transform')),
					'width'   : $(this).width(),
					'height'  : $(this).height(),
					'texture' : $(this).data('texture')
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

	function matrixToAngle(matrix) {
		if (matrix == 'none' || matrix == null) {
			return 0;
		}

		let values = matrix.split('(')[1].split(')')[0].split(',');
		let a = parseFloat(values[0]);
        let b = parseFloat(values[1]);
        let angle = Math.round(Math.atan2(b, a) * (180/Math.PI));
		angle = (angle < 0) ? angle + 360 : angle;
		return snapAngle({'rotation': angle})['rotation'];
	}

	function snapAngle(data) {
		if (data['rotation'] != 0) {
			data['rotation'] -= data['rotation'] % 15;
		}
		return data;
	}

	function snapPosition(data) {
		data['x'] -= data['x'] % 5;
		data['y'] -= data['y'] % 5;
		return data;
	}

	function makeResizableRotatableAndDraggable($element) {
		$element.resizable({
			containment: 'parent',
			grid       : [5, 5]
		}).rotatable({
			snap: true,
			step: 15,
			degrees: matrixToAngle($element.css('transform')),
			handleOffset: {
				top: 0,
				left: 0
			}
		}).draggable({
			cursor       : 'move',
			distance     : 10,
			grid         : [5, 5],
			snap         : true,
			snapTolerance: 5
		});
	}

	function removeResizableRotatableAndDraggable($element) {
		try {
			$element.resizable('destroy').draggable('destroy').rotatable('destroy');
		} catch (err) {
		}
	}

	function newZone(data) {
		data = snapPosition(data)
		data = snapAngle(data);
		let $newZone = $('<div class="floorPlan-Zone ' + data["texture"] + '" ' +
			'data-name="' + data["name"] + '" ' +
			'data-texture="' + data["texture"] + '" ' +
			'style="left: ' + data["x"] + 'px; top: ' + data["y"] + 'px; width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; transform: rotate(' + data["rotation"] + 'deg); z-index: ' + data["z-index"] + '">' +
			'<div class="inputOrText">' + data["name"] + '</div>' +
			'<div class="zindexer initialHidden">' +
				'<div class="zindexer-up"><i class="fas fa-level-up-alt" aria-hidden="true"></i></div>' +
				'<div class="zindexer-down"><i class="fas fa-level-down-alt" aria-hidden="true"></i></div>' +
			'</div>' +
			'</div>');

		initIndexers($newZone);

		$newZone.on('click touchstart', function () {
			if (buildingMode) {
				if (selectedConstruction == null || selectedConstruction == '') {
					let wallData = {
						'x'     : 50,
						'y'     : 50,
						'width' : 25,
						'height': 75,
						'rotation': 0
					}
					let wall = newWall($newZone, wallData);
					makeResizableRotatableAndDraggable(wall);
				}
				else {
					let constructionData = {
						'x'      : 25,
						'y'      : 25,
						'width'  : 50,
						'height' : 50,
						'rotation': 0,
						'texture': selectedConstruction
					}

					let $construction = newConstruction($newZone, constructionData);
					makeResizableRotatableAndDraggable($construction);
				}
			} else if (paintingMode) {
				$newZone.attr('class', 'floorPlan-Zone');
				$newZone.addClass(selectedFloor);
				$newZone.attr('data-texture', selectedFloor);
			} else if (decoratorMode) {
				if (selectedDeco == null || selectedDeco == '') {
					return;
				}

				let decoData = {
					'x'      : 25,
					'y'      : 25,
					'width'  : 50,
					'height' : 50,
					'rotation': 0,
					'texture': selectedDeco
				}

				let $deco = newDeco($newZone, decoData);
				makeResizableRotatableAndDraggable($deco);
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
		data = snapPosition(data)
		data = snapAngle(data);
		let $newWall = $('<div class="floorPlan-Wall" ' +
			'style="left: ' + data["x"] + 'px; top: ' + data["y"] + 'px; width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; z-index: auto; transform: rotate(' + data["rotation"] + 'deg);">' +
			'</div>');

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

	function newConstruction($element, data) {
		data = snapPosition(data)
		data = snapAngle(data);
		// noinspection CssUnknownTarget
		let $newConstruction = $('<div class="floorPlan-Construction" ' +
			'style="background: url(\'/static/css/images/myHome/construction/' + data["texture"] + '.png\') no-repeat; background-size: 100% 100%; left: ' + data["x"] + 'px; top: ' + data["y"] + 'px; width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; z-index: auto; transform: rotate(' + data["rotation"] + 'deg);" ' +
			'data-texture="' + data["texture"] + '">' +
			'</div>');

		$newConstruction.on('click touchstart', function () {
			return false;
		});

		$newConstruction.on('contextmenu', function () {
			if (buildingMode) {
				$(this).remove();
				return false;
			}
		});

		$element.append($newConstruction);
		return $newConstruction;
	}

	function newDeco($element, data) {
		data = snapPosition(data)
		data = snapAngle(data);
		// noinspection CssUnknownTarget
		let $newDeco = $('<div class="floorPlan-Deco" ' +
			'style="background: url(\'/static/css/images/myHome/deco/' + data["texture"] + '.png\') no-repeat; background-size: 100% 100%; left: ' + data["x"] + 'px; top: ' + data["y"] + 'px; width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; z-index: auto; transform: rotate(' + data["rotation"] + 'deg);" ' +
			'data-texture="' + data["texture"] + '">' +
			'</div>');

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
		moveMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();

		$('.inputOrText').each(function() {
			let name = $(this).text();
			$(this).empty();
			$(this).html('<input type="text" value="' + name + '">');
		})
	});

	$('#toolbarToggleHide').on('click touchstart', function () {
		$('#toolbar_full').hide();
		$('#toolbar_toggle').show();
		editMode = false;
		zoneMode = false;
		buildingMode = false;
		paintingMode = false;
		decoratorMode = false;
		moveMode = false;

		$floorPlan.removeClass('floorPlanEditMode');
		$floorPlan.removeClass('floorPlanEditMode-AddingZone');

		removeResizableRotatableAndDraggable($('.floorPlan-Zone'));
		removeResizableRotatableAndDraggable($('.floorPlan-Wall'));
		removeResizableRotatableAndDraggable($('.floorPlan-Deco'));
		removeResizableRotatableAndDraggable($('.floorPlan-Construction'));

		$('#painterTiles').hide();
		$('#decoTiles').hide();

		markSelectedTool(null);

		$('.inputOrText').each(function() {
			let name = $(this).children('input').val();
			$(this).parent().attr('data-name', name);
			$(this).remove('input');
			$(this).text(name);
		})

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
				'name'   : zoneName,
				'x'      : e.pageX - $(this).offset().left,
				'y'      : e.pageY - $(this).offset().top,
				'width'  : 100,
				'height' : 100,
				'texture': ''
			}
			let $zone = newZone(data);
			makeResizableRotatableAndDraggable($zone)
		}

		zoneMode = false;
		markSelectedTool($('#mover'));
		$('.zindexer').show();
		$(this).removeClass('floorPlanEditMode-AddingZone');
	});

	function markSelectedTool($element) {
		$('.selectedTool').removeClass('selectedTool');

		buildingMode = false;
		paintingMode = false;
		zoneMode = false;
		decoratorMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();
		$('#constructionTiles').hide();

		selectedFloor = '';
		selectedDeco = '';

		$('.floorPlan-tile').removeClass('selected');
		$('.floorPlan-tile-background').removeClass('selected');
		$('.zindexer').hide();

		if ($element != null) {
			$element.addClass('selectedTool');
		}
	}

	$('#builder').on('click touchstart', function () {
		markSelectedTool($(this));

		if (!buildingMode) {
			buildingMode = true;
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');
			$('#constructionTiles').css('display', 'flex');

			$('.floorPlan-Zone, .floorPlan-Deco').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
			$('.floorPlan-Wall, .floorPlan-Construction').each(function() {
				makeResizableRotatableAndDraggable($(this));
			});
		} else {
			$('.floorPlan-Wall, .floorPlan-Construction').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});

			markSelectedTool(null);
		}
	});

	$('#painter').on('click touchstart', function () {
		markSelectedTool($(this));

		if (!paintingMode) {
			paintingMode = true;
			$('#painterTiles').css('display', 'flex');
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');

			$('.floorPlan-Zone, .floorPlan-Deco, .floorPlan-Wall, .floorPlan-Construction').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
		} else {
			markSelectedTool(null);
		}
	});

	$('#mover').on('click touchstart', function () {
		markSelectedTool($(this));

		if (!moveMode) {
			moveMode = true;
			$('.zindexer').show();

			$('.floorPlan-Zone').each(function() {
				makeResizableRotatableAndDraggable($(this));
			});

			$('.floorPlan-Deco, .floorPlan-Wall, .floorPlan-Construction').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
		} else {
			$('.floorPlan-Zone').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
			markSelectedTool(null);
		}
	});

	$('#decorator').on('click touchstart', function () {
		markSelectedTool($(this));

		if (!decoratorMode) {
			decoratorMode = true;
			$('#decoTiles').css('display', 'flex');
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');

			$('.floorPlan-Deco').each(function() {
				makeResizableRotatableAndDraggable($(this));
			});

			$('.floorPlan-Zone, .floorPlan-Wall, .floorPlan-Construction').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
		} else {
			$('.floorPlan-Deco').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
			markSelectedTool(null);
		}
	});

	for (let i = 1; i <= 11; i++) {
		// noinspection CssUnknownTarget
		let $tile = $('<div class="floorPlan-tile" style="background: url(\'/static/css/images/myHome/construction/construction-' + i + '.png\') no-repeat; background-size: 100% 100%;"></div>');
		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedConstruction = 'construction-' + i;
			} else {
				$(this).removeClass('selected');
				selectedConstruction = '';
			}
		});
		$('#constructionTiles').append($tile);
	}

	for (let i = 1; i <= 79; i++) {
		let $tile = $('<div class="floorPlan-tile floor-' + i + '"></div>');
		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedFloor = 'floor-' + i;
			} else {
				$(this).removeClass('selected');
				selectedFloor = '';
			}
		});

		$('#painterTiles').append($tile);
	}

	for (let i = 1; i <= 167; i++) {
		// noinspection CssUnknownTarget
		let $tile = $('<div class="floorPlan-tile" style="background: url(\'/static/css/images/myHome/deco/deco-' + i + '.png\') no-repeat; background-size: 100% 100%;"></div>');
		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedDeco = 'deco-' + i;
			} else {
				$(this).removeClass('selected');
				selectedDeco = '';
			}
		});
		$('#decoTiles').append($tile);
	}

	loadHouse();
});
