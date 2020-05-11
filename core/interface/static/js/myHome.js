$(function () {

	let $floorPlan = $('#floorPlan');
	let editMode = false;

	let moveMode = false;
	let zoneMode = false;
	let buildingMode = false;
	let paintingMode = false;
	let decoratorMode = false;
	let deviceInstallerMode = false;

	let selectedFloor = '';
	let selectedDeco = '';
	let selectedDevice = '';
	let selectedDeviceSkill = '';
	let selectedConstruction = '';

	function loadHouse() {
		$.ajax({
			url : '/myhome/load/',
			type: 'GET'
		}).done(function (response) {
			let $data = response;
			$.each($data, function (i, zone) {
				let $zone = newZone(zone);
				if (zone['display']) {
					if (zone['display'].hasOwnProperty('walls')) {
						$.each(zone['display']['walls'], function (ii, wall) {
							newWall($zone, wall);
						});
					}
					if (zone['display'].hasOwnProperty('construction')) {
						$.each(zone['display']['construction'], function (iii, construction) {
							newConstruction($zone, construction);
						});
					}
					if (zone['display'].hasOwnProperty('deco')) {
						$.each(zone['display']['deco'], function (iiii, deco) {
							newDeco($zone, deco);
						});
					}
				}
				$.each(zone['devices'], function (iiiii, device) {
					newDevice($zone, device);
				});
			})
		});
	}

	function saveHouse() {
		let data = {};
		$floorPlan.children('.floorPlan-Zone').each(function () {
			let zoneName = $(this).data('name');
			data[zoneName] = {
				"id"	  : $(this).data('id'),
				"name"    : $(this).data('name')
			};
			data[zoneName]['display'] = {
				"x"       : $(this).css('left').replace('px', ''),
				"y"       : $(this).css('top').replace('px', ''),
				"z-index" : $(this).css('z-index'),
				"rotation": matrixToAngle($(this).css('transform')),
				"width"   : $(this).width(),
				"height"  : $(this).height(),
				"texture" : $(this).data('texture')
			}
			data[zoneName]['display']['walls'] = [];
			$(this).children('.floorPlan-Wall').each(function () {
				data[zoneName]['display']['walls'].push({
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height()
				})
			});

			data[zoneName]['display']['construction'] = [];
			$(this).children('.floorPlan-Construction').each(function () {
				data[zoneName]['display']['construction'].push({
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height(),
					"texture" : $(this).data('texture')
				})
			});

			data[zoneName]['display']['deco'] = [];
			$(this).children('.floorPlan-Deco').each(function () {
				data[zoneName]['display']['deco'].push({
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height(),
					"texture" : $(this).data('texture')
				})
			});

			data[zoneName]['devices'] = [];
			$(this).children('.floorPlan-Device').each(function () {
				data[zoneName]['devices'].push({
					"uid"	  : $(this).data('uid'),
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height(),
					"deviceType" : $(this).data('texture'),
					"skillName" : $(this).data('skillname')
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
		if(!data["display"]){
			data["display"] = {};
		}
		let $newZone = $('<div class="floorPlan-Zone ' + data["display"]["texture"] + '" ' +
			'data-id="' + data["id"] + '" ' +
			'data-name="' + data["name"] + '" ' +
			'data-texture="' + data["display"]["texture"] + '" ' +
			'style="left: ' + data["display"]["x"] + 'px; top: ' + data["display"]["y"] + 'px; width: ' + data["display"]["width"] + 'px; height: ' + data["display"]["height"] + 'px; position: absolute; transform: rotate(' + data["display"]["rotation"] + 'deg); z-index: ' + data["display"]["z-index"] + '">' +
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
			} else if (deviceInstallerMode) {
				if (selectedDevice == null || selectedDevice == '') {
					return;
				}

				let deviceData = {
					'x'      : 25,
					'y'      : 25,
					'width'  : 50,
					'height' : 50,
					'rotation': 0,
					'deviceType': selectedDevice,
					'skillName': selectedDeviceSkill
				}

				let $device = newDevice($newZone, deviceData);
				makeResizableRotatableAndDraggable($device);
			} else {
				let $settings = $('#settings');
				let content = "<i>"+data['id']+"</i> <h1>"+data['name']+"</h1>";
				content += "<div class='configBox'>";
				content += "<div class='configList'>";
				content += "<div class='configBlock'><div class='configLabel'>Synonyms:</div>";
				content += "<div class='configBlockContent addSynonym' id='Location/"+data['id']+"/addSynonym'><ul class='configListCurrent'/><input class='configInput'/><div class='link-hover configListAdd'><i class=\"fas fa-plus-circle\"></i>	</div></div></div>";
				content += "<div class='configBlock'><div class='configLabel'>Devices:</div><input class='configInput'/></div>";
				content += "<div class='configBlock'><div class='configLabel'>Linked Devices:</div><input class='configInput'/></div>";
				content += "</div></div>";

				//TODO load existing settings
				$settings.html(content);
				loadLocationSettings(data['id'],$settings);
				$settings.sidebar({side: "right"}).trigger("sidebar:open");

				// reroute enter to click event
				$('.configInput').keypress(function (e) {
				  if (e.which == 13) {
				  	$(this).parent().children('.configListAdd').click();
					return false;
				  }
				});

				// add new entry to conf. List
				// TODO add to DB
				$('.configListAdd').on('click touchstart',function() {
					let $parent = $(this).parent();
					let $inp = $parent.children('.configInput');
					if ($inp.val() != "") {
						$.post( '/myhome/'+$parent[0].id,
							{ value: $inp.val() } )
						.done(function( result ) {
							newConfigListVal($parent,$inp.val());
							$inp.val('');
						});
					}
				});
			}
		});

		$newZone.on('contextmenu', function () {
			if (moveMode) {
				let result = confirm('Do you really want to delete this zone?');
				if (result == true) {
					$(this).remove();
					$.post('/myhome/Location/'+data['id']+'/delete', {id : data['id']});
				}
				return false;
			}
		});

		$floorPlan.append($newZone);
		return $newZone;
	}

	function loadLocationSettings(id, $settings){
		$.post('/myhome/Location/'+id+'/getSettings').done(function (res) {
			$synonyms = $settings.find('.addSynonym');
			$.each(res, function (i, synonym) {
				newConfigListVal($synonyms, synonym,'/myhome/Location/'+id+'/deleteSynonym');
			});
		})
	}

	function newConfigListVal($parent, val, deletionLink) {
		$parent.children('.configListCurrent').append("<li>" + val + "<div class='addWidgetCheck configListRemove link-hover'><i class='fas fa-minus-circle'></i></div></li>");
		$('.configListRemove').on('click touchstart', function () {
			$(this).parent().remove();
			$.post(deletionLink, { 'value': val })
			//TODO confirmation
		});
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

	function newDevice($element, data) {
		data = snapPosition(data)
		data = snapAngle(data);
		// noinspection CssUnknownTarget
		let $newDevice = $('<div class="floorPlan-Device" ' +
			'style="background: url(\'deviceType_static/' + data['skillName'] + '/img/' + data["deviceType"] + '.png\') no-repeat; background-size: 100% 100%; left: ' + data["x"] + 'px; top: ' + data["y"] + 'px; width: ' + data["width"] + 'px; height: ' + data["height"] + 'px; position: absolute; z-index: auto; transform: rotate(' + data["rotation"] + 'deg);" ' +
			'data-texture="' + data["deviceType"] + '"; data-skillName="' + data["skillName"] +'">' +
			'</div>');

		$newDevice.on('click touchstart', function () {
			if(editMode) {
				let $settings = $('#settings');
				let content = "<h1>" + data['name'] + "</h1>";
				content += "<h2>" + data['deviceType'] + "</h2>";
				content += "<div class='configBox'>";
				content += "<div class='configList'>";
				content += "<div class='configBlock'><div class='configLabel'>Synonyms:</div>";
				content += "<div class='configBlockContent' id='Device/"+data['id']+"/addSynonym'><ul class='configListCurrent'/><input class='configInput'/><div class='link-hover configListAdd'><i class=\"fas fa-plus-circle\"></i>	</div></div></div>";
				content += "<div class='configBlock'><div class='configLabel'>Devices:</div><input class='configInput'/></div>";
				content += "<div class='configBlock'><div class='configLabel'>Linked Devices:</div><input class='configInput'/></div>";
				content += "</div></div>";

				//TODO load existing settings
				$settings.html(content);
				$settings.sidebar({side: "right"}).trigger("sidebar:open");

				// reroute synonym enter to click event
				$('.configInput').keypress(function (e) {
					if (e.which == 13) {
						$(this).parent().children('.configListAdd').click();
						return false;
					}
				});

				// add new synonym entry to conf. List
				// TODO add to DB
				// TODO check if is existing
				$('.configListAdd').on('click touchstart', function () {
					let $parent = $(this).parent();
					let $inp = $parent.children('.configInput');
					if ($inp.val() != "") {
						$.post( '/myHome/add'+$parent.id,
							{ value: $inp.val() } )
						.done(function( result ) {
							$parent.children('.configListCurrent').append("<li>" + $inp.val() + "<div class='addWidgetCheck configListRemove link-hover'><i class='fas fa-minus-circle'></i></div></li>");
							$inp.val('');

							$('.configListRemove').on('click touchstart', function () {
								$(this).parent().remove();
							});
						});
					}
				});
			} else {
				// display mode: Try toggling the device
				$.post( '/myHome/toggleDevice/',
							{ parent: 'AliceSatellite',
							deviceType: 'Satellites',
							uid: '1231231'} )
					.done(function( result ) {
						$newDevice.css('background: url("/deviceType_static/' + result + '.png')
					});

			}
			return false;
		});

		$newDevice.on('contextmenu', function () {
			if (deviceInstallerMode) {
				$(this).remove();
				return false;
			}
		});

		$element.append($newDevice);
		return $newDevice;
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
		$('#deviceTiles').hide();

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
		deviceInstallerMode = false;

		$floorPlan.removeClass('floorPlanEditMode');
		$floorPlan.removeClass('floorPlanEditMode-AddingZone');

		removeResizableRotatableAndDraggable($('.floorPlan-Zone'));
		removeResizableRotatableAndDraggable($('.floorPlan-Wall'));
		removeResizableRotatableAndDraggable($('.floorPlan-Deco'));
		removeResizableRotatableAndDraggable($('.floorPlan-Device'));
		removeResizableRotatableAndDraggable($('.floorPlan-Construction'));

		$('#painterTiles').hide();
		$('#decoTiles').hide();
		$('#deviceTiles').hide();

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
		markSelectedTool($(this));

		zoneMode = true;
		buildingMode = false;
		moveMode = false;
		paintingMode = false;
		decoratorMode = false;
		deviceInstallerMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();
		$('#deviceTiles').hide();

		$('#floorPlan').addClass('floorPlanEditMode-AddingZone');
	});

	$floorPlan.on('click touchstart', function (e) {
		if (!zoneMode) {
			return;
		}

		let zoneName = prompt('Please name this new zone');
		let x = $(this).offset().left;
		let y = $(this).offset().top;

		$.post('/myhome/Location/0/add', {name : zoneName}).done(function(data){
			zoneId = data;
			if (zoneName != null && zoneName != '') {
				let data = {
					'id'	 : zoneId,
					'name'   : zoneName,
					'x'      : e.pageX - x,
					'y'      : e.pageY - y,
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
		})
	});

	function markSelectedTool($element) {
		$('.selectedTool').removeClass('selectedTool');

		buildingMode = false;
		paintingMode = false;
		zoneMode = false;
		decoratorMode = false;
		deviceInstallerMode = false;

		$('#painterTiles').hide();
		$('#decoTiles').hide();
		$('#constructionTiles').hide();

		selectedFloor = '';
		selectedDeco = '';
		selectedDevice = '';
		selectedDeviceSkill = '';

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

	$('#deviceInstaller').on('click touchstart', function () {
		markSelectedTool($(this));

		if (!deviceInstallerMode) {
			deviceInstallerMode = true;
			$('#deviceTiles').css('display', 'flex');
			$floorPlan.removeClass('floorPlanEditMode-AddingZone');

			$('.floorPlan-Device').each(function() {
				makeResizableRotatableAndDraggable($(this));
			});

			$('.floorPlan-Zone, .floorPlan-Wall, .floorPlan-Construction').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});

			$('.floorPlan-Deco, .floorPlan-Wall, .floorPlan-Construction').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
		} else {
			$('.floorPlan-Device').each(function() {
				removeResizableRotatableAndDraggable($(this));
			});
			markSelectedTool(null);
		}
	});

	// load construction tiles
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

	// load floor tiles
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

	// load deco tiles
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

	$.get('deviceType/getList').done(function (dats) {
		$.each(dats, function(k, dat) {
		let $tile = $('<div class="floorPlan-tile" style="background: url(\'deviceType_static/' + dat['skillName'] + '/img/' + dat['deviceType'] + '.png\') no-repeat; background-size: 100% 100%;"></div>');
		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$('.floorPlan-tile').removeClass('selected');
				$(this).addClass('selected');
				selectedDevice = dat['deviceType'];
				selectedDeviceSkill = dat['skillName'];
			} else {
				$(this).removeClass('selected');
				selectedDevice = '';
				selectedDeviceSkill = '';
			}
		});
		$('#deviceTiles').append($tile);
		});
	});

	function loadDevices(){
		$.get('device/getList').done(dats, function (k, dat) {
			$.each(dats, function(k, dat) {
				newDevice($zone, device);
			})
		});
	}
	loadHouse();
});
