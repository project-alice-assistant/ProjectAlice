$(function () {
	// TODO performance: check if there is already a link before sending to alice

  	let $floorPlan = $('#floorPlan');
  	let $sideBar = $('#settings');

  	//selectors
  	let sWall = '.floorPlan-Wall';
  	let sConstr = '.floorPlan-Construction';
  	let sZone = '.floorPlan-Zone';
  	let sDeco = '.floorPlan-Deco';
  	let sDevice = '.floorPlan-Device';
	let sTile = '.floorPlan-tile';

  	let classAddZone = 'floorPlanEditMode-AddingZone';
  	
  	let sWallConstr = sWall+", "+sConstr;

	let editMode = false;

	let locationEditMode = false;
	let locationMoveMode = false;
	let zoneMode = false;
	let buildingMode = false;
	let paintingMode = false;
	let decoratorMode = false;
	let locationSettingsMode = false;

	let deviceEditMode = false;
	let deviceInstallerMode = false;
	let deviceLinkerMode = false;
	let deviceMoveMode = false;
	let deviceSettingsMode = false;

	let selectedFloor = '';
	let selectedDeco = '';
	let selectedDeviceTypeID = '';
	let selectedConstruction = '';

	// Linker
	let selectedDevice = null;
	let selectedLinks = null;

	// DATA
	let dirtyFormulars = [];

// Setup and handle MQTT
	function onConnect() {
		MQTT.subscribe('projectalice/devices/updated');
	}

	function onMessage(msg) {
		let payload = JSON.parse(msg.payloadString);
		if (msg.topic === 'projectalice/devices/updated') {
			if(payload['type'] == 'status') {
				console.log(payload);
				let tochange = $('#device_' + payload['id']);
				let url = 'Device/' + payload['id'] + '/icon?random=' + new Date().getTime();
				tochange.css('background-image', 'url('+url+')');
				console.log('done');
			}
		}

	}

	function makeDirty(event){
		dirtyFormulars.push(event.target);
	}
// Basic functionality for loading, saving
	function loadHouse() {
		$.ajax({
			url : '/myhome/load/',
			type: 'GET'
		}).done(function (response) {
			$.each(response, function (i, zone) {
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
		$floorPlan.children(sZone).each(function () {
			let zoneID = $(this).data('id');
			data[zoneID] = {
				"id"	  : $(this).data('id'),
				"name"    : $(this).data('name')
			};
			data[zoneID]['display'] = {
				"x"       : $(this).css('left').replace('px', ''),
				"y"       : $(this).css('top').replace('px', ''),
				"z-index" : $(this).css('z-index'),
				"rotation": matrixToAngle($(this).css('transform')),
				"width"   : $(this).width(),
				"height"  : $(this).height(),
				"texture" : $(this).data('texture')
			};
			data[zoneID]['display']['walls'] = [];
			$(this).children(sWall).each(function () {
				data[zoneID]['display']['walls'].push({
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height()
				})
			});

			data[zoneID]['display']['construction'] = [];
			$(this).children(sConstr).each(function () {
				data[zoneID]['display']['construction'].push({
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height(),
					"texture" : $(this).data('texture')
				})
			});

			data[zoneID]['display']['deco'] = [];
			$(this).children(sDeco).each(function () {
				data[zoneID]['display']['deco'].push({
					"x"       : $(this).css('left').replace('px', ''),
					"y"       : $(this).css('top').replace('px', ''),
					"rotation": matrixToAngle($(this).css('transform')),
					"width"   : $(this).width(),
					"height"  : $(this).height(),
					"texture" : $(this).data('texture')
				})
			});

			data[zoneID]['devices'] = [];
			$(this).children(sDevice).each(function () {
				data[zoneID]['devices'].push({
					"id"	  : $(this).data('id'),
					"uid"	  : $(this).data('uid'),
					"deviceType" : $(this).data('texture'),
					"skill" : $(this).data('skill'),
					"display" : {
						"x"       : $(this).css('left').replace('px', ''),
						"y"       : $(this).css('top').replace('px', ''),
						"rotation": matrixToAngle($(this).css('transform')),
						"width"   : $(this).width(),
						"height"  : $(this).height()
					}
				})
			});
		});

		$.ajax({'url': '/myhome/save/', data: JSON.stringify(data), 'type':'POST', 'contentType' :'application/json'});
	}

// Basic functionality for build area
	function matrixToAngle(matrix) {
		if (matrix == 'none' || matrix == null) {
			return 0;
			makeDirty(null);
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

	function makeDroppable($element, changeParent){
			$element.droppable({
  				drop: function( event, ui ) {
  					if(changeParent) {
						let roomChange = false;
						if (ui.draggable.parent()[0] != this) {
							roomChange = true;
						}
						if (roomChange) {
							$(this).append(ui.draggable);
						}
					}
					ui.draggable.draggable( "option", "revert", false );
					ui.draggable.css({top: ui.offset.top - $(this).offset().top, left: ui.offset.left - $(this).offset().left } );
					setTimeout( function() { ui.draggable.draggable( "option", "revert", true ); }, 1000 );
  				}
			});
	}

	function makeResizableRotatableAndDraggable($element, revert) {
		if(!revert){
			revert = false;
		}
		// required to handle one at a time for rotatable!
		$element.each(function () {
			$(this).resizable({
				containment: 'parent',
				grid       : [5, 5],
				autoHide   : true,
				stop        : function (e) {
					saveRequired();
				}
			}).rotatable({
				snap        : true,
				step        : 15,
				degrees     : matrixToAngle($(this).css('transform')),
				handleOffset: {
					top : 0,
					left: 0
				},
				autoHide: true,
				stop        : function (e) {
					saveRequired();
				}
			}).draggable({
				addClasses   : false,
				cursor       : 'move',
				distance     : 10,
				grid         : [5, 5],
				snap         : true,
				snapTolerance: 5,
				zIndex       : 999,
				revert       : revert,
				helper       : "clone",
				appendTo     : "body",
				start        : function (e) {
					$(e.target).css({opacity: 0.3});
				},
				stop         : function (e) {
					saveRequired();
					$(e.target).css({opacity: 1});
				}
			});
		});
	}

	function removeResizableRotatableAndDraggable($element) {
		$element.each(function () {
			try {
				$(this).resizable('destroy').draggable('destroy').rotatable('destroy');
			} catch (err) {
			}
		});
	}

	function setSelectedDevice($element, $confOut){
		saveSidebar();
		// clear old, set new, draw links
		if(selectedDevice) {
			selectedDevice.connections('remove');
			selectedDevice.removeClass('highlightedDevice');
		}
		selectedDevice = $element;
		if(selectedDevice) {
			selectedDevice.addClass('highlightedDevice');
			$.get('Device/' + selectedDevice.data('id') + '/getLinks').done(function (res) {
				res = jQuery.parseJSON(res);
				if(handleError(res)) return;
				selectedLinks = res;
				let content = "";
				$.each(res, function (id, link) {
					target = $('#floorPlan-Zone_' + link['locationID']);
					target.children('.inputOrText').connections({
						to     : selectedDevice,
						'class': 'deviceLink'
					});
					content += link['']
				});
				if($confOut && selectedLinks){
					total = "<div class='configCategoryTitle'>Available In:</div>";
					let hasOne = false;
					$.each(selectedLinks, function (id, val){
						hasOne = true;
						content = "<div class='linkTitle'>"+val['locationName']+"</div>";
						confLines = "<form>";
						$.each(val['locSettings'], function (ckey, cval) {
							confLines += "<div class='configLabel'>" + ckey + "</div><input name='" + ckey + "' class='configInput' value='" + cval + "'/>";
						});
						if (confLines) {
							//content += "<div class='configBox'><div class='configList'><form id='SetForm' name='config_for_devSet' action='Device/" + data['id'] + "/saveSettings/0' method='post'><div class='configBlock'>";
							content += confLines
							content += "</form>";
							//content += "</div>";
							//content += "<div class='buttonLine'><input id='SetFormSubmit' class='button' type='submit' value='" + $('#langSave').text() + "'></div>";
							//content += "</form></div></div>";
						}
						total += content;
					});
					if(hasOne) $confOut.append(total);
					$('input').change(makeDirty);
				}
			});
		}

	}

	// logic for individual items
	function newZone(data) {
		data = snapPosition(data)
		data = snapAngle(data);
		if(!data["display"]){
			data["display"] = {};
		}
		let $newZone = $('<div class="floorPlan-Zone ' + data["display"]["texture"] + '" ' +
			'id="floorPlan-Zone_'+data["id"]+'" '+
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
				if (selectedDeviceTypeID == null || selectedDeviceTypeID == '') {
					return;
				}

				$.post('/myhome/Device/0/add',
					{ 'locationID': data["id"],
					  'deviceTypeID': selectedDeviceTypeID } ).done(function (rec) {
					  	if(handleError(rec)){
					  		return;
						}
					  	let deviceData = {
					  		'display': {
								'x'      : 25,
								'y'      : 25,
								'width'  : 50,
								'height' : 50,
								'rotation': 0 },
							'deviceTypeID': selectedDeviceTypeID,
							'skill': rec['skill'],
							'deviceType': rec['deviceType'],
							'id': rec['id']
						};
						let $device = newDevice($newZone, deviceData);
						makeResizableRotatableAndDraggable($device);
				});

			} else if (deviceLinkerMode) {
				if (selectedDevice == null || selectedDevice == '') return;

				// add link from selected Device to zone
				target = this;
				$.post('/myhome/Device/'+selectedDevice.data('id')+'/addLink/'+data["id"]).done(function (result){
					if( handleError(result) ) return;
					// frontend: draw bezier
					$(target).children('.inputOrText').connections({
					  to: selectedDevice,
					  'class': 'deviceLink'
					});
				});

			} else if (locationSettingsMode){
				let content = "<i>"+data['id']+"</i> <h1>"+data['name']+"</h1>";
				content += "<div class='configBox'>";
				content += "<div class='configBox'>";
				content += "<div class='configList'>";
				content += "<div class='configBlock'><div class='configLabel'>Synonyms:</div>";
				content += "<div class='configBlockContent addSynonym' id='Location/"+data['id']+"/addSynonym' data-dellink='Location/"+data['id']+"/deleteSynonym'><ul class='configListCurrent'/><div class='configLine'><input class='configInput'/><div class='link-hover configListAdd'><i class=\"fas fa-plus-circle\"></i></div></div></div></div>";
//				content += "<div class='configBlock'><div class='configLabel'>Devices:</div><input class='configInput'/></div>";
//				content += "<div class='configBlock'><div class='configLabel'>Linked Devices:</div><input class='configInput'/></div>";
				content += "</div></div>";

				$sideBar.html(content);
				loadLocationSettings(data['id'],$sideBar);
				$sideBar.sidebar({side: "right"}).trigger("sidebar:open");

				// reroute enter to click event
				$('.configInput').keypress(function (e) {
				  if (e.which == 13) {
				  	$(this).parent().children('.configListAdd').click();
					return false;
				  }
				});

				// add new entry to conf. List
				$('.configListAdd').on('click touchstart',function() {
					let $parent = $(this).parent();
					let $inp = $parent.children('.configInput');
					$parent = $parent.parent();
					if ($inp.val() != '') {
						$.post( '/myhome/'+$parent[0].id,
							{ value: $inp.val() } )
						.done(function( result ) {
							if(handleError(result)){
								return;
							}
							newConfigListVal($parent,$inp.val(),$parent.data('dellink') );
							$inp.val('');
						});
					}
				});
			}
		});

		$newZone.on('contextmenu', function () {
			if (locationMoveMode) {
				if(confirm($('#langConfDeleteZone').text())){
					$(this).remove();
					$.post('/myhome/Location/'+data['id']+'/delete', {id : data['id']});
				}
				return false;
			} else if (deviceLinkerMode){
				target = this;
				$.post('Device/'+ selectedDevice.data('id') +'/removeLink/'+ $(this).data('id')).done(function (res) {
					if( handleError(res) ){
						return;
					}
					$(target).children('.inputOrText').connections('remove');
				})
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

	function newDevice($element, data) {
		data = snapPosition(data)
		data = snapAngle(data);
		// noinspection CssUnknownTarget
		let $newDevice = $('<div class="floorPlan-Device" id="device_'+data['id']+'" ' +
			'style="background: url(\'Device/'+data['id']+'/icon?random='+ new Date().getTime()+'\') no-repeat; background-size: 100% 100%; left: ' + data["display"]["x"] + 'px; top: ' + data["display"]["y"] + 'px; width: ' + data["display"]["width"] + 'px; height: ' + data["display"]["height"] + 'px; position: absolute; z-index: auto; transform: rotate(' + data["display"]["rotation"] + 'deg);" ' +
			'data-texture="' + data["deviceType"] + '" data-skill="' + data["skill"] + '" data-id="' + data["id"] + '" data-uid="' + data["uid"] + '" title="'+data['name']+'">' +
			'</div>');

		$newDevice.on('click touchstart', function () {
			if(deviceSettingsMode) {
				let content = "<h1>" + data['name'] + "</h1>";
				content += "<h2>" + data['deviceType'] + "</h2>";

				if (data['uid'] == 'undefined' || data['uid'] == null) {
					content += "NO DEVICE PAIRED!<div id='startPair' class='button'>Search Device</div>"
				} else {
					content += "<div class='techDetail' >" + data['uid'] + "</div>";
				}

				$sideBar.html(content);
				$('#startPair').on('click touchstart', function () {
					$(this).addClass('waiting')
					$.post('Device/' + data['id'] + '/pair').done(function (dataa) {
						if (handleError(dataa)) {
							return;
						}
						let sp = $('#startPair')
						sp.removeClass('waiting');
						sp.hide();
					});
				});

				$sideBar.addClass('waiting after_big')
				$sideBar.sidebar({side: "right"}).trigger("sidebar:open");

// TODO logic for synonyms of devices
// 				content += "<div class='configBlock'><div class='configLabel'>Synonyms:</div>";
//				content += "<div class='configBlockContent' id='Device/"+data['id']+"/addSynonym'><ul class='configListCurrent'/><input class='configInput'/><div class='link-hover configListAdd'><i class=\"fas fa-plus-circle\"></i>	</div></div></div>";

				$.get('/myhome/Device/' + data['id'] + '/getSettings/0').done(function (res) {
					if (handleError(res)) return;

					let confLines = '';
					content = '';
					$.each(res, function (key, val) {
						confLines += "<div class='configLabel'>" + key + "</div><input name='" + key + "' class='configInput' value='" + val + "'/>";
					});
					if (confLines) {
						content += "<div class='configBox'><div class='configList'><form id='SetForm' name='config_for_devSet' action='Device/" + data['id'] + "/saveSettings/0' method='post'><div class='configBlock'>";
						content += confLines
						content += "</div>";
						content += "<div class='buttonLine'><input id='SetFormSubmit' class='button' type='submit' value='" + $('#langSave').text() + "'></div>";
						content += "</form></div></div>";

						$sideBar.append(content);

						// perform submit/save of the form without switching page
						let form = $('#SetForm');
						let saveButton = form.find('#SetFormSubmit');
						// noinspection JSDeprecatedSymbols
						form.submit(function (event) {
							saveButton.val($('#langSaving').text());
							saveButton.addClass('saving');
							$.post(form.attr('action'), form.serialize())
								.done(function () {
									saveButton.val($('#langSaved').text());
									saveButton.addClass('saved');
								})
								.fail(function () {
									saveButton.val($('#langSaveFailed').text());
									saveButton.addClass('saveFailed');
								}).always(
								function () {
									saveButton.removeClass('saving');
								});
							event.preventDefault();
						});

						// change button back to save if something was changed
						$('.configInput').on('change', function () {
							saveButton.val($('#langSave').text());
							saveButton.removeClass('saved');
							saveButton.removeClass('saveFailed');
						});


					}
					selectedLinks = null;
					setSelectedDevice($newDevice, $sideBar);
				});

// TODO Room specific Settings
				//content += "<div class='configBlock'><div class='configLabel'>Available in following Rooms:</div><input class='configInput'/></div>";
				//content += "<span class=\"toolbarButton link-hover\" id=\"deviceLinker\" title=\"Link a device with multiple rooms\"><i class=\"fas fa-link\"></i></span>";


				// reroute synonym enter to click event
				$('.configInput').keypress(function (e) {
					if (e.which == 13) {
						$(this).parent().children('.configListAdd').click();
						return false;
					}
				});

				// add new synonym entry to conf. List
				//TODO add to DB
				// check if is existing
				/*				$('.configListAdd').on('click touchstart', function () {
									let $parent = $(this).parent();
									let $inp = $parent.children('.configInput');
									if ($inp.val() != '') {
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
								});*/
				$sideBar.removeClass('waiting after_big')
			} else if(deviceLinkerMode) {
				setSelectedDevice($(this));
			} else {
				// display mode: Try toggling the device
				$.post( 'Device/'+data['id']+'/toggle')
					.done(function( $data ) {
						if(editMode){
							return;
						}
						// check if the result gives a link to open
						if('href' in $data) {
							window.open($data['href']);
							return true;
						}
					});

			}
			return false;
		});

		$newDevice.on('contextmenu', function () {
			if (deviceInstallerMode) {
				if(confirm($('#langConfDeleteDevice').text())){
					let $dev = $(this)
					$.post('Device/'+data['id']+'/delete').done(function (res) {
						if(handleError(res)) return;
						$dev.remove();
					})
				}
				return false;
			}
		});

		$element.append($newDevice);
		return $newDevice;
	}

// helper functions
	function handleError($data){
		if('error' in $data) {
			alert($data['error']);
			return true;
		}else{
			return false;
		}
	}

	function initEditable(){
		editMode = true;
		deviceLinkerMode = deviceInstallerMode = deviceMoveMode = locationMoveMode = decoratorMode = paintingMode = buildingMode = zoneMode = deviceEditMode = false;

		removeResizableRotatableAndDraggable($(sZone+", "+sWall+", "+sDeco+", "+sDevice+", "+sConstr));

		markSelectedTool(null);

		$('#toolbarConstruction, #toolbarTechnic, #painterTiles, #decoTiles, #deviceTiles').hide();

		$floorPlan.removeClass(classAddZone);
		$floorPlan.addClass('floorPlanEditMode');
	}

	function loadLocationSettings(id, $settings){
		$.get('/myhome/Location/'+id+'/getSettings').done(function (res) {
			let $synonyms = $settings.find('.addSynonym');
			$.each(res, function (i, synonym) {
				newConfigListVal($synonyms, synonym,'/myhome/Location/'+id+'/deleteSynonym');
			});
		})
	}

	function newConfigListVal($parent, val, deletionLink) {
		$parent.find('.configListCurrent').append("<li>" + val + "<div class='addWidgetCheck configListRemove link-hover'><i class='fas fa-minus-circle'></i></div></li>");
		$('.configListRemove').on('click touchstart', function () {
			$(this).parent().remove();
			$.post(deletionLink, { 'value': val })
		});
	}

// handle toolbar
	// save, hide toolbars, restore live view
	//unused
	$('#saveToolbarAction').on('click touchstart', function () {
		if($(sZone).hasClass('blueprint')) {
			setBPMode(false);
			saveHouse();
			setBPMode(true);
		} else {
			saveHouse();
		}
	});

	$('#finishToolbarAction').on('click touchstart', function () {
		setBPMode(false);
		saveHouse();
		initEditable();
		setSelectedDevice(false);
		markSelectedTool(null);
		markSelectedToolbar(null);

		$('#toolbarOverview').hide();
		$('#toolbarToggle').show();

		$floorPlan.removeClass('floorPlanEditMode');
	});

	// enter edit mode
	$('#toolbarToggleShow').on('click touchstart', function () {
		$('#toolbarOverview').show();
		$('#toolbarToggle').hide();
		initEditable();
	});

	// enter construction/location mode
	$('#toolbarConstructionShow').on('click touchstart', function () {
		initEditable();
		setBPMode(false);
		locationEditMode = true;
		markSelectedToolbar($(this));
		$('#toolbarConstruction').show();
	});

	// enter device editing mode
	$('#toolbarTechnicShow').on('click touchstart', function () {
		initEditable();
		setBPMode(true);
		deviceEditMode = true;
		markSelectedToolbar($(this));
		$('#toolbarTechnic').show();
	});

	$('#toolbarOverviewShow').on('click touchstart', function () {
		$('#toolbarOverview').show();
		$('#toolbarToggle').hide();
		initEditable();
	});

	$floorPlan.on('click touchstart', function (e) {
		if (!zoneMode) {
			return;
		}

		let zoneName = prompt($('#langNameNewZone').text());
		let x = $(this).offset().left;
		let y = $(this).offset().top;

		$.post('/myhome/Location/0/add', {name : zoneName}).done(function(data){
			if( handleError(data) ) {
				return;
			}
			let zoneId = data['id'];

			if (zoneName != null && zoneName != '') {
				let zdata = {
					'id'	 : zoneId,
					'name'   : zoneName,
					'x'      : e.pageX - x,
					'y'      : e.pageY - y,
					'width'  : 100,
					'height' : 100,
					'texture': ''
				}
				zoneMode = false;
				markSelectedTool($('#locationMover'));
				locationMoveMode = true;
				$('.zindexer').show();
				$(this).removeClass(classAddZone);
				let $zone = newZone(zdata);
				makeResizableRotatableAndDraggable($(sZone));
				makeDroppable($floorPlan, false);
			}

		})
	});

	function markSelectedToolbar($element) {
		$('.selectedToolbar').removeClass('selectedToolbar');

		if ($element != null) {
			$element.addClass('selectedToolbar');
		}
	}

	function markSelectedTool($element) {
		$('.selectedTool').removeClass('selectedTool');

		buildingMode = false;
		paintingMode = false;
		zoneMode = false;
		decoratorMode = false;
		deviceInstallerMode = false;
		locationMoveMode = false;
		locationSettingsMode = false;
		deviceMoveMode = false;
		deviceSettingsMode = false;
		deviceLinkerMode = false;

		setSelectedDevice(null);

		$sideBar.sidebar({side: "right"}).trigger("sidebar:close");
		$('.ui-droppable').droppable('destroy');

		$('#painterTiles, #decoTiles, #constructionTiles, #deviceTiles').hide();
//		$('#decoTiles').hide();
//		$('#constructionTiles').hide();
//		$('#deviceTiles').hide();

		selectedFloor = '';
		selectedDeco = '';


		$(sTile).removeClass('selected');
		$('.floorPlan-tile-background').removeClass('selected');
		$('.zindexer').hide();

		if ($element != null) {
			$element.addClass('selectedTool');
		}
	}

// construction tools
	$('#addZone').on('click touchstart', function () {
		if(!zoneMode) {
			markSelectedTool($(this));
			zoneMode = true;
			$floorPlan.addClass(classAddZone);
			removeResizableRotatableAndDraggable($(sZone+", "+sDeco+", "+sWall+", "+sConstr));
		} else {
			zoneMode = false;
			markSelectedTool(null);
			$floorPlan.removeClass(classAddZone);
		}
	});

	$('#builder').on('click touchstart', function () {

		if (!buildingMode) {
			markSelectedTool($(this));
			buildingMode = true;
			$floorPlan.removeClass(classAddZone);
			$('#constructionTiles').css('display', 'flex');
			makeDroppable($(sZone), true);
			makeResizableRotatableAndDraggable($(sWallConstr));
			removeResizableRotatableAndDraggable($(sZone+", "+sDeco));
		} else {
			removeResizableRotatableAndDraggable($(sWallConstr));
			$(sZone).droppable('destroy');
			buildingMode = false;
			$('#constructionTiles').hide();
			markSelectedTool(null);
		}
	});

	$('#painter').on('click touchstart', function () {
		if (!paintingMode) {
			markSelectedTool($(this));
			paintingMode = true;
			$('#painterTiles').css('display', 'flex');
			$floorPlan.removeClass(classAddZone);

			removeResizableRotatableAndDraggable($(sZone+", "+sDeco+", "+sWall+", "+sConstr));
		} else {
			paintingMode = false;
			markSelectedTool(null);
			$('#painterTiles').hide();
		}
	});

	$('#locationMover').on('click touchstart', function () {

		if (!locationMoveMode) {
			markSelectedTool($(this));
			locationMoveMode = true;
			$('.zindexer').show();
			makeResizableRotatableAndDraggable($(sZone));
			removeResizableRotatableAndDraggable($(sDeco+", "+sWallConstr));

			makeDroppable($floorPlan, false);

		} else {
			$floorPlan.droppable('destroy');
			removeResizableRotatableAndDraggable($(sZone));
			markSelectedTool(null);
		}
	});

	$('#decorator').on('click touchstart', function () {

		if (!decoratorMode) {
			markSelectedTool($(this));
			decoratorMode = true;
			$(sDeco).css('pointer-events', 'auto');
			$('#decoTiles').css('display', 'flex');
			$floorPlan.removeClass(classAddZone);
			makeDroppable($(sZone), true);

			makeResizableRotatableAndDraggable($(sDeco));
			removeResizableRotatableAndDraggable($(sZone+", "+sWallConstr));
		} else {
			$(sZone).droppable('destroy');
			removeResizableRotatableAndDraggable($(sDeco));
			markSelectedTool(null);
		}
	});

	$('#locationSettings').on('click touchstart', function () {

		if (!locationSettingsMode) {
			markSelectedTool($(this));
			locationSettingsMode = true;
			$(sDeco).css('pointer-events', 'none');
			removeResizableRotatableAndDraggable($(sZone+", "+sDeco+", "+sWall+", "+sConstr));
		} else {
			locationSettingsMode = false;
			markSelectedTool(null);
		}
	});

// technic tools
	$('#deviceInstaller').on('click touchstart', function () {

		if (!deviceInstallerMode) {
			markSelectedTool($(this));
			deviceInstallerMode = true;
			$('#deviceTiles').css('display', 'flex');
			$floorPlan.removeClass(classAddZone);
			removeResizableRotatableAndDraggable($(sDevice));

		} else {
			removeResizableRotatableAndDraggable($(sDevice));
			markSelectedTool(null);
		}
	});

	$('#deviceLinker').on('click touchstart', function () {

		if(!deviceLinkerMode){
			markSelectedTool($(this));
			deviceLinkerMode = true;
			removeResizableRotatableAndDraggable($(sDevice));
		}else{
			deviceLinkerMode = false;
			markSelectedTool(null);
			setSelectedDevice(false);
		}

	});

	$('#deviceMover').on('click touchstart', function () {

		if (!deviceMoveMode) {
			markSelectedTool($(this));
			deviceMoveMode = true;

			makeResizableRotatableAndDraggable($(sDevice));

			$(sZone).droppable({
  				drop: function( event, ui ) {
  					let userConf = false;
  					let roomChange = false;
  					let errorOccured = false;
					// check if room didn't change
					if (ui.draggable.parent()[0] != this){
						roomChange = true;
					}
					if(roomChange) {
						userConf = confirm($('#langConfMoveDevice').text() + $(this).attr('data-name'));
					}
					if(!roomChange || userConf){
						//save to db
						if(roomChange){
							//async required to revert with jquery draggable standard
							let newParent = this;
							$.ajax({'url': 'Device/' + ui.draggable.data('id') + '/changeLocation/' + $(newParent).data('id'),
									'async': false,
									'method': 'POST'} )
								.done(function( result ) {
									if(handleError(result)){
										errorOccured = true
										return;
									}
									$(newParent).append(ui.draggable);
								}).fail(function(result) {
									alert("I just can't reach my servers!")
									errorOccured = true
							});
						}
						if(errorOccured){
							return;
						}

						ui.draggable.draggable( "option", "revert", false );
					    ui.draggable.css({top: ui.offset.top - $(this).offset().top, left: ui.offset.left - $(this).offset().left } );
					    if(userConf){
					    	// no BP while saving: orientation of decoration is lost!
							setBPMode(false);
					    	saveHouse();
							setBPMode(true);
						}
						setTimeout( function() { ui.draggable.draggable( "option", "revert", true ); }, 1000 );
					}
  				}
			});

		} else {
			removeResizableRotatableAndDraggable($(sDevice));
			$(sZone).droppable('destroy');
			markSelectedTool(null);
		}
	});

	$('#deviceSettings').on('click touchstart', function () {

		if (!deviceSettingsMode) {
			markSelectedTool($(this));
			deviceSettingsMode = true;
			removeResizableRotatableAndDraggable($(sDevice));
		} else {
			deviceSettingsMode = false;
			markSelectedTool(null);
		}
	});

	function setBPMode(value){
		if (value) {
			$(sDeco).css('display', 'none');
			$(sZone).addClass('blueprint')
		} else {
			$(sDeco).css('display', 'block');
			$(sZone).removeClass('blueprint')
		}
	}

// load construction tiles
	for (let i = 1; i <= 11; i++) {
		// noinspection CssUnknownTarget
		let $tile = $('<div class="floorPlan-tile" style="background: url(\'/static/css/images/myHome/construction/construction-' + i + '.png\') no-repeat; background-size: 100% 100%;"></div>');
		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$(sTile).removeClass('selected');
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
				$(sTile).removeClass('selected');
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
				$(sTile).removeClass('selected');
				$(this).addClass('selected');
				selectedDeco = 'deco-' + i;
			} else {
				$(this).removeClass('selected');
				selectedDeco = '';
			}
		});
		$('#decoTiles').append($tile);
	}

	$.get('DeviceType/getList').done(function (dats) {
		$.each(dats, function(k, dat) {
		let $tile = $('<div class="floorPlan-tile" style="background: url(\'deviceType_static/' + dat['skill'] + '/img/' + dat['deviceType'] + '.png\') no-repeat; background-size: 100% 100%;"></div>');
		$tile.on('click touchstart', function () {
			if (!$(this).hasClass('selected')) {
				$(sTile).removeClass('selected');
				$(this).addClass('selected');
				selectedDeviceTypeID = dat['id'];
			} else {
				$(this).removeClass('selected');
				selectedDeviceTypeID = '';
			}
		});
		$('#deviceTiles').append($tile);
		});
	});

	function saveSidebar(){
		if(dirtyFormulars.length == 0) return;
		dirtyFormulars.forEach(function (value){
			//todo add correct form info
			// wait for response
			// stop action if not successful
			value.form.submit();
		});
		dirtyFormulars = [];
	}

	function saveRequired(){
		$('#finishToolbarAction > .far').addClass('wiggly');
	}

//run logic on startup
	loadHouse();
	mqttRegisterSelf(onConnect, 'onConnect');
	mqttRegisterSelf(onMessage, 'onMessage');
});
