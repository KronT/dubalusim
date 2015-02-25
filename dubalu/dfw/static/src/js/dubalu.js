/**
 * Dubalu Framework
 * ~~~~~~~~~~~~~~~~
 *
 * :author: Dubalu Framework Team. See AUTHORS.
 * :copyright: Copyright (c) 2013-2014, deipi.com LLC. All Rights Reserved.
 * :license: See LICENSE for license details.
 *
*/
// temporary fix for focus bug with webkit input type=number ui
if (navigator.userAgent.indexOf("Opera") > -1 && navigator.userAgent.indexOf("Mobile") == -1) {
	var els = document.querySelectorAll('input[type=number]');
	for (var i in els) {
		var el = els[i];
		el.pattern = '\\d*';
		el.type = 'text';
	}
}

/*$.liveSetup('selectpicker', function(event, context, $$) {
	$$('select', context).selectpicker({
		iconBase: 'fa',
		tickIcon: 'fa-ok',
	});
});*/

// Setup the defaults (bootstrap and friend), not running the initializer
// as the plugins themselves have already initialized them.
$.liveSetup('default', function(event, context, $$) {
	/*if ($.fn.carousel) {
		// from bootstrap/carousel.js
		$$('[data-ride="carousel"]', context).each(function() {
			var $carousel = $(this);
			$carousel.carousel($carousel.data());
		});
	}*/

	/*if ($.fn.scrollspy) {
		// from bootstrap/scrollspy.js:
		$$('[data-spy="scroll"]', context).each(function() {
			var $spy = $(this);
			$spy.scrollspy($spy.data());
		});
	}*/

	/*if ($.fn.affix) {
		// from bootstrap/affix.js
		$$('[data-spy="affix"]', context).each(function() {
			var $spy = $(this);
			var data = $spy.data();

			data.offset = data.offset || {};

			if (data.offsetBottom) data.offset.bottom = data.offsetBottom;
			if (data.offsetTop)    data.offset.top    = data.offsetTop;

			$spy.affix(data);
		});
	}*/

	if ($.fn.datepicker) {
		// from bootstrap-datepicker.js
		$$('[data-provide="datepicker-inline"]', context).datepicker();
	}

	/*if ($.execute) {
		$$('[data-provide="execute"]', context).on('click', function(e) {
			e.preventDefault();
			e.stopPropagation();
			var url = $(this).attr('href');
			$.execute(url);
			return false;
		});
	}*/
}, false);


$.liveSetup('autoselect', function(event, context, $$) {
	$$('input:not([disabled], [type=hidden], [type="radio"], [type="checkbox"])', context)
		.on('focus', function() {
			if (!$(this).is(":focus")) {
				$(this).data('focusing', true);
			}
		})
		.on('blur', function() {
			$(this).removeData('focusing');
		})
		.on('click', function() {
			if ($(this).data('focusing')) {
				$(this).removeData('focusing');
				$(this).select().trigger('focus');
			}
		});
});


$.liveSetup('ezdz', function(event, context, $$) {
	$$('.ezdz', context).each(function() {
		var $this = $(this),
			text = $this.data('text'),
			main = $this.data('main-class'),
			accept = $this.data('accept-class'),
			reject = $this.data('reject-class'),
			enter = $this.data('enter-class'),
			focus = $this.data('focus-class'),
			maxSize = $this.data('max-size'),
			maxWidth = $this.data('max-width'),
			maxHeight = $this.data('max-height'),
			minWidth = $this.data('min-width'),
			minHeight = $this.data('min-height'),
			classes = {};

		if (main) classes.main = main;
		if (reject) classes.reject = reject;
		if (enter) classes.enter = enter;
		if (accept) classes.accept = accept;
		if (focus) classes.focus = focus;

		$this.ezdz({
			text: text,
			classes: classes,
			validators: {
				maxSize: maxSize,
				maxWidth: maxWidth,
				maxHeight: maxHeight,
				minWidth: minWidth,
				minHeight: minHeight
			},
			reject: function(file, errors) {
				$(this).trigger('ezdz-rejected-file', [file]);
			},
			accept: function(file){
				$(this).trigger('ezdz-accepted-file', [file]);
			}
		});
	});
});


$.liveSetup('formset', function(event, context, $$) {
	$$('.dynamic_formset a.add-row, .dynamic_formset a.delete-row', context).formset();
});


if (!window.isMobile) {
	$.liveSetup('tooltip', function(event, context, $$) {
		$$('[data-tooltip=tooltip]', context).tooltip({
			html: true,
			container: 'body',
			easein: 'fadeInUp',
			easeout: 'fadeOutUp'
		});
		$$('[data-tooltip=immediate]', context).tooltip({
			html: true,
			container: 'body',
			easein: 'fadeInUp',
			easeout: 'fadeOutUp',
		    delay: {
		      hover: {show: 100, hide: 100},
		      focus: {show: 100, hide: 100, vanish: 2500}
		    }
		});
	});
}


/*
$(function() {
	$('form').each(function() {
		var $this = $(this),
			fields = {};

		$this.find('input:not([disabled], [type=hidden]), select:not([disabled]), textarea:not([disabled])').each(function() {
			var $this = $(this),
				name = $this.attr('name');
			if (name) {
				var validators = $this.data('validators');
				if ($this.closest('.form-group').hasClass('required')) {
					fields[name] = {
						validators: $.extend({
							notEmpty: {},
						}, validators)
					};
				} else if(validators) {
					fields[name] = {
						validators: validators
					};
				}
			}
		});

		$this.bootstrapValidator({
			message: "This value is not valid",
			feedbackIcons: {
				valid: 'fa fa-check',
				invalid: 'fa fa-times',
				validating: 'fa fa-refresh'
			},
			submitButtons: 'button[type="submit"]',
			submitHandler: null,
			live: 'enabled',
			fields: fields
		});
	});
});
*/

$(function() {
	$('#global-announcements div.alert').each(function() {
		var $this = $(this),
			timeout = 10000;
		if ( $this.hasClass('alert-success')) {
			timeout = 10000;
		} else if ($this.hasClass('alert-info')){
			timeout = 15000;
		} else if ($this.hasClass('alert-warning')) {
			timeout = 20000;
		} else if ($this.hasClass('alert-error')) {
			timeout = 30000;
		}
		$(this).delay(timeout).fadeOut(1000);
	});

	window.announce = function(opts) {
		var defaults = {
				status: 'info',
				message: '',
				notification: '',  // if set, send it as desktopNotification (when available)
				announcement_id: 'global-announcements',
				dismissable: true,
				settimer: true,  // remain until closed
				learn_more_url: null,
				undo_link: null,
				add_icon: true,
				force_icon: null,
				timeout: null,
				icon: document.settings && document.settings.notifications.icon || '',
				title: document.settings && document.settings.notifications.title || "Notification"
			},
			o = $.extend({}, defaults, opts);

		var desktopNotification = $.desktopNotification && document.isIdle;

		var message = o.body;
		if (!message) {
			if (o.notification === true) {
				message = o.message;
			} else{
				message = o.notification || o.message;
			}
		}

		if (!message) {
			// ignoring empty messages
			return;
		}

		if ((o.body || o.notification) && desktopNotification) {
			$.desktopNotification.sendNotification(
				o.title,
				{
					icon: o.icon,
					body: message
				}
			);
		}

		if (o.message || (o.body || o.notification) && !desktopNotification) {
			var addIcon = function($alert, icon_class) {
				var $icon = $('<i/>')
						.addClass(icon_class);
				$alert.prepend($icon);
				return $alert;
			};

			var alert_class,
				alert_type_class,
				$announcements = $('#' + o.announcement_id),
				$alert = $('<div/>')
					.addClass($.grep(['alert', o.dismissable && 'alert-dismissable'], Boolean).join(' ')),
				status = o.status.toLowerCase();

			if (o.dismissable) {
				$alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button>');
			}

			$alert.append(message);

			if (status === 'info' || status === 'message') {
				if (o.add_icon)
					$alert = addIcon($alert, o.force_icon || 'fa fa-info-circle');
				alert_class = 'alert-info';
				announcement_class = 'info';
				if (o.settimer && !o.timeout) o.timeout = 15000;
			} else if (status === 'success' || status === 'ok') {
				if (o.add_icon)
					$alert = addIcon($alert, o.force_icon || 'fa fa-check-circle');
				alert_class = 'alert-success';
				announcement_class = 'success';
				if (o.settimer && !o.timeout) o.timeout = 10000;
			} else if (status === 'warning') {
				if (o.add_icon)
					$alert = addIcon($alert, o.force_icon || 'fa fa-warning');
				alert_class = 'alert-warning';
				announcement_class = 'warning';
				if (o.settimer && !o.timeout) o.timeout = 20000;
			} else if (status === 'danger' || status === 'err' || status === 'error') {
				if (o.add_icon)
					$alert = addIcon($alert, o.force_icon || 'fa fa-warning');
				alert_class = 'alert-danger';
				announcement_class = 'danger';
				if (o.settimer && !o.timeout) o.timeout = 30000;
			}
			if (o.learn_more_url) {
				var $anchor = $('<a/>')
								.attr('href', o.learn_more_url)
								.attr('target', '_blank')
								.html(undo_text)
								.attr('style', 'margin-left: 30px;');
				$alert.append($anchor);
			}
			if (o.undo_link) {
				$alert.append(o.undo_link);
			}

			$alert.addClass(alert_class);

			if (o.settimer) {
				$alert.appendTo($('.' + announcement_class, $announcements)).fadeIn(300).delay(o.timeout).fadeOut(1000);
			} else {
				$alert.appendTo($('.' + announcement_class, $announcements)).fadeIn(300);
			}
		}
	};

	window.create_eval_commands = function (default_handler, context) {
		if (!context) {
			context = window;
		}
		if (!default_handler) {
			default_handler = function(arg) {
				console.log('default handler is not defined, arg', arg);
			};
		}

		return function(commands, type) {
			for (var i = 0; i < commands.length; ++i) {
				var cmd = commands[i];
				if (cmd[0] == 'default') {
					default_handler(cmd[1]);
				} else {
					var handler = context[cmd[0]];
					if (handler) {
						handler(cmd[1]);
					} else {
						default_handler(cmd[1]);
					}
				}
			}
		};
	};

	window.eval_commands = window.create_eval_commands();
});


$(function() {
	// Handle double submit and not allowing to close walk away from pages
	// being submitted or which have changed.

	function beforeunload(e) {
		if (window.hasChanged == 'processing') {
			return gettext("Your data is still being processed.");
		}
		if (window.hasChanged) {
			return gettext("Your data has changed and has not yet been saved.");
		}
	}
	$(window).on('beforeunload', beforeunload);

	function startProcessing(hasChanged) {
		window._processingButtons = [];
		window._processingChanged = undefined;
		if (hasChanged === 'processing' || hasChanged === undefined) {
			$('input[type=submit], button[type=submit]').each(function() {
				var $this = $(this),
					button = [$this, $this.hasClass('disabled'), $this.attr('readonly')];
				window._processingButtons.push(button);
				$this.addClass('disabled').attr('readonly', 'readonly');
			});
		}
		window._processingChanged = window.hasChanged;
		window.hasChanged = '';
		setTimeout(function() {
			window.hasChanged = hasChanged;
		}, 300);
	}

	function stopProcessing() {
		if (window._processingButtons !== undefined) {
			for (var i = 0; i < window._processingButtons.length; i++) {
				var button = window._processingButtons[i],
					$this = button[0];
				if (!button[1]) {
					$this.removeClass('disabled');
				}
				if (button[2] === undefined) {
					$this.removeAttr('disabled');
				} else {
					$this.attr('disabled', button[2]);
				}
			}
			window._processingButtons = undefined;
		}

		if (window.hasChanged === 'processing') {
			window.hasChanged = window._processingChanged;
		}
		window._processingChanged = undefined;
	}

	$(document).on('submit', 'form', function(e) {
		var target = $(e.target).attr('target');
		if (!target ||  (target.toLowerCase() !== '_blank' && target.toLowerCase() !== '_new')) {
			startProcessing.apply(this, arguments);
		}
	});

	$.startProcessing = startProcessing;
	$.stopProcessing = stopProcessing;

});
