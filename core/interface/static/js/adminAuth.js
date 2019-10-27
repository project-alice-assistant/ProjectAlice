$(function () {

	let code = '';

	function checkAuth() {
		$.post('/adminAuth/checkAuthState/', function (response) {
			if (!response['success']) {
				location.reload();
			}
			else {
				setTimeout(function () {
					checkAuth();
				}, 1000);
			}
		})
	}

	$('.adminAuthKeyboardKey').on('click touchstart', function () {
		let key = $(this).html();
		code = code + key.toString();

		$('#codeContainer').children('.adminAuthDisplayDigit').each(function() {
			if (!$(this).hasClass('adminAuthDigitFilled')) {
				$(this).addClass('adminAuthDigitFilled');
				return false;
			}
		});

		if (code.length === 4) {
			$.ajax({
				url: '/adminAuth/login',
				type: 'POST',
				data: {
					usercode: code
				}
			});
		}
	});

	setTimeout(function () {
		checkAuth();
	}, 1000);
});
