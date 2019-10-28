$(function () {

	let code = '';

	function checkAuth() {
		$.post('/adminAuth/checkAuthState/', function (response) {
			if (response.hasOwnProperty('success') && !response.success) {
				setTimeout(function () {
					checkAuth();
				}, 1000);
			}
			else if (response.hasOwnProperty('username')) {
				$('#username').text(response.username);
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
				url: '/adminAuth/authenticate/',
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
