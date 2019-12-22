$(function () {

	$('.scenariosTile').draggable({
			containment: '#program',
			snap: '.scenariosTile',
			grid: [10, 10]
		}
	);

	$('dd').on('click touchstart', function() {
		let $newDiv = $('<div class="scenariosTile">' + $(this).html()+ '</div>');
		$newDiv.draggable({
				containment: '#program',
				snap: '.scenariosTile',
				grid: [10, 10]
			}
		);
		$('#program').append($newDiv);
	});


	$('.scenariosProgramHolder').droppable({
		drop: function (event, ui) {
			console.log('drop');
		}
	});
});
