$(function () {

	let code = '';
	let keyboardAuthNotified = false;

	function checkAuth() {
		$.post('/adminAuth/checkAuthState/', function (response) {
			if (response.hasOwnProperty('success') && !response.success) {
				setTimeout(function () {
					checkAuth();
				}, 250);
			} else if (response.hasOwnProperty('username')) {
				$('#username').text(response.username);
				$('#adminAuthKeyboardContainer').slideDown(250);
				setTimeout(function () {
					checkAuth();
				}, 250);
			} else if (response.hasOwnProperty('nextPage')) {
				window.location.replace(response.nextPage);
			}
		})
	}

	$(document).on('keyup', function (e) {
		let $username = $('#username');
		if (e.key == 'Backspace') {
			$username.html($username.html().slice(0, -1));
		} else if (e.key.length === 1) {
			$username.append(e.key);
		}

		$.ajax({
			url: '/adminAuth/login/',
			data: {
				'username': $username.html()
			},
			type: 'POST'
		});
	});

	$('.adminAuthKeyboardKey').not('.erase').not('.backspace').on('click touchstart', function () {
		if (!keyboardAuthNotified) {
			$.post('/adminAuth/keyboardAuth/');
			keyboardAuthNotified = true;
		}

		if (code.length >= 4) {
			return false;
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
						$(this).removeClass('adminAuthDigitFilled');
					});
				}
			});
		}
		return false;
	});

	$('.erase').on('click touchstart', function () {
		code = '';
		$('#codeContainer').children('.adminAuthDisplayDigit').each(function () {
			$(this).removeClass('adminAuthDigitFilled');
		});
	});

	$('.backspace').on('click touchstart', function () {
		code = code.slice(0, -1);
		$('#codeContainer').children('.adminAuthDigitFilled').last().removeClass('adminAuthDigitFilled')
	});

	$('#adminAuthKeyboardContainer').hide();

	setTimeout(function () {
		checkAuth();
	}, 250);
});
