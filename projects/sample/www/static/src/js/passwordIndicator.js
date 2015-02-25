/**
 * Dubalu Framework
 * ~~~~~~~~~~~~~~~~
 *
 * :author: Dubalu Framework Team. See AUTHORS.
 * :copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
 * :license: See LICENSE for license details.
 *
*/
(function($) {
	/*
		Usage Example:

			$(function() {
				$('.password-strength-input').addPasswordIndicator();
			});

	*/
	'use strict';

	var min_chars = 6,
		precision = 4,
		explanation = [
			interpolate(gettext("<ul><li>Use %s to 20 characters.</li><li>Besides letters, include at least a number or symbol (!@#$%^*-_+=).</li><li>Password is case sensitive.</li><li>Avoid using the same password for multiple sites.</li></ul>"), [min_chars])
		],
		status = [
			gettext("Password doesn't match."),
			interpolate(gettext("Must be at least %s characters."), [min_chars]),
			gettext("That could be better."),
			gettext("That's alright."),
			gettext("That's good."),
			gettext("That's great!")
		],
		css_class = [
			'invalid',
			'invalid',
			'weakest',
			'weak',
			'strong',
			'strongest'
		],
		all_classes = css_class.join(' ');

	$.fn.addPasswordIndicator = function(pair) {
		var $input = this,
			$parent = $input.parent(),
			$pair = $(pair);

		if (!$input.length) return;

		// Async load zxcvbn.js because it is heavy (includes a dictionary)
		// [https://github.com/dropbox/zxcvbn]
		asyncLoadScript('/static/zxcvbn.js');

		var indicator_html = '<span class="password-strength-indicator">';
		for (var i = 0; i < precision; i++) {
			indicator_html += '<span class="incomplete" />';
		}
		indicator_html += '</span>';

		$parent
			.addClass('password-strength')
			.addClass(css_class[0])
			.popover({
				html: true,
				title: function() {
					var strength = $input.data('password-strength');
					return status[strength + 2];
				},
				content: explanation[0],
				placement: 'auto',
				trigger: 'manual'
			});

		var popover = $parent.data('bs.popover');
		popover.tip()
			.addClass('password-strength-popover')
			.addClass(css_class[0])
			.on('click', function() {
				popover.hide();
			});

		function check_password(e, silent) {
			if (e.keyCode && $.inArray(e.keyCode, [27,37,39,38,40,32,13,9,16,17,18,91,93,20]) !== -1) {
				return;
			}

			var $input = $(e.target),
				score = -1,
				password = $input.val();

			// Get score for the input
			var l = window.zxcvbn ? window.zxcvbn(password, []) : {
					score : -1
				},
				$indicators = $input.siblings('.password-strength-indicator').children();
			if (password.length >= min_chars) {
				$indicators
					.removeClass('incomplete')
					.addClass('lit')
					.slice(0, -1 * (l.score + 1))
						.removeClass('lit');
				score = Math.min(precision - 1, l.score);
			} else {
				$indicators
					.removeClass('lit')
					.addClass('incomplete');
				if (password.length) {
					$indicators
						.last()
							.addClass('lit');
				}
				score = -1;
			}

			if (score > 0 && $pair.length && $pair.val().length && $pair.val() != password) {
				score = -2;
			}

			var status_class = css_class[score + 2],
				title = status[score + 2],
				error = score < 1 && password.length;
			$input
				.data('password-strength', score)
				.data('error', error)
				.data('password', password);

			$parent
				.removeClass(all_classes)
				.addClass(status_class);

			if (error) {
				if (!silent) {
					if (!popover.tip().hasClass('in')) {
						popover.show();
					}
				}
			} else {
				popover.hide();
			}

			popover.tip()
				.removeClass(all_classes)
				.addClass(status_class)
				.find('.popover-title')
					.text(title);
		}

		function check_valid(e) {
			check_password({
				keyCode: e.keyCode,
				target: $input
			}, true);
		}

		$pair
			.on('keyup', check_valid)
			.on('change', check_valid);

		$input
			.data('password-strength', -1)
			.on('keyup', check_password)
			.on('change', check_password)
			.on('focus', function(e) {
				check_password({target: $input});
				if ($(e.target).data('error')) {
					if (!popover.tip().hasClass('in')) {
						popover.show();
					}
				}
			})
			.on('blur', function(e) {
				check_password({target: $input});
				if ($(e.target).data('error')) {
					if (!popover.tip().hasClass('in')) {
						popover.show();
					}
				} else {
					popover.hide();
				}
				// Track strength here...
			})
			.before(indicator_html)
			.siblings('.password-strength-indicator')
				.hover(
					function(dataAndEvents) {
						if (!$input.data('error') && !popover.tip().hasClass('in')) {
							popover.show();
						}
					}, function(dataAndEvents) {
						if (!$input.data('error')) {
							popover.hide();
						}
					}
				)
				.end()
			.closest('form')
				.submit(function(e) {
					check_password({target: $input});
					if ($input.data('password-strength') < 1) {
						if (!popover.tip().hasClass('in')) {
							popover.show();
						}
						e.preventDefault();
						$input.focus();
						return false;
					}
				});
		return $input;
	};
})(jQuery);
