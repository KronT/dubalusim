$(function() {
	"use strict";

	$(document).on('lazyloader-processing ajaxify-submit-processing', '.bs-admin[data-provide="lazy-loaded"]', function(e, $loader) {
		if (this != e.target) return;

		var ladda_container = $loader.data('ladda-container'),
			$ladda_container = ladda_container && $(ladda_container) || $loader;
		$ladda_container.ladda('start');
	});

	$(document).on('lazyloader-done ajaxify-submit-done lazyloader-error ajaxify-submit-error', '.bs-admin[data-provide="lazy-loaded"]', function(e, $loader) {
		if (this != e.target) return;

		var ladda_container = $loader.data('ladda-container'),
			$ladda_container = ladda_container && $(ladda_container) || $loader;
		$ladda_container.ladda('stop');
	});

	$(document).on('lazyloader-done', '.bs-admin[data-provide="lazy-loaded"]', function(e, $loader, data) {
		if (this != e.target) return;

		var $elem = $loader.closest('[action]'),
			$target = $($elem.data('target')),
			chevron = $loader.find('.chevron')[0],
			collapse_class = $elem.data('collapse-class');

		if (chevron) {
			if ($target.hasClass(collapse_class)) {
				chevron.className = 'chevron fa fa-fw fa-chevron-right';
			} else {
				chevron.className = 'chevron fa fa-fw fa-chevron-down';
			}
		}
	});

	$(document).on('ajaxify-submit-done ajaxify-submit-error', '.bs-admin[data-provide="lazy-loaded"]', function(e, $submit, data) {
		if (this != e.target) return;

		var $elem = $submit.closest('[action]'),
			$target = $($elem.data('target')),
			$rel = $($elem.attr('rel')),
			chevron = $rel.find('.chevron')[0],
			collapse_class = $elem.data('collapse-class');

		if (data) {
			if (data.reload) {
				$('.admin-table tbody').load(data.reload);
				$('#new-row').fadeOut('fast');
				$(document).off('.addClient');
			} else if (data.info) {
				$.each(data.info, function(cls, val) {
					$rel.find(cls).html(val);
				});
			} else if (data.data) {
				var $html = $(data.data);
				$target.html($html);
				$html.liveSetup();
			}
		}

		if (chevron) {
			if ($target.hasClass(collapse_class)) {
				chevron.className = 'chevron fa fa-fw fa-chevron-right';
			} else {
				chevron.className = 'chevron fa fa-fw fa-chevron-down';
			}
		}
	});

	$('#new-row-container')
		.on('lazyloader-done', function(e) {
			var $target = $(this),
				collapse_class = 'closed',
				$newrow = $('#new-row');

			if (!$target.hasClass(collapse_class)) {
				$newrow.attr('visibility', 'hidden').show();
				$('.wrap').height($('#new-row-container').outerHeight() - 80 + 200);
				$newrow.hide().removeAttr('visibility');

				$newrow.slideToggle(800, 'easeOutBounce', function() {
					// Attach escape and click to close add new row form:
					$(document).on('keydown.newRow', function(e) {
						if (e.keyCode === 27) {
							$target.addClass(collapse_class);
							$newrow.fadeOut('fast');
							$(document).off('.newRow');
						}
					});
					$(document).on('click.newRow', function (e) {
						if($target.find(e.target).length) return;
						$target.addClass(collapse_class);
						$newrow.fadeOut('fast');
						$(document).off('.newRow');
					});
					// Focus on name (first input):
					var $inputs = $('input[type != hidden], textarea, select', $target);
					if ($inputs) {
						$inputs[0].focus();
					}
				});

			} else {
				$newrow.slideToggle(800, 'easeOutBounce');
			}
		});

	$(document).on('click', '.bs-admin[data-provide="ajaxify-delete"], .bs-admin[data-provide="ajaxify-undelete"]', function(e) {
		//if (this != e.target) return;
		e.preventDefault();
		var $this = $(this),
			data_delete = $this.data('delete'),
			data_delete_attr = $this.attr('data-delete');

		$.ajax({
			url: $this.attr('href'),
			type: 'POST',
			success: function(data, textStatus, jqXHR) {
				if (data.message) {
					var undo_url;
					if (data.undo_url) {
						undo_url = '<a href="' + data.undo_url + '" class="bs-admin" data-delete=\'' + data_delete_attr + '\' data-provide="ajaxify-undelete">' + data.undo_message + '</a>';
					}
					announce({
						status: data.status,
						message: data.message,
						settimer: data.settimer,
						undo_link: undo_url
					});
				}
				if (data_delete.onlist) {
					$.each(data_delete.onlist, function(i) {
						var $elem = $(data_delete.onlist[i]);
						$elem.toggleClass('hidden');
					});
				}
			},
			error: function(jqXHR, textStatus, errorThrown) {
				var message = jqXHR.status + ' - ' + (errorThrown || "Connection Error!");
				announce({
					status: 'ERR',
					message: message
				});
			}
		});
	});

	$(document).on('click', '.bs-admin[data-loaded="loaded-detail"]', function(e) {
		if (this != e.target) return;

		e.preventDefault();
		$('.bs-admin[data-provide="lazy-loader"]', this).trigger('click');
	});
});


$(function() {
	"use strict";

	$.endlessPaginate({
		containerSelector: '.endless-loader',
		paginateOnScroll: true,
		paginateOnScrollChunkSize: 2,
		paginateOnScrollMargin : 350
	});
});


$(function() {
	"use strict";

	$.liveSetup('stop-event-propagation', function(event, context, $$) {
		$$('.stop-event-propagation', context).on('click', function(e) {
			e.stopPropagation();
		});
	});
});


$(function() {
	"use strict";

	window.bs_execute = function(url, data, callback, type) {
		// shift arguments if data argument was omitted
		if ($.isFunction(data)) {
			type = type || callback;
			callback = data;
			data = undefined;
		}

		var $currentElem = $(this),
			target = $currentElem.attr('target');

		return $.execute(url, data, function(data) {
			if (data.status === 'OK') {
				var $head = $currentElem.closest('[rel]'),
					$rel = $($head.attr('rel')),
					$target = $rel.find(target).first();
				$target.html(data.data);
				$head
					.addClass('collapse')
					.removeClass('loaded loaded-detail')
					.trigger('ajaxify-submit-done', [$currentElem, data]);
			}
			if (callback && $.isFunction(callback)) {
				callback.apply(this, arguments);
			}
		}, type);
	};
});
