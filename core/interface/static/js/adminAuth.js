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
			else if (response.hasOwnProperty('nextPage')) {
				window.location.replace(response.nextPage);
			}
		})
	}

	$('.adminAuthKeyboardKey').on('click touchstart', function () {
		if (code.length >= 4) {
			return
		}

		let key = $(this).html();
		code = code + key.toString();

		$('#codeContainer').children('.adminAuthDisplayDigit').each(function() {
			if (!$(this).hasClass('adminAuthDigitFilled')) {
				$(this).addClass('adminAuthDigitFilled');
				return false;
			}
		});

		if (code.length === 4) {
			$.post('/adminAuth/authenticate/', {usercode: code}, function (response) {
				if (!response.hasOwnProperty('success') || !response.success) {
					code = '';
					$('#codeContainer').children('.adminAuthDisplayDigit').each(function () {
						$(this).removeClass('adminAuthDigitFilled')
					});
				}
			});
		}
	});

	setTimeout(function () {
		checkAuth();
	}, 1000);
});
